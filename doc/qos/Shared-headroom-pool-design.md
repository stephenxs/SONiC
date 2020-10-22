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

In Mellanox's platform, a dedicated shared headroom pool will be introduced for xoff buffer. The size of this pool is reflected by `BUFFER_POOL|ingress_lossless_pool.xoff` and will be passed to SAI through `SAI_BUFFER_POOL_ATTR_XOFF_SIZE` attribute in `set_buffer_pool_attribute` API. The size can be calculated in the following ways:

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

#### Table LOSSLESS_TRAFFIC_PATTERN

This table contains the parameters related to lossless traffic configuration. The table has existed in dynamic buffer calculation mode. In this design the `over_subscribe_ratio` and `congesting_probability` are introduced.

##### schema

```schema
    key                     = LOSSLESS_TRAFFIC_PATTERN|<name>   ; Name should be in captical letters. For example, "AZURE"
    mtu                     = 1*4DIGIT      ; Mandatory. Max transmit unit of packet of lossless traffic, like RDMA packet, in unit of kBytes.
    small_packet_percentage = 1*3DIGIT      ; Mandatory. The percentage of small packets against all packets.
    over_subscribe_ratio    = 1*3DIGIT      ; Optional. The over subscribe ratio for shared headroom pool. The default value is 1.
    congesting_probability  = 1*3DIGIT      ; Optional. The default probability of congestion of a buffer profile in percentage. The default value is 100.
```

##### Initialization

Typically all vendors share the identical default RoCE parameters. It should be stored in `/usr/share/sonic/templates/buffers_config.j2` which will be used to render the buffer configuration by `config qos reload`.

***Example***

```json
    "LOSSLESS_TRAFFIC_PATTERN": {
        "AZURE": {
            "mtu": "1500",
            "small_packet_percentage": "100",
            "over_subscribe_ratio": "8",
            "congesting_probability": "25"
        }
    }
```

#### BUFFER_PROFILE

Table `BUFFER_PROFILE` contains the profiles of headroom parameters and the proportion of free shared buffers can be utilized by a `port`, `PG` tuple on ingress side or a `port`, `queue` tuple on egress side.

##### Schema

Currently, there already are some fields in `BUFFER_PROFILE` table. In this design, the field `congesting_probability` is newly introduced, indicating the probability at which the PG using this profile suffers a congestion.

```schema
    key             = BUFFER_PROFILE|<name>
    pool            = reference to BUFFER_POOL object
    xon             = 1*6DIGIT      ; xon threshold
    xon_offset      = 1*6DIGIT      ; xon offset
                                    ; With this field provided, the XON packet for a PG will be generated when the memory consumed
                                    ; by the PG drops to pool size - xon_offset or xon, which is larger.
    xoff            = 1*6DIGIT      ; xoff threshold
    size            = 1*6DIGIT      ; size of reserved buffer for ingress lossless
    dynamic_th      = 1*2DIGIT      ; for dynamic pools, proportion of free pool the port, PG tuple referencing this profile can occupy
    static_th       = 1*10DIGIT     ; similar to dynamic_th but for static pools and in unit of bytes
    headroom_type   = "static" / "dynamic"
                                    ; Optional. Whether the profile is dynamically calculated or user configured.
                                    ; Default value is "static"
    congesting_probability = 1*3DIGIT;  Optional. The probability at which the PG using this profile suffers a congestion.
```

##### Initialization

The profile is configured by CLI.

***Example***

An example of mandatory entries on Mellanox platform:

```json
    "BUFFER_PROFILE": {
        "non-default-congesting-probability": {
            "pool": "[BUFFER_POOL|ingress_lossless_pool]",
            "headroom_type": "dynamic",
            "congesting_probability": "25"
        },
        "non-default-cong-prob-override": {
            "pool": "[BUFFER_POOL|ingress_lossy_pool]",
            "xon": "19456",
            "xoff": "31744",
            "size": "19456",
            "dynamic_th": "0",
            "congesting_probability": "25"
        }
    }
```

