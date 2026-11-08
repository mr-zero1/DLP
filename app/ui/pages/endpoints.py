from PySide6.QtWidgets import *
from app.ui.pages.detail_page import DetailPage
from app.ui.components.common import *
from app.ui.drawers.endpoint import EndpointDrawer
from app.ui.dialogs.enrollment import EnrollmentDialog

class EndpointsPage(DetailPage):
    def __init__(self,service,navigate):
        super().__init__(service,navigate,'Endpoints','Manage enrolled Windows devices and policy coverage.')
        self.actions.addWidget(button('↻  Refresh',self.refresh)); self.actions.addWidget(button('+ Add endpoint',lambda:EnrollmentDialog(self,service).exec(),True))
        metrics=QHBoxLayout(); self.metrics=[Metric('Enrolled','5','All registered devices'),Metric('Online','4','Currently active','#00e0ad'),Metric('Offline','1','Not reporting','#ff6b80')]
        for m in self.metrics:metrics.addWidget(m)
        self.main_layout.addLayout(metrics)
        self.status_filter=combo(['All statuses','Online','Offline']); self.group=combo(['All groups','University Lab','Pilot']); self.search=QLineEdit(); self.search.setPlaceholderText('⌕  Find an endpoint…'); self.search.setClearButtonEnabled(True)
        self.main_layout.addWidget(row(self.status_filter,self.group,self.search))
        self.table=table(['Endpoint','Group','Status','Policy','Last seen']); self.main_layout.addWidget(self.table,1)
        self.count=label('','muted'); self.main_layout.addWidget(self.count)
        self.table.cellClicked.connect(lambda r,c:self.open(self.filtered[r].id))
        for c in (self.status_filter,self.group):c.currentIndexChanged.connect(self.refresh)
        self.search.textChanged.connect(self.refresh); service.changed.connect(self.refresh); self.refresh()
    def refresh(self):
        s=self.service; stats=s.stats()
        for m,v in zip(self.metrics,[stats['endpoints'],stats['online'],stats['endpoints']-stats['online']]):m.value.setText(str(v))
        q=self.search.text().casefold(); status=self.status_filter.currentText(); group=self.group.currentText()
        self.filtered=[e for e in s.endpoints if q in (e.name+' '+e.ip).casefold() and (status=='All statuses' or e.online==(status=='Online')) and (group=='All groups' or e.group==group)]
        populate(self.table,[(e.name,e.group,'Online' if e.online else 'Offline',s.policy(e.policy_id).published_snapshot.get('name',s.policy(e.policy_id).name),e.last_seen) for e in self.filtered]); self.count.setText(f'{len(self.filtered)} of {len(s.endpoints)} endpoints' if self.filtered else 'No endpoints match these filters.')
    def open(self,id):
        if self.can_leave():self.set_drawer(EndpointDrawer(self,self.service,id,self.navigate),id)
