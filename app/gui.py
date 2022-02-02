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
from PyQt5.QtWidgets import QMainWindow, QErrorMessage, QTabWidget, QLabel, QWidget
from PyQt5.QtGui import QIntValidator, QDoubleValidator, QValidator
from PyQt5.QtCore import QThread, pyqtSignal, Qt
from logging.handlers import TimedRotatingFileHandler

from app.classes import Config, Scan, RunningScan, Event, Baseline, HistPoint, History
from app.epics import EPICS
from app.gui_run_tab import RunTab
from app.gui_base_tab import BaseTab
from app.gui_tune_tab import TuneTab
from app.gui_te_tab import TETab
from app.gui_anal_tab import AnalTab
from app.gui_expl_tab import ExplTab
from app.gui_shim_tab import ShimTab
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
    def __init__(self, parent=None):
        super().__init__(parent)
        self.error_dialog = QErrorMessage(self)
        self.status_bar = self.statusBar()
        self.status_bar.showMessage('Ready.')
        self.config_filename = 'pynmr_config.yaml'
        self.load_settings()
        self.restore_settings()
        channel_dict = self.config_dict['channels'][self.config_dict['settings']['default_channel']]  # dict of selected channel
        self.start_logger()

        self.config = Config(channel_dict, self.settings)           # current configuration
        self.event = Event(self)      # open empty event
        self.previous_event = self.event      # there is no previous event
        self.baseline = Baseline(self.config, {})     # open empty baseline
        self.history = History()   # for now, starting new history with each window
        self.new_eventfile()

        self.init_connects()
        
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
        if self.config.settings['shim_settings']['enable']:
            self.shim_tab = ShimTab(self)
            self.tab_widget.addTab(self.shim_tab, "Shims")
        #self.mag_tab = MagTab(self)
        #self.tab_widget.addTab(self.mag_tab, "Magnet")
        self.te_tab = TETab(self)
        self.tab_widget.addTab(self.te_tab, "TE")
        self.anal_tab = AnalTab(self)
        self.tab_widget.addTab(self.anal_tab, "Analysis")
        self.expl_tab = ExplTab(self)
        self.tab_widget.addTab(self.expl_tab, "Event Explorer") 
        
        self.connect_daq()
        
    def load_settings(self):
        '''Load settings from YAML config file'''

        with open(self.config_filename) as f:                           # Load settings from YAML files
           self.config_dict = yaml.load(f, Loader=yaml.FullLoader)
        self.channels = list(self.config_dict['channels'].keys())       # list of channels in config file
        self.settings = self.config_dict['settings']                    # dict of settings
        self.epics_reads = self.config_dict['epics_reads']              # dict of epics channels: name string
        self.epics_writes = self.config_dict['epics_writes']            # dict of epics channels: name string
        self.status_bar.showMessage(f"Loaded settings from {self.config_filename}.")
        
    def restore_settings(self):
        '''Restore settings from previous session'''
        with open('app/saved_settings.yaml') as f:                           # Load settings from YAML files
           self.restore_dict = yaml.load(f, Loader=yaml.FullLoader)
        
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
    
    def save_settings(self):
        '''Print settings before app exit to a file for recall on restart'''
        saved_dict  =  {
            'phase_tune' : self.config.phase_vout,
            'diode_tune' : self.config.diode_vout,
        }
        with open('app/saved_settings.yaml', 'w') as file:
            documents = yaml.dump(saved_dict, file)
            #print(saved_dict)            
            logging.info(f"Printed settings on exit to {file}.")
    
    
    def end_event(self):
        '''Start ending the event
        '''
        self.previous_event = self.event      
        self.previous_event.close_event(self.epics.read_all(), self.anal_tab.base_chosen, self.anal_tab.sub_chosen, self.anal_tab.res_chosen)    
        
    def end_finished(self):
        '''Analysis thread has returned. Finished up closing event, closing the event instance and calling updates for each tab. Updates plots, prints to file, makes new eventfile if lines are more than 500.'''
        self.previous_event.print_event(self.eventfile)
        self.eventfile_lines += 1
        if self.eventfile_lines > 500:            # open new eventfile once the current one has a number of entries
            self.new_eventfile()
        self.history.add_hist(HistPoint(self.previous_event))

        self.run_tab.update_event_plots()
        self.te_tab.update_event_plots()
        self.anal_tab.update_event_plots()
        
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
        self.status_bar.showMessage(f"Set baseline {self.baseline.stop_time.strftime('%Y-%m-%d_%H-%M-%S')} from {self.baseline.base_file}.")
        self.run_tab.baseline_label.setText(f"Baseline: {self.baseline.stop_time.strftime('%m/%d/%Y %H:%M:%S')}")

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
        self.run_tab.combo_changed()
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
        else:
            self.tune_tab.run_button.setEnabled(True)
            self.tune_tab.phase_spin.setEnabled(True)
            self.tune_tab.phase_slider.setEnabled(True)
            self.tune_tab.diode_spin.setEnabled(True)
            self.tune_tab.diode_slider.setEnabled(True)
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
        logging.info("Loaded config file")

    def divider(self):
        div = QLabel ('')
        div.setStyleSheet ("QLabel {background-color: #eeeeee; padding: 0; margin: 0; border-bottom: 0 solid #eeeeee; border-top: 1 solid #eeeeee;}")
        div.setMaximumHeight (2)
        return div

    def closeEvent(self, event):
        '''Things to do on close of window ("events" here are not related to nmr data events)
        '''
        self.epics.monitor_running = False
        self.close_eventfile()
        self.save_settings()
        event.accept()
