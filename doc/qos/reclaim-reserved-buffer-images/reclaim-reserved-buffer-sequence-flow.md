```mermaid
%Normal flow

sequenceDiagram
    participant User
    participant DATABASE
    participant buffer manager
    participant buffer orch
    participant SAI
    participant SDK
    User ->> DATABASE: Configure cable length and speed or admin-status
    DATABASE ->> buffer manager: Update notification
    alt port is admin down
    Note over DATABASE, buffer manager: (1) Don't create buffer PG if port is admin-down
    buffer manager ->> DATABASE: Finish (doing nothing)
    else port is admin up
    opt buffer profile doesn't exist?
    buffer manager ->> buffer manager: Fetch headroom parameter according to cable length/speed
    buffer manager ->> DATABASE: Create buffer profile and push into BUFFER_PROFILE
    DATABASE ->>+ buffer orch: Update notification
    buffer orch ->>+ SAI: sai_buffer_api->create_buffer_profile
    SAI ->>- buffer orch: Finish
    buffer orch ->>- DATABASE: Finish
    end
    buffer manager ->> DATABASE: Create buffer PG and push into BUFFER_PG for PG 3-4
    DATABASE ->>+ buffer orch: Update notification
    Note over buffer orch, SAI: attr.id = SAI_INGRESS_PRIORITY_GROUP_ATTR_BUFFER_PROFILE
    Note over buffer orch, SAI: attr.value.oid = OID of corresponding buffer profile;
    buffer orch ->>+ SAI: sai_buffer_api->set_ingress_priority_group_attribute
    SAI ->>+ SDK: Set parameters of PG 3, 4 according to buffer profile
    SDK ->>- SAI: Finish
    SAI ->>- buffer orch: Finish
    buffer orch ->>- DATABASE: Finish
    end
```

```mermaid
%Shutdown flow
sequenceDiagram
    participant User
    participant DATABASE
    participant buffer manager
    participant buffer orch
    participant SAI
    participant SDK
    User ->> DATABASE: Shutdown a port
    DATABASE ->> buffer manager: Update notification
    buffer manager ->> DATABASE: Remove the buffer PG 3-4
    DATABASE ->>+ buffer orch: Update notification
    loop for each priority-group in the list
    Note over buffer orch, SAI: attr.id = SAI_INGRESS_PRIORITY_GROUP_ATTR_BUFFER_PROFILE
    Note over buffer orch, SAI: attr.value.oid = SAI_NULL_OBJECT_ID;
    buffer orch ->>+ SAI: sai_buffer_api->set_ingress_priority_group_attribute(attr)
    SAI ->>+ SDK: Set headroom size of PG 3-4 to 0
    SDK ->>- SAI: Finish
    SAI ->>- buffer orch: Finish
    end
    buffer orch ->>- DATABASE: Finish
```

```mermaid
%remove queue flow
sequenceDiagram
    participant User
    participant DATABASE
    participant buffer orch
    participant SAI
    participant SDK
    User ->> DATABASE: Remove the BUFFER_QUEUE entry of the port
    DATABASE ->>+ buffer orch: Update notification
    loop for each queue in the list
    Note over buffer orch, SAI: attr.id = SAI_QUEUE_ATTR_BUFFER_PROFILE_ID
    Note over buffer orch, SAI: attr.value.oid = SAI_NULL_OBJECT_ID;
    buffer orch ->>+ SAI: sai_queue_api->set_queue_attribute(queue_id, &attr)
    SAI ->>+ SDK: Set reserved size of queue to 0
    SDK ->>- SAI: Finish
    SAI ->>- buffer orch: Finish
    end
    buffer orch ->>- DATABASE: Finish
```

```mermaid
%remove profile list flow
sequenceDiagram
    participant User
    participant DATABASE
    participant buffer orch
    participant SAI
    participant SDK
    User ->> DATABASE: Remove BUFFER_PORT_INGRESS/EGRESS_PROFILE_LIST
    DATABASE ->>+ buffer orch: Update notification
    Note over buffer orch, SAI: attr.id = SAI_PORT_ATTR_QOS_INGRESS/EGRESS_BUFFER_PROFILE_LIST
    Note over buffer orch, SAI: attr.value.objlist.list = [SAI_NULL_OBJECT_ID]
    buffer orch ->>+ SAI: sai_port_api->set_port_attribute(port.m_port_id, &attr)
    loop for each port buffer pool originally in the list
    SAI ->>+ SDK: Set reserved size of the port buffer pool to 0
    SDK ->>- SAI: Finish
    end
    SAI ->>- buffer orch: 
    buffer orch ->>- DATABASE: Finish
```

```mermaid
%Recalculate buffer pool flow
sequenceDiagram
    participant User
    participant DATABASE
    participant buffer orch
    participant SAI
    participant SDK
    User ->> User: Recalculate buffer pool and shared headroom pool size
    User ->> DATABASE: Set buffer pool size and shared headroom pool size
    DATABASE ->>+ buffer orch: Update notification
    Note over buffer orch, SAI: attr.id = SAI_BUFFER_POOL_ATTR_SIZE attr.value.u64 = size of shared buffer pool
    opt ingress_lossless_pool?
    Note over buffer orch, SAI: attr.id = SAI_BUFFER_POOL_ATTR_XOFF_SIZE attr.value.u64 = size of shared headroom pool
    end
    buffer orch ->>+ SAI: sai_buffer_api->set_buffer_pool_attribute
    SAI ->>+ SDK: Set the buffer pool size and shared headroom pool size accordingly
    SDK ->>- SAI: Finish
    SAI ->>- buffer orch: Finish
    buffer orch ->>- DATABASE: Finish
```
