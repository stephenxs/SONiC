# Shared headroom pool design

## Table of Content

### Revision

### Scope

This section describes the scope of this high-level design document in SONiC.

### Definitions/Abbreviations

This section covers the abbreviation if any, used in this high-level design document and its definitions.

### Overview

Currently, the dedicated memory are reserved as headroom for all PGs and can not shared by other traffic. Only all PGs suffer congestion at the same time can all the headroom buffer be occupied. However, this situation can hardly happen, which means all buffer is not used.

The shared headroom pool is introduced to reduce the total memory occupied by headroom and thus enlarging the size of shared buffer pool.

Currently, the shared buffer pool is calculated by subtracting reserved buffer of the following parts from the total available memory:

- reserved buffer for each port on ingress and egress side.
- reserved buffer for each PG, including xon and xoff. So it can be divided into two parts:
  - reserved buffer for xon of all PGs
  - reserved buffer for xoff of all PGs
- reserved buffer for each queue.
- reserved buffer for system, eg. management pool.

In the shared headroom pool solution, the xoff buffer will no longer be reserved for each PG.

In Mellanox's platform, a dedicated shared headroom pool will be introduced for xoff buffer. The size of this pool is reflected by `BUFFER_POOL|ingress_lossless_pool.xoff` and will be passed to SAI through `SAI_BUFFER_POOL_ATTR_XOFF_SIZE` attribute in `set_buffer_pool_attribute` API. The size can be determined in the following ways:

- the over-subscribe ratio approach: the accumulative sizes of xoff for all PGs divided by over-subscribe ratio:
- the congesting probability approach:
  1. specify the probability of congestion for each lossless buffer profile
  2. put the product of all PGs together
- the congesting factor approach: the congesting factor represents how many ports can suffer congestion at the same time at most.

All the ways are configurable. The shared headroom pool won't be enabled if none of the configuration provided.

We will detail these ways in the following chapters.

Comparison of reserved buffers before and after shared headroom pool:

| Current solution | Shared headroom pool |
|:--------:|:-----------:|:---------------:|
|reserved buffer for each port on ingress and egress side|the same|
|reserved buffer for each PG, including xon and xoff|for each PG, including xon only|
|reserved buffer for each queue|the same|
|reserved buffer for the system|the same|

### Requirements

We have the following requirements:

- Support shared headroom pool in systems without dynamic buffer
  - As in this systems all the buffer parameters are statically configured, we need to provide additional parameters for shared headroom pool.
  - No new database items or CLI introduced.
- Support shared headroom pool in systems with dynamic buffer
  - Different way in which the shared headroom pool size is calculated should be provided and configurable, including:
    - the Over-subscribe ratio
    - congesting probability
  - The shared headroom pool size should be updated whenever the headroom of a port is updated

### Architecture Design

N/A.

### High-Level Design

All the buffer configuration is statically calculated and deployed through `CONFIG_DB` without dynamic buffer and there isn't any change regarding the flows. So in this sector we will focus on supporting shared headroom pool on top of dynamic buffer calculation except it is explicitly specified.

#### Config DB Enhancements

##### Table LOSSLESS_TRAFFIC_PATTERN

This table contains the parameters related to lossless traffic configuration. The table has existed in dynamic buffer calculation mode. In this design the `over_subscribe_ratio` is introduced.

###### schema

```schema
    key                     = LOSSLESS_TRAFFIC_PATTERN|<name>   ; Name should be in captical letters. For example, "AZURE"
    mtu                     = 1*4DIGIT      ; Mandatory. Max transmit unit of packet of lossless traffic, like RDMA packet, in unit of kBytes.
    small_packet_percentage = 1*3DIGIT      ; Mandatory. The percentage of small packets against all packets.
    over_subscribe_ratio    = 1*3DIGIT      ; Optional. The over subscribe ratio for shared headroom pool. The default value is 1.
```

This table can't be updated on-the-fly. Reloading configuration is required.

###### Initialization

Typically all vendors share the identical default RoCE parameters. It should be stored in `/usr/share/sonic/templates/buffers_config.j2` which will be used to render the buffer configuration by `config qos reload`.

***Example***

```json
    "LOSSLESS_TRAFFIC_PATTERN": {
        "AZURE": {
            "mtu": "1500",
            "small_packet_percentage": "100",
            "over_subscribe_ratio": "8"
        }
    }
```

#### Algorithm update

We will describe the algorithms via which the headroom information, size of shared buffer pool and size of shared headroom pool is calculated.

##### headroom calculating

###### dynamic headroom calculating

In the dynamic headroom calculating algorithm, the `xon`, `xoff` and `size` are calculated as usual. Originally the `size` equals `xon` + `xoff`. For supporting the shared headroom buffer, the `size` should be updated from `xon` + `xoff` to `xon`.

###### headroom override

For the headroom override mode, the `xon`, `xoff` and `size` are specified by user.

Originally, in the CLI:

