'''PyNMR, J.Maxwell 2020
'''
import socket
import numpy as np

class TCP():
    '''Handle TCP commands and responses

    Args:
        config: Config object with settings
        timeout: Int for TCP timeout time (secs)

    '''

    def __init__(self, config, timeout):
        '''Start connection'''
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
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
        num_in_chunk = 0  # Number of sweeps in the chunk
        chunk = {}
        chunk['phase'] = bytearray()
        chunk['diode'] = bytearray()
        sweep_type = ''  # phase or diode, starts as ''

        while not (len(chunk['phase']) == self.freq_num * 5 and len(chunk['diode']) == self.freq_num * 5):
            # loop for chunk packets
            response = self.s.recv(self.buffer_size)

            if (
                    sweep_type == ''):  # first packet has FF FF FF FF FF then 2 chunk number bytes, then 2 chunk sw cyc bytes, then an aa or bb byte to denote phase or diode
                if b'\xff\xff\xff\xff\xff' == response[:5]:
                    chunk_num = int.from_bytes(response[5:7], 'little')
                    num_in_chunk = int.from_bytes(response[7:9], 'little')
                    # print(num_in_chunk, response[:2].hex())
                    response = response[9:]
                    sweep_type = self.adc_one

                # add in check if we don't have the type set and it's not the beginning of the chunk

            res_list = [response[i:i + 1] for i in range(len(response))]
            for b in res_list:
                if sweep_type == '':
                    # print("no type: ",b)
                    if b == b'\xbb':
                        sweep_type = self.adc_two
                    continue
                # if sweep_type == 'diode': print(b.hex())
                chunk[sweep_type] += bytearray(b)
                if (len(chunk[sweep_type]) == self.freq_num * 5):  # filled up chunk
                    sweep_type = ''  # unset type

        pchunk_byte_list = [chunk['phase'][i:i + 5] for i in range(0, len(chunk['phase']), 5)]
        dchunk_byte_list = [chunk['diode'][i:i + 5] for i in range(0, len(chunk['diode']), 5)]
        pchunk = np.fromiter(
            ((int.from_bytes(i, 'little', signed=True)) / (num_in_chunk * 2) for i in pchunk_byte_list),
            np.int64)  # average (number of sweeps times two for up and down) and put in numpy array
        dchunk = np.fromiter(
            ((int.from_bytes(i, 'little', signed=True)) / (num_in_chunk * 2) for i in dchunk_byte_list), np.int64)
        # print("phase average", np.average(pchunk))
        # print("diode average", np.average(dchunk))
        return chunk_num, num_in_chunk, pchunk / self.phase_cal, dchunk / self.diode_cal  # converting value to voltage
        # 11/20/2020: phase 1V is roughly 211692085, diode 1V is 829421
        # return chunk_num, num_in_chunk, pchunk*3/8388607/0.5845, dchunk*3/8388607/0.5845  # converting value to voltage
