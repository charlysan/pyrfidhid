# Copyright (c) 2019 charlysan

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE

r"""Example script used to discover supported commands using brute force

Flow:
    - Itarate from 0x00 to 0xFF and send each command to Feature Report 1
    - if response[12] != 143 then the command has been recognized by the device
"""

from rfidhid.usb_hid import HID
from rfidhid.core import RfidHid
from time import sleep

def main():
    try:
        # Try to open RFID device using default vid:pid (ffff:0035)
        rfid = RfidHid()
    except Exception as e:
        print(e)
        exit()

    # Initialize device
    print('Initializing device...')
    rfid.init()
    sleep(2)
    
    cmds = []

    for cmd in range (0x00,0xff):
        payload = [0x00] * 0x03
        payload[0x01] = 0x01
        payload[0x02] = 0x01
        payload[0x00] = cmd 
        buff = rfid._initialize_write_buffer(payload)

        # Write Feature Report 1
        response = rfid.hid.set_feature_report(1, buff)

        if response != rfid.BUFFER_SIZE:
            raise ValueError('Communication Error.')

        # Read from Feature Report 2    
        response = rfid.hid.get_feature_report(2, rfid.BUFFER_SIZE).tolist()
        cmd_found = ""

        if response[12] != 143 :
            cmd_found = "CMD FOUND! " + hex(cmd)
            cmds.append(cmd)

        print('CMD: ' + hex(cmd) + ' response: ' + str(response) + ' ' + cmd_found)
        sleep(0.02)
    
    print('Found ' + str(len(cmds)) + ' commands:')
    print([hex(x) for x in cmds])

if __name__ == "__main__": 
    main()