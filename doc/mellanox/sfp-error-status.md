# Fetch SFP error status through CLI #

## Table of Content

### Revision

### Scope

This is the high level design for the feature "fetch SFP error status through CLI".

### Definitions/Abbreviations

This section covers the abbreviation if any, used in this high-level design document and its definitions.
xcvrd: Transceiver daemon
CLI: Command line interface

### Overview

The purpose of this section is to give an overview of high-level design document and its architecture implementation in SONiC.

### Requirements

The requirement:

- To expose the SFP error status to CLI
- One shot command for debugging, which means the error status should be directly polled from low lever, eg. SDK, instead of being cached in the database.
- Only supported on Mellanox system. The command will be under `show platform mlnx`

### Architecture Design

CLI to call platform API directly and platform API to fetch error status by calling SDK API.

- A new platform API is introduced to fetch the error code of the SPF module via using the SDK API.
- A CLI command is introduced to display the error status to the user. Since the platform API is available in pmon docker only, the CLI has to call platform API via `docker exec` and then parse the output of the platform API.
- No database change is required.

### High-Level Design

#### Platform API

A new platform API in class SFP is required for polling the error status of the SFP module.

```
def get_error_status(self)
    """
    Get error status of the SFP module
    Returns:
        string: represent the error code
    """
```

It calls the SDK API and translates the return code to a human-readable string. In case the SFP module isn't plugged-in, it will return "no error".

The possible errors are listed below:

- Power budget exceeded
- Long range
- Bus stuck
- Bad unsupported eeprom
- Enforce part number list
- Unsupported cable
- High temperature
- Bad cable
- PMD type not enabled
- PCIE system power slot exceeded

#### CLI

##### CLI syntax

The command `show platform mlnx transceiver error-status` is designed to fetch and display the error status of the SFP modules. It is implemented by calling the platform API.

```
sonic#show platform mlnx transceiver error-status --port <port_name>
```

If the parameter `--port` is provided, the command will display the error status of the port. Otherwise, it will display the error status of all the ports.

```
admin@sonic:~$ show platform mlnx transceiver error-status --port Ethernet8
Port       Error Status
---------  ------------------------------------
Ethernet8  No error

admin@sonic:~$ show platform mlnx transceiver error-status 
Port         Error Status
-----------  ----------------------------------------------
Ethernet0    No error
Ethernet4    No error
Ethernet8    No error
Ethernet12   No error
Ethernet16   No error
Ethernet20   No error
Ethernet24   No error
Ethernet28   No error
Ethernet32   No error
Ethernet36   No error
Ethernet40   No error
Ethernet44   Exceeded power bugdet
Ethernet48   No error
Ethernet52   No error
Ethernet56   No error
Ethernet60   No error
Ethernet64   No error
Ethernet68   No error
Ethernet72   No error
Ethernet76   No error
Ethernet80   No error
Ethernet84   No error
Ethernet88   No error
Ethernet92   No error
Ethernet96   No error
Ethernet100  No error
Ethernet104  No error
Ethernet108  No error
Ethernet112  No error
Ethernet116  No error
Ethernet120  No error
Ethernet124  No error
Ethernet128  No error
Ethernet132  No error
Ethernet136  No error
Ethernet140  No error
Ethernet144  No error
Ethernet148  No error
Ethernet152  No error
Ethernet156  No error
Ethernet160  No error
Ethernet164  No error
Ethernet168  No error
Ethernet172  No error
Ethernet176  No error
Ethernet180  No error
Ethernet184  No error
Ethernet188  No error
Ethernet192  No error
Ethernet196  No error
Ethernet200  No error
Ethernet204  No error
Ethernet208  No error
Ethernet212  No error
Ethernet216  No error
Ethernet220  No error
```

##### CLI flow

The platform API is available from pmon docker but not from host. The CLI command needs to make use of `docker exec` command to call platform API in the pmon docker. It will call `python3` command with a inline python code which initializes the chassis object and then poll error status of the SPF module.

1. Parse the parameters
2. If no parameters fed, generate inline python code to:
   - initialize the chassis object and all the SFP modules
   - than call SFP.get_error_status() to poll the error status
   - print the error status
   else if a specific port fed as a parameter:
   - initialize the chassis object and the SFP module corresponding to the parameter
   - than call SFP.get_error_status() to poll the error status
   - print the error status
3. Parse the output and display to the user.

### SAI API 

N/A

### Configuration and management

N/A

#### CLI/YANG model Enhancements

N/A

#### Config DB Enhancements

N/A

### Warmboot and Fastboot Design Impact

N/A

### Restrictions/Limitations

### Testing Requirements/Design
Explain what kind of unit testing, system testing, regression testing, warmboot/fastboot testing, etc.,
Ensure that the existing warmboot/fastboot requirements are met. For example, if the current warmboot feature expects maximum of 1 second or zero second data disruption, the same should be met even after the new feature/enhancement is implemented. Explain the same here.
Example sub-sections for unit test cases and system test cases are given below. 

#### Unit Test cases  

#### System Test cases

### Open/Action items - if any 

	
NOTE: All the sections and sub-sections given above are mandatory in the design document. Users can add additional sections/sub-sections if required.