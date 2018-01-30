# Copyright (c) 2018 charlysan

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


from time import sleep
import struct
import usb.core
import usb.util
import usb.control

class RfidHid(object):
    r"""Main object used to communicate with the device""" 
    DEVICE_DEFAULT_VID = 0xffff
    DEVICE_DEFAULT_PID = 0x0035
    DEVICE_HID_REPORT_DESCRIPTOR_SIZE = 28
    DEVICE_HID_INTERFACE_0 = 0x00

    CMD_READ_TAG = 0x25
    CMD_WRITE_TAG = 0x21
    CMD_BEEP = 0x89
    TAG_EM4305 = 0x02
    TAG_T5577 = 0x00
    STX_POS = 0x08
    STX = 0xaa
    ETX = 0xbb

    HID_REPORT_TYPE_FEATURE = 0x03
    HID_REQUEST_HOST_TO_DEVICE_CLASS_INTERFACE = 0x21
    HID_REQUEST_DEVICE_TO_HOST_CLASS_INTERFACE = 0xa1
    HID_SET_REPORT = 0x09
    HID_GET_REPORT = 0x01
    CLASS_TYPE_REPORT = 0x22

    BUFFER_SIZE = 256
    

    def __init__(self, vendor_id=DEVICE_DEFAULT_VID, product_id=DEVICE_DEFAULT_PID):
        r"""Open the device using vid and pid

        If no arguments are supplied then the default vid and pid will be used.
        """
        self.dev = None
        self.dev = usb.core.find(idVendor=vendor_id, idProduct=product_id)
        if self.dev is None:
            raise ValueError("Device with id %.4x:%.4x not found." % (vendor_id, product_id))


    def init(self):
        r"""Initialize the device

        This method should be use to initialize the device in case the OS does not find it.
        Issuing a `sudo lsusb -vd vid:pid` should produce the same result.
        """
        desc = usb.control.get_descriptor(
            self.dev, 
            self.DEVICE_HID_REPORT_DESCRIPTOR_SIZE, 
            self.CLASS_TYPE_REPORT, 
            0
        )
        if not desc:
            raise ValueError("Cannot initialize Device.")

        return desc


    def beep(self, times=1):
        r"""Send a command to make the device to emit a "beep"

        Arguments:
        times -- Number of "beeps" to emit
        """
        payload_length = 3
        buff = self._initialize_buffer(payload_length)

        buff[0x06] = 0x08
        buff[0x0b] = self.CMD_BEEP
        buff[0x0c] = 0x01
        buff[0x0d] = 0x01
        buff[0x0e] = self._calculate_crc_sum(self._get_payload_from_buffer(buff, payload_length))
        buff[0x0f] = self.ETX
        
        for _ in range(0, times):
            self._hid_set_feature_report(1, buff)
            sleep(0.2)


    def read_tag(self):
        r"""Send a command to "read a tag" and retrieve the response from the device.

        Returns a PayloadResponse object
        """
        payload_length = 0x03
        buff = self._initialize_buffer(payload_length)

        # Setup payload for reading operation
        buff[0x06] = 0x08
        buff[0x0b] = self.CMD_READ_TAG
        buff[0x0e] = self._calculate_crc_sum(self._get_payload_from_buffer(buff, payload_length))
        buff[0x0f] = self.ETX

        # Write Feature Report 1
        response = self._hid_set_feature_report(1, buff)

        if response != self.BUFFER_SIZE:
            raise ValueError('Communication Error.')

        # Read from Feature Report 2    
        response = self._hid_get_feature_report(2, self.BUFFER_SIZE).tolist()

        return PayloadResponse(response)


    def write_tag(self, id_bytes, tag_type=TAG_EM4305):
        r"""Send a command to "write a tag" 

        Arguments:
        id_bytes (list) -- Customer ID + UID to be written in binary byte format.
                           Format: [cid, uid_b3, uid_b2, uid_b1, uid_b0]
        tag_type (int)  -- Tag Type (EM4305 or T5577)
        """
        payload_length = 0x1a
        buff = self._initialize_buffer(payload_length)

        # Payload containing CID, UID and CRC
        buff[0x06] = 0x1f
        buff[0x0b] = self.CMD_WRITE_TAG
        buff[0x0d] = 0x01
        buff[0x0e] = 0x01
        buff[0x0f] = tag_type
        buff[0x10] = id_bytes[0] 
        buff[0x11] = id_bytes[1]
        buff[0x12] = id_bytes[2]
        buff[0x13] = id_bytes[3]
        buff[0x14] = id_bytes[4]
        buff[0x15] = 0x80
        buff[0x25] = self._calculate_crc_sum(self._get_payload_from_buffer(buff, payload_length))
        buff[0x26] = self.ETX

        # Write to Feature Report 1
        self._hid_set_feature_report(1, buff)

        sleep(0.2)

        # Read from Feature Report 2    
        return self._hid_get_feature_report(2, self.BUFFER_SIZE)


    def write_tag_from_cid_and_uid(self, cid, uid, tag_type=TAG_EM4305):
        r"""Send a command to "write a tag" 

        Arguments:
        cid -- (32 bits Integer) Customer ID
        uid -- (8 bits Integer)  UID
        """
        packed_uid = struct.pack('>I', uid)

        if isinstance(packed_uid, str):
            # python 2.7
            ids_bytes = [cid] + [ord(x) for x in list(packed_uid)]
        else:
            # python 3
            ids_bytes = [cid] + list(packed_uid)
 
        return self.write_tag(ids_bytes, tag_type)


    def _hid_set_feature_report(self, report_number, data):

        return self.dev.ctrl_transfer(
            bmRequestType=self.HID_REQUEST_HOST_TO_DEVICE_CLASS_INTERFACE, 
            bRequest=self.HID_SET_REPORT, 
            wValue=self.HID_REPORT_TYPE_FEATURE << 8 | report_number, 
            wIndex=self.DEVICE_HID_INTERFACE_0, 
            data_or_wLength=data
        )
        

    def _hid_get_feature_report(self, report_number, report_length):

        return self.dev.ctrl_transfer(
            bmRequestType=self.HID_REQUEST_DEVICE_TO_HOST_CLASS_INTERFACE, 
            bRequest=self.HID_GET_REPORT, 
            wValue=self.HID_REPORT_TYPE_FEATURE << 8 | report_number, 
            wIndex=self.DEVICE_HID_INTERFACE_0, 
            data_or_wLength=report_length
        )


    @staticmethod
    def _calculate_crc_sum(payload, init_val=0):
        r"""Calculate CRC checksum of the payload to be sent to the device.
        
        Arguments:
        payload (list) -- binary representation of the payload as a sequence of bytes.
        """
        tmp = init_val
        for byte in payload:
            tmp = tmp ^ byte 

        return tmp  


    def _initialize_buffer(self, payload_length=0):
        buff = [0x00] * self.BUFFER_SIZE
        buff[0x00] = 0x01
        buff[0x08] = self.STX
        buff[0x0a] = payload_length

        return buff


    def _get_payload_from_buffer(self, buff, length):
        r"""Extract payload from buffer based on STX position and payload length"""

        return buff[self.STX_POS+1:self.STX_POS+1+length+2]


