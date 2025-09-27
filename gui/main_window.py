"""Main GUI window for PyNMR application"""

import datetime
import time
import socket
import sys
import os
import yaml
import pytz
import logging
import json
from PySide6.QtWidgets import (QMainWindow, QErrorMessage, QTabWidget, QLabel, 
                              QWidget, QDialog, QDialogButtonBox, QVBoxLayout)
from PySide6.QtGui import QIntValidator, QDoubleValidator, QValidator
from PySide6.QtCore import QThread, Signal, Qt
from logging.handlers import TimedRotatingFileHandler

from config import Config
from core import Scan, RunningScan, EventData, Baseline, HistPoint, History
from hardware import EPICS, DAQConnection, UDP, TCP, RS_Connection, NI_Connection
# Import tab modules individually to avoid circular dependencies
from .tabs.run_tab import RunTab
from .tabs.base_tab import BaseTab
from .tabs.tune_tab import TuneTab
from .tabs.te_tab import TETab
from .tabs.superte_tab import SuperTab
from .tabs.analysis_tab import AnalTab
from .tabs.explore_tab import ExplTab
from .tabs.shim_tab import ShimTab
from .tabs.fm_tab import FMTab
from .tabs.compare_tab import CompareTab
from .tabs.temp_tab import TempTab
from .tabs.mag_tab import MagTab


