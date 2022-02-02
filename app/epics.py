'''PyNMR, J.Maxwell 2020
'''
import epics
import time


class EPICS():
    '''Class to hold all EPICS channels to monitor and write, and methods on them. Includes test mode. Includes monitor thread to get values in intervals.
    
    Arguments:
        enable:  Won't contact server if false
        monitor_time: How long to wait between calls to get
        read_names: Dict of channel names string to read keyed on epics channel ie 'HBPT:targ_pol'
        write_atts: Dict of Event attributes to write keyed on epics channel
        
    Attributes:
        read_PVs:  Dict of most recently read variable values keyed on PV name
    
    '''
    def __init__(self, enable, monitor_time, read_names, write_atts):       
        
        self.read_names = read_names             # Dict of PV names and namestring
        self.read_list = self.read_names.keys()   # List of PV names to read from server
        self.write_atts = write_atts
        self.enable = enable
        self.monitor_time = monitor_time
                
        self.read_PVs   = {k:0 for k in self.read_list}    # initialize with 0s        
        
        if not self.enable: 
            print('EPICS in test mode.')
            self.read_PVs   = {k:0 for k in self.read_list)}     
            self.monitor_running = False
        else:               
            self.monitor_running = True            
            self.mon_thread = MonitorThread(self)
            self.mon_thread.reply.connect(self.mon_reply)
            self.mon_thread.finished.connect(self.mon_finished)
            self.mon_thread.start()
    
    def mon_reply(self):
        '''Update run tab after monitor update'''
        self.parent.run_tab.update_status()
        
    def mon_finished(self):
        '''Things to do when done'''
       return
            
    def read_all(self):
        '''Read new values from EPICS PVs. Use caget_many to do quickly
        
        Returns:
            Dict of values keyed on channel name
        '''
        if not self.enable:
            return {k:0 for k in self.read_list} 
        else:
            try:
                values = epics.caget_many(self.read_list)
                self.read_PVs = zip(self.read_list, values)
            except Exception as e: 
                print("Error getting EPICS variables.")
            #return {k:self.read_PVs[k].value for k in self.read_list}
        
    def write_all(self, event):
        '''Write all new values from event to EPICS PVs
        
        Arguments:
            event: Event class instance with values to write
        '''
    
        if not self.enable:
            return 
        else:
            return
  
  
class MonitorThread(QThread):
    '''Thread class for monitor loop. Gets values from EPICS, then waits before doing it again.
    Args:
        config: Config object of settings
    '''
    reply = pyqtSignal(tuple)       # reply signal
    finished = pyqtSignal()       # finished signal
    def __init__(self, parent):
        QThread.__init__(self)
        self.parent = parent  
                
    def __del__(self):
        self.wait()
        
    def run(self):
        '''Main monitor loop
        '''        
        
        while self.parent.monitor_running:
            self.parent.read_all()   
            self.reply.emit(True)
            time.sleep(self.parent.monitor_time)
          
        self.finished.emit()


  