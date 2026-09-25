'''PyNMR, J.Maxwell 2021
'''
import time
import epics
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
        self.monitor_time = config.settings['uWave_settings']['monitor_time']
        self.freq_pv = config.settings['uWave_settings']['counter_pv']
        self.power_pv = config.settings['uWave_settings']['power_meter_pv']

    def setup(self):
        '''Verify EPICS PV names are configured'''
        self._logger.info(f"Microwave monitoring via EPICS: freq={self.freq_pv}, power={self.power_pv}")
            
    def execute(self):
        '''Main microwave read loop'''
        while self.tab_parent.enable_button.isChecked() and not self.should_stop():
            freq = epics.caget(self.freq_pv)
            if freq is None:
                self._logger.warning(f"Counter PV read returned None: {self.freq_pv}")
                freq = "Read Error"
            else:
                self._logger.debug(f"Frequency reading: {freq}")

            power = epics.caget(self.power_pv)
            if power is None:
                self._logger.warning(f"Power meter PV read returned None: {self.power_pv}")
                power = "Read Error"
            else:
                self._logger.debug(f"Power reading: {power}")
                
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
        self._logger.info("Microwave monitor stopped")


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
        freq_pv = self.config.settings['uWave_settings']['counter_pv']
        power_pv = self.config.settings['uWave_settings']['power_meter_pv']
        monitor_time = self.config.settings['uWave_settings']['monitor_time']

        while self.parent.enable_button.isChecked():
            freq = epics.caget(freq_pv)
            if freq is None:
                freq = "Read Error"

            power = epics.caget(power_pv)
            if power is None:
                power = "Read Error"

            pot, temp = 0, 0

            try:
                self.reply.emit((freq, pot, temp, power))
            except Exception as e:
                print("Couldn't send microwave reply: "+str(e))
            time.sleep(monitor_time)

        self.finished.emit()




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
            
    
