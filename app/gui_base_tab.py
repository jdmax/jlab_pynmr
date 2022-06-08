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
import numpy as np
 

class BaseTab(QWidget): 
    '''Creates baseline tab'''   
    def __init__(self, parent):
        super(QWidget, self).__init__(parent)
        self.__dict__.update(parent.__dict__)  
        
        self.parent = parent
        
        
        self.sel_pen = pg.mkPen(color=(0, 0, 204), width=1.5)
        self.sub_pen = pg.mkPen(color=(0, 180, 0), width=1.5)
        
        # Populate Base Tab 
        self.main = QHBoxLayout()            # main layout
        
        # Left Side
        self.left = QVBoxLayout() 
                        
        # Baseline controls box     
        #self.basefile_path = self.eventfile.name
        self.basefile_path = ''
        self.basetime = 0
        self.recent_baselines_name = 'app/recent_baselines.json'
               
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
        self.recent_but = QPushButton('Show Recent Baselines')
        self.recent_but.clicked.connect(self.show_recent) 
        self.button_layout.addWidget(self.recent_but)         
        # Selection list
        self.event_model = QStandardItemModel()
        self.event_model.setHorizontalHeaderLabels(['Timestamp','Date','Time','Sweep Count','Center (MHz)','Mod (kHz)', 'Channel'])
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
        self.base_wid.showGrid(True, True)
        self.base_plot = self.base_wid.plot([], [], pen=self.sel_pen) 
        self.right.addWidget(self.base_wid)  
        self.sub_wid = pg.PlotWidget(title='Current Sweep minus Baseline')
        self.sub_wid.showGrid(True, True)
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
        
    def show_recent(self):
        '''Open recently used baselines file'''
        self.basefile_path = self.recent_baselines_name
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
                    date = dt.strftime("%m/%d/%y")
                    utcstamp = str(jd['stop_stamp'])
                                        
                    if 'base' in self.basefile_path:   # if we are using recent baseline file
                     self.events.update({utcstamp: {'channel':jd['channel'], 
                        'freq_list':jd['freq_list'], 'sweeps':jd['sweeps'], 
                        'phase':jd['phase'], 'cent_freq':jd['cent_freq'], 
                        'mod_freq':jd['mod_freq'], 'stop_time':dt, 'read_time':time,
                        'stop_stamp':jd['stop_stamp'],'date':jd['date'],
                         'base_file':self.basefile_path}})                    
                    else:               # if reading from eventfile
                        self.events.update({utcstamp: {'channel':jd['channel']['name'],
                            'freq_list':jd['freq_list'], 'sweeps':jd['sweeps'], 
                            'phase':jd['phase'], 'cent_freq':jd['channel']['cent_freq'], 
                            'mod_freq':jd['channel']['mod_freq'], 'stop_time':dt, 
                            'read_time':time, 'stop_stamp':jd['stop_stamp'],'date':date,
                            'base_file':self.basefile_path}})
                      
            self.status_bar.showMessage('Opened event file '+self.basefile_path)
            #self.event_model.clear()
            self.event_model.removeRows(0, self.event_model.rowCount())
            for i,stamp in enumerate(self.events.keys()):
                self.event_model.setItem(i,0,QStandardItem(str(stamp)))
                self.event_model.setItem(i,1,QStandardItem(self.events[stamp]['date']))
                self.event_model.setItem(i,2,QStandardItem(self.events[stamp]['read_time']))
                self.event_model.setItem(i,3,QStandardItem(str(self.events[stamp]['sweeps'])))
                self.event_model.setItem(i,4,QStandardItem(str(self.events[stamp]['cent_freq'])))
                self.event_model.setItem(i,5,QStandardItem(str(self.events[stamp]['mod_freq'])))
                self.event_model.setItem(i,6,QStandardItem(str(self.events[stamp]['channel'])))
 
    def select_event(self):    #,item):      
        '''Choose events selected from table, average to set as baseline and plot'''
        self.base_phase_avg = np.zeros(len(self.parent.event.scan.phase))
        freqs = []
        stamp = 0
        sweeps = 0
        self.base_stamps = []
        self.base_dict = {}
        for index in sorted(self.event_table.selectionModel().selectedRows()):   # average multiple events together, take timestamp of last event
            #print(index.row(), self.event_model.data(self.event_model.index(index.row(),0)))
            #print(self.event_model.data(self.event_model.index(item.row(),0)))
            stamp = self.event_model.data(self.event_model.index(index.row(),0))
            freqs = self.events[stamp]['freq_list']
            new_phase = np.array(self.events[stamp]['phase'])
            self.base_phase_avg = (self.base_phase_avg*sweeps + new_phase*self.events[stamp]['sweeps'])/(sweeps + self.events[stamp]['sweeps'])
            sweeps = sweeps + self.events[stamp]['sweeps']
            self.base_stamps.append(stamp)  
            self.base_dict = dict(self.events[stamp])    # using most entries from last baseline
        self.base_dict['sweeps'] = sweeps 
        self.base_dict['phase'] = self.base_phase_avg
        self.base_dict['base_stamps'] = self.base_stamps
        self.last_stamp = stamp
        #self.base_stamp = self.event_model.data(self.event_model.index(item.row(),0))        #self.base_plot.setData(self.events[self.base_stamp]['freq_list'],self.events[self.base_stamp]['phase'])  
        self.base_plot.setData(freqs, self.base_phase_avg)  
        sub = self.parent.event.scan.phase - self.base_phase_avg        
        self.sub_plot.setData(freqs,sub)    

    def set_base(self):
        '''Send baselines chosen to be set as the baseline for future events'''
        try:
            self.parent.new_base(self.base_dict)
        except Exception as e:
            self.status_bar.showMessage(f"Error setting baseline: {self.events[self.last_stamp]['read_time']} {e}")
        filename = re.findall('data.*\.txt', self.parent.event.base_file)
        self.curr_base_line.setText(filename[0]+', '+ str(self.parent.event.base_time))
        self.print_to_recent(self.base_dict)    
        
    def print_to_recent(self, base_dict):
        '''Prints selected baseline information to recent baselines file for reuse'''
        
        recentfile = open(self.recent_baselines_name, "a")
        for key, entry in base_dict.items():   
            if isinstance(entry, np.ndarray):       
                base_dict[key] = entry.tolist()            
            if isinstance(entry, datetime.datetime):
                base_dict.update({key:entry.__str__()})  # datetime to string  
        json_record = json.dumps(base_dict)
        recentfile.write(json_record+'\n')               # write to file as json line
        recentfile.close()
        

    def divider(self):
        div = QLabel ('')
        div.setStyleSheet ("QLabel {background-color: #eeeeee; padding: 0; margin: 0; border-bottom: 0 solid #eeeeee; border-top: 1 solid #eeeeee;}")
        div.setMaximumHeight (2)
        return div   
        
