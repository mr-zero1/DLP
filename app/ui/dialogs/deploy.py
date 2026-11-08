from PySide6.QtCore import QDateTime
from PySide6.QtWidgets import *
from app.ui.dialogs.base import EditDialog
from app.ui.components.common import *

class DeployDialog(EditDialog):
    def __init__(self,parent,service,release,controller):
        super().__init__(parent,'Deploy release',f'Windows agent v{release.version} · simulation only',760)
        self.service=service; self.release=release; self.controller=controller
        verify,vl=card('Release verification')
        vl.addWidget(label('Demo signature fixture verified' if release.verified else 'Local file selected · signature is NOT verified','success' if release.verified else 'notice',True))
        vl.addWidget(label(f'Package: {release.package}\nSize: {release.size:,} bytes\nPlatform: Windows x64',wrap=True))
        vl.addWidget(label('No package is uploaded or executed. Verification and deployment results are simulated.','muted',True)); self.body_layout.addWidget(verify)
        targets,tl=card('Target endpoints'); self.targets={}
        for e in service.endpoints:
            c=QCheckBox(f'{e.name} · {"Online" if e.online else "Offline — pending"}'); c.setChecked(e.id=='E-001'); self.targets[e.id]=c; tl.addWidget(c)
        self.body_layout.addWidget(targets)
        form=QFormLayout(); self.when=combo(['Start now','Schedule']); self.date=QDateTimeEdit(QDateTime.currentDateTime().addSecs(3600)); self.date.setMaximumDateTime(QDateTime.currentDateTime().addDays(7)); self.date.setCalendarPopup(True); self.date.setDisplayFormat('yyyy-MM-dd HH:mm'); self.date.setEnabled(False)
        self.when.currentIndexChanged.connect(lambda index:self.date.setEnabled(index==1))
        self.stop=QCheckBox('Stop rollout on failure'); self.stop.setChecked(True)
        self.fail=QCheckBox('Simulate installation failure on first online target')
        form.addRow('Deployment',self.when); form.addRow('Scheduled local time',self.date); form.addRow('',self.stop); form.addRow('',self.fail); self.body_layout.addLayout(form)
        self.body_layout.addWidget(label('Previous demo release: 1.0.3\nOffline targets stay pending. A scheduled run remains queued until its time while this app is open.','notice',True))
        self.footer.addWidget(button('Cancel',self.reject)); self.footer.addStretch(); self.footer.addWidget(button('Start simulated deployment →',self.start,True)); self.track()
    def start(self):
        ids=[id for id,c in self.targets.items() if c.isChecked()]
        if not ids: self.error.setText('Select at least one endpoint.'); return
        if self.when.currentIndex() and self.date.dateTime()<=QDateTime.currentDateTime(): self.error.setText('Choose a future schedule time.'); return
        delay=max(0,QDateTime.currentDateTime().msecsTo(self.date.dateTime())) if self.when.currentIndex() else 0
        self.controller.deploy(self.release,ids,delay,self.stop.isChecked(),self.fail.isChecked()); self.finish()
