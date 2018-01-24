# Example Scripts

## read.py

This script will try to read a tag within an infinite loop. 
If a tag is found it will  output Customer ID, UID and CRC Sum, and the device should beep once.

E.g.

```bash
$ python read.py

Initializing device...
Done!
Please hold a tag to the reader until you hear a beep...

uid: 1234567890
customer_id: 77
CRC Sum: 0x44
```

## write.py

This script will do the following:

- Try to read a tag within an infinite loop.
- If a tag is found then try to write it using CID and UID.
- Verify if the tag has been successfully written.
- If the write operation succeeds then beep twice and output CID, UID and CRC value
- If the write operation fails then beep three times and output error message.

E.g.

```bash
$ python write.py

Initializing device...
Done!
CID:UID to be written: 77:1234567890
Please hold a tag to the reader until you hear two beeps...

Write OK!
uid: 1234567890
customer_id: 77
CRC Sum: 0x44
```

