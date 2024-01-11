 # 
 # SerialWorker.py: Dispatch serial port events
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

from PyQt6.QtCore import QObject, pyqtSignal
import serial

class SerialWorker(QObject):
  connected    = pyqtSignal()
  disconnected = pyqtSignal(str)
  error        = pyqtSignal(str)
  line         = pyqtSignal(list)

  _serial      = None
  _cancelled   = False

  def connect(self, port: str, baudrate: int = 115200):
    if self._serial is not None:
      self.error.emit('Serial port is already connected')
      return

    try:
      self._serial = serial.Serial(
        port       = port,
        baudrate   = baudrate,
        parity     = serial.PARITY_NONE,
        stopbits   = serial.STOPBITS_ONE,
        bytesize   = serial.EIGHTBITS)

      self._cancelled = False # Reset cancel flag
    except serial.SerialException as e:
      self.error.emit(fr'Failed to connect to {port}: {str(e)}')
    
    if self._serial is not None:
      self.connected.emit()
      self.read_loop()

  def is_connected(self):
    return self._serial is not None
  
  def disconnect(self):
    if self._serial is None:
      self.error.emit('Serial port is not yet connected')
      return
    
    self._cancelled = True
    self._serial.cancel_read()
    self._serial.cancel_write()

  def readline(self):
    data = self._serial.readline()
    if data is None or len(data) == 0 or self._cancelled:
      self._serial.close()
      self._serial = None
      self.disconnected.emit('Disconnected by user' if self._cancelled else 'Connection lost')
      data = None
    return data
  
  def write(self, cmd: str):
    if self._serial is None:
      self.error.emit('Serial port is not yet connected')
      return

    self._serial.write(f'{cmd}\n'.encode('utf-8'))
    
  def read_loop(self):
    while self._serial is not None:
      data = self.readline()
      if data is not None:
        asString = data.decode('utf-8')
        fields   = asString.strip().split(':')
        if len(fields) > 0:
          self.line.emit(fields)
    



