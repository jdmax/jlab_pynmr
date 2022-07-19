'''PyNMR, J.Maxwell 2020
'''
import datetime
import re
import json
import os
from dateutil.parser import parse
from PyQt5.QtWidgets import QWidget, QLabel, QGroupBox, QHBoxLayout, QVBoxLayout, QGridLayout, QLineEdit, QSpacerItem, QSizePolicy, QComboBox, QPushButton, QTableView, QAbstractItemView, QAbstractScrollArea, QFileDialog
from PyQt5.QtCore import QThread, pyqtSignal,Qt
from PyQt5.QtGui import QIntValidator, QDoubleValidator, QValidator, QStandardItemModel, QStandardItem
import pyqtgraph as pg
import numpy as np
 

class SuperTab(QWidget): 
    '''Creates super te tab'''   
    def __init__(self, parent):
        super(QWidget, self).__init__(parent)
        self.__dict__.update(parent.__dict__)  
        
        self.parent = parent
        
        
        self.sel_pen = pg.mkPen(color=(0, 0, 204), width=1.5)
        self.sub_pen = pg.mkPen(color=(0, 180, 0), width=1.5)
        
        self.eventfile_path = ''
        self.to_avg = {}
        
        # Populate Super TE Tab 
        self.main = QHBoxLayout()            # main layout
        
        # Left Side
        self.left = QVBoxLayout() 
                        
        # Baseline controls box     
               
        self.base_box = QGroupBox('Build Super TE')
        self.left.addWidget(self.base_box)
        self.base_box.setLayout(QVBoxLayout()) 
        self.base_top = QHBoxLayout()
        self.base_box.layout().addLayout(self.base_top)
         
        self.button_layout = QHBoxLayout()
        self.base_box.layout().addLayout(self.button_layout)
        self.open_but = QPushButton('Eventfile Selection Dialog')
        self.open_but.clicked.connect(self.pick_eventfile) 
        self.button_layout.addWidget(self.open_but)
        self.last_but = QPushButton('Open Current Eventfile')
        self.last_but.clicked.connect(self.use_last) 
        self.button_layout.addWidget(self.last_but)     

        self.base_box.layout().addWidget(self.parent.divider()) 
        
        self.lists_layout = QHBoxLayout()
        self.base_box.layout().addLayout(self.lists_layout)
        
        
        # Selection list
        self.candidate_model = QStandardItemModel()
        self.candidate_model.setHorizontalHeaderLabels(['Time','Sweep Count'])
        self.candidate_table = QTableView()
        self.candidate_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.candidate_table.setSizeAdjustPolicy(QAbstractScrollArea.AdjustToContents)
        self.candidate_table.resizeColumnsToContents()
        self.candidate_table.setModel(self.candidate_model)
        self.candidate_table.clicked.connect(self.candidate_select)
        self.candidate_table.doubleClicked.connect(self.candidate_double)
        self.lists_layout.addWidget(self.candidate_table)    
        
        self.chosen_model = QStandardItemModel()
        self.chosen_model.setHorizontalHeaderLabels(['Time','Sweep Count'])
        self.chosen_table = QTableView()
        self.chosen_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.chosen_table.setSizeAdjustPolicy(QAbstractScrollArea.AdjustToContents)
        self.chosen_table.resizeColumnsToContents()
        self.chosen_table.setModel(self.chosen_model)
        self.chosen_table.doubleClicked.connect(self.chosen_double)                
        self.lists_layout.addWidget(self.chosen_table)    
        
        self.main.addLayout(self.left)
        
        # Right Side
        self.right = QVBoxLayout()        
        self.base_wid = pg.PlotWidget(title='Currently Selected Signal')
        self.base_wid.showGrid(True, True)
        self.base_plot = self.base_wid.plot([], [], pen=self.sel_pen) 
        self.right.addWidget(self.base_wid)  
        self.sub_wid = pg.PlotWidget(title='Chosen Signals Averaged')
        self.sub_wid.showGrid(True, True)
        self.sub_plot = self.sub_wid.plot([], [], pen=self.sub_pen) 
        self.right.addWidget(self.sub_wid)  
        
        self.main.addLayout(self.right)
        self.setLayout(self.main)
        
    def use_last(self):
        '''Open most recent eventfile for baselines'''
        self.eventfile_path = self.parent.eventfile.name
        self.open_eventfile()
        
    def pick_eventfile(self):
        '''Call open file dialog to get eventfile'''
        self.eventfile_path = QFileDialog.getOpenFileName(self, "Open Eventfile")[0]       
        self.open_eventfile() 
                
    def open_eventfile(self):
        '''Open and list contents of eventfile'''
        self.events = {}
        if self.eventfile_path:
            with open(self.eventfile_path) as json_lines:
                for line in json_lines:
                    jd = json.loads(line.rstrip('\n|\r'))
                    dt = parse(jd['stop_time'])
                    time = dt.strftime("%H:%M:%S")
                    date = dt.strftime("%m/%d/%y")
                    utcstamp = str(jd['stop_stamp'])
                    self.events.update({utcstamp: {'channel':jd['channel']['name'],
                        'freq_list':jd['freq_list'], 'sweeps':jd['sweeps'], 
                        'phase':jd['phase'], 'cent_freq':jd['channel']['cent_freq'], 
                        'mod_freq':jd['channel']['mod_freq'], 'stop_time':dt, 
                        'read_time':time, 'stop_stamp':jd['stop_stamp'],'date':date,'label':jd['label'],
                        'base_file':self.basefile_path},'polysub':jd['polysub']})
            #self.event_model.clear()
            self.event_model.removeRows(0, self.event_model.rowCount())
            for i,stamp in enumerate(self.events.keys()):
                self.event_model.setItem(i,0,QStandardItem(self.events[stamp]['read_time']))
                self.event_model.setItem(i,1,QStandardItem(str(self.events[stamp]['sweeps'])))
 
    def candidate_select(self):    #,item):      
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
        
    def candidate_double(self): 
        pass
        
    def chosen_double(self): 
        pass
 
        

    def divider(self):
        div = QLabel ('')
        div.setStyleSheet ("QLabel {background-color: #eeeeee; padding: 0; margin: 0; border-bottom: 0 solid #eeeeee; border-top: 1 solid #eeeeee;}")
        div.setMaximumHeight (2)
        return div   
        
