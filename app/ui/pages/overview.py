from PySide6.QtWidgets import *
from app.ui.components.common import *

class OverviewPage(Page):
    def __init__(self,service,navigate):
        super().__init__(service,navigate,'Security Overview','Monitor endpoints. Enforce policies. Protect sensitive data.')
        self.actions.addWidget(button('↻  Refresh',self.refresh)); self.actions.addWidget(button('+  Add endpoint',self.enroll,True))
        self.body=QWidget(); self.content=QVBoxLayout(self.body); self.content.setContentsMargins(0,0,0,0); self.content.setSpacing(14); self.layout.addWidget(scroll(self.body),1)
        service.changed.connect(self.refresh); self.refresh()
    def enroll(self):
        from app.ui.dialogs.enrollment import EnrollmentDialog
        EnrollmentDialog(self,self.service).exec()
    def refresh(self):
        clear_layout(self.content); s=self.service; stats=s.stats()
        banner=SentinelBanner(); bl=QVBoxLayout(banner); bl.setContentsMargins(20,16,20,16)
        title=label('Your lab, under control.','section'); title.setStyleSheet('font-size:22px; font-weight:700; color:#f3f5ff'); bl.addWidget(title)
        bl.addWidget(label('Central policy management · Local enforcement'))
        bl.addWidget(label('●  Mock service ready  /  Secure people · ideas · tomorrow','success'))
        self.content.addWidget(banner)
        metrics=QHBoxLayout()
        for title,value,detail,color in [('Managed endpoints',stats['endpoints'],f'{stats["online"]} online · {stats["endpoints"]-stats["online"]} offline','#00dbea'),('Blocked transfers',stats['blocked'],'Across demo channels','#ff7486'),('Open incidents',stats['open'],f'{stats["high"]} high severity','#ffc84d'),('Policy compliance',f'{stats["compliance"]}%','Applied published version','#00ddaf')]:metrics.addWidget(Metric(title,str(value),detail,color))
        self.content.addLayout(metrics)
        mid=QHBoxLayout(); activity,al=card('Incident activity'); al.addWidget(label('Today ·  ● Blocked (cyan)    ● Detected / warned (purple)','muted',True)); al.addWidget(ActivityChart(s)); mid.addWidget(activity,3)
        channels,cl=card('Channels')
        for channel,capability in [('USB','Enforced'),('Clipboard','Audit'),('Browser upload','Pilot'),('Email','Planned')]:
            count=sum(i.channel==channel for i in s.incidents); cl.addWidget(row(label(channel),None,label(str(count),'accent'),label(capability,'muted')))
            progress=QProgressBar(); progress.setRange(0,max(1,len(s.incidents))); progress.setValue(count); progress.setTextVisible(False); cl.addWidget(progress)
        mid.addWidget(channels,2); self.content.addLayout(mid)
        bottom=QHBoxLayout(); recent,rl=card(); rl.addWidget(row(label('Recent incidents','section'),None,button('View all →',lambda:self.navigate('Incidents'))))
        t=table(['Time','Endpoint','Channel','Action']); items=s.incidents[:5]
        populate(t,[(i.time,s.endpoint(i.endpoint_id).name,i.channel,i.action) for i in items]); t.cellClicked.connect(lambda r,c:self.navigate('Incidents',items[r].id)); rl.addWidget(t); bottom.addWidget(recent,3)
        fleet,fl=card('Fleet status')
        for e in s.endpoints:fl.addWidget(button(f'▣   {e.name}      {"● Online" if e.online else "○ Offline"}',lambda checked=False,id=e.id:self.navigate('Endpoints',id)))
        fl.addWidget(button('Manage policies →',lambda:self.navigate('Policies'))); bottom.addWidget(fleet,2); self.content.addLayout(bottom)
        self.content.addWidget(label('Prototype workspace · Shared synthetic data · No endpoint connection','muted'))
