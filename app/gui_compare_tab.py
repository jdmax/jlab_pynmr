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
from app.daq import RS_Connection
 
from app.te_calc import TE
from app.rf_switch import RFSwitch
from app.classes import Baseline

class CompareTab(QWidget): 
    '''Creates settings tab'''   
    def __init__(self, parent):
        super(QWidget,self).__init__(parent)
        self.__dict__.update(parent.__dict__)  
        
        self.parent = parent
        self.settings = parent.settings
        
        self.time_pen = pg.mkPen(color=(0, 0, 204), width=1.5)
        self.fit1_pen = pg.mkPen(color=(0, 0, 150), width=1.5)
        self.zoom_pen = pg.mkPen(color=(0, 180, 0), width=1.5)
        self.fit2_pen = pg.mkPen(color=(0, 130, 0), width=1.5)
        
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

        self.range_label = QLabel('History to Show (min):')
        self.controls_box.layout().addWidget(self.range_label, 1, 0)
        self.range_value = QLineEdit('60')
        self.range_value.setValidator(QIntValidator(1,10000))
        self.controls_box.layout().addWidget(self.range_value, 1, 1)
        self.iter_label = QLabel("Number of Events before Switch:")
        self.controls_box.layout().addWidget(self.iter_label, 2, 0)
        self.iter_value = QLineEdit('2')
        self.iter_value.setValidator(QIntValidator(1,100))
        self.controls_box.layout().addWidget(self.iter_value, 2, 1)

        self.channels_label = QLabel('Choose channels:')
        self.controls_box.layout().addWidget(self.channels_label, 3, 0)
        self.channel1_combo = QComboBox()
        self.channel1_combo.addItems(self.parent.channels)
        self.controls_box.layout().addWidget(self.channel1_combo, 4, 0)
        self.channel2_combo = QComboBox()
        self.channel2_combo.addItems(self.parent.channels)
        self.controls_box.layout().addWidget(self.channel2_combo, 4, 1)


        
        self.tune_label = QLabel('Channel Diode Tunes:')
        self.controls_box.layout().addWidget(self.tune_label, 7, 0)
        self.tune1_value = QLineEdit('0.0')
        self.tune1_value.setValidator(QDoubleValidator(0,100,6))
        self.controls_box.layout().addWidget(self.tune1_value, 8, 0)
        self.tune2_value = QLineEdit('0.0')
        self.tune2_value.setValidator(QDoubleValidator(0,100,6))
        self.controls_box.layout().addWidget(self.tune2_value, 8, 1)

        self.base_label = QLabel('Channel Baselines:')
        self.controls_box.layout().addWidget(self.base_label, 5, 0)
        self.base1_button = QPushButton('Select Base 1')
        self.base1_button.clicked.connect(self.base1_pushed)
        self.controls_box.layout().addWidget(self.base1_button, 6, 0)
        self.base2_button = QPushButton('Select Base 2')
        self.base2_button.clicked.connect(self.base2_pushed)
        self.controls_box.layout().addWidget(self.base2_button, 6, 1)

        self.cc_label = QLabel('Channel CCs:')
        self.controls_box.layout().addWidget(self.cc_label, 9, 0)
        self.cc1_value = QLineEdit('1.0')
        self.cc1_value.setValidator(QDoubleValidator(-100,100,6))
        self.controls_box.layout().addWidget(self.cc1_value, 10, 0)
        self.cc2_value = QLineEdit('1.0')
        self.cc2_value.setValidator(QDoubleValidator(-100,100,6))
        self.controls_box.layout().addWidget(self.cc2_value, 10, 1)

        self.left.addWidget(self.parent.divider())
        self.label = QLabel("Switches between two given channels.")
        self.left.layout().addWidget(self.label)

        self.main.addLayout(self.left)
        
        # Right Side
        self.right = QVBoxLayout()    
        # Populate pol v time plot
        self.time_axis = pg.DateAxisItem(orientation='bottom')    
        self.time_wid = pg.PlotWidget(title='Area vs. Time', axisItems={'bottom': self.time_axis})
        self.time_wid.showGrid(True,True)
        self.time_plot = self.time_wid.plot([], [], pen=self.time_pen) 
        self.right.addWidget(self.time_wid)
        
        # Populate pol v time plot
        self.time_axis2 = pg.DateAxisItem(orientation='bottom')    
        self.time_wid2 = pg.PlotWidget(title='Area vs. Time', axisItems={'bottom': self.time_axis2})
        self.time_wid2.showGrid(True,True)
        self.time_plot2 = self.time_wid2.plot([], [], pen=self.time_pen) 
        self.right.addWidget(self.time_wid2)
        
        self.main.addLayout(self.right)
        self.setLayout(self.main)   
        
        self.iteration = 0
        self.switch = True   # True is FPGA, False is NIDAQ
        self.compare_on = False
        self.base1 = self.parent.baseline
        self.base2 = self.parent.baseline
        
        self.rf = RFSwitch(self.settings['rf_switch']['ip'], self.settings['rf_switch']['port'], self.settings['rf_switch']['timeout'])
        
    def run_pushed(self):
        '''Emulate pushing button on Run Tab'''
               
        if self.run_button.isChecked():
            self.iteration = 0
            self.switch = True   # True is FPGA, False is NIDAQ
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

    def base1_pushed(self, i):
        '''Selected current baseline for this channel
        '''
        self.base1 = Baseline(self.parent.config, self.parent.baseline.__dict__)  # make new baseline from current
        self.base1_button.setText(self.base1.stop_time.strftime("%m/%d, %H:%M:%S"))
        
    def base2_pushed(self, i):
        '''Selected current baseline for this channel
        '''
        self.base2 = Baseline(self.parent.config, self.parent.baseline.__dict__)
        self.base2_button.setText(self.base2.stop_time.strftime("%m/%d, %H:%M:%S"))
        
    def mode_switch(self):
        '''Decide which mode we should be in, flip switch and change config 
        '''       
        if self.compare_on:      # If we are running compare mode
            self.iteration += 1
            if self.iteration > int(self.iter_value.text())-1:   # we have exceeded iterations, switch
                self.iteration = 0
                if self.switch:  # Switch to Channel 2
                    self.switch = False
                    self.rf.set_switch('A',1)
                    self.rf.set_switch('B',1)
                    #self.parent.channel_change(self.channel2_combo.currentIndex())
                    self.parent.run_tab.channel_combo.setCurrentIndex(self.channel2_combo.currentIndex())
                    self.parent.set_cc(float(self.cc2_value.text()), self.parent.event)
                    self.parent.baseline = self.base2
                    #self.parent.tune_tab.send_to_dac(float(self.tune2_value.text())/100, 2)
                    self.parent.tune_tab.diode_spin.setValue(float(self.tune2_value.text()))
                    self.label.setText(f"Running {self.channel2_combo.currentText()} events. {int(self.iter_value.text()) - self.iteration} remaining.")

                else:  # switch to channel 1
                    self.switch = True
                    self.rf.set_switch('A',0)
                    self.rf.set_switch('B',0)
                    #self.parent.channel_change(self.channel1_combo.currentIndex())
                    self.parent.run_tab.channel_combo.setCurrentIndex(self.channel1_combo.currentIndex())
                    self.parent.set_cc(float(self.cc1_value.text()), self.parent.event)
                    self.parent.baseline = self.base1
                    #self.parent.tune_tab.send_to_dac(float(self.tune1_value.text())/100, 2)
                    self.parent.tune_tab.diode_spin.setValue(float(self.tune1_value.text()))
                    self.label.setText(f"Running {self.channel1_combo.currentText()} events. {int(self.iter_value.text()) - self.iteration} remaining.")

    def mode_done(self):
        '''Done, set it all back to channel 1
        '''       
        self.iteration = 0
        self.compare_on = False
        self.switch = True        
        self.rf.set_switch('A',0)
        self.rf.set_switch('B',0)
        self.parent.baseline = self.base1
        #self.parent.channel_change(self.channel1_combo.currentIndex())
        self.parent.run_tab.channel_combo.setCurrentIndex(self.channel1_combo.currentIndex())
        self.parent.set_cc(float(self.cc1_value.text()), self.parent.event)
        #self.parent.tune_tab.send_to_dac(float(self.tune1_value.text())/100, 2)
        self.parent.tune_tab.diode_spin.setValue(float(self.tune1_value.text()))
        self.run_button.setText('Run Compare')
                   
    def update_event_plots(self): 
        '''Update time plot as running'''
        hist_data = {}
        new_hist_data = self.parent.history.to_plot(datetime.datetime.now(tz=datetime.timezone.utc).timestamp() - 60*int(self.range_value.text()), datetime.datetime.now(tz=datetime.timezone.utc).timestamp())  # dict of Hist objects keyed on stamps
        for k,v in new_hist_data.items():
            #if 'TE' in v.label or 'None' in v.label:  
            hist_data[k] = v
            # exclude unless labelled as TE, or not labeled
        self.time_data = np.column_stack((list(hist_data.keys()),[hist_data[k].area for k in hist_data.keys()])) # 2-d nparray to plot 
        self.time_plot.setData(self.time_data)   #plot