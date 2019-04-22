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


from time import sleep
import struct
from . import usb_hid


class RfidHid(object):
    r"""Main object used to communicate with the device"""
    DEVICE_DEFAULT_VID = 0xffff
    DEVICE_DEFAULT_PID = 0x0035
    DEVICE_HID_REPORT_DESCRIPTOR_SIZE = 28

    CMD_READ_TAG = 0x25
    CMD_WRITE_TAG = 0x21
    CMD_BEEP = 0x89
    TAG_EM4305 = 0x02
    TAG_T5577 = 0x00
    SOM_WRITE_POS = 0x08
    SOM_WRITE = 0xaa
    EOM_WRITE = 0xbb

    BUFFER_SIZE = 256

    def __init__(self, vendor_id=DEVICE_DEFAULT_VID, product_id=DEVICE_DEFAULT_PID):
        r"""Open the device using vid and pid

        If no arguments are supplied then the default vid and pid will be used.
        """
        self.hid = usb_hid.HID(vendor_id, product_id)

    def init(self):
        r"""Initialize the device

        This method should be use to initialize the device in case the OS does not find it.
        Issuing a `sudo lsusb -vd vid:pid` should produce the same result.
        """
        desc = self.hid.get_report_descriptor(
            self.DEVICE_HID_REPORT_DESCRIPTOR_SIZE)

        if not desc:
            raise ValueError("Cannot initialize Device.")

        return desc

    def beep(self, times=1):
        r"""Send a command to make the device to emit a "beep"

        Arguments:
        times -- Number of "beeps" to emit
        """
        payload = [0x00] * 0x03

        payload[0x00] = self.CMD_BEEP
        payload[0x01] = 0x01
        payload[0x02] = 0x01

        buff = self._initialize_write_buffer(payload)

        for _ in range(0, times):
            self.hid.set_feature_report(1, buff)
            sleep(0.2)

    def read_tag(self):
        r"""Send a command to "read a tag" and retrieve the response from the device.

        Returns a PayloadResponse object
        """
        payload = [0x00] * 0x03

        # Setup payload for reading operation
        payload[0x00] = self.CMD_READ_TAG

        buff = self._initialize_write_buffer(payload)

        # Write Feature Report 1
        response = self.hid.set_feature_report(1, buff)

        if response != self.BUFFER_SIZE:
            raise ValueError('Communication Error.')

        # Read from Feature Report 2
        response = self.hid.get_feature_report(2, self.BUFFER_SIZE).tolist()

        return PayloadResponse(response)

    def write_tag(self, id_bytes, tag_type=TAG_EM4305):
        r"""Send a command to "write a tag" 

        Arguments:
        id_bytes (list) -- Customer ID + UID to be written in binary byte format.
                           Format: [cid, uid_b3, uid_b2, uid_b1, uid_b0]
        tag_type (int)  -- Tag Type (EM4305 or T5577)
        """
        payload = [0x00] * 0x1a

        # Payload containing CID, UID and CRC
        payload[0x00] = self.CMD_WRITE_TAG
        payload[0x02] = 0x01
        payload[0x03] = 0x01
        payload[0x04] = tag_type
        payload[0x05] = id_bytes[0]
        payload[0x06] = id_bytes[1]
        payload[0x07] = id_bytes[2]
        payload[0x08] = id_bytes[3]
        payload[0x09] = id_bytes[4]
        payload[0x0a] = 0x80

        buff = self._initialize_write_buffer(payload)
        buff[0x06] = 0x1f  # Override 0x08 with 0x1f for write operation

        # Write to Feature Report 1
        self.hid.set_feature_report(1, buff)

        # Read from Feature Report 2
        response = self.hid.get_feature_report(2, self.BUFFER_SIZE)

        # T5577 tags cannot be read after a write operation without taking them out
        # of the field before. A workaround is to send a "beep" command with buff[0x0c] = 0x05
        # before trying to query them again. Actually this is what RWID V3 Tool does.
        payload = [0x00] * 0x03

        payload[0x00] = self.CMD_BEEP
        payload[0x01] = 0x05 if tag_type == self.TAG_T5577 else 0x04
        payload[0x02] = 0x01

        buff = self._initialize_write_buffer(payload)

        # Write to Feature Report 1
        self.hid.set_feature_report(1, buff)

        return response

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

    @staticmethod
    def _calculate_crc_sum(payload_data, init_val=0):
        r"""Calculate CRC checksum of the payload data to be sent to the device.

        Arguments:
        payload data (list) -- binary representation of the payload data as a sequence of bytes.
        """
        tmp = init_val
        for byte in payload_data:
            tmp = tmp ^ byte

        return tmp

    def _initialize_write_buffer(self, data):
        r"""Initialize the write buffer by appending to the data payload (command + arguments) 
        the SOM (start of message), EOM (end of message), Length and CRC
        """
        buff = [0x00] * self.BUFFER_SIZE
        data_length = len(data)

        buff[0x00] = 0x01
        buff[0x06] = 0x08
        buff[self.SOM_WRITE_POS] = self.SOM_WRITE
        buff[self.SOM_WRITE_POS+2] = data_length
        buff[self.SOM_WRITE_POS+3:self.SOM_WRITE_POS+3+data_length] = data
        buff[self.SOM_WRITE_POS+3 +
             data_length] = self._calculate_crc_sum([data_length] + data)
        buff[self.SOM_WRITE_POS+3+data_length+1] = self.EOM_WRITE

        return buff


