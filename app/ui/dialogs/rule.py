from copy import deepcopy
from uuid import uuid4
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import *
from app.models.entities import Rule
from app.ui.dialogs.base import EditDialog
from app.ui.components.common import *

class RuleDialog(EditDialog):
    def __init__(self,parent,service,rule=None,navigate=None):
        super().__init__(parent,'Rule editor','Local revision · test results are scripted fixtures, not a detection engine.',830)
        self.service=service; self.rule=deepcopy(rule) if rule else Rule('R-'+uuid4().hex[:6],'','Keywords',''); self.navigate=navigate
        split=QHBoxLayout(); self.body_layout.addLayout(split)
        definition,dl=card('Definition'); form=QFormLayout(); form.setVerticalSpacing(14)
        self.name=QLineEdit(self.rule.name); self.kind=combo(['Keywords','Regex','Validated pattern'],self.rule.kind)
        self.expression=QPlainTextEdit(self.rule.expression); self.expression.setPlaceholderText('Comma-separated keywords, a regex, or a pattern description'); self.expression.setMaximumHeight(110)
        self.case=QCheckBox('Case insensitive'); self.case.setChecked(self.rule.case_insensitive)
        self.mode=combo(['Any keyword','All keywords'],self.rule.match_mode); self.minimum=QSpinBox(); self.minimum.setRange(1,100); self.minimum.setValue(self.rule.minimum)
        self.severity=combo(['Low','Medium','High'],self.rule.severity)
        for key,w in [('Rule name',self.name),('Detector type',self.kind),('Conditions',self.expression),('',self.case),('Match mode',self.mode),('Minimum matches',self.minimum),('Severity',self.severity)]: form.addRow(key,w)
        dl.addLayout(form); split.addWidget(definition,1)
        test,tl=card('Test rule · simulation'); self.sample=QPlainTextEdit('CONFIDENTIAL: internal lab report'); self.sample.setMaximumHeight(160)
        tl.addWidget(label('Synthetic test text (not processed by a detector)','muted',True)); tl.addWidget(self.sample)
        self.fixture=combo(['Match fixture','No match fixture','Error fixture']); tl.addWidget(self.fixture)
        self.run=button('▶  Run simulated test',self.run_test); tl.addWidget(self.run)
        self.result=label('Choose a fixture and run the simulation.','notice',True); tl.addWidget(self.result)
        tl.addWidget(label('Used by policies','section'))
        linked=[p for p in service.policies if self.rule.id in p.rule_ids]
        for p in linked:
            tl.addWidget(button(p.name,lambda checked=False,id=p.id:self.open_policy(id)))
        if not linked: tl.addWidget(label('Not included in a policy yet.','muted',True))
        tl.addStretch(); split.addWidget(test,1)
        self.body_layout.addWidget(label('Saved revisions are drafts. Publish a policy to activate its selected rule revision.','notice',True))
        self.footer.addWidget(button('Cancel',self.reject)); self.footer.addStretch(); self.footer.addWidget(button('Save rule revision',self.save,True)); self.track()
    def open_policy(self,id):
        if self.dirty:
            if QMessageBox.question(self,'Unsaved changes','Discard changes and open the policy?',QMessageBox.Discard|QMessageBox.Cancel,QMessageBox.Cancel)!=QMessageBox.Discard:return
        self.saved=True; self.accept()
        if self.navigate:self.navigate('Policies',id)
    def run_test(self):
        if not self.sample.toPlainText().strip(): self.result.setText('Enter synthetic sample text.'); return
        self.run.setEnabled(False); self.result.setText('Running scripted fixture…'); index=self.fixture.currentIndex()
        def done():
            self.run.setEnabled(True); self.result.setText(['SIMULATION · Match found\n1 synthetic match · ****MASKED****\nNo content analysis was performed.','SIMULATION · No match\n0 synthetic matches.','SIMULATION · Test error\nFixture unavailable. Select another fixture and retry.'][index])
        QTimer.singleShot(350,done)
    def save(self):
        name=self.name.text().strip(); expr=self.expression.toPlainText().strip()
        if not name or not expr: self.error.setText('Rule name and conditions are required.'); return
        if any(r.name.casefold()==name.casefold() and r.id!=self.rule.id for r in self.service.rules): self.error.setText('Choose a unique rule name.'); return
        r=self.rule; r.name=name; r.kind=self.kind.currentText(); r.expression=expr; r.case_insensitive=self.case.isChecked(); r.match_mode=self.mode.currentText(); r.minimum=self.minimum.value(); r.severity=self.severity.currentText()
        self.service.save_rule(r); self.finish()
