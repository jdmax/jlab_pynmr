import socket
import time
import numpy as np


class DAQConnection():
    '''Handle connection to and communication with DAQ system. Designed to hide all the specifics of different DAQ systems with generic actions for all. Init will open connections and send configuration settings to DAQ.
    
    Args:
        config: Config object with settings
        timeout: Timeout for DAQ system
        tune_mode: Use tune mode, with only one chuck
    '''
    
    def __init__(self, config, timeout, tune_mode):
        
        self.daq_type = config.settings['daq_type']
        self.tune_mode = tune_mode
        self.config = config
        if self.daq_type=='FPGA':
            
            try:
                self.udp = UDP(self.config)
                self.tcp = TCP(self.config, timeout)
                
            except socket.error as e:
                print("Error creating socket:",e)
            except socket.gaierror as e:
                print("Address related error connecting:",e)
                
            self.name = str(self.udp.ip)
            self.message = 'Connected to: '+str(self.udp.ip)+', port '+str(self.udp.port)+', and set registers and frequency table.'
        elif self.daq_type=='Test':          
            v, self.test_phase, self.test_diode = np.loadtxt("app/test_data.txt", unpack=True)               
            self.message = 'DAQ Test mode.'
            self.name = 'Test'


    def __del__(self):
        '''Stop Connections'''
        if self.daq_type=='FPGA':
            del self.udp
            del self.tcp

    def start_sweeps(self):
        '''Send command to sending NMR sweeps'''
        if self.daq_type=='FPGA':
            self.udp.act_sweep()

    def get_chunk(self):
        '''Receive subset of total sweeps for the event'''
        
        if self.daq_type=='FPGA':
            return self.tcp.get_chunk()   
            
        elif self.daq_type=='Test':
            if self.tune_mode:
                num_in_chunk = self.config.settings['tune_per_chunk']
            else:
                num_in_chunk = self.config.controls['chunk'].value
            time.sleep(0.0005*num_in_chunk)
            
            p_test = self.test_phase + np.random.rand(len(self.test_phase))*0.00005*num_in_chunk   # numpy arrays
            d_test = self.test_diode + np.random.rand(len(self.test_diode))*0.00005*num_in_chunk 
            # for curves in self.test_sigs:
                # p_test = [i+random.random()*0.00005*num_in_chunk for i in curves[0]]
                # d_test = [i+random.random()*0.00005*num_in_chunk for i in curves[1]]
            return (num_in_chunk, p_test, d_test)
      
class UDP():
    '''Handle UDP commands and responses
    
    Args:
        config: Config object with settings
    '''
    def __init__(self,config):
        '''Start connection, send nmr_settings dict'''
        self.ok = bytes.fromhex('0300FA')
        self.s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, 0)
        self.s.settimeout(1)
        self.config = config
        self.ip = config.settings['fpga_settings']['ip']
        self.port = config.settings['fpga_settings']['port']
        self.s.connect((self.ip, self.port))
        if not self.set_register(): print("Set register error")
        #print(self.read_stat())
        if not self.set_freq(config.freq_bytes): print("Set frequency error")
        self.read_freq()
        
        
    def __del__(self):
        '''Stop connection'''
        self.s.close()
    
    def read_stat(self):
        '''Read status command
        Returns:
            Data sent back as hex
        '''
        self.s.send(bytes.fromhex('0F0001000000000000000000000000'))
        data, addr = self.s.recvfrom(1024)
        #print("Read Stat Message: ", data.hex())
        return data.hex()
        
    def read_freq(self):
        '''Read freqeuncy command
        Returns:
            Data sent back as hex
        '''
        self.s.send(bytes.fromhex('0F0003000000000000000000000000'))
        data, addr = self.s.recvfrom(1028)   # buffer size is 1027 to get all of the points
        #print("Read Freq Message: ", data.hex())
        return data.hex()
        
    def set_register(self):
        '''Send set register command and string
        Returns:
            Boolean denoting success
            '''
            
        # Make ADC Config int from list of bools
        test_mode = True
        phase_drate1 = False
        phase_drate0 = False
        phase_fpath = True
        diode_drate1 = True
        diode_drate0 = False
        diode_fpath = False
        states = [test_mode, False, False, False, False, False, False, False, False, False, phase_drate1, phase_drate0, phase_fpath, diode_drate1, diode_drate0, diode_fpath]
        adcbits = ''.join([str(int(i)) for i in states])
        ADCConfig = int(adcbits,2)
            
        # Make Resiter byte string from other inputs
        # Number Bytes LSB, Nymber Bytes MSB, LSByte GenSetTime, MSByte GenSetTime, LSByte NumOfSamToAve, MByte NumOfSamToAve, LSByte TotSweepCycle, MSByte TotSweepCycle, LSByte IntSweepCycle, MSByte IntSweepCycle, LSByte AdcConfig, MSByte AdcConfig
        RegSets = [bytes.fromhex('0F00'),bytes.fromhex('02')]
        RegSets.append(self.config.settings['fpga_settings']['dwell'].to_bytes(2,'little'))
        RegSets.append(self.config.settings['fpga_settings']['per_point'].to_bytes(2,'little'))
        if self.tune_mode:
            RegSets.append(self.config.settings['tune_per_chunk'].to_bytes(2,'little'))
            RegSets.append(self.config.settings['tune_per_chunk'].to_bytes(2,'little'))
        else:
            RegSets.append(self.config.controls['sweeps'].value.to_bytes(2,'little'))
            RegSets.append(self.config.controls['chunk'].value.to_bytes(2,'little'))
        RegSets.append(ADCConfig.to_bytes(2,'little'))
        RegSets.append(bytes.fromhex('FF00'))
        RegSetString = b''.join(RegSets)
        
        self.s.send(RegSetString)
        data, addr = self.s.recvfrom(1024)    # buffer size is 1024
        if data == self.ok:
            return True
        else:
            return False
    
    def set_freq(self, freq_bytes):
        '''Send frequency points, converts freq list into bytes
        Args:
            freq_bytes: List of bytes for R&S frequency modulation
            
        Returns:
            Boolean denoting success
        '''
      
        NumBytes_byte = (self.config.settings['steps']*2+3).to_bytes(2,'little')
        freqs = NumBytes_byte + bytes.fromhex('04') + b''.join(freq_bytes)
        if self.config.settings['fpga_settings']['test_freqs']:
            NumBytes_byte = (self.config.settings['steps']*2+3).to_bytes(2,'little')
            FreqList = range(1,self.config.settings['steps']+1)
            FreqBytes = [b.to_bytes(2,'little') for b in FreqList]
            TestTable = NumBytes_byte + bytes.fromhex('04') + b''.join(FreqBytes)
            self.s.send(TestTable)
        else:
            self.s.send(freqs)
        data, addr = self.s.recvfrom(1024)    # buffer size is 1024
        #print("Set Freq Message: ", data.hex())
        if data == self.ok:
            return True
        else:
            return False
        
    def act_sweep(self):
        '''Send activate sweep command
        Returns:
            Boolean denoting success
        '''
        self.s.send(bytes.fromhex('0F0005000000000000000000000000'))
        data, addr = self.s.recvfrom(1024)    # buffer size is 1024
        if data == self.ok:
            return True
        else:
            return False

    def int_sweep(self):
        '''Send interrupt sweep command
        Returns:
            Boolean denoting success
        '''
        self.s.send(bytes.fromhex('0F0006000000000000000000000000'))
        data, addr = self.s.recvfrom(1024)    # buffer size is 1024
        if data == self.ok:
            return True
        else:
            return False
    
