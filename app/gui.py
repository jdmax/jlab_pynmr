'''PyNMR, J.Maxwell 2020
'''
import datetime
import time
import socket
import sys
import os
import yaml
import pytz
import logging
import json
from PyQt5.QtWidgets import QMainWindow, QErrorMessage, QTabWidget, QLabel, QWidget, QDialog, QDialogButtonBox, QVBoxLayout
from PyQt5.QtGui import QIntValidator, QDoubleValidator, QValidator
from PyQt5.QtCore import QThread, pyqtSignal, Qt
from logging.handlers import TimedRotatingFileHandler

from app.classes import Config, Scan, RunningScan, Event, Baseline, HistPoint, History
from app.epics import EPICS
from app.gui_run_tab import RunTab
from app.gui_base_tab import BaseTab
from app.gui_tune_tab import TuneTab
from app.gui_te_tab import TETab
from app.gui_superte_tab import SuperTab
from app.gui_anal_tab import AnalTab
from app.gui_expl_tab import ExplTab
from app.gui_shim_tab import ShimTab
from app.gui_fm_tab import FMTab
from app.gui_compare_tab import CompareTab
from app.gui_temp_tab import TempTab
from app.gui_mag_tab import MagTab
from app.daq import DAQConnection, UDP, TCP, RS_Connection, NI_Connection
#from app.magnet_control import MagnetControl


