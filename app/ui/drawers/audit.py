import json
from PySide6.QtWidgets import *
from app.ui.drawers.base import Drawer
from app.ui.components.common import *

class AuditDrawer(Drawer):
    def __init__(self,event):
        super().__init__('Audit event  '+event.id)
        self.content.addWidget(label('READ ONLY · Asia/Baghdad','notice'))
        details,dl=card('Event details'); f=QFormLayout()
        for key,val in [('Actor',event.actor),('Action',event.action),('Timestamp',event.timestamp),('Source','Local mock service'),('Result',event.result),('Resource',event.resource)]:f.addRow(key,label(val,wrap=True))
        dl.addLayout(f); self.content.addWidget(details)
        changes,cl=card('Changes')
        for title,data in [('Before',event.before),('After',event.after)]:
            cl.addWidget(label(title,'accent')); text=QPlainTextEdit(json.dumps(data,indent=2,ensure_ascii=False)); text.setReadOnly(True); text.setMaximumHeight(140); cl.addWidget(text)
        self.content.addWidget(changes); self.content.addStretch()
        self.footer.addWidget(button('Copy event ID',lambda:QApplication.clipboard().setText(event.id))); self.footer.addWidget(button('Close',self.request_close))
