"""In-memory simulation. Never contacts endpoints or reads file contents."""
from copy import deepcopy
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from uuid import uuid4
from PySide6.QtCore import QObject, Signal
from app.models.entities import *

class MockService(QObject):
    changed = Signal()
    def __init__(self):
        super().__init__()
        self.reset()

    def reset(self):
        # Empty UI data until the backend API is connected.
        self.rules = []
        self.policies = []
        self.endpoints = []
        self.incidents = []
        self.audit = []
        self.tokens = []
        self.releases = []
        self.deployments = []
        self.settings = {'workspace': 'DLP Workspace', 'server_url': 'http://127.0.0.1:5000',
                         'heartbeat': 60, 'policy_interval': 60, 'email': '',
                         'notifications': False, 'retention': 30, 'role': 'Administrator'}
        self.changed.emit()

    def now(self): return datetime.now(ZoneInfo('Asia/Baghdad'))
    def log(self, action, resource, before=None, after=None, result='Success', actor='Ameer Ahmed'):
        event = AuditEvent(f'AUD-{len(self.audit)+1:04}', self.now().isoformat(timespec='seconds'), actor, action, resource, result, before or {}, after or {})
        self.audit.insert(0, event)
        return event
    def endpoint(self, id): return next(e for e in self.endpoints if e.id == id)
    def policy(self, id): return next(p for p in self.policies if p.id == id)
    def rule(self, id): return next(r for r in self.rules if r.id == id)
    def incident(self, id): return next(i for i in self.incidents if i.id == id)
    def policy_snapshot(self, p):
        return {'name':p.name, 'version':f'1.{p.version}', 'rules':list(p.rule_ids), 'actions':dict(p.actions), 'group':p.group, 'rule_revisions':{id:self.rule(id).revision for id in p.rule_ids}, 'rule_definitions':{id:{'name':self.rule(id).name,'kind':self.rule(id).kind,'expression':self.rule(id).expression,'revision':self.rule(id).revision} for id in p.rule_ids}}
    def save_policy(self, policy, publish=False):
        old = next((p for p in self.policies if p.id == policy.id), None)
        before = self.policy_snapshot(old) if old else {}
        p = deepcopy(policy)
        if publish:
            if old and old.published_snapshot: p.version = old.version + 1
            p.status = 'Published'
            p.published_snapshot = self.policy_snapshot(p)
        else: p.status = 'Draft'
        if old: self.policies[self.policies.index(old)] = p
        else: self.policies.append(p)
        if publish:
            for e in self.endpoints:
                if e.group==p.group:
                    e.policy_id=p.id
                    e.activity.append(f'Published policy {p.name} v1.{p.version} assigned; sync pending')
        self.log('Policy published' if publish else 'Policy draft saved', p.name, before, self.policy_snapshot(p))
        self.changed.emit()
    def save_rule(self, rule):
        old = next((r for r in self.rules if r.id == rule.id), None)
        r = deepcopy(rule)
        before = {'name':old.name, 'revision':old.revision} if old else {}
        if old: r.revision = old.revision + 1; self.rules[self.rules.index(old)] = r
        else: self.rules.append(r)
        r.status = 'Draft'
        self.log('Rule revision saved', r.name, before, {'name':r.name, 'revision':r.revision})
        self.changed.emit()
    def update_incident(self, incident_id, status, note):
        i = self.incident(incident_id)
        before = {'status':i.status, 'note':i.note}
        i.status, i.note = status, note
        i.timeline.append(f'{self.now():%H:%M:%S} Analyst set status to {status}')
        self.log('Incident updated', i.id, before, {'status':status, 'note':note})
        self.changed.emit()
    def assign_policy(self, endpoint_id, policy_id):
        e, p = self.endpoint(endpoint_id), self.policy(policy_id)
        if not p.published_snapshot: raise ValueError('Publish this policy before assignment.')
        old = e.policy_id
        e.policy_id = p.id
        e.activity.append(f'Policy assignment changed to {p.name}; awaiting sync')
        self.log('Policy assigned', e.name, {'policy':old}, {'policy':p.id})
        self.changed.emit()
    def sync(self, endpoint_id):
        e = self.endpoint(endpoint_id)
        if not e.online: raise ValueError('Endpoint is offline. Sync remains pending in this simulation.')
        e.applied_policy_id = e.policy_id
        e.applied_version = self.policy(e.policy_id).published_snapshot['version'].split('.')[1]
        e.applied_version = int(e.applied_version)
        e.activity.append('Mock policy sync completed')
        self.log('Policy synced (simulation)', e.name)
        self.changed.emit()
    def create_token(self, name, group, policy_id, hours, uses):
        if not name.strip(): raise ValueError('Token name is required.')
        token = EnrollmentToken(uuid4().hex[:8], name.strip(), group, policy_id, (self.now()+timedelta(hours=hours)).isoformat(timespec='seconds'), uses)
        self.tokens.append(token)
        self.log('Demo enrollment token created', name)
        self.changed.emit()
        return token, 'DEMO-ONLY-' + uuid4().hex
    def revoke_token(self, id):
        token = next(t for t in self.tokens if t.id == id)
        self.tokens.remove(token)
        self.log('Demo token revoked', token.name)
        self.changed.emit()
    def save_settings(self, values):
        before = dict(self.settings)
        self.settings.update(values)
        self.log('Settings saved', 'Workspace', before, dict(self.settings))
        self.changed.emit()
    def stats(self):
        return {'endpoints':len(self.endpoints), 'online':sum(e.online for e in self.endpoints),
                'blocked':sum(i.action == 'Blocked' for i in self.incidents),
                'open':sum(i.status == 'Open' for i in self.incidents),
                'high':sum(i.status == 'Open' and i.severity == 'High' for i in self.incidents),
                'compliance':round(100*sum(e.applied_policy_id == e.policy_id and e.applied_version == int(self.policy(e.policy_id).published_snapshot.get('version','1.0').split('.')[1]) for e in self.endpoints)/max(1,len(self.endpoints)))}
