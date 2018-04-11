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
    DEFAULT_VID = 0xffff
    DEFAULT_PID = 0x0035
    HID_REPORT_DESCRIPTOR_SIZE = 28
    CLASS_TYPE_REPORT = 0x22
    SET_REPORT = 0x09
    GET_REPORT = 0x01
    CRC_WRITE_INIT_VALUE = 0xb9
    BUFFER_SIZE = 256

    def __init__(self, vendor_id=DEFAULT_VID, product_id=DEFAULT_PID):
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
            self.dev, self.HID_REPORT_DESCRIPTOR_SIZE,
            self.CLASS_TYPE_REPORT,
            0)
        if not desc:
            raise ValueError("Cannot initialize Device.")

        return desc


    @staticmethod
    def __calculate_crc_sum(payload, init_val=CRC_WRITE_INIT_VALUE):
        r"""Calculate CRC checksum of the payload to be sent to the device.

        Arguments:
        payload -- binary representation of Tag's cid + uid as a sequence of bytes.
                   Example: cid:uid = 77:1234567890 => payload = [0xd4 0x49 0x96 0x02 0xd2]
        """

        tmp = init_val
        for byte in payload:
            tmp = tmp ^ byte

        return tmp


    def beep(self, times=1):
        r"""Send a command to make the device to emit a "beep"

        Arguments:
        times -- Number of "beeps" to emit
        """

        buff = [0x00] * self.BUFFER_SIZE

        buff[0] = 0x01
        buff[6] = 0x08
        buff[8] = 0xaa
        buff[10] = 0x03
        buff[11] = 0x89
        buff[12] = 0x01
        buff[13] = 0x01
        buff[14] = 0x8a
        buff[15] = 0xbb

        for _ in range(0, times):
            self.dev.ctrl_transfer(0x21, self.SET_REPORT, 0x0301, 0, buff)
            sleep(0.2)


    def read_tag(self):
        r"""Send a command to "read a tag" and retrieve the response from the device.

        Returns a PayloadResponse object
        """
        buff = [0x00] * self.BUFFER_SIZE

        # Setup payload for reading operation
        buff[0x00] = 0x01
        buff[0x06] = 0x08
        buff[0x08] = 0xaa
        buff[0x0a] = 0x03
        buff[0x0b] = 0x25
        buff[0x0e] = 0x26
        buff[0x0f] = 0xbb

        # Write Feature Report 1
        response = self.dev.ctrl_transfer(0x21, self.SET_REPORT, 0x0301, 0, buff)
        if response != self.BUFFER_SIZE:
            raise ValueError('Communication Error.')

        # Read from Feature Report 2
        response = self.dev.ctrl_transfer(0xa1, self.GET_REPORT, 0x0302, 0, self.BUFFER_SIZE).tolist()

        return PayloadResponse(response)


    def write_tag(self, ids_bytes):
        r"""Send a command to "write a tag"

        Arguments:
        ids_bytes -- Customer ID + UID to be written in binary byte format.
                     Format: [cid, uid_b3, uid_b2, uid_b1, uid_b0]
        """
        buff = [0x00] * self.BUFFER_SIZE

        # Setup payload for write operation
        buff[0x00] = 0x01
        buff[0x06] = 0x08
        buff[0x08] = 0xaa
        buff[0x0a] = 0x03
        buff[0x0b] = 0x89
        buff[0x0c] = 0x05
        buff[0x0d] = 0x01
        buff[0x0e] = 0x8e
        buff[0x0f] = 0xbb

        # Write to Feature Report 1
        response = self.dev.ctrl_transfer(0x21, self.SET_REPORT, 0x0301, 0, buff)
        if response != self.BUFFER_SIZE:
            raise ValueError('Communication Error.')

        # Read from Feature Report 2
        self.dev.ctrl_transfer(0xa1, self.GET_REPORT, 0x0302, 0, self.BUFFER_SIZE)

        buff = [0x00] * self.BUFFER_SIZE

        # Payload containing CID, UID and CRC
        buff[0x00] = 0x01
        buff[0x06] = 0x1f
        buff[0x08] = 0xaa
        buff[0x0a] = 0x1a
        buff[0x0b] = 0x21
        buff[0x0d] = 0x01
        buff[0x0e] = 0x01
        buff[0x0f] = 0x02
        buff[0x10] = ids_bytes[0]
        buff[0x11] = ids_bytes[1]
        buff[0x12] = ids_bytes[2]
        buff[0x13] = ids_bytes[3]
        buff[0x14] = ids_bytes[4]
        buff[0x15] = 0x80
        buff[0x25] = self.__calculate_crc_sum(ids_bytes)
        buff[0x26] = 0xbb

        # Write to Feature Report 1
        self.dev.ctrl_transfer(0x21, self.SET_REPORT, 0x0301, 0, buff)

        # Read from Feature Report 2
        self.dev.ctrl_transfer(0xa1, self.GET_REPORT, 0x0302, 0, self.BUFFER_SIZE)


    def write_tag_from_cid_and_uid(self, cid, uid):
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

        self.write_tag(ids_bytes)


class PayloadResponse(object):
    r"""Object representation of the response coming from the device"""
    RESPONSE_LENGTH_WITH_TAG = 19
    CID_POS = 12
    UID_MSB_POS = 13
    UID_LSB_POS = 16
    CRC_READ_POS = 17

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

    def get_tag_w26(self):
        r"""Interprets the Tag's UID as W26 (H10301) format.

        Returns a tuple (facility_code, card_number) or None on format mismatch."""
        if self.uid and self.uid[0] == 0:
            return struct.unpack('>BH', bytearray(self.uid[1:]))
        else:
            return None


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

