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

class CompareTab(QWidget): 
    '''Creates settings tab'''   
    def __init__(self, parent):
        super(QWidget,self).__init__(parent)
        self.__dict__.update(parent.__dict__)  
        
        self.parent = parent
        
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
        self.controls_box = QGroupBox('NMR Controls')
        self.controls_box.setLayout(QGridLayout())
        self.left.addWidget(self.controls_box)
        self.run_button = QPushButton("Run",checkable=True)       # Run button
        self.controls_box.layout().addWidget(self.run_button, 0, 0)
        self.run_button.setEnabled(False)
        self.run_button.clicked.connect(self.run_pushed)
        self.progress_bar = QProgressBar()                                  # Progress bar
        self.progress_bar.setTextVisible(False)
        self.controls_box.layout().addWidget(self.progress_bar, 0, 1)
        self.fpga_label = QLabel("FPGA Events:")
        self.controls_box.layout().addWidget(self.fpga_label, 1, 0)
        self.fpga_value = QLineEdit('4')
        self.fpga_value.setValidator(QIntValidator(1,100))
        self.controls_box.layout().addWidget(self.fpga_value, 1, 1)    
        self.nidaq_label = QLabel("NIDAQ Events:")
        self.controls_box.layout().addWidget(self.nidaq_label, 2, 0)
        self.nidaq__value = QLineEdit('4')
        self.nidaq__value.setValidator(QIntValidator(1,100))
        self.controls_box.layout().addWidget(self.nidaq__value, 2, 1)
                
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
        
        
        
        
        
    def run_pushed(self):
        '''Start main loop if conditions met'''
               
        if self.run_button.isChecked():        
            self.parent.status_bar.showMessage('Running sweeps...')
            #self.abort_button.setEnabled(True)
            self.lock_button.setEnabled(False)
            self.run_button.setText('Finish')
            self.start_thread()
            self.parent.run_toggle()
                   
        else:
            if self.run_thread.isRunning:
                self.run_button.setText('Finishing...')
                self.run_button.setEnabled(False)
        
