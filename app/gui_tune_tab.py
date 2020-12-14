'''PyNMR, J.Maxwell 2020
'''
import datetime
import time
from PyQt5.QtWidgets import QWidget, QTabWidget, QVBoxLayout, QHBoxLayout, QPushButton, QGroupBox, QGridLayout, QLabel, QLineEdit, QSizePolicy, QComboBox, QSpacerItem, QSlider, QDoubleSpinBox, QProgressBar
from PyQt5.QtGui import QIntValidator, QDoubleValidator, QValidator
from PyQt5.QtCore import QThread, pyqtSignal,Qt
import pyqtgraph as pg
 
from app.classes import RunningScan
from app.daq import DAQConnection

  
class TuneTab(QWidget):
    '''Creates tune tab'''
    def __init__(self, parent):
        super(QWidget,self).__init__(parent)
        self.__dict__.update(parent.__dict__)
        self.parent = parent
        
        self.running = False   # False will stop the running thread
        self.dac_v = 0     # Starting DAC channel value   
        self.dac_c = 3
        
        self.running_scan = RunningScan(self.config, 1000)
        
        self.dio_pen = pg.mkPen(color=(250, 0, 0), width=1)
        self.pha_pen = pg.mkPen(color=(0, 0, 204), width=1)
        self.progress = 0
        
        # Populate Tune Tab
        self.main = QVBoxLayout()            # main layout
        
        self.tune_box = QGroupBox('Tune Controls')      # top tune controls
        self.tune_box.setLayout(QHBoxLayout())
        self.run_button = QPushButton('Run', checkable=True)
        self.tune_box.layout().addWidget(self.run_button)
        self.run_button.clicked.connect(self.run_pushed)
        self.run_button.setEnabled(False)
        self.progress_bar = QProgressBar()                                  # Progress bar
        self.progress_bar.setTextVisible(False)
        self.tune_box.layout().addWidget(self.progress_bar)
        self.avg_label = QLabel('Sweeps for Running Average:')
        self.tune_box.layout().addWidget(self.avg_label)
        self.avg_value = QLineEdit('100')
        self.avg_value.setValidator(QIntValidator(1,1000000))
        self.avg_value.textChanged.connect(lambda: self.change_avg(int(self.avg_value.text())))
        self.avg_value.editingFinished.connect(lambda: self.avg_value.setStyleSheet('QLineEdit { background-color: #ffffff }'))
        self.tune_box.layout().addWidget(self.avg_value)
        
        self.lower = QHBoxLayout()
        self.left_layout = QVBoxLayout()     # Left, Diode Side
        # Diode plot
        self.diode_wid = pg.PlotWidget(title='Diode Signal')
        self.diode_wid.showGrid(True,True)
        self.diode_plot = self.diode_wid.plot([], [], pen=self.dio_pen) 
        self.left_layout.addWidget(self.diode_wid)
        self.diode_box = QGroupBox("Diode Tune Control")
        self.diode_box.setLayout(QHBoxLayout())
        self.left_layout.addWidget(self.diode_box)
        self.diode_slider = QSlider(Qt.Horizontal)
        self.diode_slider.setRange(0,1000)
        self.diode_box.layout().addWidget(self.diode_slider)
        self.diode_spin = QDoubleSpinBox()
        self.diode_spin.setRange(0,100)
        self.diode_spin.setSingleStep(0.1)
        self.diode_slider.sliderReleased.connect(self.diode_slider_changed)
        self.diode_spin.valueChanged.connect(self.diode_spin_changed)
        self.diode_box.layout().addWidget(self.diode_spin)
        self.vl1 = QLabel('Percent')
        self.diode_box.layout().addWidget(self.vl1)
        
        self.right_layout = QVBoxLayout()     # Right, Phase Side
        self.phase_wid = pg.PlotWidget(title='Phase Signal')
        self.phase_wid.showGrid(True,True)
        self.phase_plot = self.phase_wid.plot([], [], pen=self.pha_pen) 
        self.right_layout.addWidget(self.phase_wid)
        self.phase_box = QGroupBox("Phase Tune Control")
        self.phase_box.setLayout(QHBoxLayout())
        self.right_layout.addWidget(self.phase_box)
        self.phase_slider = QSlider(Qt.Horizontal)
        self.phase_slider.setRange(0,1000)
        self.phase_box.layout().addWidget(self.phase_slider)
        self.phase_spin = QDoubleSpinBox()
        self.phase_spin.setRange(0,100)
        self.phase_spin.setSingleStep(0.1)
        self.phase_slider.sliderReleased.connect(self.phase_slider_changed)
        self.phase_spin.valueChanged.connect(self.phase_spin_changed)
        self.phase_box.layout().addWidget(self.phase_spin)
        self.vl2 = QLabel('Percent')
        self.phase_box.layout().addWidget(self.vl2)
        
        self.lower.addLayout(self.left_layout)
        self.lower.addLayout(self.right_layout)
        self.main.addWidget(self.tune_box)
        self.main.addLayout(self.lower)
        self.setLayout(self.main)
        
    def phase_slider_changed(self):
        '''Slider value changed'''
        self.phase_spin.setValue(float(self.phase_slider.value()/10))
        
    def phase_spin_changed(self):
        '''Spinbox value changed'''
        self.phase_slider.setValue(int(self.phase_spin.value()*10))
        self.parent.config.phase_vout = self.phase_spin.value()/100
        self.send_to_dac(self.parent.config.phase_vout, 2)
        
    def diode_slider_changed(self):
        '''Slider value changed'''
        self.diode_spin.setValue(float(self.diode_slider.value()/10))
        #self.parent.config.diode_vout = float(self.diode_slider.value()/100)
        #self.send_to_dac(self.parent.config.diode_vout, 1)
        
    def diode_spin_changed(self):
        '''Spinbox value changed'''
        self.diode_slider.setValue(int(self.diode_spin.value()*10))
        self.parent.config.diode_vout = self.diode_spin.value()/100
        self.send_to_dac(self.parent.config.diode_vout, 1)
        
    def send_to_dac(self, value, dac_c):
        '''Send DAC voltage to DAQ, check to see if tune is running. If not, start DAQConnection to send.
        
        Arguments:
            value: Relative value to send (0 is no voltage to 1 is max)
            dac_c: channel, 1 (diode), 2 (phase), or 3 (both same)
        
        '''
        self.dac_v = value
        self.dac_c = dac_c
        
        if not self.running:
            time.sleep(0.0001)
            self.daq = DAQConnection(self.config, 4, True)
            if self.daq.set_dac(self.dac_v, self.dac_c):
                print("Set DAC:", self.dac_c,  self.dac_v)
            else:
                print("Error setting DAC.")
            del self.daq
 
    def run_pushed(self):
        '''Start tune loop if conditions met'''
        
        if self.run_button.isChecked():
        
            self.status_bar.showMessage('Running sweeps to tune...')
            self.run_button.setText('Stop')
            self.start_thread()
            self.parent.run_toggle()
                   
        else:
            self.abort_run()
            self.run_button.setText('Run')
            self.parent.run_toggle()
     
    def start_thread(self):
        '''Open new event instance, create then start threads for data taking and plotting '''
       
        self.running_scan = RunningScan(self.parent.config, int(self.avg_value.text()))
        self.running = True
        self.tune_thread = TuneThread(self, self.parent.config)
        self.tune_thread.reply.connect(self.add_sweeps)
        self.tune_thread.finished.connect(self.finished)
        self.tune_thread.start()
    
    def add_sweeps(self,new_sigs):
        '''Add the tuple of sweeps to event'''
        self.running_scan.running_avg(new_sigs)
        self.update_run_plot()
        if self.progress<100:
            self.progress+=10
        else:
            self.progress = 0
        self.progress_bar.setValue(self.progress)   
        
    def finished(self):
        '''Run when thread done'''
        self.progress = 0
        self.progress_bar.setValue(self.progress)  
        self.status_bar.showMessage('Ready.')
        self.update_run_plot()
        
    def abort_run(self):
        '''Quit now'''
        self.running = False
        
    def change_avg(self,to_avg):
        '''Set the number to average'''
        if to_avg > 0:
            self.running_scan.to_avg = int(to_avg)
        
    def update_run_plot(self):
        '''Update the running plots'''
        self.diode_plot.setData(self.running_scan.freq_list,self.running_scan.diode)
        self.phase_plot.setData(self.running_scan.freq_list,self.running_scan.phase)
 
