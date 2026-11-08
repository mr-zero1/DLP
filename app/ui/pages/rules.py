from PySide6.QtWidgets import *
from app.ui.components.common import *
from app.ui.dialogs.rule import RuleDialog

class RulesPage(Page):
    def __init__(self,service,navigate):
        super().__init__(service,navigate,'Rules Library','Build reusable sensitive-data detector definitions.')
        self.actions.addWidget(button('+  Create rule',lambda:self.edit(),True)); self.kind=combo(['All types','Keywords','Regex','Validated pattern']); self.filter=combo(['All statuses','Published','Draft']); self.search=QLineEdit(); self.search.setPlaceholderText('⌕  Find a rule…')
        self.layout.addWidget(row(self.search,self.kind,self.filter)); self.list=QWidget(); self.grid=QGridLayout(self.list); self.grid.setContentsMargins(0,0,0,0); self.grid.setSpacing(16); self.layout.addWidget(scroll(self.list),1)
        self.search.textChanged.connect(self.refresh); self.kind.currentIndexChanged.connect(self.refresh); self.filter.currentIndexChanged.connect(self.refresh); service.changed.connect(self.refresh); self.refresh()
    def refresh(self):
        clear_layout(self.grid); count=0
        for r in self.service.rules:
            if self.search.text().casefold() not in (r.name+' '+r.id).casefold() or (self.kind.currentIndex() and r.kind!=self.kind.currentText()) or (self.filter.currentIndex() and r.status!=self.filter.currentText()):continue
            f,l=card(r.name); l.addWidget(label(r.id+f'  ·  Revision {r.revision}','muted')); l.addWidget(label(r.expression,wrap=True)); l.addWidget(label(f'{r.kind}  ·  {r.severity}','accent')); l.addWidget(label('● '+r.status,'success' if r.status=='Published' else 'muted')); l.addWidget(button('Edit rule →',lambda checked=False,id=r.id:self.edit(id)))
            self.grid.addWidget(f,count//2,count%2); count+=1
        if not count:self.grid.addWidget(label('No rules match these filters.','muted'),0,0)
        self.grid.setRowStretch(count//2+1,1)
    def edit(self,id=None):RuleDialog(self,self.service,self.service.rule(id) if id else None,self.navigate).exec()
    def open(self,id):self.edit(id)
