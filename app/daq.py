'''PyNMR, J.Maxwell 2020
'''
import socket
import time
import json
import telnetlib
import unyt
import numpy as np
import nidaqmx
from nidaqmx.constants import (DigitalWidthUnits, AcquisitionType,
                               ReadRelativeTo, OverwriteMode, DigitalWidthUnits,
                               TriggerType, TaskMode, READ_ALL_AVAILABLE)
                               
class DAQConnection():
    '''Handle connection to and communication with DAQ system. Designed to hide all the specifics of different DAQ systems with generic actions for all. Init will open connections and send configuration settings to DAQ.
    
    Args:
        config: Config object with settings
        timeout: Timeout for DAQ system
        tune_mode: Use tune mode, with only one chuck
    '''
    
    def __init__(self, config, timeout, tune_mode=False):
        
        self.daq_type = config.settings['daq_type']
        self.tune_mode = tune_mode
        self.config = config
        
        if self.daq_type=='FPGA':
            
            try:
                self.udp = UDP(self.config, tune_mode)
                self.tcp = TCP(self.config, timeout)
                
            except Exception as e:
                raise
                
                
            self.name = str(self.udp.ip)
            self.message = 'Connected to: '+str(self.udp.ip)+', port '+str(self.udp.port)+', and set registers and frequency table.'
            
        elif self.daq_type=='NIDAQ':          
            try:
                self.ni = NI_Connection(self.config)
                self.message = 'Connected to NI-DAQ.'
                self.name = self.config.settings['nidaq_settings']['phase_chan']
            except Exception as e:
                self.message = 'NI-DAQ Connection failed.'
                self.name = 'Connection failed.'
                print(e)
            
            
        elif self.daq_type=='Test':          
            #v, self.test_phase, self.test_diode = np.loadtxt("app/test_data.txt", unpack=True) 
            with open(self.config.settings['test_signal'], 'r') as file:
                for line in file:
                    event = json.loads(line)
                    self.test_phase = np.array(event['phase'])
                    self.test_diode = np.array(event['diode'])
                    self.test_freqs = np.array(event['freq_list'])
            self.message = 'DAQ Test mode.'
            self.name = 'Test'
            
        else:
            print('Incorrect daq_type setting')


    def __del__(self):
        '''Stop Connections'''
        if self.daq_type=='FPGA':
            try:
                del self.udp
                del self.tcp
            except AttributeError:
                pass
            except Exception as e:
                raise

    def start_sweeps(self):
        '''Send command to sending NMR sweeps'''
        if self.daq_type=='FPGA':
            self.udp.act_sweep()
            
        if self.daq_type=='NIDAQ':   
            self.ni.start()
            
            
    def abort(self):
        '''Send command to abort NMR sweeps'''
            
        if self.daq_type=='FPGA':
            try:
                self.udp.int_sweep()
            except Exception as e:
                raise
            
    def stop(self):
        '''Send command to stop sending NMR sweeps'''
        
        if self.daq_type=='NIDAQ':   
            self.ni.stop()

    def get_chunk(self):
        '''Receive subset of total sweeps for the event'''
        
        if self.daq_type=='FPGA':
            return self.tcp.get_chunk()   
            
        elif self.daq_type=='NIDAQ':          
            return self.ni.get_chunk()            
            
        elif self.daq_type=='Test':
            if self.tune_mode:
                num_in_chunk = self.config.settings['tune_per_chunk']
            else:
                num_in_chunk = self.config.settings['num_per_chunk']
            time.sleep(0.005*num_in_chunk)
            
            p_test = self.test_phase + np.random.rand(len(self.test_phase))*0.00001*num_in_chunk   # numpy arrays
            d_test = -self.test_diode + np.random.rand(len(self.test_diode))*0.00001*num_in_chunk 
            return (0, num_in_chunk, p_test, d_test)
      
    def set_dac(self, dac_v, dac_c):
        '''Set DAC value for tuning diode or phase
        '''
        if self.daq_type=='FPGA':
            self.udp.dac_v = dac_v 
            self.udp.dac_c = dac_c    
            return self.udp.set_register()        
        if self.daq_type=='Test':
            #print("DAC", dac_v, dac_c)
            return True
      
    def read_stat(self):
        '''Read back DAQ status
        '''
        if self.daq_type=='FPGA':
            return self.udp.read_stat()            
             
