'''PyNMR, J.Maxwell 2020
'''

import telnetlib

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

            tn.write(bytes(f"FREQ {config.channel['cent_freq'] * 1000000}\n", 'ascii'))
            tn.write(bytes(f"POWer {config.channel['power']} mV\n", 'ascii'))
            if 'FPGA' in config.settings['daq_type']:
                tn.write(b"FM:SOUR EDIG\n")
            elif 'NIDAQ' in config.settings['daq_type']:
                tn.write(b"FM:SOUR EXT\n")
            else:
                tn.write(b"FM:SOUR EXT\n")
            tn.write(bytes(f"FM:EXT:DEV {config.channel['mod_freq'] * 1000}\n", 'ascii'))
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

