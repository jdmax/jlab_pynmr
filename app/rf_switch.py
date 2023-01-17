import telnetlib

class RFSwitch():
    '''Handle connection to Minicircuits RF switch via serial over ethernet. 
    '''
    def __init__(self, host, port, timeout):        
        '''Open connection to Minicircuits RF Switch
        Arguments:
            host: IP address
            port: Port of device
            timeout: Telnet timeout in secs
        '''
        self.host = host
        self.port = port
        self.timeout = timeout
        
        try:
            self.tn = telnetlib.Telnet(self.host, port=self.port, timeout=self.timeout)                  
        except Exception as e:
            print(f"RF Switch connection failed on {self.host}: {e}")
            
    def set_switch(self, switch, status):
        '''Set switch.
        Arguments:
            switch: Switch port. Can be "A" or "B"
            status: Com to 1 = 0, Com to 2 = 1        
        '''  
        try: 
            self.tn.write(bytes(f"SET{switch}={status}\n",'ascii'))     
            data = self.tn.read_until(b'\n', timeout = 2).decode('ascii')   # read until carriage return
            return data
            
        except Exception as e:
            print(f"RF Switch read failed on {self.host}: {e}")
        