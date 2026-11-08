from PySide6.QtWidgets import *
from app.ui.drawers.base import Drawer
from app.ui.components.common import *

class IncidentDrawer(Drawer):
    def __init__(self,parent,service,id,navigate):
        self.service=service; self.incident=service.incident(id); self.navigate=navigate; self.parent_page=parent
        i=self.incident; super().__init__(i.id+'  ·  '+i.severity)
        self.content.addWidget(label(f'Sensitive {i.channel} activity · {i.action}',wrap=True))
        self.tabs=QTabWidget(); self.content.addWidget(self.tabs)
        details=QWidget(); l=QVBoxLayout(details); l.setContentsMargins(0,8,0,0)
        detail,dl=card('Details'); form=QFormLayout(); e=service.endpoint(i.endpoint_id); p=service.policy(e.policy_id)
        form.addRow('Endpoint',button(e.name,lambda:self.jump('Endpoints',e.id)))
        form.addRow('Policy',button(p.name,lambda:self.jump('Policies',p.id)))
        form.addRow('Rule',button(service.rule(i.rule_id).name,lambda:self.jump('Rules Library',i.rule_id)))
        form.addRow('Channel',label(i.channel)); form.addRow('Action',label(i.action)); self.status=combo(['Open','In review','Resolved'],i.status); form.addRow('Case status',self.status)
        dl.addLayout(form); l.addWidget(detail)
        evidence,el=card('Evidence — masked')
        el.addWidget(label(f'{i.filename}\n\nDestination: '+('Removable drive E:' if i.channel=='USB' else 'Demo channel destination')+'\nMatches: 2 (synthetic)\nSensitive value: **** **** **** 4242',wrap=True))
        el.addWidget(label('Raw file content is not uploaded. All evidence is synthetic.','muted',True)); l.addWidget(evidence)
        l.addWidget(label('Analyst note','section')); self.note=QPlainTextEdit(i.note); self.note.setPlaceholderText('Add investigation notes…'); self.note.setMaximumHeight(110); l.addWidget(self.note)
        l.addStretch(); self.tabs.addTab(details,'Details')
        timeline=QWidget(); tl=QVBoxLayout(timeline); self.timeline_layout=tl
        for entry in i.timeline:tl.addWidget(label('●  '+entry,wrap=True))
        tl.addStretch(); self.tabs.addTab(timeline,'Timeline')
        self.initial=(i.status,i.note)
        self.footer.addWidget(label('Resolution changes case status only.','muted',True))
        self.footer.addWidget(row(button('Save note / status',self.save),button('Mark in review',lambda:self.save('In review'))))
        self.footer.addWidget(button('Resolve incident',lambda:self.save('Resolved'),True))
    def can_close(self):
        if (self.status.currentText(),self.note.toPlainText())!=self.initial:return QMessageBox.question(self,'Discard changes?','Discard unsaved investigation changes?',QMessageBox.Discard|QMessageBox.Cancel,QMessageBox.Cancel)==QMessageBox.Discard
        return True
    def jump(self,page,id):
        if self.can_close():self.navigate(page,id)
    def save(self,status=None):
        if not isinstance(status,str):status=self.status.currentText()
        self.service.update_incident(self.incident.id,status,self.note.toPlainText()); self.status.setCurrentText(status); self.initial=(status,self.note.toPlainText()); self.parent_page.status('Incident case and note saved locally.'); self.timeline_layout.insertWidget(self.timeline_layout.count()-1,label('●  '+self.incident.timeline[-1],wrap=True))
