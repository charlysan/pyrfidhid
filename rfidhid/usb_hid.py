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
# SOFTWARE.

import usb.core
import usb.control

class HID(object):
    REPORT_TYPE_FEATURE = 0x03
    REQUEST_HOST_TO_DEVICE_CLASS_INTERFACE = 0x21
    REQUEST_DEVICE_TO_HOST_CLASS_INTERFACE = 0xa1
    SET_REPORT = 0x09
    GET_REPORT = 0x01
    DEVICE_HID_INTERFACE_0 = 0
    CLASS_DESCRIPTOR_TYPE_REPORT = 0x22

    def __init__(self, vendor_id, product_id):
        r"""Open the device using vid and pid"""
        self.dev = usb.core.find(idVendor=vendor_id, idProduct=product_id)

        if self.dev is None:
            raise ValueError("Device with id %d:%d not found." % (vendor_id, product_id))


    def get_report_descriptor(self, length=0xff):
        try: 
            return usb.control.get_descriptor(self.dev, length, self.CLASS_DESCRIPTOR_TYPE_REPORT, 0)
        except (usb.core.USBError, usb.core.USBTimeoutError):
            print("Cannot get USB report descriptor. Maybe incompatible device?\n")
            raise


    def set_feature_report(self, report_number, data):
        
        try:
            return self.dev.ctrl_transfer(
                bmRequestType=self.REQUEST_HOST_TO_DEVICE_CLASS_INTERFACE, 
                bRequest=self.SET_REPORT, 
                wValue=self.REPORT_TYPE_FEATURE << 8 | report_number, 
                wIndex=self.DEVICE_HID_INTERFACE_0, 
                data_or_wLength=data
            )
        except (usb.core.USBError, usb.core.USBTimeoutError):
            print("Cannot write USB feature report. Maybe incompatible device?\n")
            raise 
        

    def get_feature_report(self, report_number, report_length):

        try:
            return self.dev.ctrl_transfer(
                bmRequestType=self.REQUEST_DEVICE_TO_HOST_CLASS_INTERFACE, 
                bRequest=self.GET_REPORT, 
                wValue=self.REPORT_TYPE_FEATURE << 8 | report_number, 
                wIndex=self.DEVICE_HID_INTERFACE_0, 
                data_or_wLength=report_length
            )
        except (usb.core.USBError, usb.core.USBTimeoutError):
            print("Cannot get USB feature report. Maybe incompatible device?\n")
            raise 

