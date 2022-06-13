'''PyNMR, J.Maxwell 2020
'''
from PyQt5.QtGui import QIntValidator, QDoubleValidator, QRegExpValidator
from PyQt5.QtCore import QThread, pyqtSignal, Qt
import random
import os.path
import datetime
import json
import pytz
from scipy import optimize
import numpy as np
import yaml
from bitstring import Bits

class ConfigItem():
    '''Single configurable item with validator
            
    Args:
        value: Value of item
        text: Text string describing item for label
        valid: QValidator object for the value string
    '''
    
    def __init__(self, value, text, valid):
        self.value = value
        self.text = text
        self.valid = valid
    def set_config(self, value):
        '''Change config settings to those in the LineEdit boxes, changing string to correct type based on validator
        
        Args:
            value: Value to change the config item to.
        '''
        if type(self.valid)==type(QIntValidator()):
            self.value = int(value)
        elif type(self.valid)==type(QDoubleValidator()):
            self.value = float(value)
        else:
            self.value = value

class Config():
    '''Contains all relevent settings data for NMR measurement
    
    Arguments:
        channel: Dict of current channel setting, selected from config file
        settings: Dict of settings from config file
    
    Attributes:
        channel: Dict of channel settings; keys are species, cent_freq, mod_freq, power
        controls: Dict of ConfigItems for controls
        freq_list: 1D Numpy array of frequency points in sweep as a float, in MHz
        freq_bytes: List of frequency steps, as bytes of 16 bit binary word for R&S: https://www.rohde-schwarz.com/webhelp/sma100a_webhelp_1/Content/fb359696521a42fa.htm        
        diode_vout: DAC percentage on tank circuit varactor capacitor for tuning. 1 (100%) value is set in DAQ routine.
        phase_vout: DAC percentage on electronic phase adjust for tuning. 1 (100%) value is seet in DAQ routine.
    '''
    def __init__(self, channel, settings):
    
        self.channel = channel
        self.settings = settings  
        self.diode_vout = 0   
        self.phase_vout = 0

        self.controls = {}          # NMR settings requiring control on run tab     
        self.controls['sweeps'] = ConfigItem(640, 'Sweeps per Event', QIntValidator(10, 1000000))
        self.controls['cc'] = ConfigItem(-.08, 'Calibration Constant', QDoubleValidator(-1000, 1000, 7))
        
        # Make list of frequencies and list of bytes to send to R&S
        # https://www.rohde-schwarz.com/webhelp/sma100a_webhelp_1/Content/fb359696521a42fa.htm
        # go from -32768 to 32767, convert to bytes twos complement        
        # even distribution of steps in range
        if os.path.exists(channel['sweep_file']):
            freq_ints = np.loadtxt(channel['sweep_file'], dtype=np.int32)
            print('Using sweep profile from '+channel['sweep_file']+'.')
        else:
            print('Using standard sweep profile.')
            freq_ints = np.linspace(-32768, 32767, num=self.settings['steps']).astype('int32')            # numpy array 
            #[print(x) for x in freq_ints]
        self.freq_list = self.channel['cent_freq'] + self.channel['mod_freq']/1000*(freq_ints)/32768    # in MHz
        self.freq_bytes = [int(i).to_bytes(2, byteorder='little', signed=True) for i in freq_ints]   # bytes for 16-bit word
        #self.adc_timing = [i*36.72 for i,e in enumerate(self.freq_list)]   # timing of adc measurements in us, assuming 36.72 us between
           
