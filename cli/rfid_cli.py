import optparse
import sys


def main():
    parser = optparse.OptionParser(
        description="RFID cli tool for controlling 125Khz Chinese USB HID  Reader/Writer",
        version="1.0",
    )

    

    group = optparse.OptionGroup(parser, "Setup Device",
                                 "Device Setup and initialization")

    group.add_option('-i', '--init',
                     action="store_true", dest="init",
                     help="Initialize Device", default=False)

    group.add_option('--vid',
                     action="store", dest="vid",
                     help="Set Device Vendor ID [default: %default]", default='0xffff')

    group.add_option('--pid',
                     action="store", dest="pid",
                     help="Set Device Product ID [default: %default]", default='0x0035')

    parser.add_option_group(group)

    group = optparse.OptionGroup(parser, "Read Tags",
                                 "Read a tag and get its Customer ID and UID")

    group.add_option('-r', '--read',
                     action="store_true", dest="read",
                     help="Read Tag", default=False)
    
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


    (options, args) = parser.parse_args(
        args=None if sys.argv[1:] else ['--help'])

    print options
    print args


if __name__ == "__main__":
    main()
