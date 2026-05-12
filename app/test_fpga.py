

import socket


def write_register(socket, RegSets):
    ''' Join byte array (RegSets) into string and send to socket, return True if ok returned
    '''
    RegSetString = b''.join(RegSets)
    socket.send(RegSetString)
    data, addr = socket.recvfrom(1024)  # buffer size is 1024
    print("Set string:",RegSetString.hex())
    if data == bytes.fromhex('0300FA'):
        return True
    else:
        return False


def main():
    ok = bytes.fromhex('0300FA')
    ip = '192.168.0.70'
    port = 1028

    states = [False, False, False, False, False, False, False, False, False, False, True, True,
              False, True, True, False]
    adcbits = ''.join([str(int(i)) for i in states])
    ADCConfig = int(adcbits, 2)

    dac_value = 4619

    # Make Resiter byte string from other inputs
    # Number Bytes LSB, Nymber Bytes MSB, LSByte GenSetTime, MSByte GenSetTime, LSByte NumOfSamToAve, MByte NumOfSamToAve, LSByte TotSweepCycle, MSByte TotSweepCycle, LSByte IntSweepCycle, MSByte IntSweepCycle, LSByte AdcConfig, MSByte AdcConfig, LSByte Dac Value, MSByte Dac Value, LSByte Dac Config, MSByte Dac Config
    RegSets = [bytes.fromhex('1100'), bytes.fromhex('02')]
    RegSets.append((61636).to_bytes(2, 'little'))  # GenSetTime (or trig rate 1 count=20us)
    RegSets.append((62).to_bytes(2, 'little'))  # NumOfSamToAve or pulse width

    RegSets.append((1541).to_bytes(2, 'little'))  # Number of sweeps
    RegSets.append((2055).to_bytes(2, 'little'))  # Sweeps per chunk

    RegSets.append(ADCConfig.to_bytes(2, 'little'))
    RegSets.append(dac_value.to_bytes(2, 'little'))
    RegSets.append((0).to_bytes(1, 'little'))
    RegSets.append((0).to_bytes(1, 'little'))
    #RegSets.append((0).to_bytes(2, 'little'))
    print("Last three reg bytes:",RegSets[-3].hex(),RegSets[-2].hex(), RegSets[-1].hex())


    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, 0)
        s.settimeout(2)
        s.connect((ip, port))
    except Exception as e:
        print("Error in UDP connection to DAQ at", ip, ":", e)

    print(write_register(s, RegSets))

    # run = True

    # if run:
    #     s.send(bytes.fromhex('110002c4f03e000506070836000b120000'))  #My 1st String to set Trigger rate and trigger width
    #     data, addr = s.recvfrom(1024)  # buffer size is 1024
    #     print(data)
    #     s.send(bytes.fromhex('110002c4f03e000506070836000b120404'))
    #     data, addr = s.recvfrom(1024)  # buffer size is 1024
    #     print(data)

    # if run:
    #     s.send(bytes.fromhex('0F0005000000000000000000000000'))  # start sweeps
    #     data, addr = s.recvfrom(1024)  # buffer size is 1024
    #     if data == ok:
    #         print(True)
    #     else:
    #         print(False)
    # if not run:
    #     #s.send(bytes.fromhex('0F0006000000000000000000000000'))  # cancel sweeps
    #     s.send(bytes.fromhex('110002c4f03e000506070836000b120000'))
    #     data, addr = s.recvfrom(1024)  # buffer size is 1024
    #     if data == ok:
    #         print(True)
    #     else:
    #         print(False)


if __name__ == "__main__":
    main()