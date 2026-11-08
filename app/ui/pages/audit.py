import csv,json
from PySide6.QtWidgets import *
from app.ui.pages.detail_page import DetailPage
from app.ui.components.common import *
from app.ui.drawers.audit import AuditDrawer

class AuditPage(DetailPage):
    def __init__(self,service,navigate):
        super().__init__(service,navigate,'Audit Log','Trace administrative changes and system actions · read only.')
        self.actions.addWidget(button('↓  Export log',self.export))
        self.search=QLineEdit(); self.search.setPlaceholderText('⌕  Search audit log…'); self.actor=combo(['All actors','Ameer Ahmed','System']); self.result=combo(['All results','Success','Failed']); self.action=combo(['All actions']); self.resource=combo(['All resources'])
        self.main_layout.addWidget(self.search); self.main_layout.addWidget(row(self.actor,self.result)); self.main_layout.addWidget(row(self.action,self.resource))
        self.table=table(['Time (Baghdad)','Actor','Action','Result']); self.main_layout.addWidget(self.table,1); self.count=label('','muted'); self.main_layout.addWidget(self.count)
        self.search.textChanged.connect(self.refresh)
        for c in (self.actor,self.result,self.action,self.resource):c.currentIndexChanged.connect(self.refresh)
        self.table.cellClicked.connect(lambda r,c:self.open(self.filtered[r].id)); service.changed.connect(self.refresh); self.refresh()
    def refresh(self):
        for c,values,default in [(self.action,sorted({e.action for e in self.service.audit}),'All actions'),(self.resource,sorted({e.resource for e in self.service.audit}),'All resources')]:
            current=c.currentText(); c.blockSignals(True); c.clear(); c.addItems([default]+values); c.setCurrentText(current if current in values else default); c.blockSignals(False)
        q=self.search.text().casefold()
        self.filtered=[e for e in self.service.audit if q in (e.actor+' '+e.action+' '+e.resource+' '+e.id).casefold() and (not self.actor.currentIndex() or e.actor==self.actor.currentText()) and (not self.result.currentIndex() or e.result==self.result.currentText()) and (not self.action.currentIndex() or e.action==self.action.currentText()) and (not self.resource.currentIndex() or e.resource==self.resource.currentText())]
        populate(self.table,[(e.timestamp[11:19],e.actor,e.action,e.result) for e in self.filtered]); self.count.setText(f'{len(self.filtered)} of {len(self.service.audit)} events' if self.filtered else 'No audit events match these filters.')
    def open(self,id):
        e=next(e for e in self.service.audit if e.id==id); self.set_drawer(AuditDrawer(e),id)
    def export(self):
        path,_=QFileDialog.getSaveFileName(self,'Export filtered audit log','neon-audit.csv','CSV (*.csv)')
        if not path:return
        try:
            with open(path,'w',newline='',encoding='utf-8-sig') as f:
                w=csv.writer(f); w.writerow(['ID','Timestamp','Timezone','Actor','Action','Resource','Result','Before','After'])
                for e in self.filtered:
                    values=[e.id,e.timestamp,'Asia/Baghdad',e.actor,e.action,e.resource,e.result,json.dumps(e.before),json.dumps(e.after)]
                    w.writerow(["'"+v if v.startswith(('=','+','-','@','\t','\r')) else v for v in values])
            self.status(f'Exported {len(self.filtered)} audit events to {path}')
        except OSError as exc:self.status(f'Export failed: {exc}',True)
