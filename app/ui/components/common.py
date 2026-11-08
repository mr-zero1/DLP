from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QPainterPath, QLinearGradient
from PySide6.QtWidgets import *

COLORS = {'High':'#ff6578','Medium':'#ffc84d','Low':'#8eb7e1','Blocked':'#ff6578','Detected':'#b38aff','Warned':'#ffc84d',
          'Online':'#00e3b0','Offline':'#ff6578','Published':'#00dfae','Draft':'#ffc84d','Success':'#00e0b4','Failed':'#ff6578','Open':'#56b6ff','In review':'#b88aff','Resolved':'#00dfae'}
def label(text, style=None, wrap=False):
    w = QLabel(str(text)); w.setWordWrap(wrap)
    if style: w.setObjectName(style)
    return w

def button(text, callback=None, primary=False):
    b = QPushButton(text)
    if primary: b.setObjectName('primary')
    if callback: b.clicked.connect(callback)
    b.setCursor(Qt.PointingHandCursor)
    return b

def combo(items, value=None):
    c = QComboBox(); c.addItems(list(items))
    if value is not None: c.setCurrentText(str(value))
    return c

def row(*widgets):
    w = QWidget(); l = QHBoxLayout(w); l.setContentsMargins(0,0,0,0); l.setSpacing(12)
    for item in widgets:
        if item is None: l.addStretch()
        else: l.addWidget(item)
    return w

def card(title=None):
    f = QFrame(); f.setObjectName('card'); l = QVBoxLayout(f); l.setContentsMargins(16,14,16,14); l.setSpacing(12)
    if title: l.addWidget(label(title,'section'))
    return f, l

def scroll(widget):
    a = QScrollArea(); a.setWidgetResizable(True); a.setFrameShape(QFrame.NoFrame); a.setWidget(widget)
    return a

def table(headers):
    t = QTableWidget(0, len(headers)); t.setHorizontalHeaderLabels(headers)
    t.verticalHeader().hide(); t.setAlternatingRowColors(True); t.setShowGrid(False)
    t.setSelectionBehavior(QAbstractItemView.SelectRows); t.setSelectionMode(QAbstractItemView.SingleSelection)
    t.setEditTriggers(QAbstractItemView.NoEditTriggers)
    t.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
    t.verticalHeader().setDefaultSectionSize(49); t.setMinimumHeight(200)
    t.setSortingEnabled(False)
    return t

def populate(t, rows):
    t.setRowCount(len(rows))
    for r, values in enumerate(rows):
        for c, value in enumerate(values):
            item = QTableWidgetItem(str(value))
            if str(value) in COLORS: item.setForeground(QColor(COLORS[str(value)]))
            t.setItem(r,c,item)
    t.setToolTip('Select a row to inspect details')

def clear_layout(layout):
    while layout.count():
        item = layout.takeAt(0)
        if item.widget(): item.widget().deleteLater()
        elif item.layout(): clear_layout(item.layout())

class Page(QWidget):
    def __init__(self, service, navigate, title, subtitle):
        super().__init__(); self.service = service; self.navigate = navigate
        self.layout = QVBoxLayout(self); self.layout.setContentsMargins(22,20,22,14); self.layout.setSpacing(16)
        heading = QWidget(); h = QVBoxLayout(heading); h.setContentsMargins(0,0,0,0)
        h.addWidget(label(title,'title')); h.addWidget(label(subtitle,'muted',True))
        self.actions = QHBoxLayout(); self.actions.addWidget(heading,1)
        self.layout.addLayout(self.actions)
    def status(self, message, error=False):
        self.window().show_status(message, error)

class Metric(QFrame):
    def __init__(self, title, value, detail, color='#00dfea'):
        super().__init__(); self.setObjectName('card'); l = QVBoxLayout(self); l.setContentsMargins(18,16,18,16)
        l.addWidget(label(title,'muted')); self.value = label(value,'metric'); l.addWidget(self.value)
        self.detail = label(detail,wrap=True); self.detail.setStyleSheet(f'color:{color}'); l.addWidget(self.detail)
        self.setMinimumHeight(112)

class ActivityChart(QWidget):
    def __init__(self, service):
        super().__init__(); self.service=service; self.setMinimumHeight(180)
        self.setAccessibleName('Incident activity by hour; cyan blocked, purple detected or warned')
    def paintEvent(self, event):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        area = self.rect().adjusted(32,15,-15,-30)
        series = [[0]*24,[0]*24]
        for i in self.service.incidents:
            series[0 if i.action=='Blocked' else 1][int(i.time.split(':')[0])] += 1
        maximum = max(2,max(max(s) for s in series))
        for n in range(5):
            y=area.bottom()-area.height()*n/4
            p.setPen(QPen(QColor('#244052'),1,Qt.DashLine)); p.drawLine(area.left(),int(y),area.right(),int(y))
            p.setPen(QColor('#789bb7')); p.drawText(0,int(y)+4,str(round(maximum*n/4,1)))
        for hour in (0,6,12,18,23):
            x=area.left()+area.width()*hour/23
            p.setPen(QColor('#89a7c1')); p.drawText(int(x)-12,self.height()-8,f'{hour:02}:00')
        for values,color in zip(series,['#00e4f0','#ad77ff']):
            path=QPainterPath()
            for n,v in enumerate(values):
                x=area.left()+area.width()*n/23; y=area.bottom()-area.height()*v/maximum
                if n==0: path.moveTo(x,y)
                else: path.lineTo(x,y)
            fill=QPainterPath(path); fill.lineTo(area.right(),area.bottom()); fill.lineTo(area.left(),area.bottom()); fill.closeSubpath()
            grad=QLinearGradient(0,area.top(),0,area.bottom()); grad.setColorAt(0,QColor(color)); grad.setColorAt(1,QColor('#081725'))
            p.setOpacity(.2); p.fillPath(fill,grad); p.setOpacity(1); p.setPen(QPen(QColor(color),2)); p.drawPath(path)
        p.end()

class SentinelBanner(QFrame):
    """Decorative bitmap only; all overlay text remains native Qt labels."""
    def __init__(self):
        super().__init__()
        from importlib.resources import files
        from PySide6.QtGui import QPixmap
        self.pixmap=QPixmap()
        self.pixmap.loadFromData(files('app.assets').joinpath('sentinel-banner.png').read_bytes())
        self.setMinimumHeight(142)
    def paintEvent(self,event):
        from PySide6.QtCore import QRectF
        p=QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        clip=QPainterPath(); clip.addRoundedRect(QRectF(self.rect()),8,8); p.setClipPath(clip)
        if not self.pixmap.isNull():
            src_height=self.height()*self.pixmap.width()/max(1,self.width())
            source=QRectF(0,max(0,(self.pixmap.height()-src_height)*.25),self.pixmap.width(),min(src_height,self.pixmap.height()))
            p.drawPixmap(QRectF(self.rect()),self.pixmap,source)
        shade=QLinearGradient(0,0,self.width(),0); shade.setColorAt(0,QColor(6,12,29,170)); shade.setColorAt(.55,QColor(6,12,29,130)); shade.setColorAt(1,QColor(6,12,29,15)); p.fillRect(self.rect(),shade)
        p.setClipping(False); p.setPen(QPen(QColor('#6b4ba6'),1)); p.drawRoundedRect(QRectF(self.rect()).adjusted(.5,.5,-.5,-.5),8,8); p.end()
