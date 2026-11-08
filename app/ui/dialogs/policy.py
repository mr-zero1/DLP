from copy import deepcopy
from uuid import uuid4
from PySide6.QtWidgets import *
from app.models.entities import Policy
from app.ui.dialogs.base import EditDialog
from app.ui.components.common import *

class PolicyDialog(EditDialog):
    def __init__(self,parent,service,policy=None):
        super().__init__(parent,'Edit policy' if policy else 'Create policy','Draft changes become active only after simulated publication.',860)
        self.service=service; self.policy=deepcopy(policy) if policy else Policy('P-'+uuid4().hex[:6],'')
        self.step=0
        self.steps=label('1  Basics     ━     2  Rules & scope     ━     3  Review','accent'); self.body_layout.addWidget(self.steps)
        self.stack=QStackedWidget(); self.body_layout.addWidget(self.stack)
        basics=QWidget(); form=QFormLayout(basics); form.setVerticalSpacing(16)
        self.name=QLineEdit(self.policy.name); self.name.setPlaceholderText('e.g. Lab Protection')
        form.addRow('Policy name',self.name); form.addRow(label('Create a versioned policy for your Windows lab.','muted',True)); self.stack.addWidget(basics)
        scope=QWidget(); s=QVBoxLayout(scope)
        rules,rl=card('Included rules'); self.checks={}
        for r in service.rules:
            check=QCheckBox(f'{r.id}   {r.name}  ·  revision {r.revision}'); check.setChecked(r.id in self.policy.rule_ids); self.checks[r.id]=check; rl.addWidget(check)
        s.addWidget(rules)
        channels,cl=card('Channel actions'); cf=QFormLayout(); self.actions={}
        for channel,action in self.policy.actions.items():
            c=combo(['Block','Audit','Warn'] if channel!='Email' else ['Not supported'],action); c.setEnabled(channel!='Email'); self.actions[channel]=c; cf.addRow(channel,c)
        cl.addLayout(cf); cl.addWidget(label('Browser upload: pilot simulation. Email: not supported.','muted',True)); s.addWidget(channels)
        self.group=combo(['University Lab','Pilot'],self.policy.group); self.offline=combo(['Use last valid policy','Audit only (simulation)'],self.policy.offline)
        f=QFormLayout(); f.addRow('Endpoint group',self.group); f.addRow('Offline behavior',self.offline); s.addLayout(f); self.stack.addWidget(scope)
        review=QWidget(); rv=QVBoxLayout(review); self.summary=label('',wrap=True); rv.addWidget(self.summary); rv.addStretch(); self.stack.addWidget(review)
        self.footer.addWidget(button('Cancel',self.reject)); self.footer.addStretch()
        self.back=button('Back',self.go_back); self.footer.addWidget(self.back)
        self.footer.addWidget(button('Save draft',lambda:self.save(False)))
        self.next=button('Continue →',self.go_next,True); self.footer.addWidget(self.next)
        self.update_step(); self.track()
    def collect(self):
        p=deepcopy(self.policy); p.name=self.name.text().strip(); p.rule_ids=[id for id,c in self.checks.items() if c.isChecked()]
        p.actions={k:c.currentText() for k,c in self.actions.items()}; p.group=self.group.currentText(); p.offline=self.offline.currentText(); return p
    def valid(self,p,publish=False):
        if not p.name: self.error.setText('Policy name is required.'); self.name.setFocus(); return False
        if any(x.name.casefold()==p.name.casefold() and x.id!=p.id for x in self.service.policies): self.error.setText('Choose a unique policy name.'); return False
        if publish and not p.rule_ids: self.error.setText('Select at least one rule before publication.'); return False
        self.error.clear(); return True
    def update_step(self):
        self.stack.setCurrentIndex(self.step); self.back.setEnabled(self.step>0)
        self.next.setText('Publish simulation' if self.step==2 else ('Review changes →' if self.step==1 else 'Continue →'))
        if self.step==2:
            p=self.collect(); count=sum(e.group==p.group for e in self.service.endpoints)
            self.summary.setText(f'{p.name}\n\nGroup: {p.group} · {count} endpoints\nRules: '+', '.join(self.service.rule(id).name for id in p.rule_ids)+'\n\n'+'\n'.join(f'{k}: {v}' for k,v in p.actions.items())+'\n\nOffline: '+p.offline+'\n\nPublication updates the mock policy version and assigns it to the selected group. Agents apply it only after simulated sync. Saved rule revisions do not change earlier policy snapshots.')
    def go_next(self):
        if not self.valid(self.collect(),self.step>0): return
        if self.step==2: self.save(True)
        else: self.step+=1; self.update_step()
    def go_back(self): self.step=max(0,self.step-1); self.update_step()
    def save(self,publish):
        p=self.collect()
        if not self.valid(p,publish): return
        self.service.save_policy(p,publish); self.finish()
