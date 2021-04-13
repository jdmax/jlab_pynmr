'''PyNMR, J.Maxwell 2020
'''
import datetime
import re
import json
from dateutil.parser import parse
from PyQt5.QtWidgets import QWidget, QLabel, QGroupBox, QHBoxLayout, QVBoxLayout, QGridLayout, QLineEdit, QSpacerItem, QSizePolicy, QComboBox, QPushButton, QTableView, QAbstractItemView, QAbstractScrollArea, QFileDialog
from PyQt5.QtCore import QThread, pyqtSignal,Qt
from PyQt5.QtGui import QIntValidator, QDoubleValidator, QValidator, QStandardItemModel, QStandardItem
import pyqtgraph as pg
 
from app.magnet_control import MagnetControl

class MagTab(QWidget): 
    '''Creates manget control tab'''   
    def __init__(self, parent):
        super(QWidget, self).__init__(parent)
        self.__dict__.update(parent.__dict__)  
        
        self.parent = parent
        self.mc = MagnetControl()
                
        # Populate Magnt Tab 
        self.main = QHBoxLayout()            # main layout
        
        # Left Side
        self.left = QVBoxLayout() 
        
        self.mag_box = MagnetBox(self)
        self.left.addWidget(self.mag_box)  
                
    def divider(self):
        div = QLabel ('')
        div.setStyleSheet ("QLabel {background-color: #eeeeee; padding: 0; margin: 0; border-bottom: 0 solid #eeeeee; border-top: 1 solid #eeeeee;}")
        div.setMaximumHeight (2)
        return div 

