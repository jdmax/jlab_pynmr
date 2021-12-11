'''PyNMR, J.Maxwell 2020
'''
import datetime
import glob
import json
import os
import numpy as np
import pprint as pp
from scipy import optimize
from PyQt5.QtWidgets import QWidget, QLabel, QGroupBox, QHBoxLayout, QVBoxLayout, QGridLayout, QLineEdit, QSpacerItem, QSizePolicy, QComboBox, QPushButton, QProgressBar, QStackedWidget, QDoubleSpinBox, QDateTimeEdit, QListWidget
import pyqtgraph as pg
from lmfit import Model

class ExplTab(QWidget):
    '''Creates analysis tab. '''

    def __init__(self, parent):
        super(QWidget,self).__init__(parent)
        self.__dict__.update(parent.__dict__)
        
        self.parent = parent
        
        self.event_vars_included = ['pol', 'cc', 'area']   # variables from the event to include in graph
        self.vars = []

        self.base_pen = pg.mkPen(color=(180, 0, 0), width=1.5)
        self.base2_pen = pg.mkPen(color=(0, 0, 150), width=1.5)
        self.base3_pen = pg.mkPen(color=(0, 180, 0), width=1.5)
        self.sub_pen = pg.mkPen(color=(180, 0, 0), width=1.5)
        self.sub2_pen = pg.mkPen(color=(0, 0, 150), width=1.5)
        self.sub3_pen = pg.mkPen(color=(0, 180, 0), width=1.5)
        
        self.main = QHBoxLayout()            # main layout
        self.setLayout(self.main)   
        
        # Left Side
        self.left = QVBoxLayout() 
        self.main.addLayout(self.left)
        
        # Datetime box box
        self.date_box = QGroupBox('Datetime Range Selection')
        self.date_box.setLayout(QHBoxLayout())
        self.start_label = QLabel("Start")
        self.date_box.layout().addWidget(self.start_label)
        self.left.addWidget(self.date_box)     
        self.start_dedit = QDateTimeEdit()  
        self.end_dedit = QDateTimeEdit()      
        self.start_dedit.setDateTime(self.parent.event.start_time - datetime.timedelta(seconds=3600)) 
        self.end_dedit.setDateTime(self.parent.event.start_time)   
        self.start_dedit.dateTimeChanged.connect(self.range_changed)         
        self.date_box.layout().addWidget(self.start_dedit)
        self.end_label = QLabel("End")
        self.date_box.layout().addWidget(self.end_label)  
        self.end_dedit.dateTimeChanged.connect(self.range_changed)   
        self.date_box.layout().addWidget(self.end_dedit)
               
        # Variable box
        self.var_box = QGroupBox('Variable Selection')
        self.var_box.setLayout(QVBoxLayout())
        self.left.addWidget(self.var_box)
        self.var_list = QListWidget() 
        self.var_list.setSelectionMode(QListWidget.MultiSelection)
        self.var_list.itemSelectionChanged.connect(self.update_plot)
        self.var_box.layout().addWidget(self.var_list)    
           
        # Right Side
        self.right = QVBoxLayout() 
        self.main.addLayout(self.right)
        
        self.time_axis = pg.DateAxisItem(orientation='bottom')  
        self.strip_wid = pg.PlotWidget(title='', axisItems={'bottom': self.time_axis})
        self.strip_wid.showGrid(True,True)
        self.strip_wid.addLegend(offset=(0.5, 0))
        self.right.addWidget(self.strip_wid)

        # Bounds Box
        self.bnd_box = QGroupBox('Bounds')
        self.bnd_box.setLayout(QVBoxLayout())
        self.right.addWidget(self.bnd_box)

    def range_changed(self):
        '''Update time range of events used. Looks through data directory to pull in required events
        '''
        self.start = self.start_dedit.dateTime().toPyDateTime()
        self.end = self.end_dedit.dateTime().toPyDateTime()
        self.all_files = glob.glob(f"{self.config_dict['settings']['event_dir']}/*.txt")
        self.current_name = ''
        self.current_time = datetime.datetime.strptime('Jan 1 2000  12:00AM', '%b %d %Y %I:%M%p')
        self.included = []
        for file in self.all_files:      
            name = file.replace(self.config_dict['settings']['event_dir']+'\\','')
            if 'current' in name:
                name = name.replace('current_', '').replace('.txt','')
                thistime = datetime.datetime.strptime(name,"%Y-%m-%d_%H-%M-%S")
                if self.current_time < thistime:
                    self.current_name = file
            else:
                start, stop = name.split('__')
                stop = stop.replace('.txt', '')
                start_dt = datetime.datetime.strptime(start,"%Y-%m-%d_%H-%M-%S")
                stop_dt = datetime.datetime.strptime(stop,"%Y-%m-%d_%H-%M-%S")
                if self.start < start_dt < self.end  or self.start < stop_dt < self.end:
                    self.included.append(file)
        self.included.append(self.current_name)
        #[print(l) for l in self.included]
        
        load = {}
        for eventfile in self.included:
            with open(eventfile, 'r') as f:
                for line in f:
                    temp = json.loads(line)
                    s = temp['stop_time']
                    line_stoptime = datetime.datetime.strptime(s[:26], '%Y-%m-%d %H:%M:%S.%f')
                    load[line_stoptime] = {}
                    if self.start < line_stoptime < self.end:
                        for k in temp.keys():
                            if k in self.event_vars_included:
                                load[line_stoptime][k] = temp[k]
                            if 'epics_reads' in k:
                                for key, val in temp[k].items():
                                    load[line_stoptime][key] = val        
        self.data = {}
        for time in load.keys():    # take loaded data in datetime:var:value and make var:numpy2d dict
            for var in load[time].keys():
                try:
                    self.data[var]= np.concatenate((self.data[var], np.array([[time.timestamp(), load[time][var]]])))
                except KeyError:
                    self.data[var] = np.array([[time.timestamp(), load[time][var]]])
        
        self.var_list.clear()
        self.var_list.addItems(self.data.keys())
    
    def update_plot(self):
        '''Update strip plots. 
        '''            
        self.strip_wid.clear()    
        self.strip_plot = {}
        i = 0
        for var in self.var_list.selectedItems():
            self.strip_plot[var.text()] = self.strip_wid.plot([], [], name = var.text(), pen=pg.mkPen(i)) 
            i += 1
            #print(self.data[var.text()])
            self.strip_plot[var.text()].setData(self.data[var.text()])
  
        