The `non-default-congesting-probability` is a buffer profile configured with congesting probability for dynamic calculating headroom. If this profile is configured on a port whose speed and cable length are 100G and 5m respectively, the a dynamic buffer profile `pg_lossless_100000_5m_cog25_profile` will be inserted to `APPL_DB.BUFFER_PROFILE_TABLE`.

The `non-default-cong-prob-override` is a buffer profile configured with congesting probability for headroom override.

#### Different approaches to calculating the shared headroom pool size

##### Over-subscribe ratio

A new parameter over-subscribe ratio is introduced into `CONFIG_DB` and can be configured through CLI.

The headroom pool size is calculated in the following steps:

1. For each lossless PG:

   1. Fetch the profile referenced by the PG
   2. Fetch the `xoff` from the profile.

2. Put all the `xoff` together and divide the sum by over subscribe ratio.

The calculation is triggered every time a port's speed, cable length or MTU is updated or a port is shutdown or startup. These trigger points are exactly the same as those trigger shared buffer pool size calculation.

##### Congesting probability

The probability of congestion will be introduced in this approach, representing the probability at which a port can suffer a congestion. The shared headroom pool is calculated by multiplying the accumulative xoff and the congestion probability for each port and then putting them together.

In general, the probability is determined by the peer devices the ports connected to, like the servers or peer switches. In this sense, it's possible to share the probability among physical ports and to define the probability on a per buffer profile basis. A global congesting probability can also be introduced. The priority is:

- use profiles' congesting probability if it is defined
- use global congesting probability otherwise
- treat the congesting probability as 100% if it isn't defined neither in the profile nor global

The shared headroom pool size can be calculated in the following steps:

1. For each lossless `PG`, multiply the `xoff` and the `congesting probability`
2. Put all the product together

The trigger points of the calculation are the same as those in the over-subscribe-ratio approach.

###### Dynamically create buffer profiles for lossless traffic with non-default congesting probability

According to dynamic buffer calculation design, a new lossless buffer profile should be created every time a new tuple of speed, cable length, MTU and dynamic_th appears.

Now the congesting probability should also be taken into consideration when creating a new or reusing an existing buffer profile, which means a new lossless buffer profile should be created every time a new tuple of speed, cable length, MTU, dynamic_th and congesting probability appears.

The name convention of dynamically generated buffer profile should be: `pg_lossless_<speed>_<cable-length>_<mtu>_th<dynamic_th>_cog<congesting-probability>`, in which:

- the `speed` and `cable-length` are madantory
- the `mtu`, `dynamic th` and `congesting-probability` are optional and exist only if the non-default value is configured for the profile.

#### Algorithm update

We will describe the algorithms via which the headroom information, size of shared buffer pool and size of shared headroom pool is calculated.

##### headroom calculating

In the headroom calculation algorithm, the xon, xoff and size is calculated. Originally the `size` equals `xon` + `xoff`. For supporting the shared headroom buffer, the `size` should be updated from `xon` + `xoff` to `xon`.

##### shared headroom pool size calculating

The algorithms via which the shared headroom pool size is calculated have been described in the sector "Different approaches to calculating the shared headroom pool size".

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

##### To configure the global congesting probability

The command `config buffer shared-headroom-pool congesting-probability` is introduced for configuring the global congesting probability.

```cli
sonic#config buffer shared-headroom-pool congesting-probability <probability>
```

The default value of probability is 100%. To set it to 100% will remove the configuration.

##### To configure a profile's congesting probability

The command `config buffer profile` is introduced for configuring the congesting probability of a profile. This command has already existed in dynamic buffer calculation mode. In this design we will add the argument for congesting probability.

```cli
sonic#config buffer_profile add <name> --xon <xon> --xoff <xoff> --headroom <headroom> --dynamic_th <dynamic_th> --congesting-probability <probability>
sonic#config buffer_profile set <name> --xon <xon> --xoff <xoff> --headroom <headroom> --dynamic_th <dynamic_th> --congesting-probability <probability>
sonic#config buffer_profile remove <name>
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