class PayloadResponse(object):
    r"""Object representation of the response coming from the device"""
    RESPONSE_LENGTH_WITH_TAG = 0x13
    CID_POS = 0x0c
    UID_MSB_POS = 0x0d
    UID_LSB_POS = 0x10
    CRC_READ_POS = 0x11
    BASE10 = 10
    BASE2 = 2
    BASE16 = 16

    def __init__(self, data):
        self.data = data
        self.cid = None
        self.uid = None
        self.crc = None

        if len(data) == self.RESPONSE_LENGTH_WITH_TAG:
            self.cid = self.data[self.CID_POS]
            self.uid = self.data[self.UID_MSB_POS:self.UID_LSB_POS+1]
            self.crc = self.data[self.CRC_READ_POS]

    def get_tag_uid_as_byte_sequence(self, base=BASE10, zero_padding=2):
        r"""Gets the Tag's UID as a sequence of bytes. E.g. [0x23, 0xa4, 0x23, 0x56]"""
        return self._base_convert(self.uid, base=base, zero_padding=zero_padding)

    def get_tag_uid(self, base=BASE10, zero_padding=8):
        r"""Gets the Tag's UID as a 32 bits Integer"""
        return self._base_convert(struct.unpack('>I', bytearray(self.uid))[0], base=base, zero_padding=zero_padding) if self.uid else None

    def get_tag_w26(self, base=BASE10, zero_padding_fc=2, zero_padding_cn=4):
        r"""Interprets the Tag's UID as W26 (H10301) format.

        Returns a tuple (facility_code, card_number) or None on format mismatch."""
        if self.uid and self.uid[0] == 0:
            w26 = list(struct.unpack('>BH', bytearray(self.uid[1:])))
            w26[0] = self._base_convert(
                w26[0], base=base, zero_padding=zero_padding_fc)
            w26[1] = self._base_convert(
                w26[1], base=base, zero_padding=zero_padding_cn)

            return tuple(w26)
        else:
            return None

    def get_tag_cid(self, base=BASE10, zero_padding=2):
        r"""Gets the Tag's Customer ID as a 8 bits Integer"""
        return self._base_convert(self.cid, base=base, zero_padding=zero_padding)

    def get_crc_sum(self, base=BASE10, zero_padding=2):
        r"""Gets the UID+CID CRC Sum check coming from the device"""
        return self._base_convert(self.crc, base=base, zero_padding=zero_padding)

    def has_id_data(self):
        r"""Check if the response contains the Tag's ID information"""
        return True if self.uid else False

    def get_raw_data(self, base=BASE10, zero_padding=2):
        r"""Gets the response raw data coming from the device"""
        return self._base_convert(self.data, base=base, zero_padding=zero_padding)

    def calculate_crc(self):
        r"""Calculates payload data CRC Sum"""
        return RfidHid._calculate_crc_sum(self.data[10:-2])

    def is_equal(self, payload):
        r"""check is payload is equal to other payload"""
        if isinstance(payload, PayloadResponse) and self.cid == payload.cid and self.uid == payload.uid and self.crc == payload.crc:
            return True
        return False

    def _base_convert(self, data, base=BASE10, zero_padding=0):
        def f(data, base):
            if base == self.BASE16:
                padding = "#0%sx" % (zero_padding + 2)
                return format(data, padding)
            elif base == self.BASE2:
                padding = "#0%sb" % (zero_padding * 4 + 2)
                return format(data, padding)
            else:
                return data

        if isinstance(data, list):
            return [f(i, base) for i in data]
        else:
            return f(data, base)