class MagnetBox(QGroupBox):
    '''Magnet control gui'''
    def __init__(self, parent):
        super(QWidget,self).__init__(parent)   
        self.__dict__.update(parent.__dict__)   
        self.divider = parent.divider    
        self.mc = parent.mc
                
        self.setLayout(QVBoxLayout())    
        self.setTitle('Magnet Controls')         
        self.mag_top = QHBoxLayout()
        self.layout().addLayout(self.mag_top)          
        
        self.stat_lay = QGridLayout()
        self.mag_top.addLayout(self.stat_lay)        
        i = 0 
        self.stat_values = {}
        for key, stat in self.mc.status.items():
            self.stat_lay.addWidget(QLabel(stat['text']+':'),i,0)
            self.stat_values[key] = QLineEdit(stat['value'])
            self.stat_values[key].setEnabled(False)
            self.stat_lay.addWidget(self.stat_values[key],i,1)            
            i+=1
            
        self.spacer1 = QSpacerItem(50, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.mag_top.addItem(self.spacer1)
        
        self.top_right = QVBoxLayout()
        self.mag_top.addLayout(self.top_right)  
        
        self.conn_lay = QGridLayout()
        self.top_right.layout().addLayout(self.conn_lay)
        
        self.port_comb = QComboBox()
        self.conn_lay.addWidget(self.port_comb,0,0)
        self.port_opts = []
        for opt in self.mc.get_ports():
            string = opt[1]
            self.port_opts.append(opt[0])
            self.port_comb.addItem(string)
            
        self.port_connect = QPushButton('Connect to Port', checkable=True)
        self.conn_lay.addWidget(self.port_connect,1,0)
        
        self.top_right.addWidget(self.divider())
        
        self.set_lay = QGridLayout()
        self.top_right.layout().addLayout(self.set_lay)        
        self.set_lay.addWidget(QLabel('Upper Limit:'),0,0)
        self.up_lim = QLineEdit('0',enabled=False)
        self.up_lim.setValidator(QDoubleValidator(0.,190.,3))
        self.set_lay.addWidget(self.up_lim,0,1)   
        self.set_lay.addWidget(QLabel('Lower Limit:'),1,0)
        self.low_lim = QLineEdit('0',enabled=False)
        self.low_lim.setValidator(QDoubleValidator(0.,190.,3))
        self.set_lay.addWidget(self.low_lim,1,1)        
        self.set_but = QPushButton('Set',enabled=False)
        self.set_lay.addWidget(self.set_but,2,1)
        self.set_but.clicked.connect(lambda: self.set_lims())
            
        self.layout().addWidget(self.divider()) 

        self.but_lay = QGridLayout()
        self.layout().addLayout(self.but_lay)
        self.sw_but = QPushButton('Turn Heater On', checkable=True,enabled=False)
        self.sw_but.clicked.connect(self.sw_tog)
        self.but_lay.addWidget(self.sw_but, 0, 0)    
        self.fast_but = QPushButton('Turn Fast Sweep Mode On', checkable=True,enabled=False)
        self.fast_but.clicked.connect(lambda: self.mc.fast(self.fast_but.isChecked())) 
        self.but_lay.addWidget(self.fast_but, 1, 0)  
        self.swup_but = QPushButton('Sweep Up',enabled=False)
        self.swup_but.clicked.connect(lambda: self.set('sw_up',self.mc.fast_mode))
        self.but_lay.addWidget(self.swup_but, 0, 1)  
        self.swdown_but = QPushButton('Sweep Down',enabled=False)
        self.swdown_but.clicked.connect(lambda: self.set('sw_down',self.mc.fast_mode))
        self.but_lay.addWidget(self.swdown_but, 1, 1) 
        self.swpause_but = QPushButton('Pause',enabled=False)        
        self.swpause_but.clicked.connect(lambda: self.set('sw_pause',''))
        self.but_lay.addWidget(self.swpause_but, 2, 0) 
        self.swzero_but = QPushButton('Sweep to Zero',enabled=False)
        self.swzero_but.clicked.connect(lambda: self.set('sw_zero',self.mc.fast_mode))
        self.but_lay.addWidget(self.swzero_but, 2, 1) 
        
        self.port_connect.clicked.connect(lambda: self.open_connection())
        
        
        
    def set_lims(self):
        '''Handle set button click'''
        self.set('up_lim',self.up_lim.text())
        self.set('low_lim',self.low_lim.text())
        
    def set(self, channel, value):
        '''Sends command and reads status, starts thread to monitor values if needed'''
        if self.mc.s.is_open:
            self.mc.write_port(self.mc.commands[channel]+str(value))        
            time.sleep(0.05)
            self.mc.read_all() 
            self.update_status()
            self.status_bar.showMessage('Set magnet:'+self.mc.commands[channel]+str(value))
        if 'pause' not in self.mc.status['sweep']['value']:
            #if not self.mag_thread.isRunning() 
            print('start thread')
            self.mag_thread = UpdateMag(self.mc)            
            self.mag_thread.stat_now.connect(lambda: self.update_status())
            self.mag_thread.start()
            
    def open_connection(self):
        '''Open connection to serial port, turn on controls if it works'''
        if self.port_connect.isChecked():
            self.mc.set_port(self.port_opts[self.port_comb.currentIndex()])        
            try: 
                self.mc.open_port()
                self.update_status()
            except:
                self.status_bar.showMessage('Error connecting to serial port: '+str(self.port_comb.currentText()))
                raise
            if self.mc.s.is_open:#  and 'CS4' in self.mc.status['id']:
                self.status_bar.showMessage("Opened connection to "+str(self.port_comb.currentText())+".")
                self.sw_but.setEnabled(True)
                self.swup_but.setEnabled(True)
                self.swdown_but.setEnabled(True)
                self.swpause_but.setEnabled(True)
                self.swzero_but.setEnabled(True)
                self.up_lim.setEnabled(True)
                self.low_lim.setEnabled(True)
                self.set_but.setEnabled(True)
                self.fast_but.setEnabled(True)
                self.port_connect.setText('Disconnect')
        else:
            self.mc.close_port()
            self.port_connect.setText('Connect to Port')
            self.sw_but.setEnabled(False)
            self.swup_but.setEnabled(False)
            self.swdown_but.setEnabled(False)
            self.swpause_but.setEnabled(False)
            self.swzero_but.setEnabled(False)
            self.up_lim.setEnabled(False)
            self.low_lim.setEnabled(False)
            self.set_but.setEnabled(False)
            self.fast_but.setEnabled(False)
            
            
    def update_status(self):
        '''Updates the widgets displaying the magnet status'''
        for key, stat in self.mc.status.items():
            # if 'switch' not in key:
            self.stat_values[key].setText(stat['value'])
            # else:
                # if '1' in stat['value']:
                    # self.sw_label.setText('Heater Status: On')
                # else:
                    # self.sw_label.setText('Heater Status: Off')
        if 'pause' in self.mc.status['sweep']['value']: 
            try: self.mag_thread.terminate()
            except: pass
    def sw_tog(self):
        '''Toggle switchheater'''
        sender = self.sender()
        if sender.isChecked():
            sender.setText('Turn Heater Off')
        else:    
            sender.setText('Turn Heater On')
  
  
class UpdateMag(QThread):
    '''Thread to update the magnet status'''
    stat_now = pyqtSignal()
    def __init__(self, mc):
        '''Make new thread instance for monitoring magnet status'''
        QThread.__init__(self)
        self.mc = mc
    def __del__(self):
        self.wait()
    def run(self):
        while True:
            print('Ran mag update')
            self.mc.read_all()
            self.stat_now.emit() 
            self.msleep(1000)               