from PySide6.QtWidgets import *
from app.ui.dialogs.base import EditDialog
from app.ui.components.common import *

class EnrollmentDialog(EditDialog):
    def __init__(self,parent,service):
        super().__init__(parent,'Create enrollment token','Register a Windows endpoint · DEMO ONLY · no real device enrollment',620)
        self.service=service; self.created=False
        self.form=QFormLayout(); self.form.setVerticalSpacing(15)
        self.name=QLineEdit(); self.name.setPlaceholderText('LAB-PC-06 enrollment')
        self.group=combo(['University Lab','Pilot']); self.policy=QComboBox()
        for p in service.policies:
            if p.published_snapshot:self.policy.addItem(f'{p.published_snapshot["name"]} v{p.published_snapshot["version"]}',p.id)
        self.hours=combo(['1 hour','8 hours','24 hours']); self.uses=QSpinBox(); self.uses.setRange(1,10); self.uses.setValue(1)
        for title,w in [('Token name',self.name),('Assign group',self.group),('Initial policy',self.policy),('Expires after',self.hours),('Maximum uses',self.uses)]: self.form.addRow(title,w)
        self.body_layout.addLayout(self.form)
        self.body_layout.addWidget(label('The demo token is shown once. It cannot enroll a real agent. Enrollment remains pending until a future agent connection.','notice',True))
        self.output=QLineEdit(); self.output.setReadOnly(True); self.output.setPlaceholderText('Token appears here after creation'); self.output.hide()
        self.copy=button('Copy demo token',self.copy_token); self.copy.hide()
        self.body_layout.addWidget(self.output); self.body_layout.addWidget(self.copy); self.body_layout.addStretch()
        self.cancel=button('Cancel',self.reject); self.footer.addWidget(self.cancel); self.footer.addStretch()
        self.create=button('Create demo token',self.create_token,True); self.footer.addWidget(self.create); self.track()
    def create_token(self):
        if not self.name.text().strip(): self.error.setText('Token name is required.'); self.name.setFocus(); return
        if self.policy.currentData() is None: self.error.setText('Publish a policy first.'); return
        _,secret=self.service.create_token(self.name.text(),self.group.currentText(),self.policy.currentData(),[1,8,24][self.hours.currentIndex()],self.uses.value())
        self.error.clear(); self.saved=True; self.created=True; self.create.hide(); self.cancel.setText('Close')
        for w in (self.name,self.group,self.policy,self.hours,self.uses): w.setEnabled(False)
        self.output.setText(secret); self.output.show(); self.copy.show(); self.output.setFocus(); self.output.selectAll()
    def copy_token(self): QApplication.clipboard().setText(self.output.text()); self.copy.setText('Copied · demo token')
