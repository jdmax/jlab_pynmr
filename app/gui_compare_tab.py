'''PyNMR, J.Maxwell 2020
'''
import datetime
import time
import pytz
import numpy as np
from PyQt5.QtWidgets import QWidget, QLabel, QGroupBox, QHBoxLayout, QVBoxLayout, QGridLayout, QLineEdit, QSpacerItem, QSizePolicy, QComboBox, QPushButton, QTableView, QAbstractItemView, QAbstractScrollArea, QProgressBar
from PyQt5.QtGui import QIntValidator, QDoubleValidator, QValidator, QStandardItemModel, QStandardItem
import pyqtgraph as pg
from scipy import optimize
 
from app.te_calc import TE
from app.rf_switch import RFSwitch

class CompareTab(QWidget): 
    '''Creates settings tab'''   
    def __init__(self, parent):
        super(QWidget,self).__init__(parent)
        self.__dict__.update(parent.__dict__)  
        
        self.parent = parent
        self.settings = parent.settings
        
        self.raw_pen = pg.mkPen(color=(250, 0, 0), width=1.5)
        self.sub_pen = pg.mkPen(color=(0, 0, 204), width=1.5)
        self.fit_pen = pg.mkPen(color=(255, 255, 0), width=3)
        self.fin_pen = pg.mkPen(color=(0, 160, 0), width=1.5)
        self.res_pen = pg.mkPen(color=(190, 0, 190), width=2)
        self.pol_pen = pg.mkPen(color=(250, 0, 0), width=1.5)
        self.asym_pen = pg.mkPen(color=(250, 175, 0), width=1)
        self.wave_pen = pg.mkPen(color=(153, 204, 255), width=1.5)
        self.beam_brush = pg.mkBrush(color=(0,0,160, 10))
        self.beam_pen = pg.mkPen(color=(255,255,255, 0))
        
        self.main = QHBoxLayout()            # main layout
        
        # Left Side
        self.left = QVBoxLayout() 
                        
                   
        # Populate Controls box
        self.controls_box = QGroupBox('Q-Meter Switching Controls')
        self.controls_box.setLayout(QGridLayout())
        self.left.addWidget(self.controls_box)
        self.run_button = QPushButton("Run Compare",checkable=True)       # Run button
        self.controls_box.layout().addWidget(self.run_button, 0, 0)
        self.run_button.setEnabled(True)
        self.run_button.clicked.connect(self.run_pushed)
        self.progress_bar = QProgressBar()                                  # Progress bar
        self.progress_bar.setTextVisible(False)
        self.controls_box.layout().addWidget(self.progress_bar, 0, 1)
        self.iter_label = QLabel("Number of Events before Switch:")
        self.controls_box.layout().addWidget(self.iter_label, 1, 0)
        self.iter_value = QLineEdit('2')
        self.iter_value.setValidator(QIntValidator(1,100))
        self.controls_box.layout().addWidget(self.iter_value, 1, 1)
        self.label = QLabel("Switches between FPGA and NIDAQ.")
        self.controls_box.layout().addWidget(self.label, 2, 1)
                
        self.main.addLayout(self.left)
        
        # Right Side
        self.right = QVBoxLayout()    
        # Populate pol v time plot
        self.time_axis = pg.DateAxisItem(orientation='bottom')
        self.pol_time_wid = pg.PlotWidget(
            title='', axisItems={'bottom': self.time_axis}
        )
        self.legend = self.pol_time_wid.addLegend()
        self.pol_time_wid.showGrid(True,True, alpha = 0.2)
        self.pol_time_plot = self.pol_time_wid.plot([], [], pen=self.pol_pen) 
        #self.pol_time_wid.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Expanding)
        self.right.addWidget(self.pol_time_wid)
        
        # Populate pol v time plot
        self.time_axis2 = pg.DateAxisItem(orientation='bottom')
        self.pol_time_wid2 = pg.PlotWidget(
            title='', axisItems={'bottom': self.time_axis2}
        )
        self.legend2 = self.pol_time_wid2.addLegend()
        self.pol_time_wid2.showGrid(True,True, alpha = 0.2)
        self.pol_time_plot2 = self.pol_time_wid2.plot([], [], pen=self.pol_pen) 
        #self.pol_time_wid.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Expanding)
        self.right.addWidget(self.pol_time_wid2)
        
        self.main.addLayout(self.right)
        self.setLayout(self.main)   
        
        self.iteration = 0
        self.switch = True   # True is FPGA, False is NIDAQ
        self.compare_on = False
        self.default_mode = self.parent.config.settings['daq_type']
        
        self.rf = RFSwitch(self.settings['rf_switch']['ip'], self.settings['rf_switch']['port'], self.settings['rf_switch']['timeout'])
        
    def run_pushed(self):
        '''Emulate pushing button on Run Tab'''
               
        if self.run_button.isChecked():   
            self.compare_on = True
            self.run_button.setText('Finish')
            self.parent.run_tab.run_button.toggle()  # hit the button to run
            self.parent.run_tab.run_pushed()          
            self.parent.run_toggle()
                   
        else:
            self.compare_on = False
            self.run_button.setText('Finishing...')
            self.parent.run_toggle()
            self.run_button.setEnabled(False)
            self.parent.run_tab.run_button.toggle() 
            self.parent.run_tab.run_pushed()   
        
    def mode_switch(self):
        '''Decide which mode we should be in, flip switch and change config 
        '''       
        if self.compare_on:      # If we are running compare mode
            self.iteration += 1
            if self.iteration > int(self.iter_value.text()):   # we have exceed iterations, switch
                self.iteration = 0
                if self.switch:  # Switch to NIDAQ
                    self.switch = False
                    self.rf.set_switch('A',1)
                    self.rf.set_switch('B',1)
                    self.parent.config.settings['daq_type'] = 'NIDAQ'       
                                 
                    
                if self.switch:  # switch back to FPGA
                    self.switch = True
                    self.rf.set_switch('A',0)
                    self.rf.set_switch('B',0)
                    self.parent.config.settings['daq_type'] = self.default_mode   
            
            str = 'FPGA' if self.switch else 'NIDAQ'
            self.label.setText(f"Running {str} events. {int(self.iter_value.text()) - self.iteration} remaining.") 
    def mode_done(self):
        '''Done, set it all back to defaults
        '''       
        self.iteration = 0
        self.compare_on = False
        self.switch = True        
        self.rf.set_switch('A',0)
        self.rf.set_switch('B',0)
        self.parent.config.settings['daq_type'] = self.default_mode    
        self.run_button.setText('Run Compare')
        str = 'FPGA' if self.switch else 'NIDAQ'
        self.label.setText(f"Running {str} events. {int(self.iter_value.text()) - self.iteration} remaining.") 

        
        
        