class Scan():
    '''Data object for averaged set of sweeps, with method to average.
    
    Args:
        config: Config object containing all settings for the scan
    
    Attributes:
        phase: 1D Numpy array of measurements at each frequency points for the phase
        diode: 1D Numpy array of measurements at each frequency points for the diode
    
    '''
    def __init__(self, config):
        self.num = 0            # number of sweeps currently in scan
        
        self.freq_list = config.freq_list
        
        self.phase = np.zeros(len(self.freq_list))       # list of phase curve points
        self.diode = np.zeros(len(self.freq_list))       # list of diode curve points
           
    def avg_chunks(self, new_sigs):
        '''Average new chunk with rest of set.
        
        Args:
            new_sigs: tuple of number of sweeps in the chunk, new phase data list and new diode data list
                
        '''
        chunk_num, num_in_chunk, phase_chunk, diode_chunk = new_sigs
        self.num += num_in_chunk
        self.phase = self.phase + (num_in_chunk/self.num)*(phase_chunk - self.phase)
        self.diode = self.diode + (num_in_chunk/self.num)*(diode_chunk - self.diode)
        
            # https://en.wikipedia.org/wiki/Algorithms_for_calculating_variance    # get running stats for chunks
            # rec_sweeps += num_in_chunk
            # phase_old = phase_set
            # phase_set = [i + (num_in_chunk/rec_sweeps)*(j - i) for i,j in zip(phase_old, phase_chunk)]
            # phase_S = [i + num_in_chunk*(j - k)*(j - l) for i,j,k,l in zip(phase_S, phase_chunk, phase_old, phase_set)]
            # diode_old = diode_set
            # diode_set = [i + (num_in_chunk/rec_sweeps)*(j - i) for i,j in zip(diode_old, diode_chunk)]
            # diode_S = [i + num_in_chunk*(j - k)*(j - l) for i,j,k,l in zip(diode_S, diode_chunk, diode_old, diode_set)]
            # phase_std = [math.sqrt(i/rec_sweeps) for i in phase_S]
            # diode_std = [math.sqrt(i/rec_sweeps) for i in diode_S]
      
    def change_set(self, new_sigs):
        '''Accept a new set of points, already averaged. This is used for the NIDAQ, as it accumulates internally
        '''
        num_in_chunk, phase_chunk, diode_chunk = new_sigs
        self.num = num_in_chunk
        self.phase = phase_chunk
        self.diode = diode_chunk
      
        
class RunningScan():
    '''Data object for averaged set of sweeps, with method to perform running average.
    
    Args:
        config: Config object for scan
        to_avg: Number of sweeps to keep in running average
        
    Attributes:
        freq_list: Frequency points of sweep in MHz, from config
        phase: List of measurements at each frequency points for the phase
        diode: List of measurements at each frequency points for the diode
        points_in: Number of sweeps currently in the average
    '''
    def __init__(self, config, to_avg):

        self.freq_list = config.freq_list
        self.phase = np.zeros(len(self.freq_list))       # list of phase curve points
        self.diode = np.zeros(len(self.freq_list))       # list of diode curve points
        self.points_in = 0              # sweeps currently in average
        self.to_avg = to_avg

    def running_avg(self, new_sigs):
        '''Performs running average for tuning
        
        Args:
            new_sigs: tuple of number of sweeps in the chunk, new phase data list and new diode data list
        '''
        chunk_num, num_in_chunk, new_phase, new_diode = new_sigs
        if self.points_in < self.to_avg:
            self.points_in += num_in_chunk
        else:
            self.points_in = self.to_avg
            
        self.phase = (new_phase*num_in_chunk + self.phase*(self.points_in - num_in_chunk))/self.points_in 
        self.diode = (new_diode*num_in_chunk + self.diode*(self.points_in - num_in_chunk))/self.points_in 
        
        
        # self.phase = [(i*num_in_chunk + j*(self.points_in - num_in_chunk))/self.points_in for i, j in zip(new_phase, self.phase)]
        # self.diode = [(i*num_in_chunk + j*(self.points_in - num_in_chunk))/self.points_in for i, j in zip(new_diode, self.diode)]
            

