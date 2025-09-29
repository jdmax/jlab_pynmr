"""Core data model classes for PyNMR application"""

import datetime
import json
import pytz
import numpy as np
from scipy import optimize
from dateutil.parser import parse
from typing import Dict, Any, List, Union
from PySide6.QtCore import Qt


class Scan:
    """Data object for averaged set of sweeps, with method to average.
    
    Args:
        config: Config object containing all settings for the scan
    
    Attributes:
        phase: 1D Numpy array of measurements at each frequency points for the phase
        diode: 1D Numpy array of measurements at each frequency points for the diode
    """
    
    def __init__(self, config):
        self.num = 0  # number of sweeps currently in scan
        self.freq_list = config.freq_list
        self.phase = np.zeros(len(self.freq_list))  # list of phase curve points
        self.diode = np.zeros(len(self.freq_list))  # list of diode curve points
           
    def avg_chunks(self, new_sigs):
        """Average new chunk with rest of set.
        
        Args:
            new_sigs: tuple of number of sweeps in the chunk, new phase data list and new diode data list
        """
        chunk_num, num_in_chunk, phase_chunk, diode_chunk = new_sigs
        self.num += num_in_chunk
        self.phase = self.phase + (num_in_chunk/self.num)*(phase_chunk - self.phase)
        self.diode = self.diode + (num_in_chunk/self.num)*(diode_chunk - self.diode)
      
    def change_set(self, new_sigs):
        """Accept a new set of points, already averaged. This is used for the NIDAQ, as it accumulates internally"""
        num, num_in_chunk, phase_chunk, diode_chunk = new_sigs
        self.num = num_in_chunk
        self.phase = phase_chunk
        self.diode = diode_chunk


class RunningScan:
    """Data object for averaged set of sweeps, with method to perform running average.
    
    Args:
        config: Config object for scan
        to_avg: Number of sweeps to keep in running average
        
    Attributes:
        freq_list: Frequency points of sweep in MHz, from config
        phase: List of measurements at each frequency points for the phase
        diode: List of measurements at each frequency points for the diode
        points_in: Number of sweeps currently in the average
    """
    
    def __init__(self, config, to_avg):
        self.freq_list = config.freq_list
        self.phase = np.zeros(len(self.freq_list))  # list of phase curve points
        self.diode = np.zeros(len(self.freq_list))  # list of diode curve points
        self.points_in = 0  # sweeps currently in average
        self.to_avg = to_avg

    def running_avg(self, new_sigs):
        """Performs running average for tuning
        
        Args:
            new_sigs: tuple of number of sweeps in the chunk, new phase data list and new diode data list
        """
        chunk_num, num_in_chunk, new_phase, new_diode = new_sigs
        if self.points_in < self.to_avg:
            self.points_in += num_in_chunk
        else:
            self.points_in = self.to_avg
            
        self.phase = (new_phase*num_in_chunk + self.phase*(self.points_in - num_in_chunk))/self.points_in 
        self.diode = (new_diode*num_in_chunk + self.diode*(self.points_in - num_in_chunk))/self.points_in


