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

from __future__ import print_function
import argparse
import sys
import struct

from time import sleep
from rfidhid.core import RfidHid
from rfidhid.core import PayloadResponse
from ast import literal_eval as make_tuple
from transitions import Machine


class RfidCli(object):

    states = ['start', 'init', 'read', 'print',
              'write', 'verify', 'print', 'sleep', 'exit']
    rfid = None
    machine = None
    payload_response_temp = None

    def __init__(self):
        self.args = self.parse_arguments()
        self.tag_type = RfidHid.TAG_T5577 if self.args.t5577 else RfidHid.TAG_EM4305

        self.rfid = self.connect(self.args.usb_vid, self.args.usb_pid)

        self.machine = Machine(model=self, states=self.states, initial='start')

        # Initialize Device
        self.machine.add_transition(
            trigger='next', source='start', dest='init', after='initialize', conditions=['is_init'])
        self.machine.add_transition(
            trigger='next', source='init', dest='exit', after='exit')

        # Read Tag
        self.machine.add_transition(
            trigger='next', source='start', dest='read', after='read', conditions=['is_read'])
        self.machine.add_transition(
            trigger='next', source='read', dest='print', after='print', conditions=['is_read'])
        self.machine.add_transition(
            trigger='next', source='print', dest='exit', after='exit', conditions=['is_read'], unless=['is_loop'])
        self.machine.add_transition(
            trigger='next', source='print', dest='sleep', after='sleep', conditions=['is_read', 'is_loop'])
        self.machine.add_transition(
            trigger='next', source='sleep', dest='read', after='read', conditions=['is_read', 'is_loop'])

        # Write Tag

    def is_init(self):
        return self.args.init

    def is_read(self):
        return self.args.read

    def is_loop(self):
        return self.args.loop

    def is_single(self):
        return self.args.single

    def is_beep(self):
        return self.args.beep

    def has_id_data(self):
        return self.payload_response.has_id_data()

    def sleep(self):
        sleep(self.args.loop_interval)

    def read(self):
        self.payload_response = self.rfid.read_tag()

    def connect(self, vid, pid):
        try:
            return RfidHid(vid, pid)
        except Exception as e:
            print(e)
            exit()

    def exit(self):
        exit()

    def initialize(self):
        print('Initializing device...')
        self.rfid.init()
        sleep(1)
        print('Done!')

    def parse_payload_response(self, payload_response, base):
        if base == 'hex':
            uid = payload_response.get_tag_uid(
                base=PayloadResponse.BASE16)
            cid = payload_response.get_tag_cid(
                base=PayloadResponse.BASE16)
            w26 = payload_response.get_tag_w26(
                base=PayloadResponse.BASE16)
        elif base == 'bin':
            uid = payload_response.get_tag_uid(
                base=PayloadResponse.BASE2)
            cid = payload_response.get_tag_cid(
                base=PayloadResponse.BASE2)
            w26 = payload_response.get_tag_w26(
                base=PayloadResponse.BASE2)
        else:
            uid = payload_response.get_tag_uid()
            cid = payload_response.get_tag_cid()
            w26 = payload_response.get_tag_w26()

        # simplify w26 output
        if w26:
            w26 = str('%s,%s' % (w26))

        return uid, cid, w26

    def print(self):
        if self.has_id_data() is False:
            return

        if self.payload_response.is_equal(self.payload_response_temp) and self.is_single():
            return

        uid, cid, w26 = self.parse_payload_response(
            self.payload_response, self.args.base)
        if self.args.w26:
            uid = w26

        if self.args.cid:
            print("%s %s" % (cid, uid))
        else:
            print(uid)

        self.payload_response_temp = self.payload_response
        if self.is_beep():
            # wait before sending beep
            sleep(0.2)
            self.rfid.beep()

    def parse_arguments(self):
        parser = argparse.ArgumentParser(
            description="RFID cli tool for reading and writing tags IDs using 125Khz Chinese USB HID Reader/Writer",
            version="v1.0 (March 10, 2019)",
        )

        parser.add_argument('-i',
                            action="store_true", dest="init",
                            help="Initialize Device", default=False)

        parser.add_argument('--usb-vid',
                            action='store', dest='usb_vid', metavar='VID', type=int,
                            help="Set Device Vendor ID in hex format [default: %(default)#x]", default=0xffff
                            )

        parser.add_argument('--usb-pid',
                            action="store", dest="usb_pid", metavar='PID', type=int,
                            help="Set Device Product ID in hex format [default: %(default)#x] ", default=0x0035)

        parser.add_argument('-r',
                            action="store_true", dest="read",
                            help="Read Tag", default=False)

        parser.add_argument('-b',
                            action="store", dest="base", type=str, metavar='BASE',
                            help="Output base type (dec, hex, bin) [default: %(default)#s]", default='dec')

        parser.add_argument('--w26',
                            action="store_true", dest="w26",
                            help="W26 output", default=False)

        parser.add_argument('--nocid',
                            action="store_false", dest="cid",
                            help="Do not print Customer ID", default=True)

        parser.add_argument('--loop',
                            action="store_true", dest="loop",
                            help="Enable loop mode for reading/cloning tags", default=False)

        parser.add_argument('--single',
                            action="store_true", dest="single",
                            help="If loop mode is enabled do not print same tag more than once", default=False)

        parser.add_argument('-l', metavar='INTERVAL',
                            action="store", dest="loop_interval", type=float,
                            help="Set Read loop interval in seconds [default: %(default)#2f]", default=0.1)

        parser.add_argument('-w',
                            action="store_true", dest="write",
                            help="Write Tag", default=False)

        parser.add_argument('w_cid', type=str, metavar='CID', default=None,
                            nargs='?', help=" Tag's Customer ID")

        parser.add_argument('w_uid', type=str, metavar='UID', default=None,
                            nargs='?', help=" Tag's  UID")

        parser.add_argument('--t5577',
                            action="store_true", dest="t5577",
                            help="Set tag type to T5577 [default: em4305]", default=False)

        parser.add_argument('--noverify',
                            action="store_false", dest="verify",
                            help="Do not verify tag after writing", default=True)

        parser.add_argument('-a', metavar='VALUE', type=int,
                            action="store", dest="auto_increment",
                            help="Auto increment UID on every write (loop mode) [default: %(default)#d]", default=0)

        parser.add_argument('--nobeep',
                            action="store_false", dest="beep",
                            help="Disable Beep", default=True)

        parser.add_argument('-o',
                            action="store_true", dest="overwrite",
                            help="Force overwrite", default=False)

        args = parser.parse_args(
            args=None if sys.argv[1:] else ['--help'])

        return args


