'''PyNMR, J.Maxwell 2021
'''
import datetime, time
import telnetlib
from PyQt5.QtCore import QThread, pyqtSignal, Qt
from labjack import ljm
from PyQt5.QtWidgets import QWidget, QLabel, QGroupBox, QHBoxLayout, QVBoxLayout, QGridLayout, QLineEdit, QSpacerItem, QSizePolicy, QComboBox, QPushButton, QTableView, QAbstractItemView, QAbstractScrollArea, QFileDialog, QStackedWidget
 

class TempTab(QWidget): 
    '''Creates Temperature monitor tab'''   
    def __init__(self, parent):
        super(QWidget, self).__init__(parent)
        self.__dict__.update(parent.__dict__)  
        
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
        self.time_edit = QLineEdit('0', enabled=False)
        self.read_layout.addWidget(self.time_edit, 0, 1)
                
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
        
        self.temp_edit.setText(str(freq_out))
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
        
        
class TempThread(QThread):
    '''Thread class for chassis temperature monitor
    Args:
        config: Config object of settings
    '''
    reply = pyqtSignal(tuple)       # reply signal
    finished = pyqtSignal()       # finished signal
    def __init__(self, parent, config):
        QThread.__init__(self)
        self.config = config
        self.parent = parent 
            
                
    def __del__(self):
        self.wait()
        
    def run(self):
        '''Main temp read loop
        '''        
        try:
            self.thermom = LabJack(self.config)
        except Exception as e:
            print('Exception starting temp thread, lost connection: '+str(e))
            
        temp = 0
        try:        
            temp = self.thermom.read_temp()
        except Exception as e:
            print(f"Temperature read failed: {e}")  
            #self.parent.enable_button.toggle()
            #self.parent.enable_pushed()
            #break
            
        try:
            self.reply.emit((temp,))
        except Exception as e:                
            print("Couldn't send temp reply: "+str(e))
        time.sleep(self.config.settings['temp_settings']['monitor_time'])
          
        self.finished.emit()
        del self.thermom
        
        
            
