from __future__ import print_function
import optparse
import sys

from time import sleep
from rfidhid.core import RfidHid
from rfidhid.core import PayloadResponse


def main():
    rfid = None

    options, args = parse_arguments()

    vid = int(options.dev_vid, 16)
    pid = int(options.dev_pid, 16)
    interval = float(options.interval)

    if options.init == True:
        if rfid is None:
            rfid = connect(vid, pid)
        initialize_device(rfid)

    if options.read == True:
        cid_temp = None
        uid_temp = None

        if rfid is None:
            rfid = connect(vid, pid)
        while True:
            payload_response = rfid.read_tag()
            if payload_response.has_id_data():
                if options.hex == True:
                    uid = payload_response.get_tag_uid(
                        base=PayloadResponse.BASE16)
                    cid = payload_response.get_tag_cid(
                        base=PayloadResponse.BASE16)
                elif options.bin == True:
                    uid = payload_response.get_tag_uid(
                        base=PayloadResponse.BASE2)
                    cid = payload_response.get_tag_cid(
                        base=PayloadResponse.BASE2)
                else:
                    uid = payload_response.get_tag_uid()
                    cid = payload_response.get_tag_cid()

                if options.single and uid is not None and cid is not None and uid == uid_temp and cid == cid_temp:
                    sleep(interval)
                    continue

                cid_temp = cid
                uid_temp = uid
                if options.cid == True:
                    print("%s %s" % (cid, uid))
                else:
                    print(uid)

                if options.beep == True:
                    rfid.beep()
            else:
                cid_temp = None
                uid_temp = None

            if options.loop == False:
                break
            else:
                sleep(interval)


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

    group.add_option('--dev_vid',
                     action="store", dest="dev_vid",
                     help="Set Device Vendor ID in Hexadecimal format [default: %default]", default='0xffff')

    group.add_option('--dev_pid',
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

    group.add_option('--cid',
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
        # Try to open RFID device using default vid:pid (ffff:0035)
        return RfidHid(vid, pid)
    except Exception as e:
        print(e)
        exit()


def initialize_device(rfid):
    print('Initializing device...')
    rfid.init()
    sleep(1)
    print('Done!')


if __name__ == "__main__":
    main()