class EventData:
    """Data and method object for single event point. Takes config instance on init.
    
    Arguments:
        config: Config class instance
    
    Attributes:
        config: Config object for the event
        scan: Scan object for the event
        start_time: Datetime object for time event started accumulating measurements
        start_stamp: Timestamp int for starting datetime
        stop_time: Datetime object for time event stopped accumulating measurements
        stop_stamp: Timestamp int for stop datetime
        baseline: Baseline phase sweep list selected from baseline tab
        basesweep: Baseline used, varies based on chosen method from analysis tab
        basesub: Baseline subtracted phase sweep list for event
        polysub: Polyfit subtracted basesub list
        wings: Portion of sweep to use for fit, 4 long list giving position of left start, left stop, right start and right stop positions as a decimal from 0 to 1
        cc: Calibration constant float
        area: Area under polyfit curve float
        pol: Measured polarization for event, CC*Area, float
        base_time: Datetime object for stop of baseline event
        base_stamp: Timestamp int of baseline event
        base_file: Filename string where baseline event can be found
        uwave_freq: Microwave frequency (GHz) as read from GPIB
        uwave_power: Microwave power (W) as read from serial
        elapsed: Number of seconds taken to finish sweeps
        label: type of event from combobox
    """
   
    def __init__(self, parent):
        self.config = parent.config
        self.parent = parent
        self.scan = Scan(self.config)
        
        self.start_time = datetime.datetime.now(tz=datetime.timezone.utc)        
        self.start_stamp = self.start_time.timestamp()
        
        self.baseline = np.zeros(len(self.scan.phase))
        self.basesweep = np.zeros(len(self.scan.phase))
        self.basesub = []
        self.fitsub = []
        self.wings = [0.01, 0.25, .75, 0.99]  # portion of sweep to use for fit
        
        self.cc = self.config.controls['cc'].value
        self.area = 0.
        self.pol = 0.
        self.stop_time = datetime.datetime(2000, 1, 1)
        self.stop_stamp = datetime.datetime(2000, 1, 1).timestamp()
        
        self.base_time = datetime.datetime(2000, 1, 1)
        self.base_stamp = datetime.datetime(2000, 1, 1).timestamp()
        self.base_file = 'None'       
        self.label = 'None'
        self.epics = {}  # dict of epics reads
        
        self.uwave_freq = 0
        self.uwave_power = 0
        
        self.chassis_temp = self.parent.chassis_temp
        self.shimA = self.parent.shimA
        self.shimB = self.parent.shimB
        self.shimC = self.parent.shimC
        self.shimD = self.parent.shimD
        
        self.beam_current_sum = 0
        self.beam_time_sum = 0
        self.beam_current_update_time = self.start_time
        
    def update_event(self, new_sigs):
        """Method to update event with new signal chunk
        
        Args:
            new_sigs: tuple of number of sweeps in the chunk, new phase data list and new diode data list
        """
        if 'NIDAQ' in self.config.settings['daq_type']:
            self.scan.change_set(new_sigs)
        else:
            self.scan.avg_chunks(new_sigs)

    def print_event(self, eventfile):
        """Print out event to eventfile, formatting to dict to write to json line.
        
        Args:
            eventfile: File object to write event to
        """
        exclude_list = ['freq_bytes', 'parent', 'anal_thread']
        json_dict = {}        
        json_dict.update(self.scan.__dict__)
        
        for key, entry in self.__dict__.items():  # filter event attributes for json dict
            if isinstance(entry, datetime.datetime):
                json_dict.update({key: entry.__str__()})  # datetime to string
            elif isinstance(entry, Baseline):
                json_dict.update({key: entry.stop_time.__str__()})  # baseline to stoptime string
            elif 'config' in key: 
                for key2, entry2 in entry.__dict__.items():
                    if key2 in exclude_list:
                        pass
                    elif 'controls' in key2:
                        for key3, entry3 in entry2.items():
                            json_dict.update({key3: entry3.value})
                    else: 
                        json_dict.update({key2: entry2})    
            elif 'scan' in key: 
                for key2, entry2 in entry.__dict__.items():
                    json_dict.update({key2: entry2})
            elif key in exclude_list:
                pass
            else:
                json_dict.update({key: entry})
                
        for key, entry in json_dict.items():   
            if isinstance(entry, np.ndarray):       
                json_dict[key] = entry.tolist()
                
        json_record = json.dumps(json_dict)
        eventfile.write(json_record+'\n')  # write to file as json line
            
    def close_event(self, base_method, sub_method, res_method):
        """Closes event, calls for signal analysis, adds epics reads to event
        
        Args:
            base_method: method to produce baseline subtracted signal given event instance
            sub_method: method to produce fit subtracted signal and area given event instance
            res_method: method to produce result given event instance
        """
        self.stop_time = datetime.datetime.now(tz=datetime.timezone.utc)
        self.stop_stamp = self.stop_time.timestamp()
        self.elapsed = (self.stop_time - self.start_time).seconds
        
        self.signal_analysis(base_method, sub_method, res_method)
        self.analysis_completed = True       
    
    def signal_analysis(self, base_method, sub_method, res_method):
        """Perform analysis on signal"""
        # Guard against multiple analysis thread creation
        if hasattr(self, 'anal_thread') and self.anal_thread is not None:
            if hasattr(self.anal_thread, 'isRunning') and self.anal_thread.isRunning():
                print("Analysis thread already running for this event")
                return
        
        if np.any(self.scan.phase):  # do the thing
            try:
                from .analysis import AnalThread
                from .thread_manager import get_thread_manager
                
                # Create analysis thread
                self.anal_thread = AnalThread(self, base_method, sub_method, res_method)
                
                # Get thread manager and register thread
                thread_manager = get_thread_manager()
                thread_manager.register_thread(self.anal_thread)
                
                # Connect signals
                self.anal_thread.finished.connect(self.parent.end_finished)
                
                # Start thread using thread manager
                thread_manager.start_thread(self.anal_thread.thread_name)
                
            except Exception as e: 
                print('Exception starting analysis thread: '+str(e))  
        else:  # unless the phase signal is zeroes, then set all to zeroes
            self.basesweep = np.zeros(len(self.basesweep))
            self.basesub = np.zeros(len(self.basesweep))
            self.fitcurve = np.zeros(len(self.basesweep))
            self.fitsub = np.zeros(len(self.basesweep))
            self.rescurve = np.zeros(len(self.basesweep))
            self.pol, self.area = 0, 0
            
    def poly(self, p, x):
        """Third order polynomial for fitting
        
        Args:
            p: List of polynomial coefficients
            x: Sample point
        """
        return p[0] + p[1]*x + p[2]*np.power(x, 2) + p[3]*np.power(x, 3)
        
    def fit_wings(self, wings, sweep):
        """Fit to wings with scipy
        
        Args:
            wings: Wings, 4 element list of portions of sweep to use, attribute from Config
            sweep: List of samples to fit
            
        Returns:
            pf: Tuple of final fit coefficient list
        """
        bounds = [x*len(sweep) for x in wings]
        data = [(x, y) for x, y in enumerate(sweep) if (bounds[0] < x < bounds[1] or bounds[2] < x < bounds[3])]
        X = np.array([x for x, y in data])
        Y = np.array([y for x, y in data])
        
        errfunc = lambda p, x, y: self.poly(p, x) - y
        pi = [0.01, 0.8, 0.01, 0.001, 0.00001]  # initial guess
        pf, success = optimize.leastsq(errfunc, pi[:], args=(X, Y))  # perform fit
        return pf
        
    def set_uwave(self, freq, power):
        """Set microwave power and frequency"""
        self.uwave_freq = freq
        self.uwave_power = power
        
    def sum_beam_current(self, current):
        """Sum in time-weighted beam current to make average over event"""
        time = (datetime.datetime.now(tz=datetime.timezone.utc) - self.beam_current_update_time).total_seconds()
        self.beam_current_sum = self.beam_current_sum + current*time
        self.beam_time_sum = self.beam_time_sum + time
        self.beam_current_update_time = datetime.datetime.now(tz=datetime.timezone.utc)


