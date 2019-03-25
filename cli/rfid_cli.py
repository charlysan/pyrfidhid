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

from __future__ import print_function
import argparse
import sys
import struct

from time import sleep
from rfidhid.core import RfidHid
from rfidhid.core import PayloadResponse
from ast import literal_eval as make_tuple


def main():
    rfid = None
    tag_type = RfidHid.TAG_EM4305

    args = parse_arguments()

    usb_vid = args.usb_vid
    usb_pid = args.usb_pid
    loop_interval = float(args.loop_interval)

    if args.init == True:
        if rfid is None:
            rfid = connect(usb_vid, usb_pid)
        initialize_device(rfid)

    if args.read == True:
        cid_temp = None
        uid_temp = None

        if rfid is None:
            rfid = connect(usb_vid, usb_pid)
        while True:
            payload_response = rfid.read_tag()
            if payload_response.has_id_data():
                uid, cid, w26 = parse_payload_response(
                    payload_response, args.base)

                if args.single and uid is not None and cid is not None and uid == uid_temp and cid == cid_temp:
                    sleep(loop_interval)
                    continue

                cid_temp = cid
                uid_temp = uid

                if args.cid == True:
                    if args.w26:
                        print("%s %s" % (cid, w26))
                    else:
                        print("%s %s" % (cid, uid))
                else:
                    if args.w26:
                        print(w26)
                    else:
                        print(uid)

                if args.beep == True:
                    sleep(0.2)  # wait before sending beep
                    rfid.beep()
            else:
                cid_temp = None
                uid_temp = None

            if args.loop == False:
                break
            else:
                sleep(loop_interval)

    if args.write == True:
        cid_temp = None
        uid_temp = None

        if rfid is None:
            rfid = connect(usb_vid, usb_pid)

        if (args.w_cid and args.w_uid):
            w_cid = parse_CID(args.w_cid)
            w_uid = parse_UID(args.w_uid)

            # store first value for auto increment
            uid_first = w_uid
        else:
            print('Please set Tag CID and UID')
            exit(-1)

        while True:
            payload_response = rfid.read_tag()
            if payload_response.has_id_data():
                uid = payload_response.get_tag_uid()
                # Avoid processing the same tag (CID/UID) more than once in a row
                if (uid != uid_temp and uid != uid_first) or args.overwrite is True:
                    uid_temp = uid

                    if args.t5577:
                        tag_type = RfidHid.TAG_T5577

                    rfid.write_tag_from_cid_and_uid(
                        w_cid, w_uid, tag_type=tag_type)

                    # wait before reading or beeping
                    sleep(0.2)

                    if args.beep == True:
                        rfid.beep(2)

                    # Verify write operation
                    if args.verify:
                        payload_response = rfid.read_tag()
                        uid = payload_response.get_tag_uid()
                        cid = payload_response.get_tag_cid()

                        if uid == w_uid and cid == w_cid:
                            print('Write OK!')
                            print(str('%s %s') % (cid, uid))
                        else:
                            print('Write Error!')

                    # auto increment
                    if args.auto_increment > 0:
                        w_uid = w_uid + args.auto_increment
                        uid_temp = uid_temp + args.auto_increment
            else:
                uid_temp = None
                if args.loop is False:
                    print('Please hold a tag close to the device.')

            if args.loop == False:
                break
            else:
                sleep(loop_interval)


def parse_payload_response(payload_response, base):
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
    w26 = str('%s,%s' % w26)

    return uid, cid, w26


def parse_arguments():
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

    parser.add_argument('--showcid',
                        action="store_true", dest="cid",
                        help="Print Customer ID", default=False)

    parser.add_argument('--loop',
                        action="store_true", dest="loop",
                        help="Enable loop mode for reading/cloning tags", default=False)

    parser.add_argument('--single',
                        action="store_true", dest="single",
                        help="If loop mode is enabled do not print same tag more than once", default=False)

    parser.add_argument('-l', metavar='INTERVAL',
                        action="store", dest="loop_interval",
                        help="Set Read loop_interval in seconds [default: %(default)#2f]", default=0.1)

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

    parser.add_argument('-a', metavar='INCREMENT', type=int,
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


def connect(vid, pid):
    try:
        return RfidHid(vid, pid)
    except Exception as e:
        print(e)
        exit()


def initialize_device(rfid):
    print('Initializing device...')
    rfid.init()
    sleep(1)
    print('Done!')


def parse_id(id):
    try:
        if id.startswith("0x"):
            return int(id, 16)
        else:
            return int(id, 10)
    except ValueError:
        print("Invalid input (%s). Please use integer or hex string (e.g. 0x4d)" % id)
        exit(-1)


def parse_CID(cid):
    cid = parse_id(cid)
    if cid > 0xff or cid < 0:
        print('Invalid Customer ID (%s)' % cid)
        exit(-1)
    return cid


def parse_UID(uid):
    uid = parse_id(uid)
    if uid > 0xffffffff or uid < 0:
        print('Invalid UID (%s)' % uid)
        exit(-1)
    return uid


def parse_w26_fc(fc):
    fc = parse_id(fc)
    if fc > 0xff or fc < 0:
        print('Invalid W26 Facility Code (%s)' % fc)
        exit(-1)
    return fc


def parse_w26_cn(cn):
    cn = parse_id(cn)
    if cn > 0xffffff or cn < 0:
        print('Invalid W26 Card Number (%s)' % cn)
        exit(-1)
    return cn


def w26_to_uid_int(fc, cn):
    return struct.unpack('>I', bytearray([0] + [fc] + list(bytearray(struct.pack('>H', cn)))))[0]


if __name__ == "__main__":
    main()
