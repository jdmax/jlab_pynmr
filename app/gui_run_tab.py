'''PyNMR, J.Maxwell 2020
'''
import datetime
import time
import math
import pytz
from PyQt5.QtWidgets import QWidget, QLabel, QGroupBox, QHBoxLayout, QVBoxLayout, QGridLayout, QLineEdit, QSpacerItem, QSizePolicy, QComboBox, QPushButton, QProgressBar
from PyQt5.QtGui import QIntValidator, QDoubleValidator, QValidator
from PyQt5.QtCore import QThread, pyqtSignal, Qt
import pyqtgraph as pg
 
from app.classes import *
from app.daq import *
from app.microwaves import *
   
class RunTab(QWidget):
    '''Creates run tab. Starts threads for run and to update plots'''
    def __init__(self, parent):
        super(QWidget,self).__init__(parent)
        self.__dict__.update(parent.__dict__)
        
        self.parent = parent
        self.abort_now = False
               
        # pyqtgrph styles        
        pg.setConfigOptions(antialias=True)
        self.raw_pen = pg.mkPen(color=(250, 0, 0), width=1.5)
        self.sub_pen = pg.mkPen(color=(0, 0, 204), width=1.5)
        self.fit_pen = pg.mkPen(color=(255, 255, 0), width=3)
        self.fin_pen = pg.mkPen(color=(0, 160, 0), width=1.5)
        self.res_pen = pg.mkPen(color=(190, 0, 190), width=2)
        self.pol_pen = pg.mkPen(color=(250, 0, 0), width=2)
        self.wave_pen = pg.mkPen(color=(153, 204, 255), width=1.5)
        pg.setConfigOption('background', 'w')
        pg.setConfigOption('foreground', 'k')
        
        
        # Populate Run Tab
        self.main = QVBoxLayout()            # main layout
        self.upperlayout = QHBoxLayout()     # Upper part of main layout
         
        # Populate Status Box
        self.status_box = QGroupBox('EPICS Reads')
        self.status_box.setLayout(QGridLayout())
        self.upperlayout.addWidget(self.status_box)
        i = 0
        self.stat_values = {}
        for key, name in self.parent.epics.read_names.items():
            self.status_box.layout().addWidget(QLabel(name+':'), i, 0)
            self.stat_values[key] = QLabel(str(0))
            #self.stat_values[key].setEnabled(False)
            self.status_box.layout().addWidget(self.stat_values[key], i, 1)
            self.stat_values[key].setStyleSheet("color : black")
            i+=1
        self.epics_beat = True
        
        self.midlayout = QVBoxLayout()
        self.midwidget = QWidget()
        self.midwidget.setLayout(self.midlayout)
        self.midwidget.setMaximumWidth(400)
        self.upperlayout.addWidget(self.midwidget)
        
        # Populate Controls box
        self.controls_box = QGroupBox('NMR Controls')
        self.controls_box.setLayout(QGridLayout())
        self.midlayout.addWidget(self.controls_box)
        self.run_button = QPushButton("Run",checkable=True)       # Run button
        self.controls_box.layout().addWidget(self.run_button, 0, 0)
        self.run_button.setEnabled(False)
        self.run_button.clicked.connect(self.run_pushed)
        #self.abort_button = QPushButton("Abort Now")                # Abort button
        #self.controls_box.layout().addWidget(self.abort_button, 1, 0)
        #self.abort_button.setEnabled(False)
        #self.abort_button.clicked.connect(self.abort_run)
        #self.connect_button = QPushButton("Connect DAQ",checkable=True)     # Connect button
        #self.controls_box.layout().addWidget(self.connect_button, 1, 1)
        #self.connect_button.clicked.connect(self.connect_pushed)
        self.progress_bar = QProgressBar()                                  # Progress bar
        self.progress_bar.setTextVisible(False)
        #self.progress_bar.setSizePolicy(QSizePolicy.Minimum,QSizePolicy.Expanding)
        self.controls_box.layout().addWidget(self.progress_bar, 0, 1)
        self.label = QLabel("Event Label:")
        self.controls_box.layout().addWidget(self.label, 1, 0)
        self.label_combo = QComboBox()
        self.label_combo.setEditable(True)
        self.controls_box.layout().addWidget(self.label_combo, 1, 1)
        self.labels = ('None', 'Baseline', 'TE', 'Polarize', 'Junk')
        self.label_combo.addItems(self.labels)
        self.label_combo.currentTextChanged.connect(self.parent.label_changed)
        
        
       
        # Populate uWave settings if enabled
        if self.parent.config.settings['uWave_settings']['enable']:
            self.uwave_box = QGroupBox('Microwave Controls')
            self.uwave_box.setLayout(QVBoxLayout())
            self.midlayout.addWidget(self.uwave_box)
            self.uwave_layout = QGridLayout()
            self.uwave_box.layout().addLayout(self.uwave_layout)
            self.uwave_freq_label = QLabel('Freq:')
            self.uwave_layout.addWidget(self.uwave_freq_label, 1, 0)
            self.uwave_power_label = QLabel('Power:')
            self.uwave_layout.addWidget(self.uwave_power_label, 1, 1)
            self.enable_button = QPushButton("Enable",checkable=True)      # Enable button
            self.uwave_layout.addWidget(self.enable_button, 0, 0)
            self.enable_button.clicked.connect(self.enable_uwave_pushed)
            #self.uwave_freq_line = QLineEdit(str(0))
            #self.uwave_freq_line.setEnabled(False)
            #self.uwave_layout.addWidget(self.uwave_freq_line, 0, 1)
            self.down_button = QPushButton("Down",checkable=False, enabled=False)       # Decrease freq button
            self.down_button.pressed.connect(self.down_micro)
            self.down_button.released.connect(self.off_micro)
            self.uwave_layout.addWidget(self.down_button, 2, 0)
            self.up_button = QPushButton("Up",checkable=False, enabled=False)       # Increase freq button
            self.up_button.pressed.connect(self.up_micro)
            self.up_button.released.connect(self.off_micro)
            self.uwave_layout.addWidget(self.up_button, 2, 1)
        
        
        # Populate NMR Settings box 
        self.settings_box = QGroupBox('NMR Settings')
        self.settings_box.setLayout(QVBoxLayout())
        self.midlayout.addWidget(self.settings_box)
        
        self.channel_combo = QComboBox()
        self.channel_combo.setEnabled(False)
        self.channel_label = QLabel()
        self.channel_combo.addItems(self.parent.channels)
        #i = self.channel_combo.findText(self.config.settings['default_channel'],Qt.MatchFixedString)
        #if i>=0: 
        #    self.channel_combo.setCurrentIndex(i) 
        self.channel_combo.setCurrentIndex(self.parent.restore_dict['channel']) 
        self.channel_combo.currentIndexChanged.connect(self.combo_changed)
        self.combo_changed(self.parent.restore_dict['channel'])
        self.settings_box.layout().addWidget(self.channel_combo)
        self.settings_box.layout().addWidget(self.channel_label)
        self.settings_box.layout().addWidget(self.parent.divider())        
        
        self.controls_layout = QGridLayout()
        self.settings_box.layout().addLayout(self.controls_layout)
        self.controls_lines = {}
        self.controls_labels = {}
        for i, key in enumerate(self.parent.config.controls):
            self.controls_lines[key] = QLineEdit(str(self.parent.config.controls[key].value))
            self.controls_labels[key] = QLabel(self.parent.config.controls[key].text)
            self.controls_lines[key].setValidator(self.parent.config.controls[key].valid)
            #self.controls_lines[key].setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
            #self.controls_lines[key].setMinimumWidth(60)
            self.controls_lines[key].setEnabled(False)
            self.controls_lines[key].textChanged.connect(parent.check_state)
            self.controls_lines[key].textChanged.emit(self.controls_lines[key].text())
            self.controls_layout.addWidget(self.controls_labels[key], i, 0)
            self.controls_layout.addWidget(self.controls_lines[key], i, 1)            # make entries for config items
        self.lock_button = QPushButton("Unlock",checkable=True)
        self.lock_button.clicked.connect(self.lock_pushed)
        self.controls_layout.layout().addWidget(self.lock_button, len(self.parent.config.controls), 1)
        # self.reload_button = QPushButton("Reload Settings",checkable=False)
        # self.reload_button.clicked.connect(self.reload_pushed)
        # self.controls_layout.layout().addWidget(self.reload_button, len(self.parent.config.controls), 0)
                
        self.settings_box.layout().addWidget(self.parent.divider())
        self.baseline_label = QLabel('Baseline: None selected')
        self.settings_box.layout().addWidget(self.baseline_label)
        
        
        # Populate pol v time plot
        self.time_axis = pg.DateAxisItem(orientation='bottom')
        self.pol_time_wid = pg.PlotWidget(
            title='', axisItems={'bottom': self.time_axis}
        )
        if self.parent.config.settings['epics_settings']['enable']:   # turn on uwave freq plot
            self.pol_time_plot =  self.pol_time_wid.plotItem
            
            self.wave_time_plot = pg.ViewBox()
            self.pol_time_plot.showAxis('right')
            self.pol_time_plot.setLabels(left = 'Polarization')
            self.pol_time_plot.scene().addItem(self.wave_time_plot)
            self.pol_time_plot.getAxis('right').linkToView(self.wave_time_plot)
            self.wave_time_plot.setXLink(self.pol_time_plot)
            self.pol_time_plot.getAxis('right').setLabel('Microwave Frequency (GHz)')
            self.pol_time_plot.showGrid(True,True, alpha = 0.2)
            
            self.pol_time_plot.vb.sigResized.connect(self.sync_pol_time)
        else:
            self.pol_time_wid.showGrid(True,True, alpha = 0.2)
            self.pol_time_plot = self.pol_time_wid.plot([], [], pen=self.pol_pen) 
        #self.pol_time_wid.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Expanding)
        self.upperlayout.addWidget(self.pol_time_wid)

        # Populate Results area
        self.results_lay = QVBoxLayout()
        self.results_wid = QWidget()
        self.results_wid.setLayout(self.results_lay)
        self.results_wid.setMaximumWidth(340)
        self.upperlayout.addWidget(self.results_wid)
        self.pol_box = QGroupBox("Polarization")
        self.pol_box.setLayout(QVBoxLayout())
        self.results_lay.addWidget(self.pol_box)
        self.pol_value = QLabel('{:.2%}'.format(self.parent.event.pol))
        self.pol_value.setStyleSheet("font:30pt")
        self.pol_value.setAlignment(Qt.AlignCenter)
        self.pol_box.layout().addWidget(self.pol_value)
        self.area_box = QGroupBox("Signal Area")
        self.area_box.setLayout(QVBoxLayout())
        self.results_lay.addWidget(self.area_box)
        self.area_value = QLabel('{:.6f}'.format(self.parent.event.area))
        self.area_value.setStyleSheet("font:20pt")
        self.area_value.setAlignment(Qt.AlignCenter)
        self.area_box.layout().addWidget(self.area_value)
        self.dt_box = QGroupBox("Timestamp")
        self.dt_box.setLayout(QVBoxLayout())
        self.results_lay.addWidget(self.dt_box)
        self.dt_value = QLabel(self.parent.event.stop_time.strftime("%m/%d/%Y\n%H:%M:%S"))
        self.dt_value.setStyleSheet("font:12pt")
        self.dt_value.setAlignment(Qt.AlignCenter)
        self.dt_box.layout().addWidget(self.dt_value)          
         
        self.range_layout = QHBoxLayout()
        self.range_label = QLabel('Plot Range (min):')
        self.range_layout.addWidget(self.range_label)
        self.range_value = QLineEdit('60')
        self.range_value.setValidator(QIntValidator(1,1000000))
        self.range_value.textChanged.connect(self.changed_range)
        self.range_layout.addWidget(self.range_value)
        self.dt_box.layout().addLayout(self.range_layout)
        
        self.main.addLayout(self.upperlayout)
        
        # Populate lower plots
        self.lowerlayout = QHBoxLayout()
        
        # Raw Plot
        self.raw_wid = pg.PlotWidget(title='Raw Signal')
        self.raw_wid.showGrid(True,True, alpha = 0.2)
        self.raw_plot = self.raw_wid.plot([], [], pen=self.raw_pen) 
        self.lowerlayout.addWidget(self.raw_wid)
        
        # Sub plot
        self.sub_wid = pg.PlotWidget(title='Baseline Subtracted')
        self.sub_wid.showGrid(True,True, alpha = 0.2)
        self.sub_plot = self.sub_wid.plot([], [], pen=self.sub_pen) 
        self.fit_plot = self.sub_wid.plot([], [], pen=self.fit_pen) 
        self.lowerlayout.addWidget(self.sub_wid)
        
        # Final PLot
        self.fin_wid = pg.PlotWidget(title='Fit Subtracted')
        self.fin_wid.showGrid(True,True, alpha = 0.2)
        self.fin_plot = self.fin_wid.plot([], [], pen=self.fin_pen)  
        self.res_plot = self.fin_wid.plot([], [], pen=self.res_pen)         
        self.lowerlayout.addWidget(self.fin_wid)
           
        self.main.addLayout(self.lowerlayout)
        self.setLayout(self.main)        
        
    def sync_pol_time(self):
        '''Sync resized on time plot'''
        self.wave_time_plot.setGeometry(self.pol_time_plot.vb.sceneBoundingRect())        
    
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
       
    def start_thread(self):
        '''Open new event instance, create then start threads for data taking and plotting '''

        self.parent.new_event()                 # start new event in main window
        #self.parent.set_event_base()            # set current basline to this event
        try:
            self.run_thread = RunThread(self, self.parent.config)
            self.run_thread.finished.connect(self.done)
            self.run_thread.reply.connect(self.add_sweeps)
            self.run_thread.start()
        except Exception as e: 
            print('Exception starting run thread, lost connection: '+str(e))   

    def combo_changed(self, i):
        '''Channel changed'''
        self.parent.channel_change(i)
        self.channel_label.setText(f'Frequency: {self.parent.config.channel["cent_freq"]} MHz ± {self.parent.config.channel["mod_freq"]} kHz\n' \
            f'RF Power: {self.parent.config.channel["power"]} mV')

    def add_sweeps(self,new_sigs):
        '''Add the tuple of sweeps to event'''
        self.parent.event.update_event(new_sigs)
        self.update_run_plot()

    def update_run_plot(self):
        '''Update the running plot'''
        self.raw_plot.setData(self.parent.event.scan.freq_list, self.parent.event.scan.phase)
        progress = 100*self.parent.event.scan.num/self.parent.event.config.controls['sweeps'].value
        progress = 100*self.parent.event.scan.num/self.parent.event.config.controls['sweeps'].value
        self.progress_bar.setValue(progress)
    
    # def abort_run(self):
        # '''Quit now'''
        # print("abort_run")
        # self.abort_now = True
        # now = datetime.datetime.now(tz=datetime.timezone.utc)
        # self.parent.status_bar.showMessage('Aborted at '+now.strftime("%H:%M:%S")+' UTC.')
        # self.abort_button.setEnabled(False)
        # self.run_button.setText('Run')
        # self.run_button.setEnabled(True)
        # self.run_button.setChecked(False)
        # self.update_run_plot()
        # self.progress_bar.setValue(0)
        # self.parent.run_toggle()
    
    def done(self):
        '''Finished sweeps: close event. If stop button checked, reset buttons, else run again.'''
        self.parent.end_event()        
        now = datetime.datetime.now(tz=datetime.timezone.utc)
        if not self.run_button.isChecked():     # done and stop
            self.parent.status_bar.showMessage(f'Finished event at {now:%H:%M:%S} UTC. Event took {self.parent.event.elapsed}s.')
            
            #self.abort_button.setEnabled(False)
            self.lock_button.setEnabled(True)
            self.run_button.setText('Run')
            self.run_button.setEnabled(True)
            self.run_button.setChecked(False)
            self.update_run_plot()
            self.parent.run_toggle()
        else:                                    # done, continue running
            self.parent.status_bar.showMessage(f'Finished event at  at {now:%H:%M:%S} UTC. Event took {self.parent.event.elapsed}s. Running sweeps...')
            self.start_thread()
        
    
    def update_event_plots(self):
        '''Update all plots and indicators for this event using instance data'''
        freqs = self.parent.event.scan.freq_list        
        self.raw_plot.setData(self.parent.previous_event.scan.freq_list, self.parent.previous_event.scan.phase)
        self.sub_plot.setData(self.parent.previous_event.scan.freq_list, self.parent.previous_event.basesub)
        self.fit_plot.setData(self.parent.previous_event.scan.freq_list, self.parent.previous_event.fitcurve)
        self.res_plot.setData(self.parent.previous_event.scan.freq_list, self.parent.previous_event.rescurve)
        self.fin_plot.setData(self.parent.previous_event.scan.freq_list, self.parent.previous_event.fitsub)
        #self.fin_plot.setData(self.parent.config.adc_timing, self.parent.event.fitsub)
              
        self.pol_value.setText('{:.2%}'.format(self.parent.previous_event.pol))                    # updates indicators
        self.area_value.setText('{:.6f}'.format(self.parent.previous_event.area))
        time = self.parent.previous_event.stop_time
        start_time = self.parent.previous_event.start_time
        self.dt_value.setText(time.replace(tzinfo=pytz.utc).astimezone(self.parent.tz).strftime("%m/%d/%Y, %H:%M:%S")+"\n"+self.parent.previous_event.stop_time.strftime("%H:%M:%S")+" UTC")
        
        hist_data = self.parent.history.to_plot(datetime.datetime.now(tz=datetime.timezone.utc).timestamp() - 60*int(self.range_value.text()), datetime.datetime.now(tz=datetime.timezone.utc).timestamp())     
        pol_data = np.column_stack((list([k + 3600 for k in hist_data.keys()]),[hist_data[k].pol for k in hist_data.keys()]))
        uwave_data = np.column_stack((list([k + 3600 for k in hist_data.keys()]),[hist_data[k].uwave_freq for k in hist_data.keys()]))
        # This time fix is not permanent! Graphs always seem to be one hour off, no matter the timezone. Problem is in pyqtgraph.
             
        if self.parent.config.settings['epics_settings']['enable']:   # turn on uwave freq plot
            self.pol_time_plot.plot(pol_data, pen=self.pol_pen)    
            self.wave_time_plot.addItem(pg.PlotDataItem(uwave_data, pen=self.wave_pen))
        else:       
            self.pol_time_plot.setData(pol_data)  
        self.progress_bar.setValue(0)
    
    def changed_range(self):
        '''Change time range of pol v time plot'''
        hist_data = self.parent.history.to_plot(datetime.datetime.now(tz=datetime.timezone.utc).timestamp() - 60*int(self.range_value.text()), datetime.datetime.now(tz=datetime.timezone.utc).timestamp())               
        pol_data = np.column_stack((list(hist_data.keys()),[hist_data[k].pol for k in hist_data.keys()]))
        self.pol_time_plot.setData(pol_data) 
    
    def lock_pushed(self):
        '''Enable changing settings'''
        sender = self.sender()
        if sender.isChecked():
            sender.setText('Set')
            self.channel_combo.setEnabled(True)
            for key in self.parent.config.controls:
                self.controls_lines[key].setEnabled(True)
                color = '#ffffff'
                self.controls_lines[key].setStyleSheet('QLineEdit { background-color: %s }' % color)
        else:
            self.channel_combo.setEnabled(False)
            for key in self.parent.config.controls:
                if self.controls_lines[key].validator().validate(self.controls_lines[key].text(), 0)[0]!=QValidator.Acceptable:
                    print('Setting not valid:',key)
                    sender.toggle()
                    return
            sender.setText('Unlock')
            for key in self.parent.config.controls:
                self.controls_lines[key].setEnabled(False)
                self.parent.config.controls[key].set_config(self.controls_lines[key].text())
                color = '#eeeeee'
                self.controls_lines[key].setStyleSheet('QLineEdit { background-color: %s }' % color)
        return
    
    def reload_pushed(self):
        '''Reload settings button pushed run parent load method
        '''
        self.parent.load_settings()
    
    def connect_pushed(self):
        '''Connect button pushed, run parent connect method'''
        self.parent.connect_daq()
    
    def enable_uwave_pushed(self):
        '''Enable microwaves button pushed, turn on buttons and start thread if checked'''
        sender = self.enable_button
        if sender.isChecked():
            sender.setText('Disable')
            self.up_button.setEnabled(True)
            self.down_button.setEnabled(True)
                              
            try: 
                self.utune = LabJack(self.parent.config)
            except Exception as e: 
                print('Exception starting microwave tuner: '+str(e))          
            
            try:
                self.micro_thread = MicrowaveThread(self, self.parent.config)
                self.micro_thread.reply.connect(self.freq_reply)
                self.micro_thread.start()
            except Exception as e: 
                print('Exception starting microwave thread, lost connection: '+str(e)) 
                self.enable_button.toggle()
                #self.enable_pushed() 
                
        else: 
            sender.setText('Enable')
            self.up_button.setEnabled(False)
            self.down_button.setEnabled(False)
    
    def freq_reply(self, reply):
        '''Got replay from micro thread, display it'''
        freq = reply[0]
        pot = reply[1]
        temp = reply[2]
        power = reply[3]
        self.uwave_freq_label.setText(f"Freq: {freq/1e9:.4f} GHz")
        self.uwave_power_label.setText(f"Power: {power} mW")
        #self.uwave_freq_label.setText(f"{pot, temp}")
        self.parent.event.set_uwave(freq/1e9, power)
        
    def up_micro(self):
        '''Up pressed'''
        self.utune.change_freq('up')
        
    def down_micro(self):
        '''Down pressed'''
        self.utune.change_freq('down')
        
    def off_micro(self):
        '''Button released'''
        self.utune.change_freq('off')        
        
    def update_status(self):
        '''Update gui with status from EPICS values, toggle color'''  
        
        for key in self.parent.epics.read_list:
            if abs(float(self.parent.epics.read_pvs[key]))<10000:
                self.stat_values[key].setText(f'{self.parent.epics.read_pvs[key]:6f}')
            else:                    
                self.stat_values[key].setText(f'{self.parent.epics.read_pvs[key]:.3e}')
            #if self.epics_beat: 
            #    self.stat_values[key].setStyleSheet("color : blue")
            #    self.epics_beat = False
            #else: 
            #    self.stat_values[key].setStyleSheet("color : black")
            #    self.epics_beat = True

        

        
   