def main():
    rfid_cli = RfidCli()

    while True:
        rfid_cli.next()

    # if args.init:
    #     initialize_device(rfid)

    # cid_temp = None
    # uid_temp = None

    # while True:
    #     # Read a Tag
    #     if args.read:
    #         payload_response = rfid.read_tag()
    #         if payload_response.has_id_data() is False:
    #             cid_temp = uid_temp = None

    #         uid, cid, w26 = parse_payload_response(payload_response, args.base)

    #         cid_temp = cid
    #         uid_temp = uid

    #         if args.w26:
    #             uid = w26

    #         if args.cid:
    #             print("%s %s" % (cid, uid))
    #         else:
    #             print(uid)

    #         if args.beep:
    #             # wait before sending beep
    #             sleep(0.2)
    #             rfid.beep()

    #         # if args.single is False and uid is not None and cid is not None and uid == uid_temp and cid == cid_temp:
    #         if args.single is False and (cid, uid) == (cid_temp, uid_temp):
    #             sleep(args.loop_interval)
    #             continue

    #         if args.loop == False:
    #             sleep(args.loop_interval)
    #             break

        # Write a Tag
        # elif args.write:
        #     cid_temp = uid_temp = None

        #     if (args.w_cid is None or args.w_uid is None):
        #         print('Please set Tag CID and UID')
        #         exit(-1)

        #     w_cid = parse_CID(args.w_cid)
        #     w_uid = parse_UID(args.w_uid)

        #     # store initial value for auto increment
        #     uid_first = w_uid

        #     payload_response = rfid.read_tag()
        #     if payload_response.has_id_data() is False:
        #         uid_temp = None
        #         if args.loop is False:
        #             print('Please hold a tag close to the device.')

        #     if args.loop == False:
        #         sleep(args.loop_interval)
        #         break

        #     uid = payload_response.get_tag_uid()
        #     # Avoid processing the same tag (CID/UID) more than once in a row
        #     # if (uid != uid_temp and uid != uid_first) or args.overwrite is True:
        #     if (uid == uid_temp or uid == uid_first) or args.overwrite is False:
        #         continue

        #     uid_temp = uid

        #     rfid.write_tag_from_cid_and_uid(
        #         w_cid, w_uid, tag_type=tag_type)

        #     # wait before reading or beeping
        #     sleep(0.2)

        #     if args.beep == True:
        #         rfid.beep(2)

        #     # Verify write operation
        #     if args.verify:
        #         payload_response = rfid.read_tag()
        #         uid = payload_response.get_tag_uid()
        #         cid = payload_response.get_tag_cid()

        #         if (cid, uid) != (w_cid, w_uid):
        #             print('Write Error!')
        #             continue

        #         print('Write OK!')
        #         print(str('%s %s') % (cid, uid))

        #     # auto increment
        #     if args.auto_increment > 0:
        #         w_uid = w_uid + args.auto_increment
        #         uid_temp = uid_temp + args.auto_increment

        # else:
        #     break


