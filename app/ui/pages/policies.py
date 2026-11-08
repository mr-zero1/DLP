from PySide6.QtWidgets import *
from app.ui.components.common import *
from app.ui.dialogs.policy import PolicyDialog

class PoliciesPage(Page):
    def __init__(self,service,navigate):
        super().__init__(service,navigate,'Policies','Define protection scope and publish versioned policies.')
        self.actions.addWidget(button('+  Create policy',lambda:self.edit(),True)); self.search=QLineEdit(); self.search.setPlaceholderText('⌕  Find a policy…'); self.filter=combo(['All statuses','Published','Draft'])
        self.layout.addWidget(row(self.search,self.filter)); self.list=QWidget(); self.cards=QVBoxLayout(self.list); self.cards.setContentsMargins(0,0,0,0); self.layout.addWidget(scroll(self.list),1)
        self.search.textChanged.connect(self.refresh); self.filter.currentIndexChanged.connect(self.refresh); service.changed.connect(self.refresh); self.refresh()
    def refresh(self):
        clear_layout(self.cards); count=0
        for p in self.service.policies:
            if self.search.text().casefold() not in p.name.casefold() or (self.filter.currentIndex() and p.status!=self.filter.currentText()):continue
            count+=1; f,l=card(); l.addWidget(row(label(p.name,'section'),None,button('Edit policy →',lambda checked=False,id=p.id:self.edit(id))))
            assigned=[e for e in self.service.endpoints if e.policy_id==p.id]; applied=sum(e.applied_policy_id==p.id and e.applied_version==p.version for e in assigned)
            l.addWidget(row(label(f'● {p.status}  ·  v1.{p.version}','accent'),None,label(f'{len(p.rule_ids)} rules  ·  {len(assigned)} assigned  ·  {applied} applied','muted')))
            l.addWidget(label('Group: '+p.group+'  ·  '+('Published snapshot remains active while edits are in draft.' if p.published_snapshot else 'Not published yet.'),'muted',True)); self.cards.addWidget(f)
        if not count:self.cards.addWidget(label('No policies match these filters.','muted'))
        self.cards.addStretch()
    def edit(self,id=None):
        PolicyDialog(self,self.service,self.service.policy(id) if id else None).exec()
    def open(self,id):self.edit(id)