class RunThread(QThread):
    '''Thread class for main NMR run loop
    Args:
        config: Config object of settings
    '''
    reply = pyqtSignal(tuple)       # reply signal
    finished = pyqtSignal()       # finished signal
    def __init__(self, parent, config):
        QThread.__init__(self)
        self.config = config
        self.parent = parent 
        self.sweep_num = config.controls['sweeps'].value
        self.num_per_chunk = config.settings['num_per_chunk']
        self.rec_sweeps = 0     # number of total sweeps in set that we have received
        try:
            self.daq = DAQConnection(self.config, self.config.settings['fpga_settings']['timeout_run'], False)
        except Exception as e:
            print('Exception starting run thread, lost connection: '+str(e))
            
                
    def __del__(self):
        self.wait()
        
    def run(self):
        '''Main run loop. Request start of sweeps, receive sweeps, update event, report.
        
        Returns:
            On completion of a chunk, emits new_sigs, the number of sweeps in the chunk and the phase and diode chunk data as numpy arrays
        '''
        #self.test_data = TestUDP(self.sweep_num)
        
        try: 
            self.daq.start_sweeps()              # send command to start sweeps
        except AttributeError as e:   
            self.finished.emit()
            return            
            
        rec_chunks = 0                              #  count of chunks we have received
        while (self.rec_sweeps < self.sweep_num):                 # loop for total set of sweeps
            if self.parent.abort_now:
                print("Abort in run thread")
                self.daq.abort()
                try:
                    new_sigs = self.daq.get_chunk()
                except Exception as e:
                    print("On abort:", e)
                self.parent.abort_now = False
                break
            #start_time = time.time()    
            new_sigs = self.daq.get_chunk()
            chunk_num, num_in_chunk, pchunk, dchunk = new_sigs
            #print(f"get_chunk took {time.time() - start_time }s")
            if num_in_chunk > 0:
                self.reply.emit(new_sigs)
                rec_chunks += 1
                if 'NIDAQ' in self.config.settings['daq_type']:
                    self.rec_sweeps = num_in_chunk
                else:
                    self.rec_sweeps += num_in_chunk
            if not chunk_num + 1 == rec_chunks and not chunk_num == 0:
                print(f"Lost chunk. Expecting {rec_chunks}, got {chunk_num + 1}. Aborting run.") 
                self.daq.abort()
                try:
                    new_sigs = self.daq.get_chunk()
                except Exception as e:
                    print("On abort:", e)
                break
                    
        self.daq.stop()                
        self.finished.emit()
        del self.daq
   
