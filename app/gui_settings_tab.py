import datetime, time, re
from dateutil.parser import parse
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
 
from app.classes import *
from app.config import *

class SettingsTab(QWidget): 
    '''Creates settings tab'''   
    def __init__(self, parent):
        super(QWidget,self).__init__(parent)
        self.__dict__.update(parent.__dict__)  
        
        self.parent = parent
        self.config = parent.config
        self.event = parent.event
        self.baseline = parent.baseline
        
        # Populate Settings Tab 
        self.main = QGridLayout()            # main layout
        
        # Left Side
        self.left = QVBoxLayout() 
                        
               
        # Populate NMR settings, include settings from run page and other settings       
        self.nmrset_box = QGroupBox('NMR Settings')
        self.left.addWidget(self.nmrset_box)
        self.nmrset_box.setLayout(QGridLayout()) 
        
        i = 0        
        self.settings_lines = {}
        self.settings_labels = {}
        for key in self.config.settings:   
            self.settings_lines[key] = QLineEdit(str(self.config.settings[key].value))
            self.settings_labels[key] = QLabel(self.config.settings[key].text)
            self.settings_lines[key].setValidator(self.config.settings[key].valid)
            self.settings_lines[key].setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
            self.settings_lines[key].setMinimumWidth(60)            
            self.settings_lines[key].setEnabled(False)
            self.settings_lines[key].textChanged.connect(parent.check_state)
            self.settings_lines[key].textChanged.emit(self.settings_lines[key].text())
            self.nmrset_box.layout().addWidget(self.settings_labels[key], i, 0)
            self.nmrset_box.layout().addWidget(self.settings_lines[key], i, 1)            # make entries for config items
            i+=1   
        for key in self.config.other_settings:   
            self.settings_lines[key] = QLineEdit(str(self.config.other_settings[key].value))
            self.settings_labels[key] = QLabel(self.config.other_settings[key].text)
            self.settings_lines[key].setValidator(self.config.other_settings[key].valid)
            self.settings_lines[key].setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
            self.settings_lines[key].setMinimumWidth(60)            
            self.settings_lines[key].setEnabled(False)
            self.settings_lines[key].textChanged.connect(parent.check_state)
            self.settings_lines[key].textChanged.emit(self.settings_lines[key].text())
            self.nmrset_box.layout().addWidget(self.settings_labels[key], i, 0)
            self.nmrset_box.layout().addWidget(self.settings_lines[key], i, 1)            # make entries for config items
            i+=1   
            
        # for key in parent.config.settings:   
            # parent.config.settings[key].line_edit.setEnabled(False)
            # parent.config.settings[key].line_edit.textChanged.connect(parent.check_state)
            # parent.config.settings[key].line_edit.textChanged.emit(parent.config.settings[key].line_edit.text())
            # self.nmrset_box.layout().addWidget(parent.config.settings[key].label, i, 0)
            # self.nmrset_box.layout().addWidget(parent.config.settings[key].line_edit, i, 1)            # make entries for config items
            # i+=1
                                         
        # for key in parent.config.other_settings:   
            # parent.config.other_settings[key].line_edit.textChanged.connect(parent.check_state)
            # parent.config.other_settings[key].line_edit.textChanged.emit(parent.config.other_settings[key].line_edit.text())
            # self.nmrset_box.layout().addWidget(parent.config.other_settings[key].label, i, 0)
            # self.nmrset_box.layout().addWidget(parent.config.other_settings[key].line_edit, i, 1)            # make entries for config items
            # i+=1

                
        self.main.addLayout(self.left, 0, 0)
        
        # Right Side
        self.right = QVBoxLayout()     
        self.pref_box = QGroupBox('Preferences')
        self.right.addWidget(self.pref_box)
        self.pref_box.setLayout(QGridLayout())   
        
        self.main.addLayout(self.right, 0, 1)
        self.setLayout(self.main)
            
            

    def divider(self):
        div = QLabel ('')
        div.setStyleSheet ("QLabel {background-color: #eeeeee; padding: 0; margin: 0; border-bottom: 0 solid #eeeeee; border-top: 1 solid #eeeeee;}")
        div.setMaximumHeight (2)
        return div               