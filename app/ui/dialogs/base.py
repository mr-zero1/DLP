from PySide6.QtCore import Qt
from PySide6.QtWidgets import *
from app.ui.components.common import *

class EditDialog(QDialog):
    def __init__(self, parent, title, subtitle='', width=720):
        super().__init__(parent); self.setWindowTitle(title); self.resize(width,620); self.setMinimumWidth(420)
        self.dirty=False; self.saved=False
        outer=QVBoxLayout(self); outer.setContentsMargins(20,18,20,18); outer.setSpacing(14)
        outer.addWidget(label(title,'section'))
        if subtitle: outer.addWidget(label(subtitle,'muted',True))
        self.body=QWidget(); self.body_layout=QVBoxLayout(self.body); self.body_layout.setContentsMargins(0,0,0,0); self.body_layout.setSpacing(14)
        outer.addWidget(scroll(self.body),1)
        self.error=label('','error',True); outer.addWidget(self.error)
        self.footer=QHBoxLayout(); outer.addLayout(self.footer)
    def track(self):
        for w in self.body.findChildren(QWidget):
            for name in ('textChanged','currentIndexChanged','valueChanged','toggled','dateTimeChanged'):
                sig=getattr(w,name,None)
                if sig:
                    sig.connect(self.mark_dirty); break
    def mark_dirty(self,*_): self.dirty=True
    def reject(self):
        if self.dirty and not self.saved:
            if QMessageBox.question(self,'Discard changes?','Discard your unsaved changes?',QMessageBox.Discard|QMessageBox.Cancel,QMessageBox.Cancel)!=QMessageBox.Discard: return
        super().reject()
    def finish(self): self.saved=True; self.accept()
