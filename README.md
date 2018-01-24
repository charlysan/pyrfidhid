# pyrfidhid

Python library to control Generic USB HID RFID Reader/Writer 


## Introduction

This library is the result of reverse-engineering the communication protocol of a USB RFID Reader/Writer. A detailed document describing the whole procedure can be found at the wiki section of this project:

[How to reverse engineer a USB HID RFID Reader/Writer](https://github.com/charlysan/pyrfidhid/wiki/Reverse-Engineering-A-USB-HID-RFID-Reader-Writer)

The library can be used to fully control the USB RFID device under Linux or MacOS, and it uses [pyusb](https://github.com/pyusb/pyusb) and [libusb](http://libusb.info/) to communicate through the USB port.

## Installation

You will need `Python 2.7.x` or greater, and [pip](https://pip.pypa.io/en/stable/). Just clone this repo, install the dependencies and run the `setup.py` script. 

### MacOS
 
```bash
$ brew install libusb
$ pip install pyusb
```

```bash
python setup.py install --user
```


### Linux

```bash
sudo apt-get install libusb-1.0-0-dev
sudo pip install pyusb
```

```bash
sudo python setup.py install
```

## Usage

The library should work with both Python 2.7.x and 3.x. After running the `setup.py` script you should be able to import and use the library within your project like this:

```python
from rfidhid.core import RfidHid

rfid = RfidHid()
payload_response = rfid.read_tag()
uid = payload_response.get_tag_uid()

rfid.beep()
print(uid)
```

The above script should try to connect to the device, read a Tag (if it is already close to the device), print the UID and beep.

For more complex read/write examples, please check out the [examples](https://github.com/charlysan/pyrfidhid/tree/lib_draft/examples) folder.

You can also check the [API documentation](documentation/apidoc.txt) for a list of exported methods.


## Final Notes

This is still in beta, and there are a couple of "to-do's":

- Support [T5577](http://www.xccrfid.com/uploadfile/downloads/T5577.pdf) tags.
- Support write protection.
- Implement a console tool capable of reading, writing and cloning tags with the same ease as `IDRW V3` tool.
