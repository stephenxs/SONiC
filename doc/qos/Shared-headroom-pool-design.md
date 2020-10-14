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
|reserved for each port on ingress and egress side|not changed|
|reserved for each PG, including xon and xoff|for each PG, including xon only|
||shared headroom pool|
|reserved for each queue|not changed|
|reserved for the system|not changed|

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
- the `size` of ingress lossless profiles have updated to reflect shared headroom pool, but the logic of calculating the buffer pool isn't changed.

#### Upgrading flows

##### Upgrading from 201911 to 202012 with dynamic buffer calculation

##### Upgrading from 201911 to 202012 without dynamic buffer calculation

##### Upgrading from 201811 to 201911

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