import csv
from PySide6.QtWidgets import *
from app.ui.pages.detail_page import DetailPage
from app.ui.components.common import *
from app.ui.drawers.incident import IncidentDrawer

class IncidentsPage(DetailPage):
    def __init__(self,service,navigate):
        super().__init__(service,navigate,'Incidents','Investigate sensitive data activity. Evidence is synthetic and masked.')
        self.actions.addWidget(button('↓  Export CSV',self.export))
        self.tabs=QTabBar(); self.tabs.addTab('Open'); self.tabs.addTab('In review'); self.tabs.addTab('Resolved'); self.main_layout.addWidget(self.tabs)
        self.severity=combo(['All severities','High','Medium','Low']); self.channel=combo(['All channels','USB','Clipboard','Browser upload','Email']); self.endpoint=QComboBox(); self.endpoint.addItem('All endpoints',None)
        for e in service.endpoints:self.endpoint.addItem(e.name,e.id)
        self.search=QLineEdit(); self.search.setPlaceholderText('⌕  Search incidents…'); self.search.setClearButtonEnabled(True)
        self.main_layout.addWidget(row(self.severity,self.channel,self.endpoint)); self.main_layout.addWidget(self.search)
        self.table=table(['ID','Endpoint','Channel','Severity','Status']); self.main_layout.addWidget(self.table,1); self.count=label('','muted'); self.main_layout.addWidget(self.count)
        self.table.cellClicked.connect(lambda r,c:self.open(self.filtered[r].id))
        self.tabs.currentChanged.connect(self.refresh)
        for c in (self.severity,self.channel,self.endpoint):c.currentIndexChanged.connect(self.refresh)
        self.search.textChanged.connect(self.refresh); service.changed.connect(self.refresh); self.refresh()
    def refresh(self):
        s=self.service; states=['Open','In review','Resolved']
        for n,state in enumerate(states):self.tabs.setTabText(n,f'{state}  {sum(i.status==state for i in s.incidents)}')
        q=self.search.text().casefold(); state=states[self.tabs.currentIndex()]
        self.filtered=[i for i in s.incidents if i.status==state and (self.severity.currentIndex()==0 or i.severity==self.severity.currentText()) and (self.channel.currentIndex()==0 or i.channel==self.channel.currentText()) and (not self.endpoint.currentData() or i.endpoint_id==self.endpoint.currentData()) and q in (i.id+' '+s.endpoint(i.endpoint_id).name+' '+s.rule(i.rule_id).name).casefold()]
        populate(self.table,[(i.id,s.endpoint(i.endpoint_id).name,i.channel,i.severity,i.status) for i in self.filtered]); self.count.setText(f'{len(self.filtered)} incidents · export uses the current filters' if self.filtered else 'No incidents match these filters.')
    def open(self,id):
        if self.can_leave():self.set_drawer(IncidentDrawer(self,self.service,id,self.navigate),id)
    def export(self):
        path,_=QFileDialog.getSaveFileName(self,'Export filtered incidents','neon-incidents.csv','CSV (*.csv)')
        if not path:return
        try:
            with open(path,'w',newline='',encoding='utf-8-sig') as f:
                w=csv.writer(f); w.writerow(['ID','Time','Endpoint','Channel','Rule','Severity','Action','Status','Note'])
                for i in self.filtered:
                    values=[i.id,i.time,self.service.endpoint(i.endpoint_id).name,i.channel,self.service.rule(i.rule_id).name,i.severity,i.action,i.status,i.note]
                    w.writerow(["'"+str(v) if str(v).startswith(('=','+','-','@','\t','\r')) else v for v in values])
            self.service.log('Incidents exported','Filtered incidents',after={'rows':len(self.filtered)}); self.service.changed.emit(); self.status(f'Exported {len(self.filtered)} incidents to {path}')
        except OSError as exc:self.status(f'Export failed: {exc}',True)
