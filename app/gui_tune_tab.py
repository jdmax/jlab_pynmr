'''PyNMR, J.Maxwell 2020
'''
import datetime
import time
from PyQt5.QtWidgets import QWidget, QTabWidget, QVBoxLayout, QHBoxLayout, QPushButton, QGroupBox, QGridLayout, QLabel, QLineEdit, QSizePolicy, QComboBox, QSpacerItem, QSlider, QDoubleSpinBox
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
        self.running = False
        
        self.running_scan = RunningScan(self.config,1000)
        
        self.dio_pen = pg.mkPen(color=(250, 0, 0), width=1)
        self.pha_pen = pg.mkPen(color=(0, 0, 204), width=1)
        
        # Populate Tune Tab
        self.main = QVBoxLayout()            # main layout
        
        self.tune_box = QGroupBox('Tune Controls')      # top tune controls
        self.tune_box.setLayout(QHBoxLayout())
        self.run_button = QPushButton('Run', checkable=True)
        self.tune_box.layout().addWidget(self.run_button)
        self.run_button.clicked.connect(self.run_pushed)
        self.run_button.setEnabled(False)
        self.avg_label = QLabel('Sweeps for Running Average:')
        self.tune_box.layout().addWidget(self.avg_label)
        self.avg_value = QLineEdit('1000')
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
        self.diode_slider.setRange(0,1400)
        self.diode_box.layout().addWidget(self.diode_slider)
        self.diode_spin = QDoubleSpinBox()
        self.diode_spin.setRange(0,14)
        self.diode_spin.setSingleStep(0.01)
        self.diode_slider.valueChanged.connect(lambda: self.diode_spin.setValue(float(self.diode_slider.value()/100)))
        self.diode_spin.valueChanged.connect(lambda: self.diode_slider.setValue(int(self.diode_spin.value()*100)))
        self.diode_box.layout().addWidget(self.diode_spin)
        self.vl1 = QLabel('Volts')
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
        self.phase_slider.setRange(0,1500)
        self.phase_box.layout().addWidget(self.phase_slider)
        self.phase_spin = QDoubleSpinBox()
        self.phase_spin.setRange(0,15)
        self.phase_spin.setSingleStep(0.01)
        self.phase_slider.valueChanged.connect(lambda: self.phase_spin.setValue(float(self.phase_slider.value()/100)))
        self.phase_spin.valueChanged.connect(lambda: self.phase_slider.setValue(int(self.phase_spin.value()*100)))
        self.phase_box.layout().addWidget(self.phase_spin)
        self.vl2 = QLabel('Volts')
        self.phase_box.layout().addWidget(self.vl2)
        
        self.lower.addLayout(self.left_layout)
        self.lower.addLayout(self.right_layout)
        self.main.addWidget(self.tune_box)
        self.main.addLayout(self.lower)
        self.setLayout(self.main)
        
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
       
        self.running_scan = RunningScan(self.config, int(self.avg_value.text()))
        self.running = True
        self.tune_thread = TuneThread(self, self.event.config)
        self.tune_thread.reply.connect(self.add_sweeps)
        self.tune_thread.start()
    
    def add_sweeps(self,new_sigs):
        '''Add the tuple of sweeps to event'''
        self.running_scan.running_avg(new_sigs)
        self.update_run_plot()
        
    def abort_run(self):
        '''Quit now'''
        self.running = False
        #self.tune_thread.terminate()
        self.status_bar.showMessage('Ready.')
        self.update_run_plot()
        
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
        try:
            self.daq = DAQConnection(self.config, 4, True)
        except Exception as e:
            print('Exception: '+str(e))
        
        
    def __del__(self):
        del self.daq
        self.wait()

    def run(self):
        '''Main run loop. Request start of sweeps, receive sweeps, update event, report.'''
        
        while self.parent.running:
            self.daq.start_sweeps()              # send command to start sweeps
            self.reply.emit(self.daq.get_chunk())
        




