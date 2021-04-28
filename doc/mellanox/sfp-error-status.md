# Fetch SFP error status through CLI on Mellanox platform #

## Table of Content

### Revision

### Scope

This is the high level design for the feature "fetch SFP error status through CLI on Mellanox platform".

### Definitions/Abbreviations

This section covers the abbreviation if any, used in this high-level design document and its definitions.
xcvrd: Transceiver daemon
CLI: Command line interface

### Overview

The purpose of this section is to give an overview of high-level design document and its architecture implementation in SONiC.

### Requirements

The requirement:

- To expose the SFP error status to CLI
- One shot command for debugging, which means the error status should be directly fetched from low lever, eg. SDK, instead of being cached in the database.
- Only supported on Mellanox system. The command will be under `show platform mlnx`

### Architecture Design

CLI to call platform API directly and platform API to fetch error status by calling SDK API.

- A new platform API is introduced to fetch the error code of the SPF module via using the SDK API.
  This platform API is Mellanox-specific and won't be supported on other platforms for now. Neither will the base class definition be added into `sonic-platform-common` for it.
- A CLI command is introduced to display the error status to the user. Since the platform API is available in pmon docker only, the CLI has to call platform API via `docker exec` and then parse the output of the platform API.
- No database change is required.

### High-Level Design

#### Platform API

A new platform API in class SFP is required for fetching the error status of the SFP module.

```
def get_error_status(self)
    """
    Get error status of the SFP module
    Returns:
        string: represent the error code
    """
```

It calls the SDK API and translates the return code to a human-readable string. In case the SFP module isn't plugged-in, it will return "OK".

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
Ethernet8  OK

admin@sonic:~$ show platform mlnx transceiver error-status 
Port         Error Status
-----------  ----------------------------------------------
Ethernet0    OK
Ethernet4    OK
Ethernet8    OK
Ethernet12   OK
Ethernet16   OK
Ethernet20   OK
Ethernet24   OK
Ethernet28   OK
Ethernet32   OK
Ethernet36   OK
Ethernet40   OK
Ethernet44   Exceeded power bugdet
Ethernet48   OK
Ethernet52   OK
Ethernet56   OK
Ethernet60   OK
Ethernet64   OK
Ethernet68   OK
Ethernet72   OK
Ethernet76   OK
Ethernet80   OK
Ethernet84   OK
Ethernet88   OK
Ethernet92   OK
Ethernet96   OK
Ethernet100  OK
Ethernet104  OK
Ethernet108  OK
Ethernet112  OK
Ethernet116  OK
Ethernet120  OK
Ethernet124  OK
Ethernet128  OK
Ethernet132  OK
Ethernet136  OK
Ethernet140  OK
Ethernet144  OK
Ethernet148  OK
Ethernet152  OK
Ethernet156  OK
Ethernet160  OK
Ethernet164  OK
Ethernet168  OK
Ethernet172  OK
Ethernet176  OK
Ethernet180  OK
Ethernet184  OK
Ethernet188  OK
Ethernet192  OK
Ethernet196  OK
Ethernet200  OK
Ethernet204  OK
Ethernet208  OK
Ethernet212  OK
Ethernet216  OK
Ethernet220  OK
```

##### CLI flow

The platform API is available from pmon docker but not from host. The CLI command needs to make use of `docker exec` command to call platform API in the pmon docker. It will call `python3` command with a inline python code which initializes the chassis object and then fetch error status of the SPF module.

1. Parse the parameters
2. If no parameters fed, generate inline python code to:
   - initialize the chassis object and all the SFP modules
   - than call SFP.get_error_status() to fetch the error status
   - print the error status
   else if a specific port fed as a parameter:
   - initialize the chassis object and the SFP module corresponding to the parameter
   - than call SFP.get_error_status() to fetch the error status
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