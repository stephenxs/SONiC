# Mellanox firmware update platform api design
## Introduction
### Background
Mellanox firmware update new platform api is based on the new platform api defined by SONiC community. It is mainly implemented by wrapping the Mellanox's private firmware update tools.
### Requirements
#### Components whose firmware updating to be supported
Currently we're going to support the following components:
- BIOS
- ONIE
- CPLD
  - All CPLDs will be treated as one integrated component as a whole.
  - CPLD's version consists of version string of all CPLD devices in ascending order. For example, there are 3 CPLDs in the system and their version are `4`, `3`, `12` respectively, then the version of CPLD is `4.3.12`.
  - This is because the CPLD updating tool's working logic:
    - The only argument the tool accepts when updating CPLD is the image file.
    - The information of which CPLD to be updated is encoded in the CPLD file and no way for user to designate.
    - Hence the CPLD number information is hiden in the blackbox in terms of updating CPLDs.
#### Functionalities to be supported of each kind of firmware
- Get the name of a component
- Get the description of a component
- Get the current version of firmware running in a component
- Install/update the firmware of a component
### Restrictions
- BIOS update tool can on be provided in ONIE but not in SONiC due to license restriction. In such case, to install/update BIOS requires the system to be rebooted to ONIE.
- Currently no modular switch model is implemented by Mellanox. This part is omitted. 
## Design
### Summary
#### sonic_platform.component_base.ComponentBase
All of the APIs defined in sonic_platform/component_base.py should be implemented. Each ComponentBase object represents a certain component in Mellanox's switch system, including: CPLD, ASIC Firmware, BIOS and ONIE.
The following methods in ComponentBase should be implemented:
- get_name which gets the name of a component
- get_description which gets the human-readable description of a component
- get_firmware_version which gets the version of the current running firmware
- install_firmware which trigger the installation of a given firmware
  - Each component has its certain way to install/update its firmware. It will be elaborated in the following section.
  - The prototype of this method has to be changed from `boolean` to `boolean, str`. The added str value represents hints and output returned from low level tools.
Firmware is updated via different way for variant components in the following two aspects:
- each component has their own command to install/update firmware
- reboot is required for some components to complete installation while it's not for others
To achieve that a subclass derived from ComponentBase is defined for each type of components.
#### sonic_platform.chassis_base.ChassisBase
The following APIs defined in sonic_platform/chassis_base.py should be implemented:
- get_name which gets the name of the chassis.
  - SKU+" Chassis" is returned for now. For example, on 2700 it returns "2700 Chassis"
### Install/Update firmware for variant components
In nutshell, the logic of installing/updating firmwares is to wrap the steps in which they are done manually.
If a component's firmware can be updated in multiple ways, the way used in platform api is chosen according to the following criteria:
1. The most stable way is chosen.
2. If multiple ways have similar stabilities, the most efficient way is chosen.
3. If multiple ways have similar stabilities and efficiency, the most convenient way is chosen.

Generally speaking, we have two categories of way in which firmware can be updated:
1. to use tools dedicated for the firmware.
2. to use firmware update script which gets firmware image prepared, and then triggers the switch to reboot to ONIE and finally notifies the ONIE to do the real work of updating firmware.

#### Install/Update CPLD
There are multiple ways in which CPLD can be manually updated.
##### To update CPLD via cpldupdate
cpldupdate is a tool provided and customized for Mellanox by Lattice Semiconductor. It can be used to update CPLD in the following ways:

1. Update CPLD via firmware:
    ```
    cpldupdate --dev <device_name> <file1> <file2>
    ```
    This is the default mode which will check the device type, if it supports GPIO, then it will use GPIO, otherwise will use fw.
    The device_name is file name of the mst device, typically the file in /dev/mst/mtxxxx_pciconf0
    The file1 and file2 are CPLD image files.
2. Update CPLD via GPIO:
    ```
    cpldupdate --gpio <file1> <file2>
    ```
    To use GPIO anyway. No need to specify device.
3. Update CPLD via lid-<n> device:
    ```
    cpldupdate --dev lid-<n> <file1> <file2>
    ```
    To update GPIO via ASIC lid devices.

In platform API, to update CPLD will be preformed in the following approach:
1. Try to execute in the most preferred way
2. If failed, then try to execute in the 2nd preferred way
3. And so on.

#### Install/Update BIOS, ONIE and CPLD via onie_fw_update
The tool used to update BIOS can not be provided in SONiC due to license restriction. onie_fw_update is provided to address the restriction. It works following the below steps:
1. onie_fw_update add <file>, which add the file into its list pending to be updated. file must be a valid ONIE firmware.
2. onie_fw_update update, which reboots the switch to ONIE and update firmware previously added, thus the updating procedure being done.

### Open questions
#### cpld update
1. We have two ways to update cpld, cpldupdate and onie-fw-update. Which way is preferred?
2. What do file1 and file2 stand for? Images for each CPLD? Is it necessary to provide both file1 and file2 when update? Can one of them be updated independently?

#### ASIC firmware
Open questions to be discussed with team & ll team:
1. Is the only device file having the name convention of "/dev/mst/mt[0-9]{5}_pciconf0" the one that should be fet mlxfwmanager with when updating ASIC firmware?

#### To do list after discussed with team
1. in terms of cpld updating, which tool is faster and less likely to impact normal service?
    use burn image/power cycle to update cpld if it is supported on all of our platforms
    otherwise to use cpldupdate to update cpld

2. handle the case that sonic_install and onie_update interleaved, making sure that the image installed by sonic_install won't be overwritten by onie_update. consider the following sequence:
    current boot A
    sonic_install install some new firmware, next boot: newly installed image, B
    onie_fw_update update, next boot: onie.
    system boots to ONIE.
    updating jobs done in ONIE.
    system reboot to A or B?
    should we handle this kind of problem?

low level team questions
1. whether batch mode is supported by onie_update
2. whether cpld update tool is supported by all of the platforms
3. whether power cycle is supported on all of the platforms
