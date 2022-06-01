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
 

class TempTab(QWidget): 
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
        self.mon_box = QGroupBox('Temp Monitor')
        self.mon_box.setLayout(QVBoxLayout())
        self.left.addWidget(self.mon_box)  

        self.read_layout = QGridLayout() 
        self.mon_box.layout().addLayout(self.read_layout) 
        self.temp_label = QLabel('Chassis Temp (deg F):')
        self.read_layout.addWidget(self.temp_label, 0, 0)
        self.temp_edit = QLineEdit('0')
        self.read_layout.addWidget(self.temp_edit, 0, 1)
        
        self.read_button.clicked.connect(self.read_temp)
        
        # Right Side
        self.right = QVBoxLayout()  
        self.main.addLayout(self.right)

        
    def read(self):
        '''Open connection to generator and read FM settings'''
        
        self.temp = LabJack(self.parent.config)
        temp = self.temp.read()
        del self.temp
        
        self.temp_edit.setText(str(freq_out))

    
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
        return ljm.eReadNames(self.lj, len(aNames), aNames)
        
    # def __del__(self):
        # '''Close on delete'''
        # ljm.close(self.lj) 
            
