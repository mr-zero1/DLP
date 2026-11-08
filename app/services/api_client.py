import json
import os

from PySide6.QtCore import QObject, QUrl, Signal
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest


DEFAULT_API_URL = "http://192.168.122.1:5000"


class ApiClient(QObject):
    health_check_completed = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.base_url = os.environ.get("DLP_API_URL", DEFAULT_API_URL).strip().rstrip("/")
        self.network_manager = QNetworkAccessManager(self)
        self.network_manager.setTransferTimeout(5000)
        self._request_in_flight = False

    def check_health(self):
        if self._request_in_flight:
            return

        url = QUrl(f"{self.base_url}/api/v1/health")
        if not url.isValid() or url.scheme() not in ("http", "https") or not url.host():
            self.health_check_completed.emit(False)
            return

        self._request_in_flight = True
        reply = self.network_manager.get(QNetworkRequest(url))
        reply.finished.connect(lambda: self._handle_health_reply(reply))

    def _handle_health_reply(self, reply):
        self._request_in_flight = False
        status_code = reply.attribute(QNetworkRequest.HttpStatusCodeAttribute)
        is_healthy = False

        if reply.error() == QNetworkReply.NoError and status_code is not None and 200 <= status_code < 300:
            try:
                payload = json.loads(bytes(reply.readAll()).decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                payload = None
            is_healthy = isinstance(payload, dict) and payload.get("status") == "ok"

        reply.deleteLater()
        self.health_check_completed.emit(is_healthy)
