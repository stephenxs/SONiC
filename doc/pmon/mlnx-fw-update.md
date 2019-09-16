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
  - including CPLDs running on both CPU side and board.
- ASIC Firmware
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
Firmware is updated via different way for variant components in the following two aspects:
- each component has their own command to install/update firmware
- reboot is required for some components to complete installation while it's not for others
To achieve that a subclass derived from ComponentBase is defined for each type of components.
#### sonic_platform.chassis_base.ChassisBase
The following APIs defined in sonic_platform/chassis_base.py should be implemented:
- get_name which gets the name of the chassis.
  - SKU+" Chassis" is returned for now. For example, on 2700 it returns "2700 Chassis"
- get_component_name_list which returns the list containing names of all the components in the chassis.
- get_firmware_version which returns the version of the firmware running in the given component.
### Install/Update firmware for variant components
In nutshell, the logic of installing/updating firmwares is to wrap the steps in which they are done manually.
If a component's firmware can be updated in multiple ways, the way used in platform api is chosen according to the following criteria:
1. The most stable way is chosen.
2. If multiple ways have similar stabilities, the most efficient way is chosen.
3. If multiple ways have similar stabilities and efficiency, the most convenient way is chosen.

Generally speaking, we have two categories of way in which firmware can be updated:
1. to use tools customized for the firmware.
2. to use firmware update script which gets firmware image prepared, and then triggers the switch to reboot to ONIE and finally notifies the ONIE to do the real work of updating firmware.

#### Install/Update ASIC firmware
The flow of manually updating ASIC firmware is like the following:

1. Fetch the PCI Device Name of the ASIC via using mlxfwmanager
    ```
    Device Type: Spectrum2
    Part Number: MSN3700-VxxxO_Ax
    Description: Spectrum(TM)-2 based 200GbE 1U Open Switch bare metal switch with ONIE boot loader only; 32 QSFP28 ports; 2 Power Supplies (AC); Standard depth; x86 CPU; RoHS6
    PSID: MT_0000000201
    PCI Device Name: /dev/mst/mt53100_pci_cr0
    Base MAC: b8599fa68200
    Versions: Current Available
    FW 29.2000.0190 N/A

    Status: No matching image found
    ```
2. Extract PCI Device Name from the output, which is the content following "PCI Device Name".
3. Copy the correct FW to target, which is done by another API.
4. Update FW, via the following command:
    ```
    mlxfwmanager -d /dev/mst/mt53100_pciconf0 -u -f -i /tmp/fw-SPC2-rel-29_2000_0960
    ```
5. If it fails, then try using non failsafe burn flow:
    ```
    mlxfwmanager -d /dev/mst/mt53100_pciconf0 -u -f --nofs -i /tmp/fw-SPC2-rel-29_2000_0960
    ```

#### Install/Update CPLD
There are multiple ways in which CPLD can be manually updated.
##### To update CPLD via cpldupdate
cpldupdate is a tool provided and customized for Mellanox by Lattice Semiconductor. It can be used to update CPLD in the following ways:

1. Update CPLD via firmware:
    ```
    cpldupdate --dev <device_name> <file1> <file2>
    ```
    The device_name is file name of the mst device, typically the file in /dev/mst/mtxxxx_pciconf0
    The file1 and file2 are CPLD image files.
2. Update CPLD via GPIO:
    ```
    cpldupdate --gpio <file1> <file2>
    ```
3. Update CPLD via lid-<n> device:
    ```
    cpldupdate --dev lid-<n> <file1> <file2>
    ```

#### Install/Update BIOS, ONIE and CPLD via onie_fw_update
The tool used to update BIOS can not be provided in SONiC due to license restriction. onie_fw_update is provided to address the restriction. It works following the below steps:
1. onie_fw_update add <file>, which add the file into its list pending to be updated. file must be a valid ONIE firmware.
2. onie_fw_update update, which reboots the switch to ONIE and update firmware previously added, thus the updating procedure being done.

### Open questions
- cpld update
1. We have two ways to update cpld, cpldupdate and onie-fw-update. Which way is preferred?
2. What do file1 and file2 stand for? Images for each CPLD? Is it necessary to provide both file1 and file2 when update? Can one of them be updated independently?

- ASIC firmware
Open questions to be discussed with team & ll team:
1. What's the difference between "non failsafe burn flow" and the normal flow?
2. Should we try non failsafe burn flow if the normal flow fails or use non failfsafe burn flow directly?
3. Is the only device file having the name convention of "/dev/mst/mt[0-9]{5}_pciconf0" the one that should be fet mlxfwmanager with when updating ASIC firmware?
4. I faced the error "Device #1: Error - no matching image found" when trying updating ASIC firmware.

