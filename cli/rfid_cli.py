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
import signal

from time import sleep
from rfidhid.core import RfidHid
from rfidhid.core import PayloadResponse
from ast import literal_eval as make_tuple
from transitions import Machine


class RfidCli(object):

    states = ['start', 'init', 'read', 'print',
              'write', 'clone', 'verify', 'exit']
    rfid = None
    machine = None
    payload_response_temp = None

    def __init__(self):
        self.args = self.parse_arguments()
        self.tag_type = RfidHid.TAG_T5577 if self.args.t5577 else RfidHid.TAG_EM4305

        self.rfid = self.connect(self.args.usb_vid, self.args.usb_pid)

        self.machine = Machine(
            model=self, states=self.states, initial='start', send_event=True)

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
            trigger='next', source='print', dest='read', before='sleep', after=['read'], conditions=['is_read', 'is_loop'])

        # Write Tag
        self.machine.add_transition(
            trigger='next', source='start', dest='write', after='write', conditions=['is_write'], unless=['is_read_before_write'])
        self.machine.add_transition(
            trigger='next', source='start', dest='read', after='read', conditions=['is_write', 'is_read_before_write'])
        self.machine.add_transition(
            trigger='next', source='read', dest='write', before='sleep', after='write', conditions=['is_write', 'is_read_before_write', 'has_id_data'])
        self.machine.add_transition(
            trigger='next', source='read', dest='read', before='sleep', after='read', conditions=['is_write', 'is_read_before_write'], unless=['has_id_data'])
        self.machine.add_transition(
            trigger='next', source='write', dest='exit', after='exit', conditions=['is_write'], unless=['is_loop', 'is_verify'])
        self.machine.add_transition(
            trigger='next', source='write', dest='write', before='sleep', after=['write', 'beep', 'increment'], conditions=['is_write', 'is_loop'], unless=['is_verify'])
        self.machine.add_transition(
            trigger='next', source='write', dest='verify', before='sleep', after=['verify', 'beep', 'increment'], conditions=['is_write', 'is_verify'])
        self.machine.add_transition(
            trigger='next', source='verify', dest='exit', after=['beep', 'exit'], conditions=['is_write', 'is_verify'], unless=['is_loop'])
        self.machine.add_transition(
            trigger='next', source='verify', dest='read', after=['sleep', 'read'], conditions=['is_write', 'is_loop', 'is_verify'])

        # Clone Tag
        self.machine.add_transition(
            trigger='next', source='start', dest='read', before=['print_clone_src_notice'], after='read', conditions=['is_clone'])
        self.machine.add_transition(
            trigger='next', source='read', dest='read', before='sleep', after='read', conditions=['is_clone'], unless='has_id_data')
        self.machine.add_transition(
            trigger='next', source='read', dest='start', before=['beep', 'prompt'], after=['read', 'switch_to_write_condition', 'print_clone_dest_notice'], conditions=['is_clone', 'is_prompt'])
        self.machine.add_transition(
            trigger='next', source='read', dest='start', before=['beep', 'prompt'], after=['sleep','read', 'switch_to_write_condition', 'print_clone_dest_notice'], conditions=['is_clone'], unless=['is_prompt'])

    def is_init(self, event):
        return self.args.init

    def is_read(self, event):
        return self.args.read

    def is_write(self, event):
        return self.args.write

    def is_clone(self, event):
        return self.args.clone

    def is_loop(self, event):
        return self.args.loop

    def is_verify(self, event):
        return self.args.verify

    def is_auto_increment(self, event):
        return True if self.args.auto_increment > 0 else False

    def is_read_before_write(self, event):
        return self.args.read_before_write

    def is_single(self, event):
        return self.args.single

    def is_beep(self, event):
        return self.args.beep

    def is_prompt(self, event):
        return self.args.prompt

    def has_id_data(self, event):
        return self.payload_response.has_id_data()

    def sleep(self, event):
        delay = self.args.read_interval
        if (event.transition.source == 'write' and event.transition.dest == 'write'):
            delay = self.args.write_interval
        if (event.transition.source == 'verify' and event.transition.dest == 'read'):
            delay = self.args.write_interval
        if (event.transition.source == 'read' and event.transition.dest == 'start' and self.is_clone):
            delay = self.args.write_interval
        sleep(delay)

    def switch_to_write_condition(self, event):
        r"""Used to switch from `clone to `write` condition"""
        self.args.clone = False
        self.args.read = False
        self.args.write = True

    def read(self, event):
        r"""Read a Tag"""
        self.payload_response = self.rfid.read_tag()

    def write(self, event):
        r"""Write a Tag"""
        if (self.w_cid is None or self.w_uid is None):
            print('Please set Tag CID and UID')
            exit(-1)

        self.rfid.write_tag_from_cid_and_uid(
            self.w_cid, self.w_uid, tag_type=self.tag_type)

    def verify(self, event):
        r"""Verify written Tag"""
        payload_response = self.rfid.read_tag()
        uid = payload_response.get_tag_uid()
        cid = payload_response.get_tag_cid()

        if cid != self.w_cid or uid != self.w_uid:
            print('Write Error!')
        else:
            print(str('Write OK! %s %s') % (cid, uid))

    def increment(self, event):
        r"""Increment UID. Used in `auto-increment mode`"""
        self.w_uid = self.w_uid + self.args.auto_increment

    def prompt(self, event):
        r"""Prompt user to press any key after reading source tag (clone mode)"""
        self.w_cid = self.payload_response.get_tag_cid()
        self.w_uid = self.payload_response.get_tag_uid()

        print("Read done! %s %s" % (self.w_cid, self.w_uid))
        if self.args.prompt:
            raw_input("Move source tag away from reader and press ENTER...")

    def print_clone_src_notice(self, event):
        print("Put source tag close to the reader...")

    def print_clone_dest_notice(self, event):
        print("Put target tag close to the reader...")

    def connect(self, vid, pid):
        try:
            return RfidHid(vid, pid)
        except Exception as e:
            print(e)
            exit()

    def beep(self, event):
        if self.args.beep:
            times = 1 if event.transition.source == 'print' or event.transition.dest == 'prompt' else 2
            # wait before sending beep
            sleep(0.2)
            self.rfid.beep(times)

    def exit(self, event):
        exit()

    def initialize(self, event):
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

    def print(self, event):
        if self.payload_response.has_id_data() is False:
            return

        if self.payload_response.is_equal(self.payload_response_temp) and self.args.single:
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
        if self.args.beep:
            # wait before sending beep
            sleep(0.2)
            self.rfid.beep()

    def parse_CID(self, cid):
        cid = self.parse_id(cid)
        if cid > 0xff or cid < 0:
            print('Invalid Customer ID (%s)' % cid)
            exit(-1)
        return cid

    def parse_UID(self, uid):
        uid = self.parse_id(uid)
        if uid > 0xffffffff or uid < 0:
            print('Invalid UID (%s)' % uid)
            exit(-1)
        return uid

    def parse_id(self, id):
        try:
            if id.startswith("0x"):
                return int(id, 16)
            else:
                return int(id, 10)
        except ValueError:
            print("Invalid input (%s). Please use integer or hex string (e.g. 0x4d)" % id)
            exit(-1)

    def parse_arguments(self):

        example_text = r'''Examples:

        rfid_cli -r -b hex
        rfid_cli -r --w26
        rfid_cli -r -b bin --loop --single
        rfid_cli -w 12 12345 --t5577
        rfid_cli -w 0x0b 0xaabb
        rfid_cli -w 12 12345 --loop -a 1'''

        parser = argparse.ArgumentParser(
            description="RFID cli tool for reading and writing tags IDs using 125Khz Chinese USB HID Reader/Writer",
            epilog=example_text,
            formatter_class=argparse.RawDescriptionHelpFormatter
        )

        parser.add_argument('--version',
                            action="version",
                            version="v1.1.4 (Nov 14th, 2020)")

        parser.add_argument('-i',
                            action="store_true", dest="init",
                            help="Initialize Device", default=False)

        parser.add_argument('--usb-vid',
                            action='store', dest='usb_vid', metavar='VID', type=int,
                            help="Set Device Vendor ID in decimal format [default: %(default)#x]", default=65535
                            )

        parser.add_argument('--usb-pid',
                            action="store", dest="usb_pid", metavar='PID', type=int,
                            help="Set Device Product ID in decimal format [default: %(default)#x] ", default=53)

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

        parser.add_argument('--read-delay', metavar='DELAY',
                            action="store", dest="read_interval", type=float,
                            help="Set Read loop interval in seconds [default: %(default)#2f]", default=0.2)

        parser.add_argument('--write-delay', metavar='DELAY',
                            action="store", dest="write_interval", type=float,
                            help="Set Write loop interval in seconds [default: %(default)#2f]", default=1)

        parser.add_argument('-w',
                            action="store_true", dest="write",
                            help="Write Tag", default=False)

        parser.add_argument('-c',
                            action="store_true", dest="clone",
                            help="Clone Tag", default=False)

        parser.add_argument('w_cid', type=str, metavar='CID', default=None,
                            nargs='?', help=" Tag's Customer ID (in dec or hex format)")

        parser.add_argument('w_uid', type=str, metavar='UID', default=None,
                            nargs='?', help=" Tag's  UID")

        parser.add_argument('--t5577',
                            action="store_true", dest="t5577",
                            help="Set tag type to T5577 [default: em4305]", default=False)

        parser.add_argument('--noverify',
                            action="store_false", dest="verify",
                            help="Do not verify tag after writing", default=True)

        parser.add_argument('--no-read',
                            action="store_false", dest="read_before_write",
                            help="Do not read tag before trying to write it", default=True)
        
        parser.add_argument('--no-prompt',
                            action="store_false", dest="prompt",
                            help="Do not prompt the user to press a key in clone mode", default=True)

        parser.add_argument('-a', metavar='VALUE', type=int,
                            action="store", dest="auto_increment",
                            help="Auto increment UID on every write [default: %(default)#d]", default=0)

        parser.add_argument('--beep',
                            action="store_true", dest="beep",
                            help="Enable Beep", default=False)

        args = parser.parse_args(
            args=None if sys.argv[1:] else ['--help'])

        if (args.read and args.write) or (args.read and args.clone) or (args.write and args.clone):
            args = parser.parse_args(['--help'])

        if args.write:
            if args.w_cid is None or args.w_uid is None:
                args = parser.parse_args(['--help'])

            self.w_cid = self.parse_CID(args.w_cid)
            self.w_uid = self.parse_UID(args.w_uid)

        return args

def signal_handler(sig, frame):
        print('\nProcess terminated by user')
        sys.exit(0)

def main():
    signal.signal(signal.SIGINT, signal_handler)
    rfid_cli = RfidCli()

    while True:
        rfid_cli.next()


if __name__ == "__main__":
    main()