class Event():
    '''Data and method object for single event point. Takes config instance on init.
    
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
    '''
   
    def __init__(self, parent):
        self.config = parent.config
        self.parent = parent
        self.scan = Scan(self.config)
        
        #self.start_time =  datetime.datetime.now(tz=pytz.timezone('US/Eastern'))
        self.start_time =  datetime.datetime.now(tz=datetime.timezone.utc)        
        self.start_stamp = self.start_time.timestamp()
        #self.start_stamp = (datetime.datetime.now(tz=datetime.timezone.utc) - datetime.datetime(1970,1,1,0,0,0)).total_seconds()
        
        self.baseline  = np.zeros(len(self.scan.phase))
        self.basesweep = np.zeros(len(self.scan.phase))
        self.basesub = []
        self.fitsub = []
        self.wings = [0.01,0.25,.75,0.99]  # portion of sweep to use for fit
        

        self.cc = self.config.controls['cc'].value
        self.area = 0.
        self.pol = 0.
        self.stop_time = datetime.datetime(2000,1,1)
        self.stop_stamp = datetime.datetime(2000,1,1).timestamp()
        
        self.base_time = datetime.datetime(2000,1,1)
        self.base_stamp = datetime.datetime(2000,1,1).timestamp()
        self.base_file = 'None'       
        self.label = 'None'
        
        self.uwave_freq = 0
        self.uwave_power = 0
        
        self.chassis_temp = self.parent.chassis_temp
        
    def update_event(self, new_sigs):  # new_sigs looks like ((p_tup1,d_tup1), (p_tup2,d_tup2)...)
        '''Method to update event with new signal chunk
        
        Args:
            new_sigs: tuple of number of sweeps in the chunk, new phase data list and new diode data list
        '''
        if 'NIDAQ' in self.config.settings['daq_type']:
            self.scan.change_set(new_sigs)
        else:
            self.scan.avg_chunks(new_sigs)

    def print_event(self, eventfile):
        '''Print out event to eventfile, formatting to dict to write to json line.
        
        Args:
            eventfile: File object to write event to
        '''
        
        exclude_list = [ 'freq_bytes', 'parent', 'anal_thread' ]
        json_dict = {}        
        json_dict.update(self.scan.__dict__)
        for key, entry in self.__dict__.items():               # filter event attributes for json dict
            if isinstance(entry, datetime.datetime):
                json_dict.update({key:entry.__str__()})  # datetime to string
            elif isinstance(entry, Baseline):
                json_dict.update({key:entry.stop_time.__str__()})   # baseline to stoptime string
            elif 'config' in key: 
                for key2, entry2 in entry.__dict__.items():
                    if key2 in exclude_list:
                        pass
                    elif 'controls' in key2:
                        for key3, entry3 in entry2.items():
                            json_dict.update({key3:entry3.value}) 
                    else: 
                        json_dict.update({key2:entry2})    
            elif 'scan' in key: 
                for key2, entry2 in entry.__dict__.items():
                    json_dict.update({key2:entry2})
            #elif 'status' in key: 
            #    json_dict.update({key:entry.chan})
            elif key in exclude_list: pass
            else:
                json_dict.update({key:entry})
        for key, entry in json_dict.items():   
            if isinstance(entry, np.ndarray):       
                json_dict[key] = entry.tolist()    
        json_record = json.dumps(json_dict)
        eventfile.write(json_record+'\n')               # write to file as json line
            
    def close_event(self, base_method, sub_method, res_method):
        '''Closes event, calls for signal analysis, adds epics reads to event
        
        Args:
            epics_reads: Return of read_all of EPICS class, Dict
            base_method: method to produce baseline subtracted signal given event instance, return baseline and subtracted
            sub_method: method to produce fit subtracted signal and area given event instance, return fit, subtracted, sum
        
        Todo:
            * Send data to EPICS, history
        '''
        #self.stop_time =  datetime.datetime.now(tz=pytz.timezone('US/Eastern'))
        self.stop_time =  datetime.datetime.now(tz=datetime.timezone.utc)
        self.stop_stamp = self.stop_time.timestamp()
        self.elapsed = (self.stop_time - self.start_time).seconds
        #print(self.stop_time, self.stop_stamp, self.elapsed)
             
        self.signal_analysis(base_method, sub_method, res_method)       
    
    def signal_analysis(self, base_method, sub_method, res_method):
        '''Perform analysis on signal
        '''

        if np.any(self.scan.phase):  # do the thing
            try:
                self.anal_thread = AnalThread(self, base_method, sub_method, res_method)
                self.anal_thread.finished.connect(self.parent.end_finished)
                self.anal_thread.start()
            except Exception as e: 
                print('Exception starting run thread: '+str(e))  
            # self.basesweep, self.basesub  = base_method(self)        
            # self.fitcurve, self.fitsub = sub_method(self)
            # self.rescurve, self.area, self.pol = res_method(self)            
        else:               # unless the phase signal is zeroes, then set all to zeroes
            self.basesweep = np.zeros(len(self.basesweep))
            self.basesub = np.zeros(len(self.basesweep))
            self.fitcurve = np.zeros(len(self.basesweep))
            self.fitsub = np.zeros(len(self.basesweep))
            self.rescurve = np.zeros(len(self.basesweep))
            self.pol, self.area = 0, 0
            
    def poly(self,p,x):
        '''Third order polynomial for fitting
        
        Args:
            p: List of polynomial coefficients
            x: Sample point
        '''
        return p[0] + p[1]*x + p[2]*np.power(x,2) + p[3]*np.power(x,3) #+ p[4]*np.power(x,4)
        
    def fit_wings(self, wings, sweep):
        '''Fit to wings with scipy
        
        Args:
            wings: Wings, 4 element list of portions of sweep to use, attribute from Config
            sweep: List of samples to fit
            
        Returns:
            pf: Tuple of final fit coefficient list
        
        '''
        bounds = [x*len(sweep) for x in wings]
        data = [(x,y) for x,y in enumerate(sweep) if (bounds[0]<x<bounds[1] or bounds[2]<x<bounds[3])]
        X = np.array([x for x,y in data])
        Y = np.array([y for x,y in data])
        
        errfunc = lambda p, x, y: self.poly(p,x) - y
        pi = [0.01, 0.8, 0.01, 0.001, 0.00001]  # initial guess
        pf, success = optimize.leastsq(errfunc, pi[:], args=(X,Y))  # perform fit
        return pf
        
    def set_uwave(self, freq, power):
        '''Set microwave power and frequency'''
        self.uwave_freq = freq
        self.uwave_power = power
        