class TuneThread(QThread):
    '''Thread class for tune loop'''
    reply = pyqtSignal(tuple)       # reply signal

    def __init__(self, parent, config):
        '''Make new thread instance for running NMR'''
        QThread.__init__(self)
        self.config = config
        self.parent = parent 
        self.dac_v = 0
        self.dac_c = 0
        self.set_time = 0 # time when DAC last set
        try:
            self.daq = DAQConnection(self.config, 4, True)
        except Exception as e:
            print('Exception in tune thread: '+str(e))
        
        
    def __del__(self):
        self.wait()

    def run(self):
        '''Main run loop. Request start of sweeps, receive sweeps, update event, report.'''
        
        while self.parent.running:
            now = time.time()
            if now > self.set_time + 0.0001:
                if (self.dac_v != self.parent.dac_v) or (self.dac_c != self.parent.dac_c):
                    self.dac_v = self.parent.dac_v
                    self.dac_c = self.parent.dac_c
                    try:
                        self.daq.set_dac(self.dac_v, self.dac_c)   
                        print("Set DAC:", self.dac_c,  self.dac_v)
                        self.set_time = now
                    except Exception as e:
                        print("Exception setting DAC value: "+str(e))
            self.daq.start_sweeps()              # send command to start sweeps
            new_sigs = self.daq.get_chunk()
            while new_sigs[1] < self.config.settings['tune_per_chunk']:   # for NIDAQ, we need to wait for all the sweeps
                new_sigs = self.daq.get_chunk()                  
            if num_in_chunk > 0:
                self.reply.emit(new_sigs)
        self.daq.stop()   
        self.finished.emit()
        del self.daq 
        




