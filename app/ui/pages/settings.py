from urllib.parse import urlparse
from PySide6.QtWidgets import *
from app.ui.components.common import *
from app.ui.dialogs.enrollment import EnrollmentDialog

class SettingsPage(Page):
    def __init__(self,service,navigate,reset):
        super().__init__(service,navigate,'Settings','Configure workspace, access and endpoint enrollment · local forms.')
        self.reset_callback=reset; self.dirty=False; self.loading=False
        self.tabs=QTabWidget(); self.layout.addWidget(self.tabs,1)
        self.fields={}
        for title in ['General','Access & roles','Enrollment','Notifications','Retention']:
            w=QWidget(); lay=QVBoxLayout(w); lay.setContentsMargins(0,14,0,0); self.tabs.addTab(scroll(w),title)
            if title=='Enrollment':
                f,l=card('Endpoint enrollment'); l.addWidget(row(label('Short-lived demo tokens for Windows agents.','muted',True),None,button('+ Create token',lambda:EnrollmentDialog(self,service).exec(),True)))
                self.token_table=table(['Token name','Group','Uses','Expires (Baghdad)']); self.token_table.setMinimumHeight(180); l.addWidget(self.token_table)
                l.addWidget(button('Revoke selected demo token',self.revoke)); lay.addWidget(f)
                conn,cl=card('Connection settings'); self.connection=label('',wrap=True); cl.addWidget(self.connection); lay.addWidget(conn); lay.addStretch(); continue
            f,l=card(title); form=QFormLayout(); form.setVerticalSpacing(18)
            if title=='General':
                self.fields['workspace']=QLineEdit(); self.fields['server_url']=QLineEdit()
                for key in ['heartbeat','policy_interval']:
                    self.fields[key]=QSpinBox(); self.fields[key].setRange(10,3600); self.fields[key].setSuffix(' seconds')
                names={'workspace':'Workspace name','server_url':'Future server URL','heartbeat':'Heartbeat interval','policy_interval':'Policy check interval'}
                for k,n in names.items():form.addRow(n,self.fields[k])
            elif title=='Access & roles':
                self.fields['role']=combo(['Administrator','Analyst','Viewer']); form.addRow('Demo display role',self.fields['role']); form.addRow('Current user',label('Ameer Ahmed'))
                l.addWidget(label('Role selection is a UI preference. It does not provide authentication or authorization.','notice',True))
            elif title=='Notifications':
                self.fields['email']=QLineEdit(); self.fields['notifications']=QCheckBox('Enable demo incident notifications'); form.addRow('Notification email',self.fields['email']); form.addRow('',self.fields['notifications'])
                l.addWidget(label('No emails or external notifications are sent.','muted',True))
            elif title=='Retention':
                self.fields['retention']=QSpinBox(); self.fields['retention'].setRange(1,365); self.fields['retention'].setSuffix(' days'); form.addRow('Retention preference',self.fields['retention']); l.addWidget(label('Local preference only. Demo records are not deleted automatically.','muted',True))
            l.addLayout(form); lay.addWidget(f); lay.addStretch()
        self.error=label('','error',True); self.layout.addWidget(self.error)
        self.layout.addWidget(row(button('Reset demo data',self.reset_data),None,button('Discard form changes',self.discard),button('Save local settings',self.save,True)))
        for w in self.fields.values():
            if isinstance(w,QLineEdit):w.textChanged.connect(self.mark_dirty)
            elif isinstance(w,QSpinBox):w.valueChanged.connect(self.mark_dirty)
            elif isinstance(w,QComboBox):w.currentIndexChanged.connect(self.mark_dirty)
            else:w.toggled.connect(self.mark_dirty)
        service.changed.connect(self.refresh); self.load(); self.refresh()
    def mark_dirty(self,*_):
        if not self.loading:self.dirty=True
    def can_leave(self):
        if not self.dirty:return True
        if QMessageBox.question(self,'Discard settings?','Discard unsaved settings?',QMessageBox.Discard|QMessageBox.Cancel,QMessageBox.Cancel)==QMessageBox.Discard:self.load(); return True
        return False
    def discard(self):
        if self.can_leave():self.load()
    def load(self):
        self.loading=True
        for k,w in self.fields.items():
            value=self.service.settings[k]
            if isinstance(w,QLineEdit):w.setText(value)
            elif isinstance(w,QSpinBox):w.setValue(value)
            elif isinstance(w,QComboBox):w.setCurrentText(value)
            else:w.setChecked(value)
        self.loading=False; self.dirty=False; self.error.clear()
    def refresh(self):
        populate(self.token_table,[(t.name,t.group,f'{t.uses}/{t.maximum_uses}',t.expires_at) for t in self.service.tokens])
        s=self.service.settings; self.connection.setText(f'Server URL: {s["server_url"]}\nTransport: HTTPS (future connection)\nHeartbeat: {s["heartbeat"]} seconds\nPolicy check: {s["policy_interval"]} seconds\n\nNo server is connected.')
    def save(self):
        values={}
        for k,w in self.fields.items():
            values[k]=w.text().strip() if isinstance(w,QLineEdit) else w.value() if isinstance(w,QSpinBox) else w.currentText() if isinstance(w,QComboBox) else w.isChecked()
        if not values['workspace']:self.error.setText('Workspace name is required.'); self.fields['workspace'].setFocus(); return
        url=urlparse(values['server_url'])
        if url.scheme!='https' or not url.hostname:self.error.setText('Server URL must be a valid HTTPS URL.'); self.fields['server_url'].setFocus(); return
        import re
        if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',values['email']):self.error.setText('Enter a valid notification email.'); self.fields['email'].setFocus(); return
        self.service.save_settings(values); self.dirty=False; self.error.clear(); self.status('Local settings saved for this session.')
    def revoke(self):
        r=self.token_table.currentRow()
        if r<0:self.error.setText('Select a demo token to revoke.'); return
        t=self.service.tokens[r]
        if QMessageBox.question(self,'Revoke token?',f'Revoke {t.name}?',QMessageBox.Yes|QMessageBox.Cancel,QMessageBox.Cancel)==QMessageBox.Yes:self.service.revoke_token(t.id); self.error.clear()
    def reset_data(self):self.reset_callback()
