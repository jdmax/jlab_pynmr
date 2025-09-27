'''PyNMR, J.Maxwell 2021
'''
import telnetlib, time
from labjack import ljm
import requests
from PySide6.QtCore import QThread, Signal, Qt
from core.thread_manager import BaseThread

  
class MicrowaveThread(BaseThread):
    '''Thread class for microwave loop
    Args:
        parent: Parent widget 
        config: Config object of settings
    '''
    def __init__(self, parent, config):
        super().__init__(name=f"microwave_{id(parent)}", parent=parent, config=config)
        self.tab_parent = parent
        self.count = None
        self.pow_meter = None
        self.monitor_time = config.settings['uWave_settings']['monitor_time']
        
    def setup(self):
        '''Initialize counter and power meter connections'''
        try:
            self.count = Counter(self.config)
            self.pow_meter = PowMeter(self.config)
            time.sleep(self.monitor_time)  # Initial settle time
            self._logger.info("Microwave instruments initialized")
        except Exception as e:
            error_msg = f'Exception starting microwave instruments: {e}'
            self._logger.error(error_msg)
            raise Exception(error_msg)
            
    def execute(self):
        '''Main microwave read loop'''
        if not self.count or not self.pow_meter:
            self._logger.error("Microwave instruments not initialized")
            return
            
        while self.tab_parent.enable_button.isChecked() and not self.should_stop():       
            freq = 0
            try:        
                freq = self.count.read_freq()
                self._logger.debug(f"Frequency reading: {freq}")
            except Exception as e:
                self._logger.warning(f"Counter read failed: {e}")
                freq = "Read Error"
                
            power = 0
            try:        
                power = self.pow_meter.read_power()
                self._logger.debug(f"Power reading: {power}")
            except Exception as e:
                self._logger.warning(f"Power meter read failed: {e}")
                power = "Read Error"
                
            pot, temp = 0, 0
            # Disabling Readback of uwave pot and temp for now 5/26/22     
            # Original code was commented out for LabJack readback
                
            try:
                self.emit_reply((freq, pot, temp, power))
            except Exception as e:                
                self._logger.error(f"Couldn't send microwave reply: {e}")
                
            # Sleep with interruption checking
            sleep_intervals = int(self.monitor_time * 10)  # Check stop every 0.1s
            for _ in range(sleep_intervals):
                if self.should_stop() or not self.tab_parent.enable_button.isChecked():
                    return
                time.sleep(0.1)
          
    def cleanup(self):
        '''Clean up instrument connections'''
        if self.count:
            try:
                del self.count
                self.count = None
            except Exception as e:
                self._logger.warning(f"Error cleaning up counter: {e}")
                
        if self.pow_meter:
            try:
                del self.pow_meter
                self.pow_meter = None
            except Exception as e:
                self._logger.warning(f"Error cleaning up power meter: {e}")
        
        self._logger.info("Microwave instruments cleaned up")


# Legacy compatibility wrapper
class LegacyMicrowaveThread(QThread):
    '''Legacy compatibility wrapper for old MicrowaveThread interface.'''
    reply = Signal(tuple)       # reply signal
    finished = Signal()       # finished signal
    
    def __init__(self, parent, config):
        QThread.__init__(self)
        self.config = config
        self.parent = parent 
                
    def __del__(self):
        if self.isRunning():
            self.quit()
        
    def run(self):
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
                
            try:        
                power = self.pow_meter.read_power()
            except Exception as e:
                print(f"Power meter read failed: {e}")  
                power = "Read Error"
                
            pot, temp = 0, 0
                
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
        self.ip = config.settings['uWave_settings']['relay-ip']
        self.timeout = config.settings['uWave_settings']['relay-timeout']
        self.port = '30000'
        self.all_off = '44'   # command urls for each relay
        self.one_on = '01'
        self.two_on = '03'
        self.three_on = '05'
        self.four_on = '07'
        
        try:
            r = requests.get(f'http://{self.ip}/{self.port}/{self.all_off}', timeout=self.timeout)        
        except Exception as e:
            print(f"Connection to EIO tune relays failed on {self.ip}: {e}")
            
    def change_freq(self, direction, duration):
        '''Write to relay to change microwave frequency up or down for a certain duration
        '''         
               
        try: 
            r = requests.get(f'http://{self.ip}/{self.port}/{self.all_off}', timeout=self.timeout)          # it's not 00, whatever all open is
        except Exception as e:
            print(f"Connection to EIO tune relays failed on {self.ip}: {e}")
        time.sleep(0.128)
            
        if "up" in direction:
            commands = [self.two_on,self.four_on]
        elif "down" in direction:
            commands = [self.one_on,self.three_on,self.two_on,self.four_on]
        else:    
            commands = [self.all_off]
            
        for c in commands: 
            time.sleep(0.05)           
            try:
                r = requests.get(f'http://{self.ip}/{self.port}/{c}', timeout=self.timeout)    
                print('microwaves',direction, duration)
            except requests.exceptions.Timeout:
                print('Relay timeout has been raised.')  
                try: 
                    r = requests.get(f'http://{self.ip}/{self.port}/{self.all_off}', timeout=self.timeout)          # it's not 00, whatever all open is
                except Exception as e:
                    print(f"Connection to EIO tune relays failed on {self.ip}: {e}")  
            except Exception as e:
                print(f"Connection to EIO tune relays failed on {self.ip}: {e}")       
               
       
        time.sleep(duration)  
        try:
            r = requests.get(f'http://{self.ip}/{self.port}/{self.all_off}', timeout=self.timeout) 
        except requests.exceptions.Timeout:
            print('Relay timeout has been raised.')  
            try: 
                r = requests.get(f'http://{self.ip}/{self.port}/{self.all_off}', timeout=self.timeout)          # it's not 00, whatever all open is
            except Exception as e:
                print(f"Connection to EIO tune relays failed on {self.ip}: {e}")  
        except Exception as e:
            print(f"Connection to EIO tune relays failed on {self.ip}: {e}") 
           
           
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
            
    
