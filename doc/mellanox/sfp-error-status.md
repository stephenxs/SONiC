# Fetch SFP error status through CLI on Mellanox platform #

## Table of Content

### Revision

### Scope

This is the high level design for the feature "expose SFP error status to CLI".
Currently, the error status will be fetched from the low level layer directly.
In the future, we will support fetching error status from STATE_DB, which is not covered by this design.

### Definitions/Abbreviations

This section covers the abbreviation if any, used in this high-level design document and its definitions.
|          |              |
|----------|--------------|
| **Term** | **Meaning** |
| xcvrd | Transceiver daemon |
| CLI | Command line interface |

### Overview

The purpose of this section is to give an overview of high-level design document and its architecture implementation in SONiC.

### Requirements

The requirement:

- To expose the SFP error status to CLI
- Debug command which
  - Fetch the error status from the low level directly, eg. SDK.
  - Fetch the cached from the `STATE_DB`. This will be developed in the second phase and not covered by this design for now.
- Generic feature, supported on Mellanox system for now. The command will be under `show interface transceiver error-status`

### Architecture Design

CLI to call platform API directly and platform API to fetch error status by calling low level APIs.

- A new platform API is introduced to fetch the error code of the SPF module.
- A CLI command is introduced to display the error status to the user. Since the platform API is available in pmon docker only, the CLI has to call platform API via `docker exec` and then parse the output of the platform API.
- In the feature, the existing bitmap format of SFP error event will be leveraged to store error status into `STATE_DB`.

### High-Level Design

#### Platform API

A new platform API in class SFP is required for fetching the error status of the SFP module.

```
def get_error_status(self)
    """
    Get error status of the SFP module
    Returns:
        string: represent the error
    """
```

It calls the SDK API and translates the return code to a human-readable string:

- In case the SFP module isn't plugged-in, it will return `unplugged`.
- In case the SDK API returns a error code not listed in the below table, it will return `Unknown error: <error code>`.
- Otherwise, it will return the error description defined in the below table.

The errors are divided to two parts: generic errors and vendor specific errors.
The description of generic errors are listed below:

|                         |
|-------------------------|
| **Error description** |
| Power budget exceeded |
| Bus stuck (I2C data or clock shorted) |
| Bad or unsupported eeprom |
| Unsupported cable |
| High temperature |
| Bad cable (module/cable is shorted) |
| Vendor specific error |

Each vendor can have its own vendor specific errors.
On Mellanox platform, there are following:

|                   |
|-------------------|
| **Error description** |
| Long range for non Mellanox cable or module |
| Enforce part number list |
| PMD type not enabled |
| PCIE system power slot exceeded |

#### CLI

##### show interface transceiver error-status

The command `show interface transceiver error-status` is designed to fetch and display the error status of the SFP modules. It is implemented by calling the platform API.

```
sonic#show interface transceiver error-status <--read-from-db> <port>
```

If the parameter `port` is provided, the command will display the error status of the port. Otherwise, it will display the error status of all the ports.

```
admin@sonic:~$ show interface transceiver error-status Ethernet8
Port       Error Status
---------  ------------------------------------
Ethernet8  OK

admin@sonic:~$ show interface transceiver error-status
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
Ethernet44   Power budget exceeded
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
Ethernet168  Unplugged
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
###### Fetch error status from low level directly

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

N/A

### Testing Requirements/Design

#### Unit Test cases

1. Verify for each error code fetched from the SDK API, the platform API returns the correct description of the error

#### System Test cases

N/A
### Open/Action items

NOTE: All the sections and sub-sections given above are mandatory in the design document. Users can add additional sections/sub-sections if required.
#### Proposal for the second phase: fetch the error status from the database

The error status of each xSFP module have been stored into TRANSCEIVER_STATUS table as a bitmap by `xcvrd`. Each bit stands for an error code.
To support fetching the error status from the database, we need to:

1. Extend the error codes exposed to `xcvrd` from platform API. Currently, only the errors that can block the xSFP's EEPROM from being read are exposed to the `xcvrd`. We need to expose all the error codes instead.
2. Split the error bit definition to two parts: the generic error shared among all vendors and the vendor specific errors.
   Currently, all error bits are treated as generic. As we have vendor specific errors, we have to define error bits for vendor specific errors as well.
   Assume the error bitmap is a 64-bit word, one solution is to define the lower part (bit 0 ~ bit 31) as generic errors and upper part (bit 32 ~ bit 63) as vendor specific errors. The bit 0 is the least significant bit.
3. The error bitmap definition should be moved from `xcvrd` to `sonic-platform-common`.
4. A new platform API should be introduced to map the vendor specific error bit to the error description.
