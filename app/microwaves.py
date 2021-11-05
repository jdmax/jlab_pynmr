'''PyNMR, J.Maxwell 2021
'''
import telnetlib, time
from PyQt5.QtCore import QThread, pyqtSignal, Qt

  
class MicrowaveThread(QThread):
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
        '''Main microwave control loop
        '''        
        try:
            self.count = Counter(self.config)
            time.sleep(self.config.settings['uWave_settings']['monitor_time'])
        except Exception as e:
            print('Exception starting counter thread, lost connection: '+str(e))
            
        while self.parent.enable_button.isChecked():       
            try:        
                freq = self.count.read_freq()
                self.reply.emit((freq,))
            except Exception as e:
                print(f"GPIB connection failed: {e}")  
                self.parent.enable_button.toggle()
                self.parent.enable_pushed()
                break
            
            time.sleep(self.config.settings['uWave_settings']['monitor_time'])
          
        self.finished.emit()
        del self.count



class Counter():
    '''Class to interface with Prologix GPIB controller to control frequency counter
        
    Arguments:
        config: Current Config object 
    '''
    
    
    def __init__(self, config):    
        '''Open connection to GPIB, send commands for all settings. Close.  
        '''
        self.host = config.settings['uWave_settings']['ip']
        self.port = 1234   
        timeout: 2              # Telnet timeout in secs

 
        try:
            self.tn = telnetlib.Telnet(self.host, port=self.port, timeout=config.settings['uWave_settings']['timeout'])
            
            # Write all required settings
            self.tn.write(bytes(f"FE 1\n", 'ascii'))  # Fetch setup 1
            
            # self.tn.write(bytes(f"++addr {config.settings['uWave_settings']['counter_addr']}\n", 'ascii'))
            # self.tn.write(bytes(f"BA {config.settings['uWave_settings']['band']}\n", 'ascii'))
            # self.tn.write(bytes(f"SU {config.settings['uWave_settings']['subband']}\n", 'ascii'))
            # self.tn.write(bytes(f"CE {config.settings['uWave_settings']['cent_freq']} GHz\n", 'ascii'))
            # self.tn.write(bytes(f"SA {config.settings['uWave_settings']['rate']} ms\n", 'ascii'))
            
            
            self.tn.write(bytes(f"OU DE\n", 'ascii'))  # Read displayed data
            freq = self.tn.read_some().decode('ascii')        
                     
            print(f"Successfully sent settings to GPIB on {self.host}")
            
        except Exception as e:
            print(f"GPIB connection failed on {self.host}: {e}")
    
    def read_freq(self):
        '''Read frequency from open connection'''        
        try:
            self.tn.write(bytes(f"OU DE\n", 'ascii'))  # Read displayed data
            freq = self.tn.read_some().decode('ascii')  
            return freq  
        except Exception as e:
            print(f"GPIB connection failed on {self.host}: {e}")  
        
    def close(self):           
        try:
            tn.close()
        except Exception as e:
            print(f"GPIB connection failed on {self.host}: {e}")