class UDP():
    '''Handle UDP commands and responses
    
    Args:
        config: Config object with settings
        
    Attributes:
        dac_v: DAC value for given dac_c channel to set, from 0 (off) to 1 (max)
        dac_c: DAC channel to set (1 is phase, 2 is diode, 3 is both)
    '''
    def __init__(self, config, tune_mode):
        '''Start connection, send nmr_settings dict'''
        self.tune_mode = tune_mode
        self.ok = bytes.fromhex('0300FA')
        self.s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, 0)
        self.s.settimeout(config.settings['fpga_settings']['timeout_udp'])
        self.config = config
        self.dac_v = 0  
        self.dac_c = 0
        self.ip = config.settings['fpga_settings']['ip']
        self.port = config.settings['fpga_settings']['port']
        try:
            self.s.connect((self.ip, self.port))
            if not self.set_register(): print("Set register error")
            #print(self.read_stat())
            if not self.set_freq(config.freq_bytes): print("Set frequency error")
            self.read_freq()
        except Exception as e:
            print("Error in UDP connection to DAQ at", self.ip, ":", e)
            raise
        
        
    def __del__(self):
        '''Stop connection'''
        try:
            self.s.close()
        except Exception as e:
            raise
    
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
        '''Read frequency command
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
        test_mode = self.config.settings['fpga_settings']['adc_test']
        reset = False
        phase_drate1 = self.config.settings['fpga_settings']['adc_drate1']
        phase_drate0 = self.config.settings['fpga_settings']['adc_drate0']
        phase_fpath = self.config.settings['fpga_settings']['adc_fpath']
        diode_drate1 = self.config.settings['fpga_settings']['adc_drate1']
        diode_drate0 = self.config.settings['fpga_settings']['adc_drate0']
        diode_fpath = self.config.settings['fpga_settings']['adc_fpath']
        rf_off = False
        states = [test_mode, reset, False, False, False, False, False, False, False, rf_off, phase_drate1, phase_drate0, phase_fpath, diode_drate1, diode_drate0, diode_fpath]
        adcbits = ''.join([str(int(i)) for i in states])
        ADCConfig = int(adcbits,2)
        #ADCConfig = 0x0036
        
        #dac_value = int(self.dac_v * (65535/5/3.2037))
        # Set up DAC value from desired percentage:
        # voltage =~ (16/65535) * DAC value 1/12/2021
        dac_value = int(self.dac_v * 65535)
        #print(self.dac_v, dac_value, dac_value.to_bytes(2,'little').hex())
                    
        # Make Resiter byte string from other inputs
        # Number Bytes LSB, Nymber Bytes MSB, LSByte GenSetTime, MSByte GenSetTime, LSByte NumOfSamToAve, MByte NumOfSamToAve, LSByte TotSweepCycle, MSByte TotSweepCycle, LSByte IntSweepCycle, MSByte IntSweepCycle, LSByte AdcConfig, MSByte AdcConfig, LSByte Dac Value, MSByte Dac Value, LSByte Dac Config, MSByte Dac Config
        RegSets = [bytes.fromhex('1100'),bytes.fromhex('02')]
        RegSets.append(self.config.settings['fpga_settings']['dwell'].to_bytes(2,'little'))
        RegSets.append(self.config.settings['fpga_settings']['per_point'].to_bytes(2,'little'))
        if self.tune_mode:
            RegSets.append(self.config.settings['tune_per_chunk'].to_bytes(2,'little'))
            RegSets.append(self.config.settings['tune_per_chunk'].to_bytes(2,'little'))
        else:
            RegSets.append(self.config.controls['sweeps'].value.to_bytes(2,'little'))
            RegSets.append(self.config.settings['num_per_chunk'].to_bytes(2,'little'))
        RegSets.append(ADCConfig.to_bytes(2,'little'))  
        RegSets.append(dac_value.to_bytes(2,'little'))
        RegSets.append(self.dac_c.to_bytes(2,'little'))
        #print("Last two reg bytes:",RegSets[-2].hex(), RegSets[-1].hex())    
        RegSetString = b''.join(RegSets)
        self.s.send(RegSetString)
        data, addr = self.s.recvfrom(1024)    # buffer size is 1024
        #print("Set string:",RegSetString.hex())
        #print("Read string:",self.read_stat())
        if data == self.ok:
            return True
        else:
            #print(data)
            return False
    
    def set_freq(self, freq_bytes):
        '''Send frequency points, converts freq list into bytes
        Args:
            freq_bytes: List of bytes for R&S frequency modulation
            
        Returns:
            Boolean denoting success
        '''
      
        NumBytes_byte = (self.config.settings['steps']*2+3).to_bytes(2,'little')   # number of bytes to send
        freqs = NumBytes_byte + bytes.fromhex('04') + b''.join(freq_bytes)         # freq string to send, including
        #[print(f.hex()) for f in freq_bytes]
        if self.config.settings['fpga_settings']['test_freqs']:
            NumBytes_byte = (self.config.settings['steps']*2+3).to_bytes(2,'little')
            #FreqList = range(1,self.config.settings['steps']+1)
            FreqList = range(-self.config.settings['steps'],0)
            FreqBytes = [b.to_bytes(2,'little', signed=True) for b in FreqList]
            TestTable = NumBytes_byte + bytes.fromhex('04') + b''.join(FreqBytes)            
            self.s.send(TestTable)
            #print("Set Freq: ", TestTable.hex())
        else:
            self.s.send(freqs)
            #print("Set Freq: ", freqs.hex())
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
    def __init__(self, config, timeout):
        '''Start connection'''
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM,0)
        self.s.settimeout(timeout)
        self.ip = config.settings['fpga_settings']['ip']
        self.port = config.settings['fpga_settings']['port']
        self.buffer_size = config.settings['fpga_settings']['tcp_buffer']
        self.s.connect((self.ip, self.port))
        self.freq_num = config.settings['steps']
        self.phase_cal = config.settings['fpga_settings']['phase_cal']
        self.diode_cal = config.settings['fpga_settings']['diode_cal']
                
        if config.settings['fpga_settings']['phase_adc_number'] == 2:
            self.adc_one = 'diode'
            self.adc_two = 'phase'
        else:
            self.adc_one = 'phase'
            self.adc_two = 'diode'
        
    def __del__(self):
        '''Stop connection'''
        try:
            self.s.close()
        except Exception as e:
            raise
        
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
        
        while not (len(chunk['phase'])==self.freq_num*5 and len(chunk['diode'])==self.freq_num*5):    
        # loop for chunk packets
            response = self.s.recv(self.buffer_size)
            
            if (sweep_type == ''):   # first packet has FF FF FF FF FF then 2 chunk number bytes, then 2 chunk sw cyc bytes, then an aa or bb byte to denote phase or diode 
                if b'\xff\xff\xff\xff\xff' == response[:5]:
                    chunk_num = int.from_bytes(response[5:7],'little')
                    num_in_chunk = int.from_bytes(response[7:9],'little')
                    #print(num_in_chunk, response[:2].hex())
                    response = response[9:]
                    sweep_type = self.adc_one
                    
                # add in check if we don't have the type set and it's not the beginning of the chunk  
                       
            res_list = [response[i:i+1] for i in range(len(response))]
            for b in res_list:
                if sweep_type == '':
                    #print("no type: ",b)
                    if b == b'\xbb':
                        sweep_type = self.adc_two
                    continue
                #if sweep_type == 'diode': print(b.hex())
                chunk[sweep_type] += bytearray(b)
                if (len(chunk[sweep_type]) == self.freq_num*5):             # filled up chunk
                    sweep_type = ''                   # unset type
                    
        pchunk_byte_list = [chunk['phase'][i:i + 5] for i in range(0, len(chunk['phase']), 5)]
        dchunk_byte_list = [chunk['diode'][i:i + 5] for i in range(0, len(chunk['diode']), 5)]
        pchunk = np.fromiter(((int.from_bytes(i, 'little', signed=True))/(num_in_chunk*2) for i in pchunk_byte_list), np.int64)   # average (number of sweeps times two for up and down) and put in numpy array
        dchunk = np.fromiter(((int.from_bytes(i, 'little', signed=True))/(num_in_chunk*2) for i in dchunk_byte_list), np.int64)
        #print("phase average", np.average(pchunk))
        #print("diode average", np.average(dchunk))
        return chunk_num, num_in_chunk, pchunk/self.phase_cal, dchunk/self.diode_cal  # converting value to voltage
        # 11/20/2020: phase 1V is roughly 211692085, diode 1V is 829421
        #return chunk_num, num_in_chunk, pchunk*3/8388607/0.5845, dchunk*3/8388607/0.5845  # converting value to voltage
        
class RS_Connection():
    '''Handle connection to Rohde and Schwarz SMA100A via Telnet. 
    
    Arguments:
        config: Current Config object
    '''
    def __init__(self, config):        
        '''Open connection to R&S, send commands for all settings, and read all back to check. Close.
        '''
        self.host = config.settings['RS_settings']['ip']
        self.port = config.settings['RS_settings']['port']
        
        try:
            tn = telnetlib.Telnet(self.host, port=self.port, timeout=config.settings['RS_settings']['timeout'])
            
            # Write all required settings
            
            tn.write(bytes(f"FREQ {config.channel['cent_freq']*1000000}\n", 'ascii'))
            tn.write(bytes(f"POWer {config.channel['power']} mV\n", 'ascii'))
            if 'FPGA' in config.settings['daq_type']:
                tn.write(b"FM:SOUR EDIG\n")
            elif 'NIDAQ' in config.settings['daq_type']:
                tn.write(b"FM:SOUR EXT\n")
            else:
                tn.write(b"FM:SOUR EXT\n")  
            tn.write(bytes(f"FM:EXT:DEV {config.channel['mod_freq']*1000}\n", 'ascii'))
            tn.write(b"FM:EXT:DIG:BFOR DCOD\n")
            tn.write(b"FM:STATE ON\n")
            tn.write(b"OUTP ON\n")
            tn.write(b"FREQ?\n")
            freq = tn.read_some().decode('ascii')
            tn.write(b"POW?\n")
            pow = tn.read_some().decode('ascii')
            tn.write(b"FM:SOUR?\n")
            sour = tn.read_some().decode('ascii')
            tn.write(b"FM:EXT:DEV?\n")
            dev = tn.read_some().decode('ascii')
            tn.write(b"FM:EXT:DIG:BFOR?\n")
            bfor = tn.read_some().decode('ascii')
            tn.write(b"FM:STATE?\n")
            fmstate = tn.read_some().decode('ascii')
            tn.write(b"OUTP?\n")
            outp = tn.read_some().decode('ascii')
            
            tn.close()
            print(f"Successfully sent settings to R&S on {self.host}")
            
        except Exception as e:
            print(f"R&S connection failed on {self.host}: {e}")
        
    def rf_off(self):
        '''Connect to turn off RF, then close.'''        
        try:
            tn = telnetlib.Telnet(self.host, port=self.port)
            tn.write(b"FM:STATE OFF\n")
            tn.close()
        except Exception as e:
            print(f"R&S connection failed on {self.host}: {e}")
        
    def rf_on(self):
        '''Connect to turn on RF, then close.'''
        try:
            tn = telnetlib.Telnet(self.host, port=self.port)
            tn.write(b"FM:STATE ON\n")
            tn.close()
        except Exception as e:
            print(f"R&S connection failed on {self.host}: {e}")
        
        
        
        
class NI_Connection():
    '''NI DAQ in and out tasks and methods to use them. Code from C.Carlin.
    
    Arguments:
        config: Current Config object
    
    '''
    
    def __init__(self, config):
    
        self.ai = nidaqmx.Task()
        self.ao = nidaqmx.Task()
    
        ramp_min_V,ramp_max_V = -1 * unyt.V, 1 * unyt.V
        self.pts_per_ramp = config.settings['steps']
        self.pretris = config.settings['nidaq_settings']['pretris']
        self.tris_per_scan = config.controls['sweeps'].value #//2  Difference in nomenclature. My sweeps are same as Carlin's triangles.
        time_per_pt_us = config.settings['nidaq_settings']['time_per_pt'] * unyt.us
        settling_delay_ratio = config.settings['nidaq_settings']['settling_ratio']
        ai_min_V,ai_max_V = -1 * unyt.V, 1 * unyt.V

        phase_chan = config.settings['nidaq_settings']['phase_chan']
        diode_chan = config.settings['nidaq_settings']['diode_chan']
        ao_chan = config.settings['nidaq_settings']['ao_chan']

        self.pts_per_tri = self.pts_per_ramp * 2
        self.total_pts = self.pts_per_tri * (self.tris_per_scan + self.pretris)
        sample_rate_Hz = 1 / time_per_pt_us.to(unyt.s)
        settling_delay_us = time_per_pt_us * settling_delay_ratio
        self.pretri_delay_s = (self.pretris * time_per_pt_us * self.pts_per_tri).to(unyt.s)
        
        self.triangle = list(np.linspace(ramp_min_V, ramp_max_V, self.pts_per_ramp))
        self.triangle += self.triangle[::-1] # Concat the list reversed
        
        self.ao.control(TaskMode.TASK_UNRESERVE)
        self.ao.ao_channels.add_ao_voltage_chan(ao_chan,
                                           min_val=ramp_min_V,
                                           max_val=ramp_max_V)

        self.ao.timing.cfg_samp_clk_timing(sample_rate_Hz,
                                      sample_mode=AcquisitionType.CONTINUOUS,
                                      samps_per_chan=self.pts_per_tri)

        self.ao.triggers.start_trigger.trig_type = TriggerType.NONE
        self.ao_start_terminal = self.ao.triggers.start_trigger.term

        #Setup AI channel
        self.ai.ai_channels.add_ai_voltage_chan(phase_chan, min_val=ai_min_V, max_val=ai_max_V)
        self.ai.ai_channels.add_ai_voltage_chan(diode_chan, min_val=ai_min_V, max_val=ai_max_V)

        self.ai.timing.delay_from_samp_clk_delay = settling_delay_us.to(unyt.s)
        self.ai.timing.delay_from_samp_clk_delay_units = DigitalWidthUnits.SECONDS

        self.ai.timing.cfg_samp_clk_timing(sample_rate_Hz,
                                      sample_mode=AcquisitionType.CONTINUOUS,
                                      samps_per_chan=self.total_pts*2)

        self.ai.in_stream.read_all_avail_samp = True
        self.ai.in_stream.relative_to = ReadRelativeTo.FIRST_SAMPLE
        self.ai.in_stream.over_write = OverwriteMode.OVERWRITE_UNREAD_SAMPLES

        self.ai.triggers.start_trigger.cfg_dig_edge_start_trig(self.ao_start_terminal)
        self.ai.triggers.start_trigger.trig_type = TriggerType.DIGITAL_EDGE
        self.ai.triggers.start_trigger.delay = self.pretri_delay_s
        self.ai.triggers.start_trigger.delay_units = DigitalWidthUnits.SECONDS
    
    def __del__(self):
        self.stop()
        self.ai.close()
        self.ao.close()
    
    def start(self):
        self.ao.stop()
        self.ai.stop()
        self.ao.write(self.triangle)
        self.ai.in_stream.offset = 0
        self.ai.start()
        self.ao.start()

    def stop(self):
        self.ao.stop()
        self.ai.stop()    

    def get_chunk(self):
        '''Get sweeps from NI board, return number of sweeps in chunk, phase np.array, diode np.array
        
        Notes:
            Results stream from the NI board and we ask for them after a second. What comes back is a number of sweeps, probably not ending in a whole numnber of sweeps. Have to save the last set of numbers to tack on to the front of the next chunk. Or we could discard the extra on the end...? 
        
        '''
        samples = self.ai.read(READ_ALL_AVAILABLE, timeout=self.pretri_delay_s)  # list of lists
        pchunks, dchunks = samples              # split into phase and diode        
        num_in_chunk = len(pchunks)//(self.pts_per_ramp)
        if  num_in_chunk < 1:      
            pchunk = np.zeros(self.pts_per_ramp)
            dchunk = np.zeros(self.pts_per_ramp)
            return 0, num_in_chunk, pchunk, dchunk
        pchunks = pchunks[:2*(num_in_chunk*self.pts_per_ramp//2)]    # discard extra samples if partially accumulated
        dchunks = dchunks[:2*(num_in_chunk*self.pts_per_ramp//2)]
        pchunks = np.array(pchunks).reshape(num_in_chunk, self.pts_per_ramp)  # 2D array with steps number of rows
        pchunks[1::2,:] = np.flip(pchunks[1::2,:])  # flip every other row
        dchunks = np.array(dchunks).reshape(num_in_chunk, self.pts_per_ramp)  # 2D array with steps number of rows
        dchunks[1::2,:] = np.flip(dchunks[1::2,:])  # flip every other row
        
        pchunk = np.average(pchunks, axis=0)
        dchunk = np.average(dchunks, axis=0)
        
        time.sleep(1)
        return 0, num_in_chunk, pchunk, dchunk

     