# def parse_payload_response(payload_response, base):
#     if base == 'hex':
#         uid = payload_response.get_tag_uid(
#             base=PayloadResponse.BASE16)
#         cid = payload_response.get_tag_cid(
#             base=PayloadResponse.BASE16)
#         w26 = payload_response.get_tag_w26(
#             base=PayloadResponse.BASE16)
#     elif base == 'bin':
#         uid = payload_response.get_tag_uid(
#             base=PayloadResponse.BASE2)
#         cid = payload_response.get_tag_cid(
#             base=PayloadResponse.BASE2)
#         w26 = payload_response.get_tag_w26(
#             base=PayloadResponse.BASE2)
#     else:
#         uid = payload_response.get_tag_uid()
#         cid = payload_response.get_tag_cid()
#         w26 = payload_response.get_tag_w26()

#     # simplify w26 output
#     if w26:
#         w26 = str('%s,%s' % (w26))

#     return uid, cid, w26


# def connect(vid, pid):
#     try:
#         return RfidHid(vid, pid)
#     except Exception as e:
#         print(e)
#         exit()


# def initialize_device(rfid):
#     print('Initializing device...')
#     rfid.init()
#     sleep(1)
#     print('Done!')


# def parse_id(id):
#     try:
#         if id.startswith("0x"):
#             return int(id, 16)
#         else:
#             return int(id, 10)
#     except ValueError:
#         print("Invalid input (%s). Please use integer or hex string (e.g. 0x4d)" % id)
#         exit(-1)


# def parse_CID(cid):
#     cid = parse_id(cid)
#     if cid > 0xff or cid < 0:
#         print('Invalid Customer ID (%s)' % cid)
#         exit(-1)
#     return cid


# def parse_UID(uid):
#     uid = parse_id(uid)
#     if uid > 0xffffffff or uid < 0:
#         print('Invalid UID (%s)' % uid)
#         exit(-1)
#     return uid


# def parse_w26_fc(fc):
#     fc = parse_id(fc)
#     if fc > 0xff or fc < 0:
#         print('Invalid W26 Facility Code (%s)' % fc)
#         exit(-1)
#     return fc


# def parse_w26_cn(cn):
#     cn = parse_id(cn)
#     if cn > 0xffffff or cn < 0:
#         print('Invalid W26 Card Number (%s)' % cn)
#         exit(-1)
#     return cn

# def w26_to_uid_int(fc, cn):
#     return struct.unpack('>I', bytearray([0] + [fc] + list(bytearray(struct.pack('>H', cn)))))[0]
if __name__ == "__main__":
    main()
