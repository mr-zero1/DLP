from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import *
from app.ui.components.common import *

class Drawer(QFrame):
    closed=Signal()
    def __init__(self,title):
        super().__init__(); self.setObjectName('drawer'); self.setMinimumWidth(330)
        outer=QVBoxLayout(self); outer.setContentsMargins(16,16,16,16)
        self.close_button=button('✕',self.request_close); self.close_button.setAccessibleName('Close details')
        outer.addWidget(row(label(title,'section'),None,self.close_button))
        self.body=QWidget(); self.content=QVBoxLayout(self.body); self.content.setContentsMargins(0,0,0,0); self.content.setSpacing(14)
        outer.addWidget(scroll(self.body),1); self.footer=QVBoxLayout(); outer.addLayout(self.footer)
        shortcut=QShortcut(QKeySequence('Escape'),self); shortcut.setContext(Qt.WidgetWithChildrenShortcut); shortcut.activated.connect(self.request_close)
    def can_close(self):return True
    def request_close(self):
        if self.can_close(): self.closed.emit()
