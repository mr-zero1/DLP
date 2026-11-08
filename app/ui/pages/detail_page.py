from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve
from PySide6.QtWidgets import *
from app.ui.components.common import *

class DetailPage(Page):
    def __init__(self,*args):
        super().__init__(*args); self.drawer=None; self.selected_id=None
        self.splitter=QSplitter(Qt.Horizontal); self.main=QWidget(); self.main_layout=QVBoxLayout(self.main); self.main_layout.setContentsMargins(0,0,0,0); self.main_layout.setSpacing(16)
        self.splitter.addWidget(self.main); self.splitter.setChildrenCollapsible(False); self.layout.addWidget(self.splitter,1)
    def can_leave(self):return self.drawer is None or self.drawer.can_close()
    def close_drawer(self):
        if self.drawer:
            self.drawer.hide(); self.drawer.setParent(None); self.drawer.deleteLater(); self.drawer=None; self.selected_id=None
        if hasattr(self,'table'):self.table.setFocus()
    def set_drawer(self,drawer,id):
        self.close_drawer(); self.drawer=drawer; self.selected_id=id; self.splitter.addWidget(drawer); drawer.closed.connect(self.close_drawer)
        self.splitter.setSizes([650,440]); drawer.close_button.setFocus()
        effect=QGraphicsOpacityEffect(drawer); drawer.setGraphicsEffect(effect)
        drawer.animation=QPropertyAnimation(effect,b'opacity',drawer); drawer.animation.setDuration(150); drawer.animation.setStartValue(.25); drawer.animation.setEndValue(1.0); drawer.animation.setEasingCurve(QEasingCurve.OutCubic); drawer.animation.start()
