 # 
 # DishUIWidget.py: Parse and interact with the AzElBox
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

from PyQt6 import QtCore, uic
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6 import QtWidgets
from PyQt6.QtWidgets import QMessageBox, QDialogButtonBox, QFileDialog, QSpacerItem, QSizePolicy, QLabel
import pathlib

IDLE_CSS    = 'background-color: gray;     color: white;'
ANGLE_CSS   = 'background-color: black;    color: white;'
ERROR_CSS   = 'background-color: red;      color: white;'
RUNNING_CSS = 'background-color: blue;     color: white;'
OK_CSS      = 'background-color: #00ff00;  color: black;'
INFO_CSS    = 'background-color: white;    color: black;'

STATUSES    = ['IDLE', 'ACK', 'RUNNING', 'FINALIZED']
REASONS     = ['OK', 'ABORTED', 'TIMEOUT', 'LIMIT', 'OVER', 'NOCMD', 'STILL']

class DishUIWidget(QtWidgets.QWidget):
    newCommand = pyqtSignal(str)
    connect    = pyqtSignal(str)
    disconnect = pyqtSignal()
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        dir = pathlib.Path(__file__).parent.resolve()
        uic.loadUi(fr"{dir}/DishUI.ui", self)

        self._azState    = self.make_motor_state()
        self._elState    = self.make_motor_state()
        self._connected  = False
        self._inconsistent = False
        self._first_az   = True
        self._first_el   = True

        self._azUI = {}
        self._azUI['angle']   = self.azLabel
        self._azUI['status']  = self.azStatusLabel
        self._azUI['reason']  = self.azReasonLabel
        self._azUI['current'] = self.azCurrentLabel

        self._elUI = {}
        self._elUI['angle']   = self.elLabel
        self._elUI['status']  = self.elStatusLabel
        self._elUI['reason']  = self.elReasonLabel
        self._elUI['current'] = self.elCurrentLabel

        self.update_ui_state()
        self.connect_all()
        
    def refresh_motor(self, ui, state):
        if not self._connected:
            ui['angle'].setStyleSheet(IDLE_CSS)
            ui['status'].setStyleSheet(IDLE_CSS)
            ui['reason'].setStyleSheet(IDLE_CSS)
            ui['current'].setStyleSheet(IDLE_CSS)

            ui['angle'].setText('???.?')
            ui['status'].setText('N/A')
            ui['reason'].setText('N/A')
            ui['current'].setText('N/A')
        else:
            ui['angle'].setStyleSheet(ANGLE_CSS)
            ui['angle'].setText(fr"{state['angle']:.1f}")
            # Refresh status
            status = state['status']
            if status == 2:
                ui['status'].setStyleSheet(RUNNING_CSS)
            else:
                ui['status'].setStyleSheet(IDLE_CSS)
            ui['status'].setText(STATUSES[status])

            # Refresh reason
            reason = state['reason']
            if reason == 0:
                ui['reason'].setStyleSheet(OK_CSS)
            else:
                ui['reason'].setStyleSheet(ERROR_CSS)
            ui['reason'].setText(REASONS[reason])
            
            # Set current
            current = state['current']
            if current < -.5:
                ui['current'].setStyleSheet(ERROR_CSS)
                ui['current'].setText('POWER DOWN')
            else:
                if current < 0:
                    current = 0.
                ui['current'].setStyleSheet(INFO_CSS)
                ui['current'].setText(f'{current:.3f} A')

    def update_ui_state(self):
        self.refresh_motor(self._azUI, self._azState)
        self.refresh_motor(self._elUI, self._elState)

        self.dishGroup.setEnabled(self._connected)
        self.cmdGroup.setEnabled(self._connected)
        
        self.connectButton.setEnabled(not self._connected and not self._inconsistent)
        self.disconnectButton.setEnabled(self._connected and not self._inconsistent)

    def make_motor_state(self):
        state = {}
        state['angle']   = 0
        state['status']  = 0
        state['reason']  = 0
        state['current'] = -2
        return state
        
    def connect_all(self):
        self.connectButton.clicked.connect(self.on_connect)
        self.disconnectButton.clicked.connect(self.on_disconnect)
        self.gotoButton.clicked.connect(self.on_goto)
        self.advanceButton.clicked.connect(self.on_delta)
        self.vhButton.clicked.connect(self.on_vh)
        self.abortButton.clicked.connect(self.on_abort)
        self.currentLimitButton.clicked.connect(self.on_over)

    def process_report(self, line: list, target: dict):
        target['angle'] = float(line[2])
        target['current'] += .1 * (float(line[3]) - target['current'])
        target['status'] = int(line[4])
        target['reason'] = int(line[5])
    
    def process_info(self, line: list):
        cmd = line[1]

        if cmd == 'REPORT[AZ]' and len(line) == 6:
            self.process_report(line, self._azState)
            self.refresh_motor(self._azUI, self._azState)

            if self._first_az:
                self._first_az = False
                self.azSpin.setValue(self._azState['angle'])
                self.azVHSpin.setValue(self._azState['angle'])

        elif cmd == 'REPORT[EL]' and len(line) == 6:
            self.process_report(line, self._elState)
            self.refresh_motor(self._elUI, self._elState)
        
            if self._first_el:
                self._first_el = False
                self.elSpin.setValue(self._elState['angle'])
                self.elVHSpin.setValue(self._elState['angle'])

    def process_response(self, line: list):
        if len(line) > 1:
            if line[0] == 'I':
                self.process_info(line)
            elif line[0] == 'E':
                self.lastErrorLabel.setText(':'.join(line[1:]))
            
    def command(self, cmd: str):
        self.newCommand.emit(cmd)
    
    def send_init_commands(self):
        self.command('REPORT ON')
        self.on_over()
        self._first_az = True
        self._first_el = True

    def send_cleanup_commands(self):
        self.command('REPORT OFF')
    
    def notify_connection(self, state, reason = None):
        self._inconsistent = False
        if reason is None:
            if state:
                reason = 'Connected'
            else:
                reason = 'Disconnected'

        self.uiStatusLabel.setText(reason)
        if state != self._connected:
            self._connected = state
            self.update_ui_state()
            if state:
                self.send_init_commands()
            else:
                self.lastErrorLabel.setText('No errors')

    # Slots
    def on_connect(self):
        self._inconsistent = True
        self.uiStatusLabel.setText('Connecting...')
        self.connect.emit(self.portEdit.text())
        self.update_ui_state()

    def on_disconnect(self):
        if self._connected:
            self._inconsistent = True
            self.send_cleanup_commands()
            self.uiStatusLabel.setText('Disconnecting...')
            self.disconnect.emit()
            self.update_ui_state()

    def on_abort(self):
        self.command('ABORT')
    
    def on_goto(self):
        self.command(fr'GOTO {self.azSpin.value()} {self.elSpin.value()}')
    
    def on_delta(self):
        az = self._azState["angle"]
        el = self._elState["angle"]

        self.command(fr'GOTO {az + self.azDeltaSpin.value()} {el + self.elDeltaSpin.value()}')

    def on_vh(self):
        self.command(fr'VH {self.azVHSpin.value()} {self.elVHSpin.value()}')

    def on_over(self):
        self.command(fr'OVERCURRENT AZ {self.azCurrentSpin.value()}')
        self.command(fr'OVERCURRENT EL {self.elCurrentSpin.value()}')
