"""Run with python -m app.main or the neon-sentinel console command."""
import sys
from importlib.resources import files
from PySide6.QtCore import QStandardPaths
from PySide6.QtWidgets import QApplication
from app.mocks.service import MockService
from app.ui.main_window import MainWindow

def create_app():
    app=QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName('NEON SENTINEL'); app.setOrganizationName('NeonSentinel'); app.setApplicationVersion('0.1.0')
    app.setStyle('Fusion'); app.setStyleSheet(files('app.themes').joinpath('neon.qss').read_text())
    return app

def user_data_path():
    """Future persistence belongs here, never beside installed resources."""
    return QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)

def main():
    app=create_app(); service=MockService(); window=MainWindow(service); window.show(); return app.exec()

if __name__=='__main__':sys.exit(main())
