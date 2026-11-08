from pathlib import Path
from PySide6.QtWidgets import *
from app.models.entities import Release
from app.ui.components.common import *
from app.ui.dialogs.deploy import DeployDialog

class UpdatesPage(Page):
    def __init__(self,service,navigate,controller):
        super().__init__(service,navigate,'Agent Updates','Distribute Windows agent releases in controlled stages · SIMULATION')
        self.controller=controller; self.actions.addWidget(button('+  Select local release',self.select_file,True))
        self.metrics=QHBoxLayout(); self.layout.addLayout(self.metrics)
        releases,rl=card('Available releases'); self.releases=QComboBox(); self.deploy_button=button('Deploy simulation →',self.deploy,True); rl.addWidget(row(self.releases,self.deploy_button)); self.metadata=label('',wrap=True); rl.addWidget(self.metadata); self.layout.addWidget(releases)
        self.table=table(['Deployment','Version','Targets','State','Completed']); self.layout.addWidget(self.table,1)
        self.details=QPlainTextEdit(); self.details.setReadOnly(True); self.details.setMaximumHeight(135); self.details.setPlaceholderText('Select a deployment to inspect per-device simulation results.'); self.layout.addWidget(self.details)
        self.layout.addWidget(label('No package is uploaded, installed or executed. Schedules are session-only; closing the app cancels timers.','notice',True))
        self.releases.currentIndexChanged.connect(self.release_info); self.table.cellClicked.connect(self.show_job); service.changed.connect(self.refresh); self.refresh()
        body=QWidget(); body_layout=QVBoxLayout(body); body_layout.setContentsMargins(0,0,0,0)
        while self.layout.count()>1:
            item=self.layout.takeAt(1)
            if item.widget():body_layout.addWidget(item.widget())
            elif item.layout():body_layout.addLayout(item.layout())
        self.layout.addWidget(scroll(body),1)
    def refresh(self):
        s=self.service; clear_layout(self.metrics)
        versions={e.agent for e in s.endpoints}; current=max(versions,key=lambda v:sum(e.agent==v for e in s.endpoints)) if versions else '—'
        for title,v,d in [('Current fleet version',current,'Most common demo agent version'),('Available releases',str(len(s.releases)),'Demo fixtures and local selections'),('Online endpoints',str(sum(e.online for e in s.endpoints)),'Offline devices remain pending')]:self.metrics.addWidget(Metric(title,v,d))
        current_index=self.releases.currentIndex(); self.releases.blockSignals(True); self.releases.clear()
        for r in s.releases:self.releases.addItem(f'v{r.version} · {r.package}')
        self.releases.setCurrentIndex(max(0,min(current_index,len(s.releases)-1))); self.releases.blockSignals(False); self.release_info()
        populate(self.table,[(j['id'],j['version'],len(j['targets']),j['status'],f'{j["completed"]} / {len(j["targets"])}') for j in s.deployments])
        if self.table.currentRow()>=0:self.show_job(self.table.currentRow(),0)
    def release_info(self,*_):
        if self.releases.currentIndex()<0:return
        r=self.service.releases[self.releases.currentIndex()]
        self.metadata.setText(f'{r.size:,} bytes · '+('Demo signature fixture verified' if r.verified else 'Unverified local metadata only')+'\n'+r.notes)
    def select_file(self):
        path,_=QFileDialog.getOpenFileName(self,'Select Windows agent package','','Windows installer (*.msi *.exe);;All files (*)')
        if not path:return
        try:
            file=Path(path); size=file.stat().st_size
            version,ok=QInputDialog.getText(self,'Local release metadata','Version (e.g. 1.2.0):')
            if not ok:return
            import re
            if not re.fullmatch(r'\d+\.\d+\.\d+',version):self.status('Enter a version such as 1.2.0.',True); return
            if any(r.version==version for r in self.service.releases):self.status('That version already exists.',True); return
            self.service.releases.insert(0,Release(version,file.name,size,False,'Local file metadata selected. No upload or verification performed.'))
            self.service.log('Local release selected',file.name,after={'version':version,'bytes':size}); self.service.changed.emit(); self.releases.setCurrentIndex(0)
        except OSError as exc:self.status(f'Cannot read file metadata: {exc}',True)
    def deploy(self):
        if self.releases.currentIndex()>=0:DeployDialog(self,self.service,self.service.releases[self.releases.currentIndex()],self.controller).exec()
    def show_job(self,r,c):
        if r>=len(self.service.deployments):return
        j=self.service.deployments[r]; self.details.setPlainText(j['id']+' · '+j['when']+'\n'+'\n'.join(f'{self.service.endpoint(id).name}: {value}' for id,value in j['results'].items()))
