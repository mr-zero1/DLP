import sys
from pathlib import Path
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QProcess
from PySide6.QtGui import QKeySequence, QShortcut, QIcon, QPainter, QColor, QPixmap, QPen, QPolygonF
from PySide6.QtCore import QPointF
from PySide6.QtWidgets import *
from app.ui.components.common import *
from app.ui.pages.overview import OverviewPage
from app.ui.pages.endpoints import EndpointsPage
from app.ui.pages.incidents import IncidentsPage
from app.ui.pages.policies import PoliciesPage
from app.ui.pages.rules import RulesPage
from app.ui.pages.updates import UpdatesPage
from app.ui.pages.audit import AuditPage
from app.ui.pages.settings import SettingsPage
from app.controllers.deployment import DeploymentController
from app.services.api_client import ApiClient, DEFAULT_API_URL

class MainWindow(QMainWindow):
    def __init__(self,service):
        super().__init__(); self.service=service; self.controller=DeploymentController(service)
        self.setWindowTitle('NEON SENTINEL · DLP Control Center · UI'); self.resize(1366,768); self.setMinimumSize(1000,650)
        self.setWindowIcon(self.shield_icon())
        shell=QWidget(); shell.setObjectName('shell'); self.setCentralWidget(shell); root=QHBoxLayout(shell); root.setContentsMargins(0,0,0,0); root.setSpacing(0)
        sidebar=QFrame(); sidebar.setObjectName('sidebar'); sidebar.setFixedWidth(232); side=QVBoxLayout(sidebar); side.setContentsMargins(14,20,14,18); side.setSpacing(5)
        logo=QLabel(); logo.setPixmap(self.windowIcon().pixmap(34,40)); brand=label('NEON SENTINEL','brand'); brand.setStyleSheet('font-size:15px; font-weight:700; color:#00e6f3'); side.addWidget(row(logo,brand))
        side.addWidget(label('       DLP CONTROL CENTER','muted')); side.addSpacing(22); side.addWidget(label('WORKSPACE','muted')); self.workspace=label('⌂  DLP Workspace','section'); side.addWidget(self.workspace); side.addSpacing(16)
        self.nav={}; self.stack=QStackedWidget()
        names=['Overview','Endpoints','Incidents','Policies','Rules Library','Agent Updates','Audit Log','Settings']; glyphs=['⌂','▣','△','▤','◫','↻','▥','⚙']
        for name,glyph in zip(names,glyphs):
            if name=='Settings':side.addStretch()
            b=button(f'{glyph}    {name}',lambda checked=False,n=name:self.navigate(n)); b.setObjectName('nav'); b.setCheckable(True); self.nav[name]=b; side.addWidget(b)
        side.addSpacing(16); side.addWidget(label('Administrator','section')); side.addWidget(label('UI preview · MockService active','muted',True)); root.addWidget(sidebar)
        main=QVBoxLayout(); main.setContentsMargins(0,0,0,0); main.setSpacing(0); root.addLayout(main,1)
        top=QFrame(); top.setObjectName('topbar'); tl=QHBoxLayout(top); tl.setContentsMargins(22,12,22,12)
        self.breadcrumb=label('Workspace  /  Overview','accent'); tl.addWidget(self.breadcrumb); tl.addStretch()
        self.search=QLineEdit(); self.search.setPlaceholderText('⌕  Search devices, incidents, rules…'); self.search.setMaximumWidth(350); self.search.setMinimumWidth(230); self.search.returnPressed.connect(self.global_search); tl.addWidget(self.search)
        tl.addWidget(button('⌕',self.global_search)); tl.addWidget(button('UI ONLY',self.demo_info)); main.addWidget(top)
        main.addWidget(self.stack,1)
        self.pages={'Overview':OverviewPage(service,self.navigate),'Endpoints':EndpointsPage(service,self.navigate),'Incidents':IncidentsPage(service,self.navigate),'Policies':PoliciesPage(service,self.navigate),'Rules Library':RulesPage(service,self.navigate),'Agent Updates':UpdatesPage(service,self.navigate,self.controller),'Audit Log':AuditPage(service,self.navigate),'Settings':SettingsPage(service,self.navigate,self.reset)}
        for p in self.pages.values():self.stack.addWidget(p)
        self.status_label=label('Checking backend…','muted'); self.statusBar().addWidget(self.status_label,1)
        self.api_client=ApiClient(self); self.api_client.health_check_completed.connect(self._update_backend_status)
        self.backend_process=QProcess(self)
        self._stopping_backend=False
        self.backend_process.setProgram(sys.executable)
        self.backend_process.setArguments(['-m','backend.main'])
        self.backend_process.setWorkingDirectory(str(Path(__file__).resolve().parents[2]))
        self.backend_process.setProcessChannelMode(QProcess.MergedChannels)
        self.backend_process.readyReadStandardOutput.connect(self._read_backend_output)
        self.backend_process.errorOccurred.connect(self._backend_process_error)
        self.backend_process.finished.connect(self._backend_process_finished)
        self.backend_process.started.connect(lambda: QTimer.singleShot(500,self.api_client.check_health))
        self.health_check_timer=QTimer(self); self.health_check_timer.setInterval(10000); self.health_check_timer.timeout.connect(self.api_client.check_health); self.health_check_timer.start()
        self.api_client.check_health()
        self.current='Overview'; self.nav['Overview'].setChecked(True)
        QShortcut(QKeySequence('Ctrl+K'),self,activated=lambda:self.search.setFocus())
        QShortcut(QKeySequence('Ctrl+R'),self,activated=self.refresh)
        service.changed.connect(lambda:self.workspace.setText('⌂  '+service.settings['workspace']))
    def _update_backend_status(self,connected):
        self.status_label.setText('Backend Connected' if connected else 'Backend Disconnected')
        self.status_label.setObjectName('success' if connected else 'error')
        self.status_label.style().unpolish(self.status_label); self.status_label.style().polish(self.status_label)
        if not connected and self.api_client.base_url == DEFAULT_API_URL and self.backend_process.state() == QProcess.NotRunning:
            print(f'Starting backend with {sys.executable} -m backend.main', file=sys.stderr, flush=True)
            self.backend_process.start()
    def _read_backend_output(self):
        output=bytes(self.backend_process.readAllStandardOutput()).decode('utf-8',errors='replace')
        sys.stderr.write(output); sys.stderr.flush()
    def _backend_process_error(self,error):
        if error == QProcess.FailedToStart:
            print(f'Backend failed to start: {self.backend_process.errorString()}',file=sys.stderr,flush=True)
    def _backend_process_finished(self,exit_code,exit_status):
        if not self._stopping_backend and (exit_status == QProcess.CrashExit or exit_code):
            print(f'Backend exited unexpectedly (code {exit_code}): {self.backend_process.errorString()}',file=sys.stderr,flush=True)
    def stop_backend(self):
        if self.backend_process.state() == QProcess.NotRunning:
            return
        self._stopping_backend=True
        self.backend_process.terminate()
        if not self.backend_process.waitForFinished(3000):
            self.backend_process.kill()
            if not self.backend_process.waitForFinished(1000):
                print('Backend process did not stop after terminate/kill.',file=sys.stderr,flush=True)
    def shield_icon(self):
        pix=QPixmap(64,64); pix.fill(Qt.transparent); p=QPainter(pix); p.setRenderHint(QPainter.Antialiasing)
        points=[QPointF(32,4),QPointF(55,14),QPointF(51,39),QPointF(32,59),QPointF(13,39),QPointF(9,14)]
        p.setPen(QPen(QColor('#00ddee'),3)); p.setBrush(QColor('#0c2e44')); p.drawPolygon(QPolygonF(points)); p.drawLine(20,19,44,40); p.drawLine(44,19,20,40); p.end(); return QIcon(pix)
    def navigate(self,name,id=None):
        old=self.pages[self.current]
        if (name!=self.current or id) and hasattr(old,'can_leave') and not old.can_leave():return False
        if (name!=self.current or id) and hasattr(old,'close_drawer'):old.close_drawer()
        self.current=name; self.stack.setCurrentWidget(self.pages[name]); self.breadcrumb.setText('Workspace  /  '+name)
        for n,b in self.nav.items():b.setChecked(n==name)
        if id and hasattr(self.pages[name],'open'):self.pages[name].open(id)
        return True
    def show_status(self,text,error=False):
        self.status_label.setText(text); self.status_label.setObjectName('error' if error else 'success'); self.status_label.style().unpolish(self.status_label); self.status_label.style().polish(self.status_label)
    def refresh(self):
        p=self.pages[self.current]
        if hasattr(p,'refresh'):p.refresh()
        self.show_status('Local view refreshed.')
    def demo_info(self):
        QMessageBox.information(self,'Lab / Demo','NEON SENTINEL · UI preview\n\nAll data and operations are in memory.\nNo backend, agents, authentication, prevention or real updates.\nChanges reset when the application closes.\n\nCtrl+K: global search\nCtrl+R: refresh view\nEscape: close a dialog or focused detail panel')
    def global_search(self):
        q=self.search.text().strip().casefold()
        if not q:self.show_status('Enter an endpoint, incident, policy or rule name.'); return
        results=[]
        for name,items in [('Endpoints',self.service.endpoints),('Incidents',self.service.incidents),('Policies',self.service.policies),('Rules Library',self.service.rules)]:
            for item in items:
                text=getattr(item,'name',item.id)
                if q in (text+' '+item.id).casefold():results.append((f'{name} · {text} · {item.id}',name,item.id))
        if not results:self.show_status('No results for “'+self.search.text()+'”.'); return
        choice,ok=QInputDialog.getItem(self,'Search results','Open a matching record:',[r[0] for r in results],0,False)
        if ok:
            result=next(r for r in results if r[0]==choice); self.navigate(result[1],result[2])
    def reset(self):
        if QMessageBox.question(self,'Reset demo data?','Reset all session edits, tokens, notes and deployments?',QMessageBox.Reset|QMessageBox.Cancel,QMessageBox.Cancel)!=QMessageBox.Reset:return
        self.controller.reset()
        for p in self.pages.values():
            if hasattr(p,'close_drawer'):p.close_drawer()
        self.service.reset(); self.pages['Settings'].load(); self.show_status('Demo data reset.')
    def closeEvent(self,event):
        for p in self.pages.values():
            if hasattr(p,'can_leave') and not p.can_leave():event.ignore(); return
        self.controller.reset(); self.stop_backend(); event.accept()