class Baseline:
    """Data object for baseline event.
    
    Args:
        config: Config object
        dict: Dict of all event attributes to add as attributes to this object.
    """

    def __init__(self, config, dict_data):
        self.config = config
        self.stop_stamp = 0
        self.stop_time = datetime.datetime(2000, 1, 1)
        self.base_file = ''
        self.phase = np.zeros(self.config.settings['steps'])
        self.__dict__.update(dict_data)  # update with attributes from passed event
        self.phase = np.array(self.phase)


class HistPoint:
    """Single history point. History contains only critical info from event.
    
    Attributes:
        dt: Datetime object of time event stopped
        pol: Float measured polarization
        cc: Float calibration constant
        area: Float area under polyfit
        label: event label
        uwave_freq: microwave frequency in GHz
        epics_reads: dict of all epics variables read
        beam_current: time averaged beam current
    """
    
    def __init__(self, event):
        if isinstance(event, EventData):
            self.new_point(event)
        else:
            self.restore_point(event)
            
    def restore_point(self, entry):
        """Make new point from a restored dict"""
        self.dt = parse(entry['dt'])
        self.dt_stamp = entry['dt_stamp']
        self.pol = entry['pol']
        self.cc = entry['cc']
        self.area = entry['area']
        self.label = entry['label']
        self.uwave_freq = entry['uwave_freq']
        self.epics_reads = entry['epics_reads']
        self.beam_current = entry['beam_current']    
    
    def new_point(self, event):
        """Make new point from event"""
        self.dt = event.stop_time
        self.dt_stamp = event.stop_stamp
        self.pol = event.pol
        self.cc = event.cc
        self.area = event.area
        self.label = event.label
        self.uwave_freq = event.uwave_freq
        self.epics_reads = event.epics   
        try:
            self.beam_current = event.beam_current_sum/event.beam_time_sum
        except ZeroDivisionError:
            self.beam_current = 0


class History:
    """Contains polarization history since start, methods for returning subset of points"""
    
    def __init__(self):
        self.data = {}  # dict of HistPoints keyed on dt stamp
        
    def add_hist(self, hp, hist_file):  
        """Add to history dict, and write to history file"""
        self.data[hp.dt_stamp] = hp
        json_record = json.dumps(hp.__dict__, default=str)
        hist_file.write(json_record+'\n')           
        
    def res_hist(self, hp):  
        """Restore to history dict"""
        self.data[hp.dt_stamp] = hp        
        
    def to_plot(self, start_stamp=0, stop_stamp=0):
        """Gets datetimes and polarizations in history
        
        Returns:
            Dict keyed on timestamps of HistPoints          
        """
        if start_stamp == 0:
            return self.data
        else:
            hist_data = {k: v for k, v in self.data.items() if start_stamp < k < stop_stamp}
            return hist_data