class Baseline():
    '''Data object for baseline event.
    
    Args:
        dict: Dict of all event attributes to add as attributes to this object.
        '''

    def __init__(self, config, dict):
        self.config = config
        self.stop_stamp = 0
        self.stop_time = datetime.datetime(2000,1,1)
        self.base_file = ''
        self.phase = np.zeros(self.config.settings['steps'])
        self.__dict__.update(dict)	# update with attributes from passed event
        self.phase = np.array(self.phase)
        
  
 
class Status():
    '''Data object for external EPICS status variables, handles calls to get new values
    
    Arguments:
        chan_names: Dict of epics channels: names strings
    
    Attributes:
        chan_names: Dict of epics channels: names strings
        chan: Dict of channels: values

    Todo:
        Calls to EPICS to get values
    '''
    def __init__(self, chan_names):
        self.chan_names = chan_names
        self.chan = dict.fromkeys(self.chan_names.keys(),0)

   
class HistPoint():
    '''Single history point. History contains only critical info from event.
    
    Attributes:
        dt: Datetime object of time event stopped
        pol: Float measured polarization
        cc: Float calibration constant
        area: Float area under polyfit
    '''
    def __init__(self, event):
        self.dt = event.stop_time
        self.dt_stamp = event.stop_stamp
        self.pol = event.pol
        self.cc = event.cc
        self.area = event.area
        self.label = event.label
        self.epics_reads = event.status
        
        
class History():
    '''Contains polarization history since start, methods for returning subset of points'''
    def __init__(self):
        self.data = {}              # dict of HistPoints keyed on dt stamp
    def add_hist(self, hp):
        self.data[hp.dt_stamp] = hp
    def to_plot(self, start_stamp=0, stop_stamp=0):
        '''Gets datetimes and polarizations in history
        
        Returns:
            Dict keyed on timestamps of HistPoints          
        '''
        if start_stamp==0:
            return self.data
        else:
            hist_data = {k:v for k,v in self.data.items() if start_stamp<k<stop_stamp}
            return hist_data
      

class AnalThread(QThread):
    '''Thread class for analysis. Calls for epics reads and writes once done.
    Args:
        config: Config object of settings
    '''
    reply = pyqtSignal(tuple)       # reply signal
    finished = pyqtSignal()       # finished signal
    def __init__(self, parent,  base_method, sub_method, res_method):
        QThread.__init__(self)
        self.parent = parent    # event object
        self.base_method = base_method
        self.sub_method = sub_method
        self.res_method = res_method
        
                
    def __del__(self):
        self.wait()
        
    def run(self):
        '''Main analysis loop. 
        '''
        self.parent.basesweep, self.parent.basesub  = self.base_method(self.parent)        
        self.parent.fitcurve, self.parent.fitsub = self.sub_method(self.parent)
        self.parent.rescurve, self.parent.area, self.parent.pol = self.res_method(self.parent) 
        #print("Analysis done, waiting on epics.")
        
        self.parent.parent.epics_update(self.parent)
                
        self.finished.emit()
  
   
