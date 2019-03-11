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
import optparse
import sys
import struct

from time import sleep
from rfidhid.core import RfidHid
from rfidhid.core import PayloadResponse
from ast import literal_eval as make_tuple


def main():
    rfid = None
    tag_type = RfidHid.TAG_EM4305

    options, args = parse_arguments()

    dev_vid = int(options.dev_vid, 16)
    dev_pid = int(options.dev_pid, 16)
    interval = float(options.interval)

    if options.init == True:
        if rfid is None:
            rfid = connect(dev_vid, dev_pid)
        initialize_device(rfid)

    if options.read == True:
        cid_temp = None
        uid_temp = None

        if rfid is None:
            rfid = connect(dev_vid, dev_pid)
        while True:
            payload_response = rfid.read_tag()
            if payload_response.has_id_data():
                if options.hex == True:
                    uid = payload_response.get_tag_uid(
                        base=PayloadResponse.BASE16)
                    cid = payload_response.get_tag_cid(
                        base=PayloadResponse.BASE16)
                    w26 = payload_response.get_tag_w26(
                        base=PayloadResponse.BASE16)
                elif options.bin == True:
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

                if options.single and uid is not None and cid is not None and uid == uid_temp and cid == cid_temp:
                    sleep(interval)
                    continue

                cid_temp = cid
                uid_temp = uid
                if options.cid == True:
                    if options.w26:
                        print("%s %s" % (cid, w26))
                    else:
                        print("%s %s" % (cid, uid))
                else:
                    if options.w26:
                        print(w26)
                    else:
                        print(uid)

                if options.beep == True:
                    sleep(0.1) # wait before sending beep
                    rfid.beep()
            else:
                cid_temp = None
                uid_temp = None

            if options.loop == False:
                break
            else:
                sleep(interval)

    if options.write == True:
        # TODO: implement verify and loop
        # if options.verify:
        #     payload_response = rfid.read_tag()
        #     uid = payload_response.get_tag_uid()
        #     sleep(0.2) # wait before writing
        if (options.w_cid and options.w_uid):
            w_cid = parse_CID(options.w_cid)
            w_uid = parse_UID(options.w_uid)
        elif (options.w_cid and options.w_w26_fc and options.w_w26_cn) and options.w_uid is None:
            w_cid = parse_CID(options.w_cid)
            w26_fc = parse_w26_fc(options.w_w26_fc)
            w26_cn = parse_w26_cn(options.w_w26_cn)

            w_uid = w26_to_uid_int(w26_fc, w26_cn)
        else:
            print('Please set Tag CID and UID or CID and W26 (FC,CN)')
            exit(-1)

        if rfid is None:
            rfid = connect(dev_vid, dev_pid)

        if options.t5577:
            tag_type = RfidHid.TAG_T5577

        rfid.write_tag_from_cid_and_uid(w_cid, w_uid, tag_type=tag_type)
        if options.beep == True:
            sleep(0.1) # wait before sending beep
            rfid.beep(2)


def parse_arguments():
    parser = optparse.OptionParser(
        description="RFID cli tool for reading and writing tags using 125Khz Chinese USB HID Reader/Writer",
        version="v1.0 (March 10, 2019)",
    )

    group = optparse.OptionGroup(parser, "Setup Device",
                                 "Device Setup and initialization")

    group.add_option('-i', '--init',
                     action="store_true", dest="init",
                     help="Initialize Device", default=False)

    group.add_option('--devVid',
                     action="store", dest="dev_vid",
                     help="Set Device Vendor ID in Hexadecimal format [default: %default]", default='0xffff')

    group.add_option('--devPid',
                     action="store", dest="dev_pid",
                     help="Set Device Product ID in Hexadecimal format [default: %default]", default='0x0035')

    parser.add_option_group(group)

    group = optparse.OptionGroup(parser, "Read Tags",
                                 "Read a tag and get its Customer ID and UID")

    group.add_option('-r', '--read',
                     action="store_true", dest="read",
                     help="Read Tag", default=False)

    group.add_option('--hex',
                     action="store_true", dest="hex",
                     help="Hexadecimal output", default=False)

    group.add_option('--bin',
                     action="store_true", dest="bin",
                     help="Binary output", default=False)

    group.add_option('--w26',
                     action="store_true", dest="w26",
                     help="W26 output", default=False)

    group.add_option('--showcid',
                     action="store_true", dest="cid",
                     help="Print Customer ID", default=False)

    group.add_option('--loop',
                     action="store_true", dest="loop",
                     help="Enable loop mode for reading/cloning tags", default=False)

    group.add_option('--single',
                     action="store_true", dest="single",
                     help="If loop mode is enabled do not print same tag more than once", default=False)

    group.add_option('--interval',
                     action="store", dest="interval",
                     help="Set Read Interval in seconds [default: %default]", default=0.1)

    parser.add_option_group(group)

    group = optparse.OptionGroup(parser, "Write Tags",
                                 "Write Customer ID and UID to a tag")

    group.add_option('-w', '--write',
                     action="store_true", dest="write",
                     help="Write Tag", default=False)
    
    group.add_option('-v', '--verify',
                     action="store_true", dest="verify",
                     help="Verify tag after writing", default=False)

    group.add_option('--t5577',
                     action="store_true", dest="t5577",
                     help="Set tag type to T5577 [default: em4305]", default=False)

    group.add_option('--autoinc',
                     action="store", dest="autoinc",
                     help="Auto increment UID on every write (for loop mode) [default: %default]", default=0)

    group.add_option('--wcid',
                     action="store", dest="w_cid",
                     help="Set Customer ID")

    group.add_option('--wuid',
                     action="store", dest="w_uid",
                     help="Set UID")

    group.add_option('--ww26fc',
                     action="store", dest="w_w26_fc",
                     help="Set W26 Facility Code")

    group.add_option('--ww26cn',
                     action="store", dest="w_w26_cn",
                     help="Set W26 Card Number")

    parser.add_option_group(group)

    group = optparse.OptionGroup(parser, "Clone Tags",
                                 "Read a tag and write its Customer ID and UID to another tag")

    group.add_option('-c', '--clone',
                     action="store_true", dest="clone",
                     help="Clone Tag", default=False)

    parser.add_option_group(group)

    group = optparse.OptionGroup(parser, "General options",
                                 "General purposes options")

    group.add_option('--nobeep',
                     action="store_false", dest="beep",
                     help="Disable Beep", default=True)

    parser.add_option_group(group)

    (options, args) = parser.parse_args(
        args=None if sys.argv[1:] else ['--help'])

    return options, args


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
