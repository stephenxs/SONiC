# Reclaim reserved buffer #

## Table of Content ###

### Revision ###

### Scope ###

This section describes the scope of this high-level design document in SONiC.

### Definitions/Abbreviations ###

This section covers the abbreviation if any, used in this high-level design document and its definitions.

### Overview ###

Shared buffer is used to absorb traffic when a switch is under congestion. The larger the buffer, the better the performance in terms of congestion handling.

On Mellanox platforms, buffers are reserved for each port, PG and queue. The size of shared buffer pool is equal to the total memory minus the accumulative reserved buffers. So we would like to reduce the reserved buffer as many as possible. One way to do that is to reclaim the buffers reserved for admin down ports.

There are some admin down ports in user's scenario. There should not be any buffer reserved for admin down ports but currently there are by default.

The purpose of this document is to provide a way to reclaim the buffer reserved for admin down ports and then increase the shared buffer pool size.

### Requirements ###

The requirement is to reclaim the reserved buffer for admin down ports, including:

- Reserved by applying configuration by SONiC
  - BUFFER_PG
  - BUFFER_QUEUE
  - BUFFER_PORT_INGRESS_PROFILE_LIST / BUFFER_PORT_EGRESS_PROFILE_LIST
- Reserved by SDK/SAI, out of scope of this design
  - management PG when the port is shutdown
  - If the SONiC configures buffer pools
    - The default lossy priority group configured by SDK
    - The reserved buffer in the port buffer pool
    - The reserved buffer in the queues configured by SDK (queue 8 ~ 15)

### Architecture Design ###

The SONiC will destroy the related priority groups, queues and port ingress / egress buffer profile lists for admin down ports. It will call related SAI API with `SAI_NULL_OBJECT_ID` as SAI OID. The SAI will set the reserved buffer of the objects to zero.

### High-Level Design ###

#### Static buffer model ####

##### Buffer manager to Remove lossless PGs on admin down port #####

Currently, the lossless PGs are configured by default in static buffer model, which needs to be avoided.

There are two options to address that.

1. 0m-cable approach

   The user to configure cable length as `0m`, indicating there should not be any buffer usage on the port.
   `buffermgr` doesn't generate lossless PGs on such port

   - pros
     - Least code change
   - cons
     - Currently, `buffermgr` only records the cable length when it's changed. It depends on reloading configuration to make the change take effect.
2. Handle port admin state

   The user doesn't need to take any specific action.
   `buffermgr` to handle port admin state change:
   - to remove lossless PGs configured on a port if its admin state is down
   - to configure lossless PGs on a port if its admin state is up

   - pros
     - No action for user
     - Admin down state is completely handled. No need to reload configuration.

The 2nd option is preferred. Originally, we had decided to use a zero buffer profile to reclaim the reserved buffer for admin down ports. To be consistent, we introduced 0m-cable to indicate a zero buffer profile. Later on, we realized that the zero buffer profile didn't really work and decided to use `SAI_NULL_OBJECT_ID` to reclaim the reserved buffer. The 0m-cable won't be consistent with the rest part any more.

##### The script to update shared buffer pool size ###

This script is to add the reclaimed buffer for admin down ports back to the shared buffer pool.

It will be invoked in the following scenarios:

- Adjust the shared buffer pool and shared headroom pool on the fly after the ports have been admin down
- Adjust the shared buffer pool and shared headroom pool in `db_migrator` for comparing with the default buffer configurations against the current value.

Its flow is like this:

1. Fetch the default shared buffer pool sizes from the buffer templates according to the `SKU` and `topology`.
2. For each admin down ports
   1. Fetch its speed and cable length
   2. Calculate the PG size, xoff size.
3. Put the `size`s of all PGs together, getting the accumulative size
4. Put the `xoff`s of all PGs together, getting the accumulative xoff
5. Calculate the accumulative private headroom for preserved buffer
   - `10 kB` * `number of admin-down ports`
