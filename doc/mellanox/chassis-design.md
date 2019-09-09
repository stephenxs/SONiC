Terms:
NPAPI: new platform API

According to the NPAPI design document:
- It's CLI's responsibility to determine whether to use the data in database or trigger daemons to retrieve data (via NPAPI).
- It's daemons' responsibility to invoke the APIs and update database correspondingly.
- It’s APIs’ responsibility to invoke vendor-specific interfaces provided by low-level to retrieve related data.
This series of NPAPIs are defined in sonic-platform-common/sonic_platform_base. Vendors can have their specific implementation by deriving classes based on them, which is the only way to handle vendor-specific details. CLI and daemons should be vendor independent. Since daemons have already contained the logic of saving info to database, which also provide caching abilities, NPAPIs can chose to implement the further cache facilities or not.

Currently there are following data that should be returned by chassis API:
1. Data stored in eeprom, including mac, serial number, and a dictionary containing OCP ONIE TlvInfo EEPROM. 
    1. Currently two common classes have been implemented to represent vendor-independent logic like EEPROM reading, caching and parsing.
    2. A class derived from TlvInfoDecoder should be introduced in order to encapsulates mlnx specific details, including: the path of the symbol link point to the real eeprom file in sysfs.
    3. All required info are stored in private members of the above-mentioned derived class in order to avoid reading and parsing EEPROM every time when API is invoked. This is feasible since data in EEPROM data can not be changed. (However, if online reprogramming EEPROM is supported, this part should be removed.)
2. Reboot cause can be retrieved by reading file /host/reboot-cause/previous-reboot-cause.txt and parsing to align with the format defined in base class. Currently only causes like “reboot”, “fast reboot” are supported.
3. Versions of components, including BIOS, CPLD and firmware. Related mechanism will be covered in the next section.
4. sfps, fans and psus related data will be (have been) designed and implemented independently and discussion of them is out of the scope of this design.

Retrieving versions of components
As all vendors have their specific way to access their device like BIOS, cpld and firmware, it is inevitable to install some vendor-specific tools into pmon docker. For Mellanox, the vendor-specific part includes at least mlxfwmanager for now. They are supposed to be put into $PMON_VENDOR_TOOLS which is defined as /usr/share/sonic/device/$SWITCH_TYPE for now.
1. CPLD version can be retrieved by reading files in /var/run/hw-management/system/cpld[1-2]_version which are accessible in pmon docker.
2. BIOS version can be read via dmidecode which is a common tool installed on host but not in pmon docker. 
    1. This tool has to be installed in the pmon docker so that bios version can be retrieved.
    2. It can be installed in the compiling stage by adding “dmidecode” in “Install required packages” section of Dockerfile.j2 of pmon docker.
    3. It is not installed into vendor-specific part of pmon, because it is a common tool and to get BIOS version via dmidecode is a common practice which can be shared by all vendors.
3. Firmware version can be retrieved by mlxfwmanager which is part of mft tools. It have to be installed into the docker when the docker is initializing for the first time, which is only a one-shot operation and doesn’t consume too much time when executing. To do it in this way is based on the following points(concerns):
    1. The .deb file containing it, which is mft-4.12.0-34-x86_64-deb, is too large (rough 61M) to fit in the docker so we have to pick the mlxfwmanager exactly out of the deb and install it only.
    2. In SONiC we don’t build mft tools from source code but download the .deb file directly, which make it impossible to write makefile rules to do what is required in a. What’s more, to install it at compiling time require detailed knowledge about how mft tools are organized, which introduces unnecessary and tighter dependencies.
    And it can be implemented in the following way:
    1. Expose the host dir $PMON_VENDOR_TOOLS to docker with the same path;
    2. Check whether mlxfwmanager has been copied into $PMON_VENDOR_TOOLS each time docker starts and copy if not. The full path name of mlxfwmanager has to be hardcoded in this script for now.

Misc:
1. Full path name of mlxfwmanager and files containing CPLD versions can differ in different SONiC releases. We have to trace it manually.
