from PySide6.QtCore import QTimer
from PySide6.QtWidgets import *
from app.ui.drawers.base import Drawer
from app.ui.components.common import *

class EndpointDrawer(Drawer):
    def __init__(self,parent,service,id,navigate):
        self.service=service; self.endpoint=service.endpoint(id); self.navigate=navigate; e=self.endpoint
        super().__init__(e.name); self.parent_page=parent
        self.content.addWidget(label('●  Online' if e.online else '●  Offline','success' if e.online else 'error'))
        self.tabs=QTabWidget(); self.content.addWidget(self.tabs)
        overview=QWidget(); ov=QVBoxLayout(overview); ov.setContentsMargins(0,8,0,0)
        device,dl=card('Device details'); form=QFormLayout()
        for key,val in [('OS',e.os),('Agent version',e.agent),('IP address',e.ip),('Last heartbeat',e.last_seen),('Group',e.group)]:form.addRow(key,label(val))
        dl.addLayout(form); ov.addWidget(device)
        assignment,al=card('Policy assignment'); self.policy=QComboBox()
        for p in service.policies:
            if p.published_snapshot:self.policy.addItem(p.published_snapshot['name']+' v'+p.published_snapshot['version'],p.id)
        self.policy.setCurrentIndex(self.policy.findData(e.policy_id)); self.initial=e.policy_id; al.addWidget(self.policy)
        self.sync_status=label(f'Applied: {service.policy(e.applied_policy_id).published_snapshot.get("name",service.policy(e.applied_policy_id).name)} v1.{e.applied_version}','muted',True); al.addWidget(self.sync_status)
        self.sync_button=button('↻  Request policy sync',self.sync); al.addWidget(self.sync_button); ov.addWidget(assignment)
        coverage,cl=card('Channel coverage'); self.coverage_layout=cl; p=service.policy(e.policy_id)
        for channel,action in p.published_snapshot.get('actions',p.actions).items(): cl.addWidget(row(label(channel),None,label(action,'accent')))
        ov.addWidget(coverage); ov.addStretch(); self.tabs.addTab(overview,'Overview')
        incidents=QWidget(); il=QVBoxLayout(incidents)
        items=[i for i in service.incidents if i.endpoint_id==id]
        for i in items:il.addWidget(button(f'{i.id} · {i.channel} · {i.status}',lambda checked=False,iid=i.id:self.jump('Incidents',iid)))
        if not items:il.addWidget(label('No incidents for this endpoint.','muted'))
        il.addStretch(); self.tabs.addTab(incidents,'Incidents')
        activity=QWidget(); ac=QVBoxLayout(activity); self.activity_layout=ac
        for item in e.activity:ac.addWidget(label('• '+item,wrap=True))
        ac.addStretch(); self.tabs.addTab(activity,'Activity')
        self.footer.addWidget(button('Save assignment',self.save,True)); self.footer.addWidget(button('Close',self.request_close))
    def can_close(self):
        if self.policy.currentData()!=self.initial:return QMessageBox.question(self,'Discard assignment?','Discard the unsaved policy assignment?',QMessageBox.Discard|QMessageBox.Cancel,QMessageBox.Cancel)==QMessageBox.Discard
        return True
    def jump(self,page,id):
        if self.can_close():self.navigate(page,id)
    def save(self):
        try:self.service.assign_policy(self.endpoint.id,self.policy.currentData()); self.initial=self.policy.currentData(); self.sync_status.setText('Assignment saved · request sync to apply.'); self.parent_page.status('Policy assignment saved locally.'); self.refresh_coverage(); self.activity_layout.insertWidget(self.activity_layout.count()-1,label('• '+self.endpoint.activity[-1],wrap=True))
        except ValueError as exc:self.sync_status.setText(str(exc))
    def refresh_coverage(self):
        while self.coverage_layout.count()>1:
            item=self.coverage_layout.takeAt(1)
            if item.widget():item.widget().deleteLater()
        p=self.service.policy(self.endpoint.policy_id)
        for channel,action in p.published_snapshot.get('actions',p.actions).items():self.coverage_layout.addWidget(row(label(channel),None,label(action,'accent')))
    def sync(self):
        if self.policy.currentData()!=self.initial:self.sync_status.setText('Save the assignment before requesting sync.'); return
        self.sync_button.setEnabled(False); self.sync_status.setText('Simulating policy sync…')
        def done():
            try:self.service.sync(self.endpoint.id); self.sync_status.setText(f'Simulation complete · applied v1.{self.endpoint.applied_version}'); self.activity_layout.insertWidget(self.activity_layout.count()-1,label('• '+self.endpoint.activity[-1],wrap=True))
            except ValueError as exc:self.sync_status.setText(str(exc))
            self.sync_button.setEnabled(True)
        QTimer.singleShot(650,done)