6. Calculate other per port reserved buffer
   - egress reserved buffer as `egress_lossy_profile.size` * `number of admin-down ports`
   - reserved headroom for mirror as `10 kB` * `number of admin-down ports`
7. Add `accumulative size` + (`accumulative xoff` - `accumulative private headroom`) / 2 + `per port egress reserved` to the shared buffer pool
8. Subtract `accumulative xoff` / 2 from the shared headroom pool size

Open questions:

1. Should this script be run by user or automatically?
   Prefer to being run by user because sometimes the user can shutdown a port for a short-term maintainance. In this case, the user probably doesn't want to reclaim the reserved buffer.

##### db_migrator #####

There is a logic in `Mellanox buffer migrator`: only the buffer configuration matches the default value in old image will it be migrated to the default value in new images.
If the reserved buffer of admin down ports are reclaimed, the buffer configuration won't match the default one, which means the buffer configuration won't be migrated.
This can be avoided by subtracting the reclaimed buffer to shared buffer pool size when comparing. The flow is like this:

1. For each flavor in default configurations in the old version
   - Adjust the shared buffer pool size and shared headroom pool size in the default configuration
   - Compare it with the current buffer configuration in the switch
   - if they matches
     - record the `current flavor`
     - break the iteration
2. Stop the flow if none of the adjusted default configuration matches the current configuration
3. Pick the default configuration of the `current flavor`
4. Adjust the sharred buffer pool size and shared headroom pool size according to the number of admin down ports
5. Apply the adjusted buffer configurations

Open question

1. Should we migrate the buffer pool size to the one with reserved buffer for admin-down ports' reclaimed? Don't preper to doing so.

### SAI API ###

#### Reclaim priority groups ####

The SAI API `sai_buffer_api->set_ingress_priority_group_attribute` is used for reclaiming reservied buffer for priority groups. The arguments should be the following:

    attr.id = SAI_INGRESS_PRIORITY_GROUP_ATTR_BUFFER_PROFILE;
    attr.value.oid = SAI_NULL_OBJECT_ID;
    sai_buffer_api->set_ingress_priority_group_attribute(pg_id, &attr); // pg_id is the SAI object ID of the priority group

After this SAI API called, the reserved buffer of the priority group indicated by pg_id will be set to zero.

#### Reclaim queues ####

The SAI API `sai_queue_api->set_queue_attribute` is used for reclaiming reservied buffer for queues. The arguments should be the following:

    attr.id = SAI_QUEUE_ATTR_BUFFER_PROFILE_ID;
    attr.value.oid = SAI_NULL_OBJECT_ID;
    sai_queue_api->set_queue_attribute(queue_id, &attr); // queue_id is the SAI object ID of the queue

After this SAI API called, the reserved buffer of the queue indicated by pg_id will be set to zero.

#### Reclaim port reserved buffers ####

The SAI API `sai_port_api->set_port_attribute` is used for reclaiming reserved buffer for queues. The arguments should be the following:

    // Reclaim reserved buffer on ingress side
    attr.id = SAI_PORT_ATTR_QOS_INGRESS_BUFFER_PROFILE_LIST
    attr.value.objlist.count = 0;
    sai_port_api->set_port_attribute(port.m_port_id, &attr);

    // Reclaim reserved buffer on egress side
    attr.id = SAI_PORT_ATTR_QOS_EGRESS_BUFFER_PROFILE_LIST
    attr.value.objlist.count = 0;
    sai_port_api->set_port_attribute(port.m_port_id, &attr);

### Configuration and management ###

N/A

#### CLI/YANG model Enhancements ####

N/A

#### Config DB Enhancements ####

N/A

### Warmboot and Fastboot Design Impact ###

No impact on warm/fast boot.

### Restrictions/Limitations ###

N/A

### Testing Requirements/Design ###

#### Unit Test cases ####

#### System Test cases ####

### Open/Action items - if any ###