class PayloadResponse(object):
    r"""Object representation of the response coming from the device"""
    RESPONSE_LENGTH_WITH_TAG = 0x13
    CID_POS = 0x0c
    UID_MSB_POS = 0x0d
    UID_LSB_POS = 0x10
    CRC_READ_POS = 0x11

    def __init__(self, data):
        self.data = data
        self.cid = None
        self.uid = None
        self.crc = None

        if len(data) == self.RESPONSE_LENGTH_WITH_TAG:
            self.cid = self.data[self.CID_POS]
            self.uid = self.data[self.UID_MSB_POS:self.UID_LSB_POS+1]
            self.crc = self.data[self.CRC_READ_POS]


    def get_tag_uid_as_byte_sequence(self):
        r"""Gets the Tag's UID as a sequence of bytes. E.g. [0x23, 0xa4, 0x23, 0x56]"""
        return self.uid 


    def get_tag_uid(self):
        r"""Gets the Tag's UID as a 32 bits Integer"""
        return struct.unpack('>I', bytearray(self.uid))[0] if self.uid else None


    def get_tag_cid(self):
        r"""Gets the Tag's Customer ID as a 8 bits Integer"""
        return self.cid


    def get_crc_sum(self):
        r"""Gets the UID+CID CRC Sum check coming from the device"""
        return self.crc   


    def has_id_data(self):
        r"""Check if the response contains the Tag's ID information"""
        return True if self.uid else False


    def get_raw_data(self):
        r"""Gets the response raw data coming from the device"""
        return self.data

