# RFID_CLI

A command line tool used to read, write and clone 125Khz tags, implemented using a state machine.

## Introduction

This is just an experiment on how a state machine could be used to implement a command line tool that contains many conditional statements. 

When I first started to write the tool I realized that the code was not very "easy to read" as it had a lot of conditional statements in order to meet all the requirements (read, write and clone tags using different modes), so I decided to try out a different approach. I identified several states within the involved processes and implemented a state machine using [transitions library](https://github.com/pytransitions/transitions).

## Requirements

- The tool should be implemented as a command line tool.
- The tool should be able to read, write and clone tags.
- The tool should be able to allow the user to choose between different modes"
  - Read in normal mode: read a tag once and quit.
  - Read in loop mode: read a tag (or several tags) in a loop until the user sends a SIGINT.
  - Read in loop-single mode: same as loop mode but do not output same tag id more than once.
  - Write in normal mode: write CID and UID to tag and quit.
  - Write in loop mode: write CID and UID within a loop until the user sends a SIGINT.
  - Clone mode: clone a tag 
- The tool should also support the following features:
  - Write verify: verify that the correct data has been written to a tag after a write operation.
  - Print output in decimal, hexadecimal and binary format.
  - Print output in Wiegand 34 and Wiegand 26 formats.
  - Allow the user to input CID and UID using decimal or hexadecimal format.
  - Allow the user to choose between em4305 and t5577 tags.
  - Allow the user to enable or disable Beep.
  - Allow the user to initialize the device.


## State machine definition

The following states could be identified from the requirements:

- start
- init
- read
- print
- write
- clone
- exit

### Command line arguments

The following arguments will be used to choose between the different operations and modes:

```bash
positional arguments:
  CID                  Tag's Customer ID (in dec or hex format)
  UID                  Tag's UID

optional arguments:
  -i                   Initialize Device
  --usb-vid VID        Set Device Vendor ID in hex format [default: 0xffff]
  --usb-pid PID        Set Device Product ID in hex format [default: 0x35]
  -r                   Read Tag
  -b BASE              Output base type (dec, hex, bin) [default: dec]
  --w26                W26 output
  --nocid              Do not print Customer ID
  --loop               Enable loop mode for reading/cloning tags
  --single             If loop mode is enabled do not print same tag more than once
  --read-delay DELAY   Set Read loop interval in seconds [default: 0.200000]
  --write-delay DELAY  Set Write loop interval in seconds [default: 1.000000]
  -w                   Write Tag
  -c                   Clone Tag
  --t5577              Set tag type to T5577 [default: em4305]
  --noverify           Do not verify tag after writing
  --no-read            Do not read tag before trying to write it
  -a VALUE             Auto increment UID on every write [default: 0]
  --beep               Enable Beep
```

### Diagrams

The state machine for the write operation would look like this:

![write_sm](img/write_sm.png)


**Note**: To keep the diagram as simple and clean as possible I'm including only the states related to the `write operation`


## Implementation

`transitions` library allows to define call-back functions to be executed before and after a transition. I will take advantage of this feature in order to have less states and to execute common actions like beep and increment. Below are listed the transitions and call-back functions executions for the write operation:

```python
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
```

**Read operation** should be simpler and straightforward:

```python
 # Read Tag
        self.machine.add_transition(
            trigger='next', source='start', dest='read', after='read', conditions=['is_read'])
        self.machine.add_transition(
            trigger='next', source='read', dest='print', after='print', conditions=['is_read'])
        self.machine.add_transition(
            trigger='next', source='print', dest='exit', after='exit', conditions=['is_read'], unless=['is_loop'])
        self.machine.add_transition(
            trigger='next', source='print', dest='read', before='sleep', after=['read'], conditions=['is_read', 'is_loop']
```

Finally, **clone operation** looked like this:

```python
# Clone Tag
        self.machine.add_transition(
            trigger='next', source='start', dest='read', before=['print_clone_src_notice'], after='read', conditions=['is_clone'])
        self.machine.add_transition(
            trigger='next', source='read', dest='read', before='sleep', after='read', conditions=['is_clone'], unless='has_id_data')
        self.machine.add_transition(
            trigger='next', source='read', dest='read', before=['beep', 'prompt'], after=['read', 'switch_to_write_condition', 'print_clone_dest_notice'], conditions=['is_clone'])
```

As clone operation is basically a read operation and a prompt to the user to switch tags and press a key when ready. After that, the usual write process should be followed. To implement this and reuse the previous `write` states I call `switch_to_write_condition` call-back function at the end of the last transition, this will change the condition from `clone` to `write` and will allow to "switch" to write mode:

```python
def switch_to_write_condition(self, event):
        r"""Used to switch from `clone to `write` condition"""
        self.args.clone = False
        self.args.read = False
        self.args.write = True
```


### Final notes

The final code was cleaner and easier to maintain than the original one that used to have many `if-else` statements. However, it might not be the best approach for these use cases as understanding the state machine transitions without a state diagram might not be straightforward at all for another person who sees this code for the first time. As I said before, this was just an experiment, and I'm not sure if I would recommend to take this approach; nevertheless I would be glad to hear any feedback.
