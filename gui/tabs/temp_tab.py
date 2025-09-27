'''PyNMR, J.Maxwell 2021
'''
import datetime, time
import telnetlib
from PySide6.QtCore import QThread, Signal, Qt
from labjack import ljm
from core.thread_manager import BaseThread
from PySide6.QtWidgets import QWidget, QLabel, QGroupBox, QHBoxLayout, QVBoxLayout, QGridLayout, QLineEdit, QSpacerItem, QSizePolicy, QComboBox, QPushButton, QTableView, QAbstractItemView, QAbstractScrollArea, QFileDialog, QStackedWidget
 

class TempTab(QWidget): 
    '''Creates Temperature monitor tab'''   
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        
        # Populate  Tab 
        self.main = QVBoxLayout()            # main layout
        self.setLayout(self.main) 
        
        # Left Side
        self.left = QVBoxLayout() 
        self.main.addLayout(self.left)
        
        # FM Controls box
        self.mon_box = QGroupBox('Temp Monitor')
        self.mon_box.setLayout(QVBoxLayout())
        self.left.addWidget(self.mon_box)  

        self.read_layout = QGridLayout() 
        self.mon_box.layout().addLayout(self.read_layout) 
        self.temp_label = QLabel('Chassis Temp:')
        self.read_layout.addWidget(self.temp_label, 0, 0)
        self.temp_edit = QLineEdit('0', enabled=False)
        self.read_layout.addWidget(self.temp_edit, 0, 1)
        self.time_label = QLabel('Update Time:')
        self.read_layout.addWidget(self.time_label, 0, 2)
        self.time_edit = QLineEdit('0', enabled=False)
        self.read_layout.addWidget(self.time_edit, 0, 3)
                
        # Right Side
        self.right = QVBoxLayout()  
        self.main.addLayout(self.right)
        
        try:
            self.temp_thread = TempThread(self, self.parent.config)
            self.temp_thread.reply.connect(self.temp_reply)
            self.temp_thread.start()
        except Exception as e: 
            print('Exception starting temperature thread: '+str(e)) 

    def temp_reply(self, reply):
        '''Receive reply from temp thread'''
        temp = reply[0]
        self.temp_edit.setText(f"{temp} K")
        self.parent.chassis_temp = temp
        pass
   
        
    def read(self):
        '''Open connection to generator and read FM settings'''
        
        self.temp_lj = LabJack(self.parent.config)
        temp = self.temp_lj.read()
        del self.temp_lj
        
        self.temp_edit.setText(str(temp))
        now = datetime.datetime.now()
        self.time_edit.setText(now.strftime("%Y-%m-%d_%H-%M-%S"))

    
    def divider(self):
        div = QLabel ('')
        div.setStyleSheet ("QLabel {background-color: #eeeeee; padding: 0; margin: 0; border-bottom: 0 solid #eeeeee; border-top: 1 solid #eeeeee;}")
        div.setMaximumHeight (2)
        return div     
      
           
class LabJack():      
    '''Access LabJack device to read temp from probe 
    '''
    
    def __init__(self, config):
        '''Open connection to LabJack
        '''  
        ip = config.settings['temp_settings']['ip']
        try:
            self.lj = ljm.openS("T4", "TCP", ip) 
        except Exception as e:
            print(f"Connection to LabJack failed on {ip}: {e}")
               
    
    def read_temp(self):
        '''Read temperature and potentiometer position from LabJack. Returns array of ADC values.
        '''
        aNames = ["AIN0",]
        temps = ljm.eReadNames(self.lj, len(aNames), aNames)
        temp = temps[0]*55.56 - 17.78 + 273.15
        return temp
        
    # def __del__(self):
        # '''Close on delete'''
        # ljm.close(self.lj) 
        
        
class TempThread(BaseThread):
    '''Thread class for chassis temperature monitor
    Args:
        parent: Parent widget (TempTab)
        config: Config object of settings
    '''
    def __init__(self, parent, config):
        super().__init__(name=f"temp_{id(parent)}", parent=parent, config=config)
        self.tab_parent = parent  # TempTab instance
        self.thermom = None
        self.monitor_time = config.settings['temp_settings']['monitor_time']
        
    def setup(self):
        '''Initialize LabJack connection'''
        try:
            from hardware.instruments import LabJack
            self.thermom = LabJack(self.config)
            self._logger.info("LabJack connection established for temperature monitoring")
        except Exception as e:
            error_msg = f'Exception starting temp thread: {e}'
            self._logger.error(error_msg)
            raise Exception(error_msg)
                
    def execute(self):
        '''Main temp read loop - single reading'''
        if not self.thermom:
            self._logger.error("LabJack not initialized")
            return
            
        temp = 0
        try:        
            temp = self.thermom.read_temp()
            self._logger.debug(f"Temperature reading: {temp}")
        except Exception as e:
            self._logger.error(f"Temperature read failed: {e}")
            # Note: Original code had commented out error handling for UI toggle
            
        try:
            self.emit_reply(temp)  # Emit just the temperature value
        except Exception as e:                
            self._logger.error(f"Couldn't send temp reply: {e}")
            
        # Sleep for monitor time interval
        sleep_intervals = int(self.monitor_time * 10)  # Check stop every 0.1s
        for _ in range(sleep_intervals):
            if self.should_stop():
                return
            time.sleep(0.1)
        
    def cleanup(self):
        '''Clean up LabJack connection'''
        if self.thermom:
            try:
                del self.thermom
                self.thermom = None
                self._logger.info("LabJack connection cleaned up")
            except Exception as e:
                self._logger.warning(f"Error cleaning up LabJack: {e}")


# Legacy compatibility wrapper
class LegacyTempThread(QThread):
    '''Legacy compatibility wrapper for old TempThread interface.'''
    reply = Signal(tuple)       # reply signal
    finished = Signal()       # finished signal
    
    def __init__(self, parent, config):
        QThread.__init__(self)
        self.config = config
        self.parent = parent 
                
    def __del__(self):
        if self.isRunning():
            self.quit()
        
    def run(self):
        try:
            from hardware.instruments import LabJack
            self.thermom = LabJack(self.config)
        except Exception as e:
            print('Exception starting temp thread, lost connection: '+str(e))
            
        temp = 0
        try:        
            temp = self.thermom.read_temp()
        except Exception as e:
            print(f"Temperature read failed: {e}")  
            
        try:
            self.reply.emit((temp,))
        except Exception as e:                
            print("Couldn't send temp reply: "+str(e))
        time.sleep(self.config.settings['temp_settings']['monitor_time'])
          
        self.finished.emit()
        del self.thermom
        
        
            