- the `size` equals to `xon` + `xoff` if it is not specified. With the shared headroom supported, the `size` equals to `xon` by default. If `size` > `xon`, `size` - `xon` will be treated as `hysteresis`.
- the `xoff` equals to `size` - `xon` if it is not specified. With the shared headroom supported, the `xoff` must be provided.

##### shared headroom pool size calculating

A new parameter over-subscribe ratio is introduced into `CONFIG_DB` and can be configured through CLI.

Meanwhile, there has been an existing parameter `BUFFER_POOL|ingress_lossless_pool.xoff` which also represents the size of the shared headroom pool. In case both parameters are provided, the `BUFFER_POOL|ingress_lossless_pool.xoff` will take affect and the shared headroom pool size won't be calculated dynamically.

During database migrating, if the `BUFFER_POOL|ingress_lossless_pool.xoff` equals the default value (in the old image), it will be removed and replaced by over-subscribe ratio.

In case the shared headroom pool needs to be dynamically calculated, it is done in the following steps:

1. For each lossless PG:

   1. Fetch the profile referenced by the PG
   2. Fetch the `xoff` from the profile.

2. Put all the `xoff` together and divide the sum by over subscribe ratio.

The calculation is triggered every time a port's speed, cable length or MTU is updated or a port is shutdown or startup. These trigger points are exactly the same as those trigger shared buffer pool size calculation.

##### buffer pool size calculating

No update for buffer pool size calculating because:

- the buffer pool is calculated based on the `size` of profiles
- the `size` of ingress lossless profiles have been updated to reflect shared headroom pool, but the logic of calculating the buffer pool isn't changed.

### Upgrading from old version via using db_migrator

To support shared headroom pool means we will have different buffer configuration from the current one, which means a new db_version needs to be introduced.

Currently we have the following config_db versions:

- `v1.0.4`, represents the latest configuration on 201911 and master.
- `v2.0.0`, represents the configuration for dynamic buffer calculation mode, which is only supported on master.

We are going to support shared headroom pool in 201911 which means a new version needs to be inserted between the current version `1.0.4` and `2.0.0`, which is `1.0.5`.

The upgrading flow from `v1.0.4` to `v1.0.5` and from `v1.0.5` to `v2.0.0` also need to be handled.

For the upgrading flow from `v1.0.4` to `v1.0.5`, the logic is if all the buffer configuration aligns with the default value, the system will adjust the buffer configuration with the shared headroom pool supported.

For the upgrading flow from `v1.0.5` to `v2.0.0`, the logic is if all the buffer configuration aligns with the default value, the system will adjust the buffer configuration to the dynamic calculation one.

#### Upgrading from 201811 to 201911

A PoC script in which the ASIC registers are directly programmed without calling SDK/SAI to implement shared headroom pool can have been deployed on switches running 201811. At the time this kind of switches are updated from 201811 to 201911, the shared headroom pool should have been the default configuration. In this sense, the db_migrator will upgrade the configuration to the 201911 default one which includes the shared headroom pool support. The script just needs to update the buffer configuration to the single ingress pool one.

However, if the default buffer configuration in 201911 doesn't support the shared headroom pool, the script needs to do the following steps:

- update the buffer configuration from 201911 default to the one with shared headroom pool supported, which includes the following adjustment
- merge two ingress pools into one

### SAI API

No new SAI API or attribute is introduced.

### Configuration and management

#### CLI Enhancements

##### To configure over-subscribe ratio

The command `config buffer shared-headroom-pool over-subscribe-ratio` is introduced for configuring the over-subscribe ratio.

```cli
sonic#config buffer shared-headroom-pool over-subscribe-ratio <over-subscribe-ratio>
```

By default, the over-subscribe-ratio should be 2.

To configure it as 0 means disable shared headroom pool.

##### To configure the shared headroom pool size

The command `config buffer shared-headroom-pool size` is introduced for configuring the size of shared-headroom pool.

```cli
sonic#config buffer shared-headroom-pool size <size>
```

### Warmboot and Fastboot Design Impact

No extra flow required for warm reboot/fast reboot.

### Restrictions/Limitations

### Testing Requirements/Design

#### Unit Test cases

TBD.

#### System Test cases

TBD.

#### RPC test cases

There is already a test case in the qos test for the shared headroom pool. The flow:

1. fill the shared buffer and the xon part of each PG under testing by sending trig_pfc packets to each PG
2. trigger PFC for each PG under testing by sending less than 10 packet to each PG
3. fill the PG headroom pool by sending pkts_num_hdrm_partial packets to each PG
4. send one more packet to trigger the ingress drop to the last PG

### Open/Action items - if any

1. In case configuration for different approaches of calculating the shared headroom pool is provided, which approach should be chozen?
2. What's the expected behavior of the congesting factor approach? Should we support it?

  - which ports should we choose to calculate the shared headroom pool size?
  - do we need to sort them? based on xoff?
  - is it necessary to configure it based on peer device? (switch or NIC)
