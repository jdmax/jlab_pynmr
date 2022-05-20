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
        self.freq_edit = QLineEdit('1000')
        self.setit_layout.addWidget(self.freq_edit, 1, 2)
        self.amp_label = QLabel('Amplitude (V):')
        self.setit_layout.addWidget(self.amp_label, 2, 1)
        self.amp_edit = QLineEdit('1')
        self.setit_layout.addWidget(self.amp_edit, 2, 2)
        self.off_label = QLabel('Offset (V):')
        self.setit_layout.addWidget(self.off_label, 3, 1)
        self.off_edit = QLineEdit('0')
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
        
        freq = float(self.freq_edit.text())
        amp = float(self.amp_edit.text())
        off = float(self.off_edit.text())

        self.fm = FMGenerator(self.parent.config)
        freq_out, amp_out, off_out = self.fm.set(freq, amp, off)
        del self.fm
        
        self.r_freq_edit.setText(str(freq_out))
        self.r_amp_edit.setText(str(amp_out))
        self.r_off_edit.setText(str(off_out))
        
    def read_fm(self):
        '''Open connection to generator and read FM settings'''
        
        self.fm = FMGenerator(self.parent.config)
        freq_out, amp_out, off_out = self.fm.read()
        del self.fm
        
        self.r_freq_edit.setText(str(freq_out))
        self.r_amp_edit.setText(str(amp_out))
        self.r_off_edit.setText(str(off_out))

    
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
        self.config = config

 
    def set(self, freq, amp, off):
        '''Write settings to generator, and read them back'''
        try:
            self.tn = telnetlib.Telnet(self.host, port=self.port, timeout=self.timeout)

            # Write all required settings            
            self.tn.write(bytes(f"++addr {self.addr}\n", 'ascii'))
            self.tn.write(bytes(f"FREQ {freq}\n", 'ascii'))
            self.tn.write(bytes(f"FREQ?\n", 'ascii'))
            freq_out = self.tn.read_some().decode('ascii') 
            
            self.tn.write(bytes(f"VOLT {amp}\n", 'ascii'))
            self.tn.write(bytes(f"VOLT?\n", 'ascii'))
            amp_out = self.tn.read_some().decode('ascii')   
                      
            self.tn.write(bytes(f"VOLT:OFFS {off}\n", 'ascii'))
            self.tn.write(bytes(f"VOLT:OFFS?\n", 'ascii'))
            off_out = self.tn.read_some().decode('ascii')     
                     
            print(f"Successfully sent settings to GPIB on {self.host}")
            return freq_out, amp_out, off_out
            
        except Exception as e:
            print(f"Network connection to GPIB failed on FM generator {self.host}: {e}")
            return 0,0,0
            
    
    def read(self):
        '''Read settings from generator'''   
        try:
            self.tn = telnetlib.Telnet(self.host, port=self.port, timeout=self.timeout)

            # Write all required settings            
            self.tn.write(bytes(f"FREQ?\n", 'ascii'))
            freq_out = self.tn.read_some().decode('ascii') 
            self.tn.write(bytes(f"VOLT?\n", 'ascii'))
            amp_out = self.tn.read_some().decode('ascii')        
            self.tn.write(bytes(f"VOLT:OFFS?\n", 'ascii'))
            off_out = self.tn.read_some().decode('ascii')    
                     
            print(f"Successfully sent settings to GPIB on {self.host}")
            return freq_out, amp_out, off_out
                        
        except Exception as e:
            print(f"Network connection to GPIB failed on FM generator {self.host}: {e}")
            return 0,0,0
            
    
        
    def close(self):           
        try:
            tn.close()
        except Exception as e:
            pass
            #print(f"GPIB connection failed on {self.host}: {e}")
            
    def __del__(self):
        self.close()
