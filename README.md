# pyrfidhid

Python library to control Chinese USB HID 125Khz RFID Reader/Writer 


## Introduction

This library is the result of reverse-engineering the communication protocol of a Chinese USB 125Khz RFID Reader/Writer. A detailed document describing the whole procedure can be found at the wiki section of this project:

[How to reverse engineer a USB HID RFID Reader/Writer](https://github.com/charlysan/pyrfidhid/wiki/Reverse-Engineering-A-USB-HID-RFID-Reader-Writer)

The library can be used to control the USB RFID device under Linux or MacOS, and it uses [pyusb](https://github.com/pyusb/pyusb) and [libusb](http://libusb.info/) to communicate through the USB port.

## Installation (using pip)

You will need `Python 2.7.x` or greater, and [pip](https://pip.pypa.io/en/stable/). 

### MacOS
 
```bash
$ brew install libusb
$ pip install pyusb
$ pip install --upgrade pyrfidhid
```


### Linux

```bash
$ sudo apt-get install libusb-1.0-0-dev
$ sudo pip install pyusb
$ sudo pip install --upgrade pyrfidhid
```

## Manual Installation

If you can't install the library using pip, then try to install it using `setup.py` script. Just clone this repo, install the dependencies and run the `setup.py` script: 

```bash
$ python setup.py install
```


## Usage

The library should work with both Python 2.7.x and 3.x. After running the `setup.py` script you should be able to import and use the library within your project like this:

```python
from rfidhid.core import RfidHid

try:
    # Try to open RFID device using default vid:pid (ffff:0035)
    rfid = RfidHid()
except Exception as e:
    print(e)
    exit()

payload_response = rfid.read_tag()
uid = payload_response.get_tag_uid()

rfid.beep()
print(uid)
```

The above script should try to connect to the device, read a Tag (if it is already close to the device), print the UID and beep.

For more complex read/write examples, please check out the [examples](https://github.com/charlysan/pyrfidhid/tree/master/examples) folder.

You can also check the [API documentation](documentation/apidoc.txt) for a list of exported methods.


## RFID CLI Tool

A command line tool called `rfid_cli` is also included with the library, and it can be used to read, write and clone tags. For a complete documentation please check [rfid_cli documentation](cli/README.md)


## Final notes

If you are looking for an Android tool similar to `IDRW V3` you can check [this project](https://github.com/NiceLabs/usb-125khz-idrw)
