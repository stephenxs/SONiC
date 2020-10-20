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

In Mellanox's platform, a dedicated shared headroom pool will be introduced for xoff buffer with the quantity the accumulative sizes of xoff for all PGs divided by over-subscribe ratio as its size. The size of this pool is reflected by `BUFFER_POOL|ingress_lossless_pool.xoff`.

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
  - The shared headroom pool should be updated whenever the headroom of a port is updated
  - Over-subscribe ratio should be configurable

### Architecture Design

N/A.

### High-Level Design

#### Support headroom pool without dynamic buffer

All the buffer configuration is statically calculated and deployed through `CONFIG_DB`.

#### Support headroom pool on top of dynamic buffer calculation

##### Trigger shared headroom pool to be updated

The shared headroom pool should be updated whenever the headroom of a port is updated, including:

- A port's speed, cable length or MTU is updated.
- The lossless priority groups of a port is updated, a new one added or an old one removed.
- A port is shutdown/start up

These are exactly the same trigger points as those triggering update buffer pool size.

##### Algorithm update

###### headroom calculating

In the headroom calculation algorithm, the xon, xoff and size is calculated. Originally the `size` equals `xon` + `xoff`. For supporting the shared headroom buffer, the `size` should be updated from `xon` + `xoff` to `xon`.

###### shared headroom pool size calculating

1. Fetch the `xoff` of all the PGs.
2. Put them together and divide the sum by over subscribe ratio.

###### buffer pool size calculating

No update for buffer pool size calculating because

- the buffer pool is calculated based on the `size` of profiles
- the `size` of ingress lossless profiles have been updated to reflect shared headroom pool, but the logic of calculating the buffer pool isn't changed.

#### Upgrading from old version via using db_migrator

To support shared headroom pool means we will have different buffer configuration from the current one, which means a new db_version needs to be introduced.

However, this is a bit complicatd. Currently we have the following config_db versions:

- `v1.0.4`, represents the latest configuration on 201911 and master.
- `v1.0.5`, represents the configuration for dynamic buffer calculation mode, which is only supported on master.

We are going to support shared headroom pool in 201911 which means a new version needs to be inserted between `v1.0.4` and `v1.0.5`, like `v1.0.4.1`.

The upgrading flow from `v1.0.4` to `v1.0.4.1` and from `v1.0.4.1` to `v1.0.5` also need to be handled.

For the upgrading flow from `v1.0.4` to `v1.0.4.1`, the logic is if all the buffer configuration aligns with the default value, the system will adjust the buffer configuration with the shared headroom pool supported.

For the upgrading flow from `v1.0.4.1` to `v1.0.5`, the logic is if all the buffer configuration aligns with the default value, the system will adjust the buffer configuration to the dynamic calculation one.

#### Upgrading from old version via using script

Some customers, like Microsoft, doesn't deploy the default configuration in their production switches. In this case, the db_migrator won't migrate configuration. Dedicated script needs to be provided for each of the upgrading scenarios.

Currently, the script only includes the steps which merge two ingress pool into one.

##### Upgrading from 201811 to 201911

A PoC script in which the ASIC registers are directly programmed without calling SDK/SAI to implement shared headroom pool can have been deployed on switches running 201811. At the time this kind of switches are updated from 201811 to 201911, the shared headroom pool should have been the default configuration. In this sense, the db_migrator will upgrade the configuration to the 201911 default one which includes the shared headroom pool support. The script just needs to update the buffer configuration to the single ingress pool one.

However, if the default buffer configuration in 201911 doesn't support the shared headroom pool, the script needs to do the following steps:

- update the buffer configuration from 201911 default to the one with shared headroom pool supported, which includes the following adjustment
- merge two ingress pools into one

### SAI API

N/A.

### Configuration and management

#### CLI Enhancements

##### To configure over-subscribe ratio

The command `config buffer shared-headroom-pool over-subscribe-ratio` is introduced for configuring the over-subscribe ratio.

```cli
sonic#config buffer shared-headroom-pool over-subscribe-ratio <over-subscribe-ratio>
```

By default, the over-subscribe-ratio should be 2.

To configure it as 0 means disable shared headroom pool.

#### Config DB Enhancements

N/A.

### Warmboot and Fastboot Design Impact

N/A.

### Restrictions/Limitations

### Testing Requirements/Design

Explain what kind of unit testing, system testing, regression testing, warmboot/fastboot testing, etc.,
Ensure that the existing warmboot/fastboot requirements are met. For example, if the current warmboot feature expects maximum of 1 second or zero second data disruption, the same should be met even after the new feature/enhancement is implemented. Explain the same here.
Example sub-sections for unit test cases and system test cases are given below.

#### Unit Test cases  

#### System Test cases

### Open/Action items - if any
