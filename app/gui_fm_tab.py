'''PyNMR, J.Maxwell 2021
'''
import datetime
import re
import json
import time
import numpy as np
from scipy.optimize import minimize
from dateutil.parser import parse
from PyQt5.QtWidgets import QWidget, QLabel, QGroupBox, QHBoxLayout, QVBoxLayout, QGridLayout, QLineEdit, QSpacerItem, QSizePolicy, QComboBox, QPushButton, QTableView, QAbstractItemView, QAbstractScrollArea, QFileDialog, QStackedWidget
from PyQt5.QtGui import QIntValidator, QDoubleValidator, QValidator
import pyqtgraph as pg
from PyQt5.QtCore import QThread, pyqtSignal,Qt
from RsInstrument import * 
import telnetlib
 

class FMTab(QWidget): 
    '''Creates FM control tab'''   
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
        self.fm_box = QGroupBox('FM Controls')
        self.fm_box.setLayout(QVBoxLayout())
        self.left.addWidget(self.fm_box)  

        self.setit_layout = QGridLayout() 
        self.fm_box.layout().addLayout(self.setit_layout) 
        self.set_label = QLabel('Settings:')
        self.setit_layout.addWidget(self.set_label, 0, 0)
        self.freq_label = QLabel('Frequency (Hz):')
        self.setit_layout.addWidget(self.freq_label, 1, 1)
        self.freq_edit = QLineEdit()
        self.setit_layout.addWidget(self.freq_edit, 1, 2)
        self.amp_label = QLabel('Amplitude (V):')
        self.setit_layout.addWidget(self.amp_label, 2, 1)
        self.amp_edit = QLineEdit()
        self.setit_layout.addWidget(self.amp_edit, 2, 2)
        self.off_label = QLabel('Offset (V):')
        self.setit_layout.addWidget(self.off_label, 3, 1)
        self.off_edit = QLineEdit()
        self.setit_layout.addWidget(self.off_edit, 3, 2)
        self.setit_button = QPushButton('Set Now', checkable=False)
        self.setit_layout.addWidget(self.setit_button, 4, 2)
        self.setit_button.clicked.connect(self.set_fm)
        
        self.fm_box.layout().addWidget(self.divider())
        
        self.read_layout = QGridLayout()  
        self.fm_box.layout().addLayout(self.read_layout) 
        self.read_label = QLabel('Readback:')
        self.read_layout.addWidget(self.read_label, 0, 0)  
        self.r_freq_label = QLabel('Frequency (Hz):')
        self.read_layout.addWidget(self.r_freq_label, 1, 1)
        self.r_freq_edit = QLineEdit('0', enabled=False)
        self.read_layout.addWidget(self.r_freq_edit, 1, 2)
        self.r_amp_label = QLabel('Amplitude (V):')
        self.read_layout.addWidget(self.r_amp_label, 2, 1)
        self.r_amp_edit = QLineEdit('0', enabled=False)
        self.read_layout.addWidget(self.r_amp_edit, 2, 2)
        self.r_off_label = QLabel('Offset (V):')
        self.read_layout.addWidget(self.r_off_label, 3, 1)
        self.r_off_edit = QLineEdit('0', enabled=False)
        self.read_layout.addWidget(self.r_off_edit, 3, 2)
        self.read_button = QPushButton('Readback Now', checkable=False)
        self.read_layout.addWidget(self.read_button, 4, 2)
        self.read_button.clicked.connect(self.read_fm)
        
        # Right Side
        self.right = QVBoxLayout()  
        self.main.addLayout(self.right)
        
    def set_fm(self):
        '''Open connection to generator and send FM settings'''
        
        self.fm = FMGenerator()
        del self.fm
        
    def read_fm(self):
        '''Open connection to generator and read FM settings'''
        
        self.fm = FMGenerator()
        del self.fm

    
    def divider(self):
        div = QLabel ('')
        div.setStyleSheet ("QLabel {background-color: #eeeeee; padding: 0; margin: 0; border-bottom: 0 solid #eeeeee; border-top: 1 solid #eeeeee;}")
        div.setMaximumHeight (2)
        return div     
      
      
class FMGenerator():
    '''Class to interface with Prologix GPIB controller to control uwave FM
        
    Arguments:
        config: Current Config object 
    '''    
    
    def __init__(self, config):    
        '''Open connection to GPIB, send commands for all settings. Close.  
        '''
        self.host = config.settings['fm_settings']['ip']
        self.port = config.settings['fm_settings']['port']   
        self.timeout = config.settings['fm_settings']['timeout']              # Telnet timeout in secs
        self.addr = config.settings['fm_settings']['addr'] 

 
        try:
            self.tn = telnetlib.Telnet(self.host, port=self.port, timeout=self.timeout)
            
            # Write all required settings
            #self.tn.write(bytes(f"FE 1\n", 'ascii'))  # Fetch setup 1
            
            self.tn.write(bytes(f"++addr {config.settings['uWave_settings']['counter_addr']}\n", 'ascii'))
            
            #self.tn.write(bytes(f"OU DE\n", 'ascii'))  # Read displayed data
            #freq = self.tn.read_some().decode('ascii')        
                     
            print(f"Successfully sent settings to GPIB on {self.host}")
            
        except Exception as e:
            print(f"GPIB connection failed on {self.host}: {e}")
    
    def read_freq(self):
        '''Read frequency from open connection'''        
        #try:
        self.tn.write(bytes(f"OU DE\n", 'ascii'))  # Read displayed data
        freq = self.tn.read_some().decode('ascii')  
        return int(freq.strip())  
        #except exception as e:
        #   print(f"GPIB connection failed on {self.host}: {e}")  
        
    def close(self):           
        try:
            tn.close()
        except Exception as e:
            print(f"GPIB connection failed on {self.host}: {e}")
            
    def __del__(self):
        self.close()