class MainWindow(QMainWindow):
    '''Main window of application, with all the utility gui tabs. Includes methods for
    starting Event, Base instances. Event and Baselines are attributes, so that all child
    tabs can access. Many attributes concern the GUI, the attributes that effect operation
    are listed.

    Attributes:
        config: Current Config configuration instance
        event: Current Event instance
        baseline: Current Baseline instance
        epics: Open EPICS connection
        history: History instance containing set of HistPoints
        eventfile: Current event data filehandle
        eventfile_start: String of eventfile start time
        eventfile_lines: Number of entries in current eventfile
        channels: List of channels from config file
        settings: Dict of settings from config file
        epics_reads: Dict keyed on epics channels with name strings
        epics_writes: Dict keyed on epics channels with Event attributes to send

    '''
    def __init__(self, config_file, parent=None):
        super().__init__(parent)
        self.error_dialog = QErrorMessage(self)
        self.status_bar = self.statusBar()
        self.status_bar.showMessage('Ready.')
        self.config_filename = config_file
        self.load_settings()
        channel_dict = self.config_dict['channels'][self.config_dict['settings']['default_channel']]  # dict of selected channel
        self.start_logger()
        self.chassis_temp = 0
        self.shimA = 0
        self.shimB = 0
        self.shimC = 0
        self.shimD = 0
        
        self.label_changed('None')
        
        self.config = Config(channel_dict, self.settings)           # current configuration
        self.event = Event(self)      # open empty event
        self.previous_event = self.event      # there is no previous event
        self.baseline = Baseline(self.config, {})     # open empty baseline
        self.restore_history()
        self.new_eventfile()        
        self.restore_session()
        self.init_connects()
        
        self.tz = pytz.timezone('US/Eastern')
        
        self.left = 100
        self.top = 100
        self.title = 'JLab Polarization Display'
        self.width = 1200
        self.height = 800
        self.setWindowTitle(self.title)
        self.setGeometry(self.left, self.top, self.width, self.height)

        self.tab_widget = QTabWidget(self)
        self.setCentralWidget(self.tab_widget)

        # Make tabs
        self.run_tab = RunTab(self)
        self.tab_widget.addTab(self.run_tab, "Run")
        self.tune_tab = TuneTab(self)
        self.tab_widget.addTab(self.tune_tab, "Tune")
        self.base_tab = BaseTab(self)
        self.tab_widget.addTab(self.base_tab, "Baseline")
        #self.mag_tab = MagTab(self)
        #self.tab_widget.addTab(self.mag_tab, "Magnet")
        self.te_tab = TETab(self)
        self.tab_widget.addTab(self.te_tab, "TE")
        #self.super_tab = SuperTab(self)
        #self.tab_widget.addTab(self.super_tab, "Super TE")
        self.anal_tab = AnalTab(self)
        self.tab_widget.addTab(self.anal_tab, "Analysis")
        if self.config.settings['shim_settings']['enable']:
            self.shim_tab = ShimTab(self)
            self.tab_widget.addTab(self.shim_tab, "Shims")
        if self.config.settings['fm_settings']['enable']:
            self.fm_tab = FMTab(self)
            self.tab_widget.addTab(self.fm_tab, "FM")
        if self.config.settings['compare_tab']['enable']:
            self.compare_tab = CompareTab(self)
            self.tab_widget.addTab(self.compare_tab, "Compare")
        if self.config.settings['temp_settings']['enable']:
            self.temp_tab = TempTab(self)
            self.tab_widget.addTab(self.temp_tab, "Chassis Temp")
        if self.config.settings['explorer']['enable']:
            self.expl_tab = ExplTab(self)
            self.tab_widget.addTab(self.expl_tab, "Event Explorer")         
        
        self.set_cc(self.restore_dict['cc'])   
        self.connect_daq()
        
    def load_settings(self):
        '''Load settings from YAML config file'''

        with open(self.config_filename) as f:                           # Load settings from YAML files
           self.config_dict = yaml.load(f, Loader=yaml.FullLoader)
        self.channels = list(self.config_dict['channels'].keys())       # list of channels in config file
        self.settings = self.config_dict['settings']                    # dict of settings
        self.epics_reads = self.config_dict['epics_reads']              # dict of epics channels: name string
        self.epics_writes = self.config_dict['epics_writes']            # dict of epics channels: name string
        #self.status_bar.showMessage(f"Loaded settings from {self.config_filename}.")
        print(f"Loaded settings from {self.config_filename}.")
                
    def new_event(self):
        '''Create new event instance'''
        self.event = Event(self)
        self.set_event_base()

    def new_eventfile(self):
        '''Open new eventfile'''
        self.close_eventfile()    # try to close previous eventfile
        now = datetime.datetime.now(tz=datetime.timezone.utc)
        self.eventfile_start = now.strftime("%Y-%m-%d_%H-%M-%S")
        self.eventfile_name = os.path.join(self.config.settings["event_dir"], f'current_{self.eventfile_start}.txt')
        self.eventfile = open(self.eventfile_name, "w")
        self.eventfile_lines = 0
        logging.info(f"Opened new evenfile {self.eventfile_name}")

    def close_eventfile(self):
        '''Try to close and rename eventfile'''
        try:
            self.eventfile.close()
            now = datetime.datetime.now(tz=datetime.timezone.utc)
            new = f'{self.eventfile_start}__{now.strftime("%Y-%m-%d_%H-%M-%S")}.txt'
            os.rename(self.eventfile_name, os.path.join(self.config.settings["event_dir"], new))
            logging.info(f"Closed eventfile and moved to {new}.")
        except AttributeError:
            logging.info(f"Error closing eventfile.")
            
    
    def save_session(self):
        '''Print settings before app exit to a file for recall on restart'''
        saved_dict  =  {
            'phase_tune' : self.config.phase_vout,
            'diode_tune' : self.config.diode_vout,
            'cc' : float(self.run_tab.controls_lines['cc'].text()),
            'channel' : self.run_tab.channel_combo.currentIndex()
        }
        with open(f'app/{self.config.settings["session_file"]}.yaml', 'w') as file:
            documents = yaml.dump(saved_dict, file)
            #print(saved_dict)            
            logging.info(f"Printed settings on exit to {file}.") 
            
    def restore_session(self):
        '''Restore settings from previous session'''
        with open(f'app/{self.config.settings["session_file"]}.yaml') as f:                     
           self.restore_dict = yaml.load(f, Loader=yaml.FullLoader)
           
    def restore_history(self):
        '''Open history object and restore previous history into it'''       
        self.hist_file = open(f"app/{self.config_dict['settings']['history_file']}.json", "a+") 
        self.hist_file.seek(0)   #go to beginning to file to read
        self.history = History()   # for now, starting new history with each window
        for line in self.hist_file:
            jd = json.loads(line.rstrip('\n|\r'))            
            self.history.res_hist(HistPoint(jd))
        
    def end_event(self):
        '''Start ending the event
        '''
        self.previous_event = self.event    
        self.previous_event.label = self.label        
        self.previous_event.close_event(self.anal_tab.base_chosen, self.anal_tab.sub_chosen, self.anal_tab.res_chosen)  
        self.start_end = datetime.datetime.now(tz=datetime.timezone.utc)    
        
    def epics_update(self, event):
        '''Writes current event data to EPICS and reads status variables from EPICS.
        '''        
        self.epics.write_event(event)
        self.epics.read_all()
        event.epics = self.epics.read_pvs     # Put recently read EPICS variables in event
    
    def end_finished(self):
        '''Analysis thread has returned. Finish up closing event, closing the event instance and calling updates for each tab. Updates plots, prints to file, makes new eventfile if lines are more than 500.'''
                
        self.previous_event.print_event(self.eventfile)
        self.eventfile_lines += 1
        if self.eventfile_lines > 500:            # open new eventfile once the current one has a number of entries
            self.new_eventfile()
        self.history.add_hist(HistPoint(self.previous_event), self.hist_file)

        self.run_tab.update_event_plots()
        self.te_tab.update_event_plots()
        self.anal_tab.update_event_plots() 
        if self.config.settings['compare_tab']['enable']:
            self.compare_tab.update_event_plots()      
        
        now = datetime.datetime.now(tz=datetime.timezone.utc)
        elapsed = now.timestamp() - self.start_end.timestamp() 
        #print(self.start_end.timestamp(), now.timestamp(), elapsed)
        mes = f'Finished event at {self.event.stop_time:%H:%M:%S} UTC, after {self.previous_event.elapsed}s. Analysis returned at {now:%H:%M:%S} UTC, after {elapsed:.1f}s.'
        self.status_bar.showMessage(mes)
        logging.info(mes)
        
        if self.config.settings["ss_dir"]:
            screenshot = self.run_tab.grab()
            now = datetime.datetime.now(tz=datetime.timezone.utc)
            screenshot.save(f'{self.config.settings["ss_dir"]}/{now.strftime("%Y-%m-%d_%H-%M-%S")}.png')
          

    def new_base(self, basedict):
        '''Choose eventfile and event to act as baseline for this and future events
        Args:
            basedict: Dict of baseline event attributes, from save file
            '''
        self.baseline = Baseline(self.config, basedict)
        self.set_event_base()
        logging.info(f"Set baseline {self.baseline.stop_stamp} from {self.baseline.base_file}.")
        self.status_bar.showMessage(f"Set baseline {self.baseline.stop_time.strftime('%Y-%m-%d_%H-%M-%S')} with {self.baseline.sweeps} sweeps from {self.baseline.base_file}.")
        self.run_tab.baseline_label.setText(f"Baseline: {self.baseline.stop_time.strftime('%m/%d %H:%M')}, {self.baseline.sweeps}")

    def set_event_base(self):
        '''Set baseline in current event'''
        self.event.base_stamp = self.baseline.stop_stamp
        self.event.base_time = self.baseline.stop_time
        self.event.base_file = self.baseline.base_file
        self.event.baseline = self.baseline.phase
        #self.event.basesweep = self.baseline.phase

    def set_cc(self, cc):
        '''Set new Calibration Constant
        '''
        self.run_tab.controls_lines['cc'].setText(f"{cc:.6f}")
        self.config.controls['cc'].set_config(f"{cc:.6f}")
        logging.info(f"Saved TE data and set new calibration constant {cc}.")
        self.status_bar.showMessage(f"Saved TE data and set new calibration constant {cc}.")

    def channel_change(self, i):
        '''Channel setting changed. Make new config.'''
        name = self.channels[i]
        self.config = Config(self.config_dict['channels'][name], self.settings)           # new configuration
        self.event = Event(self)      # open empty event
        self.rs = RS_Connection(self.config)   # send new settings to R&S
        logging.info(f"Changed channel to {self.config.channel['name']}.")

    def init_connects(self):
        '''Initialize connections to required instruments, EPICS server
        '''      
        self.epics = EPICS(self)  # open EPICS
        self.rs = RS_Connection(self.config)            # open connection to Rohde and Schwarz, set stuff        

    def connect_daq(self):
        '''Try test connect to DAQ devices, turn on run buttons if successful'''
        try:
            self.daq = DAQConnection(self.config, self.config.settings['fpga_settings']['timeout_check'])     # open connection to DAQ of choice
            self.status_bar.showMessage(self.daq.message)
            logging.info(self.daq.message)

            self.run_tab.run_button.setEnabled(True)                   # turn on buttons
            self.tune_tab.run_button.setEnabled(True)
            #self.run_tab.connect_button.setEnabled(False)
            #self.run_tab.connect_button.setText('Connected: '+self.daq.name)

            del self.daq

        except Exception as e:
            self.error_dialog.showMessage('DAQ socket not connected: '+str(e))
            
    def disconnected_daq(self):
        '''DAQ has been disconnected, reset buttons'''

        self.run_tab.run_button.setEnabled(False)                   # turn on buttons
        self.tune_tab.run_button.setEnabled(False)
        self.run_tab.connect_button.setEnabled(True)
        self.run_tab.connect_button.setText('Connect')


    def run_toggle(self):
        '''Disable or enable buttons on other tabs when one tab is running'''
        if self.run_tab.run_button.isChecked():
            self.tune_tab.run_button.setEnabled(False)
            self.tune_tab.phase_spin.setEnabled(False)
            self.tune_tab.phase_slider.setEnabled(False)
            self.tune_tab.diode_spin.setEnabled(False)
            self.tune_tab.diode_slider.setEnabled(False)
            if self.config.settings['compare_tab']['enable']:
                if not self.compare_tab.compare_on:
                    self.compare_tab.run_button.setEnabled(False)
        else:
            self.tune_tab.run_button.setEnabled(True)
            self.tune_tab.phase_spin.setEnabled(True)
            self.tune_tab.phase_slider.setEnabled(True)
            self.tune_tab.diode_spin.setEnabled(True)
            self.tune_tab.diode_slider.setEnabled(True)
            if self.config.settings['compare_tab']['enable']:
                self.compare_tab.run_button.setEnabled(True)
        if self.tune_tab.run_button.isChecked():
            self.run_tab.run_button.setEnabled(False)
        else:
            self.run_tab.run_button.setEnabled(True)


    def check_state(self, *args, **kwargs):
        '''Enables colors for LineEdit validators'''
        sender = self.sender()
        validator = sender.validator()
        state = validator.validate(sender.text(), 0)[0]
        if sender.isEnabled():
            if state == QValidator.Acceptable:
                color = '#c4df9b' # green
            elif state == QValidator.Intermediate:
                color = '#fff79a' # yellow
            else:
                color = '#f6989d' # red
            sender.setStyleSheet('QLineEdit { background-color: %s }' % color)

    def label_changed(self, label):
        '''Change event label'''
        self.label = label

    def start_logger(self):
        '''Start logger
        '''
        logHandler = TimedRotatingFileHandler(os.path.join(self.config_dict['settings']['log_dir'],"log"),when="midnight")    # setup logfiles
        logHandler.suffix = "%Y-%m-%d.txt"
        logFormatter = logging.Formatter('%(asctime)s %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
        logHandler.setFormatter(logFormatter)
        logger = logging.getLogger()
        logger.addHandler(logHandler)
        logger.setLevel(logging.INFO)
        logging.info("Started new instance.")
        logging.info("Loaded config file {self.config_filename}.")

    def divider(self):
        div = QLabel ('')
        div.setStyleSheet ("QLabel {background-color: #eeeeee; padding: 0; margin: 0; border-bottom: 0 solid #eeeeee; border-top: 1 solid #eeeeee;}")
        div.setMaximumHeight (2)
        return div


    def closeEvent(self, event):
        '''Things to do on close of window ("events" here are not related to nmr data events)
        '''
        self.hist_file.close()    
        if self.run_tab.run_button.isChecked():
            self.dlg = ExitDialog()
            if self.dlg.exec():
                self.epics.monitor_running = False
                self.close_eventfile()
                self.save_session()
                event.accept()
            else: 
                event.ignore()  
        else:
            self.epics.monitor_running = False
            self.close_eventfile()
            self.save_session()
            event.accept()
        
        
         
class ExitDialog(QDialog):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Exit While Running?")

        QBtn = QDialogButtonBox.Ignore | QDialogButtonBox.Abort

        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        self.layout = QVBoxLayout()
        message = QLabel("Exiting the program while sweeps\nare running will require entry to the hall\nto reboot the DAQ. Click 'Abort'\nunless you know what you are doing!")
        self.layout.addWidget(message)
        self.layout.addWidget(self.buttonBox)
        self.setLayout(self.layout)       
        
