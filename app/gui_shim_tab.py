'''PyNMR, J.Maxwell 2021
'''
import datetime
import re
import json
from dateutil.parser import parse
from PyQt5.QtWidgets import QWidget, QLabel, QGroupBox, QHBoxLayout, QVBoxLayout, QGridLayout, QLineEdit, QSpacerItem, QSizePolicy, QComboBox, QPushButton, QTableView, QAbstractItemView, QAbstractScrollArea, QFileDialog
from PyQt5.QtCore import QThread, pyqtSignal,Qt
from RsInstrument import * 
 

class ShimTab(QWidget): 
    '''Creates shim control tab'''   
    def __init__(self, parent):
        super(QWidget, self).__init__(parent)
        self.__dict__.update(parent.__dict__)  
        
        self.parent = parent
                
        # Populate Magnt Tab 
        self.main = QHBoxLayout()            # main layout
        
        # Left Side
        self.left = QVBoxLayout() 
        
        self.shim_box = ShimBox(self)
        self.left.addWidget(self.shim_box)  
                
    def divider(self):
        div = QLabel ('')
        div.setStyleSheet ("QLabel {background-color: #eeeeee; padding: 0; margin: 0; border-bottom: 0 solid #eeeeee; border-top: 1 solid #eeeeee;}")
        div.setMaximumHeight (2)
        return div 

class ShimBox(QGroupBox):
    '''Magnet control gui'''
    def __init__(self, parent):
        super(QWidget,self).__init__(parent)   
        self.__dict__.update(parent.__dict__)   
        self.divider = parent.divider    
                
        self.setLayout(QVBoxLayout())    
        self.setTitle('Shim Controls')         
        self.shim_top = QHBoxLayout()
        self.layout().addLayout(self.shim_top)          
        
        
        
class ShimControl():
    '''Interface with R&S HMP4040
    
    Arguments:
        Config: Current Config object
    '''
        
    def __init__(self, config):    
        '''Open connection to Rsimstrument  
        '''
        self.host = config.settings['shim_settings']['ip']
        self.port = 5025    
        
        
        