class MainWindow(QMainWindow):
    """Main window of application, with all the utility gui tabs.
    
    Includes methods for starting Event, Base instances. Event and Baselines 
    are attributes, so that all child tabs can access.

    Attributes:
        config: Current Config configuration instance
        event: Current EventData instance
        baseline: Current Baseline instance
        epics: Open EPICS connection
        history: History instance containing set of HistPoints
        eventfile: Current event data filehandle
        eventfile_start: String of eventfile start time
        eventfile_lines: Number of entries in current eventfile
        channels: List of channels from config file
        settings: Dict of settings from config file
        epics_reads: Dict keyed on epics channels with name strings
        epics_writes: Dict keyed on epics channels with EventData attributes to send
    """
    
    def __init__(self, config_file, parent=None):
        super().__init__(parent)
        self.error_dialog = QErrorMessage(self)
        self.status_bar = self.statusBar()
        self.status_bar.showMessage('Ready.')
        self.config_filename = config_file
        self.load_settings()
        channel_dict = self.config_dict['channels'][self.config_dict['settings']['default_channel']]
        self.start_logger()
        self.chassis_temp = 0
        self.shimA = 0
        self.analysis_in_progress = False
        self.pending_next_run = False
        self.active_threads = []  # Centralized thread registry
        self.shimB = 0
        self.shimC = 0
        self.shimD = 0
        
        self.label_changed('None')
        
        self.config = Config(channel_dict, self.settings)
        self.event = EventData(self)
        self.previous_event = self.event
        self.baseline = Baseline(self.config, {})
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
        self.te_tab = TETab(self)
        self.tab_widget.addTab(self.te_tab, "TE")
        self.anal_tab = AnalTab(self)
        self.tab_widget.addTab(self.anal_tab, "Analysis")
        
        # Conditional tabs based on settings
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
        
        cc_value = self.restore_dict.get('cc', 1.0)  # Default cc value
        self.set_cc(cc_value)   
        self.connect_daq()
        
        # Enable run button after initialization
        self.run_toggle()
        
    def load_settings(self):
        """Load settings from YAML config file"""
        with open(self.config_filename) as f:
           self.config_dict = yaml.load(f, Loader=yaml.FullLoader)
        self.channels = list(self.config_dict['channels'].keys())
        self.settings = self.config_dict['settings']
        self.epics_reads = self.config_dict['epics_reads']
        self.epics_writes = self.config_dict['epics_writes']
        print(f"Loaded settings from {self.config_filename}.")
                
    def new_event(self):
        """Create new event instance"""
        self.event = EventData(self)
        self.set_event_base()

    def new_eventfile(self):
        """Open new eventfile"""
        self.close_eventfile()
        now = datetime.datetime.now(tz=datetime.timezone.utc)
        self.eventfile_start = now.strftime("%Y-%m-%d_%H-%M-%S")
        self.eventfile_name = os.path.join(self.config.settings["event_dir"], f'current_{self.eventfile_start}.txt')
        self.eventfile = open(self.eventfile_name, "w")
        self.eventfile_lines = 0
        logging.info(f"Opened new evenfile {self.eventfile_name}")

    def close_eventfile(self):
        """Try to close and rename eventfile"""
        try:
            self.eventfile.close()
            now = datetime.datetime.now(tz=datetime.timezone.utc)
            new = f'{self.eventfile_start}__{now.strftime("%Y-%m-%d_%H-%M-%S")}.txt'
            os.rename(self.eventfile_name, os.path.join(self.config.settings["event_dir"], new))
            logging.info(f"Closed eventfile and moved to {new}.")
        except AttributeError:
            logging.info(f"Error closing eventfile.")
    
    def save_session(self):
        """Print settings before app exit to a file for recall on restart"""
        saved_dict = {
            'phase_tune': self.config.phase_vout,
            'diode_tune': self.config.diode_vout,
            'cc': float(self.run_tab.controls_lines['cc'].text()),
            'channel': self.run_tab.channel_combo.currentIndex()
        }
        with open(f'{self.config.settings["session_file"]}.yaml', 'w') as file:
            yaml.dump(saved_dict, file)
            logging.info(f"Printed settings on exit to {file}.") 
            
    def restore_session(self):
        """Restore settings from previous session"""
        try:
            with open(f'{self.config.settings["session_file"]}.yaml') as f:                     
                self.restore_dict = yaml.load(f, Loader=yaml.FullLoader)
        except FileNotFoundError:
            # No session file exists, skip restoration
            self.restore_dict = {}
           
    def restore_history(self):
        """Open history object and restore previous history into it"""       
        self.hist_file = open(f"{self.config_dict['settings']['history_file']}.json", "a+") 
        self.hist_file.seek(0)
        self.history = History()
        for line in self.hist_file:
            jd = json.loads(line.rstrip('\n|\r'))            
            self.history.res_hist(HistPoint(jd))
        
    def end_event(self):
        """Start ending the event"""
        self.analysis_in_progress = True
        self.previous_event = self.event    
        self.previous_event.label = self.label        
        self.previous_event.close_event(self.anal_tab.base_chosen, self.anal_tab.sub_chosen, self.anal_tab.res_chosen)  
        self.start_end = datetime.datetime.now(tz=datetime.timezone.utc)    
        
    def epics_update(self, event):
        """Writes current event data to EPICS and reads status variables from EPICS."""        
        self.epics.write_event(event)
        self.epics.read_all()
        event.epics = self.epics.read_pvs
    
    def end_finished(self):
        """Analysis thread has returned. Finish up closing event."""
        # Prevent duplicate writes of the same event
        if hasattr(self.previous_event, 'written_to_file') and self.previous_event.written_to_file:
            return
        
        self.previous_event.print_event(self.eventfile)
        self.previous_event.written_to_file = True
        self.eventfile_lines += 1
        if self.eventfile_lines > 500:
            self.new_eventfile()
        self.history.add_hist(HistPoint(self.previous_event), self.hist_file)

        self.run_tab.update_event_plots()
        self.te_tab.update_event_plots()
        self.anal_tab.update_event_plots() 
        if self.config.settings['compare_tab']['enable']:
            self.compare_tab.update_event_plots()      
        
        now = datetime.datetime.now(tz=datetime.timezone.utc)
        elapsed = now.timestamp() - self.start_end.timestamp() 
        mes = f'Finished event at {self.event.stop_time:%H:%M:%S} UTC, after {self.previous_event.elapsed}s. Analysis returned at {now:%H:%M:%S} UTC, after {elapsed:.1f}s.'
        self.status_bar.showMessage(mes)
        logging.info(mes)
        
        if self.config.settings["ss_dir"]:
            screenshot = self.run_tab.grab()
            now = datetime.datetime.now(tz=datetime.timezone.utc)
            screenshot.save(f'{self.config.settings["ss_dir"]}/{now.strftime("%Y-%m-%d_%H-%M-%S")}.png')
            
        # Analysis is complete, clear flag and start next run if needed
        self.analysis_in_progress = False
        if self.pending_next_run:
            self.pending_next_run = False
            if hasattr(self, 'run_tab') and self.run_tab.run_button.isChecked():
                self.run_tab.start_thread()
                
    def register_thread(self, thread):
        """Register a thread to prevent premature garbage collection"""
        if thread not in self.active_threads:
            self.active_threads.append(thread)
            # DON'T connect finished signal here - let the thread handle its own connections
            # thread.finished.connect(lambda: self.cleanup_thread(thread))
            
    def cleanup_thread(self, thread):
        """Remove thread from registry when finished"""
        if thread in self.active_threads:
            self.active_threads.remove(thread)
            # Schedule for deletion after event loop processes
            thread.deleteLater()
            
    def cleanup_all_threads(self):
        """Stop and cleanup all active threads"""
        for thread in self.active_threads[:]:  # Copy list since we'll modify it
            if thread.isRunning():
                thread.quit()
        self.active_threads.clear()

    def new_base(self, basedict):
        """Choose eventfile and event to act as baseline for this and future events
        
        Args:
            basedict: Dict of baseline event attributes, from save file
        """
        self.baseline = Baseline(self.config, basedict)
        self.set_event_base()
        logging.info(f"Set baseline {self.baseline.stop_stamp} from {self.baseline.base_file}.")
        self.status_bar.showMessage(f"Set baseline {self.baseline.stop_time.strftime('%Y-%m-%d_%H-%M-%S')} with {self.baseline.sweeps} sweeps from {self.baseline.base_file}.")
        self.run_tab.baseline_label.setText(f"Baseline: {self.baseline.stop_time.strftime('%m/%d %H:%M')}, {self.baseline.sweeps}")

    def set_event_base(self):
        """Set baseline for current event"""
        self.event.base_stamp = self.baseline.stop_stamp
        self.event.base_time = self.baseline.stop_time
        self.event.base_file = self.baseline.base_file
        self.event.baseline = self.baseline.phase

    def set_cc(self, new_cc):
        """Set calibration constant"""
        self.config.controls['cc'].value = new_cc

    def label_changed(self, new_label):
        """Update event label"""
        self.label = new_label

    def channel_change(self, i):
        """Channel setting changed. Make new config."""
        name = self.channels[i]
        self.config = Config(self.config_dict['channels'][name], self.settings)
        self.event = EventData(self)
        self.rs = RS_Connection(self.config)
        logging.info(f"Changed channel to {self.config.channel['name']}.")

    def init_connects(self):
        """Initialize EPICS connections"""
        self.epics = EPICS(self)

    def connect_daq(self):
        """Connect to DAQ system"""
        # DAQ connections are now created by individual threads when needed
        # to avoid multiple simultaneous connections to the same device


    def closeEvent(self, close_event):
        """Handle application close event"""
        if hasattr(self, 'run_tab') and self.run_tab.run_button.isChecked():
            reply = ExitDialog().exec()
            if reply == QDialog.Rejected:
                close_event.ignore()  
        else:
            # Stop all threads before closing
            if hasattr(self, 'epics') and self.epics:
                self.epics.monitor_running = False
            
            # Use ThreadManager for centralized cleanup
            try:
                from core.thread_manager import get_thread_manager, cleanup_thread_manager
                thread_manager = get_thread_manager()
                thread_manager.stop_all_threads(timeout=3000)  # 3 second timeout
                cleanup_thread_manager()  # Clean up the global thread manager
            except Exception as e:
                print(f"Error during ThreadManager cleanup: {e}")
            
            # Fallback to old thread cleanup for any remaining threads
            self.cleanup_all_threads()
                    
            self.close_eventfile()
            self.save_session()
            close_event.accept()

    def check_state(self, *args, **kwargs):
        """Enable colors for LineEdit validators"""
        sender = self.sender()
        validator = sender.validator()
        state = validator.validate(sender.text(), 0)[0]
        if sender.isEnabled():
            if state == QValidator.Acceptable:
                color = '#c4df9b'  # green
            elif state == QValidator.Intermediate:
                color = '#fff79a'  # yellow
            else:
                color = '#f6989d'  # red
            sender.setStyleSheet('QLineEdit { background-color: %s }' % color)

    def start_logger(self):
        """Initialize logging system"""
        os.makedirs(self.config_dict['settings']['log_dir'], exist_ok=True)
        log_filename = os.path.join(self.config_dict['settings']['log_dir'], 'pynmr.log')

        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                TimedRotatingFileHandler(log_filename, when='midnight', interval=1, backupCount=30),
                logging.StreamHandler()
            ]
        )

    def divider(self):
        """Create a visual divider line"""
        div = QLabel('')
        div.setStyleSheet("QLabel {background-color: #eeeeee; padding: 0; margin: 0; border-bottom: 0 solid #eeeeee; border-top: 1 solid #eeeeee;}")
        div.setMaximumHeight(2)
        return div

    def run_toggle(self):
        """Disable or enable buttons on other tabs when one tab is running"""
        if hasattr(self, 'run_tab') and self.run_tab.run_button.isChecked():
            if hasattr(self, 'tune_tab'):
                self.tune_tab.run_button.setEnabled(False)
                self.tune_tab.phase_spin.setEnabled(False)
                self.tune_tab.phase_slider.setEnabled(False)
                self.tune_tab.diode_spin.setEnabled(False)
                self.tune_tab.diode_slider.setEnabled(False)
            if self.config.settings['compare_tab']['enable'] and hasattr(self, 'compare_tab'):
                if not self.compare_tab.compare_on:
                    self.compare_tab.run_button.setEnabled(False)
        else:
            if hasattr(self, 'tune_tab'):
                self.tune_tab.run_button.setEnabled(True)
                self.tune_tab.phase_spin.setEnabled(True)
                self.tune_tab.phase_slider.setEnabled(True)
                self.tune_tab.diode_spin.setEnabled(True)
                self.tune_tab.diode_slider.setEnabled(True)
            if self.config.settings['compare_tab']['enable'] and hasattr(self, 'compare_tab'):
                self.compare_tab.run_button.setEnabled(True)
        if hasattr(self, 'tune_tab') and self.tune_tab.run_button.isChecked():
            if hasattr(self, 'run_tab'):
                self.run_tab.run_button.setEnabled(False)
        else:
            if hasattr(self, 'run_tab'):
                self.run_tab.run_button.setEnabled(True)


class ExitDialog(QDialog):
    """Dialog for confirming exit while DAQ is running"""
    
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