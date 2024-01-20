 # 
 # DishUI.py: Main application UI
 # Copyright (c) 2024 Gonzalo J. Carracedo
 # 
 # This program is free software: you can redistribute it and/or modify  
 # it under the terms of the GNU General Public License as published by  
 # the Free Software Foundation, version 3.
 #
 # This program is distributed in the hope that it will be useful, but 
 # WITHOUT ANY WARRANTY; without even the implied warranty of 
 # MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU 
 # General Public License for more details.
 #
 # You should have received a copy of the GNU General Public License 
 # along with this program. If not, see <http://www.gnu.org/licenses/>.
 #

from PyQt6 import QtWidgets
from PyQt6.QtCore import QObject, Qt, QThread
from PyQt6.QtWidgets import QMessageBox, QApplication
from DishUIWidget import DishUIWidget
from SerialWorker import SerialWorker

import sys

class DishUI(QObject):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.app      = QtWidgets.QApplication(sys.argv)
        self.window   = QtWidgets.QDialog()
        self.uiWidget = DishUIWidget()
        self.layout   = QtWidgets.QVBoxLayout(self.window)
        self.layout.addWidget(self.uiWidget)

        self.init_serial()

        self.window.setWindowTitle('GonzaloScope rotor control [disconnected]')
        
        self.connect_all()

    def init_serial(self):
        self.serialThread = QThread()
        self.serialWorker = SerialWorker()

        self.serialWorker.moveToThread(self.serialThread)
        self.serialThread.finished.connect(self.serialThread.deleteLater)

        self.serialThread.start()

    def connect_all(self):
        self.uiWidget.connect.connect(self.serialWorker.connect)
        self.uiWidget.disconnect.connect(self.on_ui_disconnect)
        self.uiWidget.newCommand.connect(self.on_command)

        self.serialWorker.line.connect(self.uiWidget.process_response)
        self.serialWorker.error.connect(self.on_serial_error)
        self.serialWorker.connected.connect(self.on_serial_connected)
        self.serialWorker.disconnected.connect(self.on_serial_disconnected)

    def run(self):
        self.window.show()
        val = self.app.exec()
        if self.serialWorker.is_connected():
            self.serialWorker.write('REPORT OFF')
    
    # Slots
    def on_serial_disconnected(self, reason: str):
        self.uiWidget.notify_connection(False, reason)

    def on_serial_connected(self):
        self.uiWidget.notify_connection(True)

    def on_serial_error(self, error: str):
        self.uiWidget.notify_connection(False, error)

    def on_ui_disconnect(self):
        self.serialWorker.disconnect()
    
    def on_command(self, cmd: str):
        self.serialWorker.write(cmd)
