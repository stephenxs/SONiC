#Test name

#SONiC Test Plan




<span id="_Toc205800613" class="anchor"><span id="_Toc463421032" class="anchor"><span id="_Toc463514628" class="anchor"></span></span></span>**Related documents**

|                   |          |
|-------------------|----------|
| **Document Name** | **Link** |
| Fetch SFP error status through CLI on Mellanox platform |          |
|                   |          |
|                   |          |

## Overview

This is the test plan for the feature `fetch SFP error status through CLI`. This feature is available on Mellnox platform only.

The feature is implemented in the following way:

- A new platform API is introduced to fetch the error status by calling the SDK API.
- A CLI command is introduced to call the platform API and display the error status to end user.

### Scope

---------

The purpose of test cases is to verify the feature works as expected. It is achieved by mocking the returned value of the SDK API and verifying the CLI output accordingly.

### Scale / Performance

---------

N/A

### Related **DUT** CLI commands

---------

| **Command**                                                      | **Comment** |
|------------------------------------------------------------------|-------------|
| **Configuration commands**                                       |
| N/A |             |
| **Show commands**                                                |
| show platform mlnx transceiver error-status | To display the error status of all transceivers or a certain transceiver according to the input argument |

### Related DUT configuration files

---------

N/A

### Related SAI APIs

---------

N/A

## Test structure

===============

### Setup configuration

---------

SONiC community setup

### Configuration scripts

---------

N/A

### Test cases

---------

### Test case \#1

To verify whether the `show platform mlnx transceiver error-status` displays `OK` for all SFP modules.

Test description

| **\#** | **Test Description** | **Expected Result** |
|--------|----------------------|---------------------|
| 3.     | Run `show platform mlnx transceiver error-status` and check whether error descriptions displayed by the command are `OK` for all SFP modules. | All descriptions should be `OK` |