class TCP():
    '''Handle TCP commands and responses
    
    Args:
        config: Config object with settings
        timeout: Int for TCP timeout time (secs)
    
    '''
    def __init__(self,config,timeout):
        '''Start connection'''
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM,0)
        self.s.settimeout(timeout)
        self.ip = config.settings['fpga_settings']['ip']
        self.port = config.settings['fpga_settings']['port']
        self.buffer_size = config.settings['fpga_settings']['tcp_buffer']
        self.s.connect((self.ip, self.port))
        
    def __del__(self):
        '''Stop connection'''
        self.s.close()
        
    def get_chunk(self):
        '''Receive chunks over tcp
        
        Returns:
            Number of sweeps in chunk, phase chunk and diode chunk numpy arrays
        '''
        num_in_chunk = 0              #  Number of sweeps in the chunk
        chunk = {}
        chunk['phase'] = bytearray()
        chunk['diode'] = bytearray()
        sweep_type = ''    # phase or diode, starts as ''
        
        while not (len(chunk['phase'])==512*5 and len(chunk['diode'])==512*5):       # loop for chunk packets
            response = self.s.recv(self.buffer_size)
            if (sweep_type == ''):   # first packet has 3 init bytes: 2 for chucks sw cyc, 1 for aa, bb
                num_in_chunk = int.from_bytes(response[:2],'little')
                response = response[3:]
                sweep_type = 'phase'
                       
            res_list = [response[i:i+1] for i in range(len(response))]
            for b in res_list:
                if sweep_type == '':
                    #print("no type: ",b)
                    if b == b'\xbb':
                        sweep_type = 'diode'
                    continue
                #if sweep_type == 'diode': print(b.hex())
                chunk[sweep_type] += bytearray(b)
                if (len(chunk[sweep_type]) == 512*5):             # filled up chunk
                    sweep_type = ''                   # unset type
                    
        pchunk_byte_list = [chunk['phase'][i:i + 5] for i in range(0, len(chunk['phase']), 5)]
        dchunk_byte_list = [chunk['diode'][i:i + 5] for i in range(0, len(chunk['diode']), 5)]
        pchunk = np.fromiter(((int.from_bytes(i,'little'))/(num_in_chunk*2) for i in pchunk_byte_list), np.int64)   # numpy array
        dchunk = np.fromiter(((int.from_bytes(i,'little'))/(num_in_chunk*2) for i in dchunk_byte_list), np.int64)
                        
        return (num_in_chunk, pchunk, dchunk)
        
 