'''PyNMR, J.Maxwell 2021
'''
import telnetlib, time
from labjack import ljm
import requests
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
        '''Main microwave read loop
        '''        
        try:
            self.count = Counter(self.config)
            self.pow_meter = PowMeter(self.config)
            time.sleep(self.config.settings['uWave_settings']['monitor_time'])
        except Exception as e:
            print('Exception starting counter thread, lost connection: '+str(e))
      
        while self.parent.enable_button.isChecked():       
            try:        
                freq = self.count.read_freq()
            except Exception as e:
                print(f"Counter read failed: {e}")  
                freq = "Read Error"
                #self.parent.enable_button.toggle()
                #self.parent.enable_pushed()
                #break
                
            try:        
                power = self.pow_meter.read_power()
            except Exception as e:
                print(f"Power meter read failed: {e}")  
                power = "Read Error"
                #self.parent.enable_button.toggle()
                #self.parent.enable_pushed()
                #break
                
            pot, temp = 0, 0
            # Disabling Readback of uwave pot and temp for now 5/26/22     
            #try: 
            #    pot, temp = self.parent.utune.read_back()
            #except Exception as e:                
            #    print('Exception reading LabJack: '+str(e))
                
            try:
                self.reply.emit((freq, pot, temp, power))
            except Exception as e:                
                print("Couldn't send microwave reply: "+str(e))
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
        self.host = config.settings['uWave_settings']['counter']['ip']
        self.port = config.settings['uWave_settings']['counter']['port']   
        self.timeout = config.settings['uWave_settings']['counter']['timeout']              # Telnet timeout in secs

 
        try:
            self.tn = telnetlib.Telnet(self.host, port=self.port, timeout=self.timeout)
            
            # Write all required settings
            #self.tn.write(bytes(f"FE 1\n", 'ascii'))  # Fetch setup 1
            
            self.tn.write(bytes(f"++addr {config.settings['uWave_settings']['counter']['addr']}\n", 'ascii'))
            self.tn.write(bytes(f"BA {config.settings['uWave_settings']['counter']['band']}\n", 'ascii'))
            self.tn.write(bytes(f"SU {config.settings['uWave_settings']['counter']['subband']}\n", 'ascii'))
            self.tn.write(bytes(f"CE {config.settings['uWave_settings']['counter']['cent_freq']} GHz\n", 'ascii'))
            self.tn.write(bytes(f"SA {config.settings['uWave_settings']['counter']['rate']} ms\n", 'ascii'))
            
            
            #self.tn.write(bytes(f"OU DE\n", 'ascii'))  # Read displayed data
            #freq = self.tn.read_some().decode('ascii')        
                     
            print(f"Successfully sent settings to counter on {self.host}")
            
        except Exception as e:
            print(f"GPIB connection failed on {self.host}: {e}")
    
    def read_freq(self):
        '''Read frequency from open connection'''        
        #try:
        self.tn.write(bytes(f"OU DE\n", 'ascii'))  # Read displayed data
        freq = self.tn.read_until(b'\r', timeout=self.timeout).decode('ascii')  
        #print(int(freq.strip()))
        try:
            ret = int(freq.strip())
        except ValueError:
            ret = 'Read Error'
        return ret  
        #except exception as e:
        #   print(f"GPIB connection failed on {self.host}: {e}")  
        
    def close(self):           
        try:
            tn.close()
        except Exception as e:
            print(f"GPIB connection failed on {self.host}: {e}")

 
class PowMeter():
    '''Class to interface with serial to ethernet adapter, accessing ELVA-1 power meter
        
    Arguments:
        config: Current Config object 
    '''    
    
    def __init__(self, config):    
        '''Open connection to GPIB, send commands for all settings. Close.  
        '''
        self.host = config.settings['uWave_settings']['power_meter']['ip']
        self.port = config.settings['uWave_settings']['power_meter']['port']   
        self.timeout = config.settings['uWave_settings']['power_meter']['timeout']              # Telnet
        self.freq = config.settings['uWave_settings']['power_meter']['freq']  # center freq setting, GHz

 
        try:
            self.tn = telnetlib.Telnet(self.host, port=self.port, timeout=self.timeout)
            
            # Write all required settings
            self.tn.write(bytes(f"sens:freq {self.freq}\n", 'ascii'))  # Write freq   
            self.tn.write(bytes(f"unit:pow w\n", 'ascii'))  # Write unit      
                     
            #print(f"Successfully sent settings to GPIB on {self.host}")
            
        except Exception as e:
            print(f"Connection to serial port failed on {self.host}: {e}")
    
    def read_power(self):
        '''Read power from open connection'''          
        try:
            self.tn.write(bytes(f"read?\n", 'ascii'))  # Read power
            power = self.tn.read_some().decode('ascii')              
        except Exception as e:
            print(f"Connection to serial port failed on {self.host}: {e}")
              
        if 'U' in power:     # turn into float of mW 
            p = power.strip().split()
            power = float(p[0])/1000.0
        elif 'error' in power:
            power = -1                
        else:
            p = power.strip().split()
            power = float(p[0])   
        return power
        
    def close(self):           
        try:
            tn.close()
        except Exception as e:
            print(f"Network to serial connection failed on {self.host}: {e}")


class NetRelay():
    '''Access Ethernet Relay device to control EIO tune motor'''
    
    def __init__(self, config):
        '''Open connection to relays
        '''  
        ip = config.settings['uWave_settings']['relay-ip']
        port = '30000'
        try:
            r = requests.get(f'{ip}/{port}')        
        except Exception as e:
            print(f"Connection to EIO tune relays failed on {ip}: {e}")
            
    def change_freq(self, direction):
        '''Write to relay to change microwave frequency up or down 
        '''
               
               
        try: 
            r = requests.get(f'{ip}/{port}/00')          # it's not 00, whatever all open is
        except Exception as e:
            print(f"Connection to EIO tune relays failed on {ip}: {e}")
        time.sleep(0.128)
            
        if "up" in direction:
            commands = ['01','03']
        elif "down" in direction:
            commands = ['05','07']
        else:    
            commands = ['00']
            
        for c in commands:            
            try:
                r = requests.get(f'{ip}/{port}/c')        
            except Exception as e:
                print(f"Connection to EIO tune relays failed on {ip}: {e}")
           
           
           
class LabJack():      
    '''Access LabJack device to change microwave frequency, readback temp, pot      
    '''
    
    def __init__(self, config):
        '''Open connection to LabJack
        '''  
        ip = config.settings['uWave_settings']['lj-ip']
        try:
            self.lj = ljm.openS("T4", "TCP", ip) 
        except Exception as e:
            print(f"Connection to LabJack failed on {ip}: {e}")
        
    def change_freq(self, direction):
        '''Write to LabJack to change microwave frequency up or down 
        '''
        #print("changing to", direction)
        aNames = ["DAC0","DAC1"]
               
        aValues = [0, 0]
        ljm.eWriteNames(self.lj, len(aNames), aNames, aValues)
        time.sleep(0.128)
            
        if "up" in direction:
            aValues = [5, 0]
        elif "down" in direction:
            aValues = [0, 5]
        else:    
            aValues = [0, 0]
        
        ljm.eWriteNames(self.lj, len(aNames), aNames, aValues)
        
    
    def read_back(self):
        '''Read temperature and potentiometer position from LabJack. Returns array of ADC values.
        '''
        aNames = ["AIN4","AIN5"]
        return ljm.eReadNames(self.lj, len(aNames), aNames)
        
    # def __del__(self):
        # '''Close on delete'''
        # ljm.close(self.lj) 
            
    
