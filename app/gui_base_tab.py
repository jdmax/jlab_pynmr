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
 

class BaseTab(QWidget): 
    '''Creates baseline tab'''   
    def __init__(self, parent):
        super(QWidget, self).__init__(parent)
        self.__dict__.update(parent.__dict__)  
        
        self.parent = parent
        
        
        self.sel_pen = pg.mkPen(color=(0, 0, 204), width=1)
        self.sub_pen = pg.mkPen(color=(0, 180, 0), width=1)
        
        # Populate Base Tab 
        self.main = QHBoxLayout()            # main layout
        
        # Left Side
        self.left = QVBoxLayout() 
                        
        # Baseline controls box     
        #self.basefile_path = self.eventfile.name
        self.basefile_path = ''
        self.basetime = 0
               
        self.base_box = QGroupBox('Baseline Controls')
        self.left.addWidget(self.base_box)
        self.base_box.setLayout(QVBoxLayout()) 
        self.base_top = QHBoxLayout()
        self.base_box.layout().addLayout(self.base_top)
        self.curr_base_label = QLabel('Currently selected baseline:')
        self.base_top.addWidget(self.curr_base_label)
        self.curr_base_line = QLineEdit(self.parent.event.base_file+', '+ self.parent.event.base_time.strftime('%H:%M:%S'), enabled=False)
        self.base_top.addWidget(self.curr_base_line)
        
        self.base_box.layout().addWidget(self.parent.divider()) 
        self.button_layout = QHBoxLayout()
        self.base_box.layout().addLayout(self.button_layout)
        self.open_but = QPushButton('Eventfile Selection Dialog')
        self.open_but.clicked.connect(self.pick_basefile) 
        self.button_layout.addWidget(self.open_but)
        self.last_but = QPushButton('Select Current Eventfile')
        self.last_but.clicked.connect(self.use_last) 
        self.button_layout.addWidget(self.last_but)        
        # Selection list
        self.event_model = QStandardItemModel()
        self.event_model.setHorizontalHeaderLabels(['UTC Timestamp','Time','Sweep Count','Center (MHz)','Modulation (kHz)', 'Channel'])
        self.event_table = QTableView()
        self.event_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.event_table.setSizeAdjustPolicy(QAbstractScrollArea.AdjustToContents)
        self.event_table.resizeColumnsToContents()
        self.event_table.setModel(self.event_model)
        self.event_table.clicked.connect(self.select_event)
        self.base_box.layout().addWidget(self.event_table)    
        self.base_but = QPushButton('Set Baseline')
        self.base_box.layout().addWidget(self.base_but)
        self.base_but.clicked.connect(self.set_base)
                
        self.main.addLayout(self.left)
        
        # Right Side
        self.right = QVBoxLayout()        
        self.base_wid = pg.PlotWidget(title='Selected Baseline')
        self.base_wid.showGrid(True,True)
        self.base_plot = self.base_wid.plot([], [], pen=self.sel_pen) 
        self.right.addWidget(self.base_wid)  
        self.sub_wid = pg.PlotWidget(title='Current Sweep minus Baseline')
        self.sub_wid.showGrid(True,True)
        self.sub_plot = self.sub_wid.plot([], [], pen=self.sub_pen) 
        self.right.addWidget(self.sub_wid)  
        
        self.main.addLayout(self.right)
        self.setLayout(self.main)
        
    def pick_basefile(self):
        '''Call open file dialog to get eventfile'''
        self.basefile_path = QFileDialog.getOpenFileName(self, "Open Eventfile")[0]        
        self.open_basefile()
        
    def use_last(self):
        '''Open most recent eventfile for baselines'''
        self.basefile_path = self.parent.eventfile.name
        self.open_basefile()
        
    def open_basefile(self):
        '''Open and list contents of eventfile'''
        self.events = {}
        if self.basefile_path:
            with open(self.basefile_path) as json_lines:
                for line in json_lines:
                    jd = json.loads(line.rstrip('\n|\r'))
                    dt = parse(jd['stop_time'])
                    time = dt.strftime("%H:%M:%S")
                    utcstamp = str(jd['stop_stamp'])
                    self.events.update({utcstamp: {'channel':jd['channel']['name'], 'freq_list':jd['freq_list'], 'sweeps':jd['sweeps'], 'phase':jd['phase'], 'cent_freq':jd['channel']['cent_freq'], 'mod_freq':jd['channel']['mod_freq'], 'stop_time':dt, 'read_time':time, 'stop_stamp':jd['stop_stamp'], 'base_file':self.basefile_path}})
                      
            self.status_bar.showMessage('Opened event file '+self.basefile_path)
            for i,stamp in enumerate(self.events.keys()):
                self.event_model.setItem(i,0,QStandardItem(str(stamp)))
                self.event_model.setItem(i,1,QStandardItem(self.events[stamp]['read_time']))
                self.event_model.setItem(i,2,QStandardItem(str(self.events[stamp]['sweeps'])))
                self.event_model.setItem(i,3,QStandardItem(str(self.events[stamp]['cent_freq'])))
                self.event_model.setItem(i,4,QStandardItem(str(self.events[stamp]['mod_freq'])))
                self.event_model.setItem(i,5,QStandardItem(str(self.events[stamp]['channel'])))
 
    def select_event(self,item):      
        '''Choose event selected from table, set as baseline and plot'''
        self.base_stamp = self.event_model.data(self.event_model.index(item.row(),0))      
        self.base_plot.setData(self.events[self.base_stamp]['freq_list'],self.events[self.base_stamp]['phase'])  
        sub = self.parent.event.scan.phase - self.events[self.base_stamp]['phase']        
        self.sub_plot.setData(self.events[self.base_stamp]['freq_list'],sub)

    def set_base(self):
        '''Send baseline chosen to be set as the baseline for future events'''
        try:
            self.parent.new_base(self.events[self.base_stamp])
        except Exception as e:
            self.status_bar.showMessage(f"Error setting baseline: {self.events[self.base_stamp]['read_time']} {e}")
        filename = re.findall('data.*\.txt', self.parent.event.base_file)
        self.curr_base_line.setText(filename[0]+', '+ str(self.parent.event.base_time))

    def divider(self):
        div = QLabel ('')
        div.setStyleSheet ("QLabel {background-color: #eeeeee; padding: 0; margin: 0; border-bottom: 0 solid #eeeeee; border-top: 1 solid #eeeeee;}")
        div.setMaximumHeight (2)
        return div   
        