'''PyNMR, J.Maxwell 2020
'''
from epics import PV


class EPICS():
    '''Class to hold all EPICS channels to monitor and write, and methods on them. Includes test mode which is used if test_chan get returns None. All channels are using Process Variables, which allow direct access without using a caget or caput. For example:
    
        p1 = PV('chan')
        print(p1.value)        # this is a get
        p1.value = 2.0         # this is a put
    
    Arguments:
        test_chan:  Won't contact server if test_mode is true
        read_names: Dict of channel names string to read keyed on epics channel ie 'HBPT:targ_pol'
        write_atts: Dict of Event attributes to write keyed on epics channel
    
    '''
    def __init__(self, enable, read_names, write_atts):       
        
        self.read_names = read_names
        self.write_atts = write_atts
        self.enable = enable
        
        if not self.enable: 
            print('EPICS in test mode.')
            self.read_PVs   = {k:0 for k in self.read_names.keys()}   
            self.write_PVs  = {k:0 for k in self.write_atts.keys()}    
        else:          
            self.read_PVs   = {k:PV(k) for k in self.read_names.keys()}    # dict of PV objects keyed on channel names
            self.write_PVs  = {k:PV(k) for k in self.write_atts.keys()}    # dict of PV objects keyed on channel names
            
    def read_all(self):
        '''Read new values from EPICS PVs
        
        Returns:
            Dict of values keyed on channel name
        '''
        if not self.enable:
            return {k:0 for k in self.read_names.keys()} 
        else:
            return {k:self.read_PVs[k].value for k in self.read_names.keys()}
        
    def write_all(self, event):
        '''Write all new values to EPICS PVs
        
        Arguments:
            event: Event class instance with values to write
        '''
    
        if not self.enable:
            return 
        else:
            for k, v in self.write_atts.items():
                self.write_PVs[k].value = event.__dict__[v] 
  

  
class MonitorThread(QThread):
    '''Thread class for microwave loop
    Args:
        config: Config object of settings
    '''
    reply = pyqtSignal(tuple)       # reply signal
    finished = pyqtSignal()       # finished signal
    def __init__(self, parent, config):
        QThread.__init__(self)
        self.config = config
        self.parent = parent 
            
                
    def __del__(self):
        self.wait()
        
    def run(self):
        '''Main monitor loop
        '''        
        
        while:
            self.reply.emit((freq, pot, temp))
            time.sleep(self.config.settings['uWave_settings']['monitor_time'])
          
        self.finished.emit()
        del self.count


  