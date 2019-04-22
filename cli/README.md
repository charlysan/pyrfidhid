# RFID_CLI

A command line tool used to read, write and clone 125Khz tags.


## Introduction

`rfid_cli` is basically a command line tool that provides a similar functionality to the original Windows `IDRW` application, but with several useful extra features:

- Output data in different formats (dec/hex/bin)
- Write verification
- Enable/disable beep
- Read and write in loop mode
- Clone tags using a single operation

If you are interested in the architecture behind this tool please refer to rfid_cli architecture [document](doc/architecture.md)


## Hardware support

For the moment it only supports USB HID reader/writer labeled as "Microsoft Windows USB Reader".


## Installation

The tool should be installed automatically when you install [pyrfidhid library](../README.md#Installation).


## Usage

After installing the library, an executable script called `rfid_cli` should also be available. You can run it like this:

```bash
rfid_cli
```

You should get a listing of all the supported arguments and usage:

```bash
rfid_cli
usage: rfid_cli [-h] [-v] [-i] [--usb-vid VID] [--usb-pid PID] [-r] [-b BASE]
                [--w26] [--nocid] [--loop] [--single] [--read-delay DELAY]
                [--write-delay DELAY] [-w] [-c] [--t5577] [--noverify]
                [--no-read] [-a VALUE] [--beep]
                [CID] [UID]

RFID cli tool for reading and writing tags IDs using 125Khz Chinese USB HID Reader/Writer

positional arguments:
  CID                  Tag's Customer ID (in dec or hex format)
  UID                  Tag's UID

optional arguments:
  -h, --help           show this help message and exit
  -v, --version        show program's version number and exit
  -i                   Initialize Device
  --usb-vid VID        Set Device Vendor ID in hex format [default: 0xffff]
  --usb-pid PID        Set Device Product ID in hex format [default: 0x35]
  -r                   Read Tag
  -b BASE              Output base type (dec, hex, bin) [default: dec]
  --w26                W26 output
  --nocid              Do not print Customer ID
  --loop               Enable loop mode for reading/cloning tags
  --single             If loop mode is enabled do not print same tag more than
                       once
  --read-delay DELAY   Set Read loop interval in seconds [default: 0.200000]
  --write-delay DELAY  Set Write loop interval in seconds [default: 1.000000]
  -w                   Write Tag
  -c                   Clone Tag
  --t5577              Set tag type to T5577 [default: em4305]
  --noverify           Do not verify tag after writing
  --no-read            Do not read tag before trying to write it
  -a VALUE             Auto increment UID on every write [default: 0]
  --beep               Enable Beep

Examples:

        rfid_cli -r -b hex
        rfid_cli -r --w26
        rfid_cli -r -b bin --loop --single
        rfid_cli -w 12 12345 --t5577
        rfid_cli -w 0x0b 0xaabb
        rfid_cli -w 12 12345 --loop -a 1
```

You can also run it from the library root folder:

```bash
python cli/rfid_cli.py
```


## Examples

### Read a tag

```bash
$ rfid_cli -r -b hex

0x0c 0x0001e242
```

#### Loop mode

This mode allows to continuously read a tag until the user sends a SIGINT:

```bash
$ rfid_cli -r -b hex --loop
0x0c 0x0001e242
0x0c 0x0001e242
0x0c 0x0001e242
0x0c 0x0001e242
0x0c 0x0001e242
0x0c 0x0001e242
^C
Process terminated by user
```

If you don't want to see the same tag id printed more than once you can use the `--single` flag. This will prevent printing the same tag data multiple times. The tool is still reading continuously within a loop, but it will not print the tag's id if it is the same id that has been previously read. If you take the tag away from the reader and approach another one (with a different id), then you should see the new id:

```bash
$ rfid_cli -r -b dec --w26 --loop --single
12 1,57922
12 1,57920
```

### Write a tag

To write a tag you should pass the Product ID and the UID as arguments using decimal or hexadecimal format. For hexadecimal format you should add `0x` prefix:

```bash
rfid_cli -w 22 123456
Write OK! 22 123456
```

```bash
$ rfid_cli -w 0x1a 0x11abcd
Write OK! 26 1158093
```

Loop mode is also supported for write operation by adding `--loop` flag. When using this mode the tool will keep reading continuously until it successfully reads a tag, after that it will try to write the specified values.

### Clone a tag

This mode is just a write after a read operation along with a user prompt in between:

```bash
$ rfid_cli -c
Put source tag close to the reader...
Read done! 12 123456
Move source tag away from reader and press any key...
Put target tag close to the reader...
Write OK! 12 123456
```

You can also disable user prompt by including `--no-prompt` flag.
