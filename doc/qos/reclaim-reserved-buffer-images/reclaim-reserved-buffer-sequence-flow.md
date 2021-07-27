```mermaid
%Scripts can be rendered online by https://mermaid-js.github.io/mermaid-live-editor/edit
%Deploy flow
sequenceDiagram
    participant User
    participant CLI
    participant minigraph
    participant sonic cfggen
    participant buffer template
    participant DATABASE
    User ->> minigraph: set device type
    loop for each used port
        User ->> minigraph: set speed
        User ->> minigraph: set neighbor device name
        User ->> minigraph: set neighbor device detail
        User ->> minigraph: set other info (not related to buffer)
    end
    User ->>+ CLI: Execute "config load-minigraph"
    CLI ->>+ sonic cfggen: load minigraph
    sonic cfggen ->>+ minigraph: Load minigraph information
    minigraph ->>- sonic cfggen: Return minigraph info
    sonic cfggen ->> DATABASE: Set device type: ToRRouter, LeafRouter, or SpineRouter
    loop for each port
        sonic cfggen ->> DATABASE: Set port admin status to up if port is active
        sonic cfggen ->> DATABASE: Set port speed
        sonic cfggen ->> DATABASE: Set port's cable length according to both ends
    end
    Note over sonic cfggen, buffer template: Collect active ports and inactive ports
    loop for each port
        alt Neithbor is defined for the port
            sonic cfggen ->> buffer template: Add port to ACTIVE PORT set
        else
            rect rgb(255, 0, 255)
                sonic cfggen ->> buffer template: Add port to INACTIVE PORT set
            end
        end
    end
    sonic cfggen ->> sonic cfggen: Determine switch's topology according to its device type
    sonic cfggen ->> buffer template: Load buffer template according to SKU and topo
    buffer template ->> sonic cfggen: Return buffer templates
    Note over sonic cfggen, DATABASE: Generating buffer table items by rendering buffer templates.
    sonic cfggen ->> DATABASE: Generate default buffer pool objects
    sonic cfggen ->> DATABASE: Generate default buffer profile objects
    rect rgb(255, 0, 255)
        sonic cfggen ->> DATABASE: Generate default zero buffer profile objects
    end
    loop for each active port
        sonic cfggen ->> DATABASE: Generate BUFFER_QUEUE item for queue 0-2, 3-4, 5-6 for the port
        sonic cfggen ->> DATABASE: Generate BUFFER_PORT_INGRESS_PROFILE_LIST item
        sonic cfggen ->> DATABASE: Generate BUFFER_PORT_EGRESS_PROFILE_LIST item
        rect rgb(255, 0, 0)
            opt script to generate buffer priority-group DOES NOT exist?
                rect rgb(255, 255, 255)
                Note over sonic cfggen, DATABASE: Generat lossy PGs by rendering the buffer template if NO special script to generate them 
                sonic cfggen ->> DATABASE: Generate lossy BUFFER_PG item PG 0 for the port, using normal ingress lossy buffer profile
                end
            end
        end
    end
    rect rgb(255, 0, 0)
        opt script to generate buffer priority-group exist?
            Note over sonic cfggen, DATABASE: On platforms with 8-lane ports, the reserved size differs between normal port and 8-lane ports. In that case, special script is required to generate lossy buffer PGs
            sonic cfggen ->> DATABASE: Call script to generate buffer priority-group for all active ports
        end
    end
    rect rgb(255, 0, 255)
        opt zero profiles exist
            Note over sonic cfggen, DATABASE: Generate items for inactive ports by rendering bufer template if zero profiles exist
            loop for each inactive port
                sonic cfggen ->> DATABASE: Generate zero buffer profile item in BUFFER_QUEUE table for queue 0-2, 3-4, 5-6
                sonic cfggen ->> DATABASE: Generate zero buffer profile item in BUFFER_PORT_INGRESS_PROFILE_LIST table
                sonic cfggen ->> DATABASE: Generate zero buffer profile item in BUFFER_PORT_EGRESS_PROFILE_LIST table
                sonic cfggen ->> DATABASE: Generate zero buffer profile item for lossy PG 0 in BUFFER_PG table
            end
        end
    end
    sonic cfggen ->>- CLI: Finish
```

```mermaid
%Deploy lossy PGs flow
sequenceDiagram
    participant script
    participant DATABASE
    rect rgb(255, 0, 0)
    loop for each active port
    script ->>+ DATABASE: Get lanes
    DATABASE ->>- script: Result
    alt there are 8 lanes on the port
    script ->> DATABASE: Create lossy PG for the port, using lossy profile for 8 lanes (reserved size doubled)
    else there are 1, 2, or 4 lanes on the port
    script ->> DATABASE: Create lossy PG for the port, using normal lossy profile
    end
    end
    end
```

```mermaid
%System start
sequenceDiagram
    participant swss
    participant SAI
    participant SDK
    CLI ->> swss: Start swss, syncd and other services
    CLI ->>- User: finish
    Note over swss, SDK: Unrelated calls omitted
    loop for each port
    swss ->> SAI: sai_port_api->create_port
    SAI ->> SDK: Create port
    rect rgb(0, 128, 255)
    loop for each buffer objects created by SDK
    SAI ->> SDK: Set reserved size to 0
    end
    end
    end
```

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
    alt Handle the case port is admin-down
        rect rgb(255, 0, 255)
            alt Zero buffer profile exists (Mellanox approach)
            buffer manager ->> DATABASE: Create buffer PG with zero buffer profile and push them into BUFFER_PG
            else Non zero buffer profile exist (Other vendors)
            buffer manager ->> DATABASE: Finish (do nothing)
            end
        end
    else
        opt cable length or speed is not configured
            buffer manager ->> DATABASE: Finish (need retry)
        end
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
        loop for PG in [3, 4]
            Note over buffer orch, SAI: attr.id = SAI_INGRESS_PRIORITY_GROUP_ATTR_BUFFER_PROFILE
            Note over buffer orch, SAI: attr.value.oid = OID of corresponding buffer profile;
            buffer orch ->>+ SAI: sai_buffer_api->set_ingress_priority_group_attribute
            SAI ->>+ SDK: Set parameters of PG according to buffer profile
            SDK ->>- SAI: Finish
            SAI ->>- buffer orch: Finish
        end
        buffer orch ->>- DATABASE: Finish
    end
```

```mermaid
%Create queue flow

sequenceDiagram
    participant User
    participant DATABASE
    participant buffer orch
    participant SAI
    participant SDK
    User ->> DATABASE: Configure an entry in BUFFER_QUEUE
    DATABASE ->>+ buffer orch: Update notification
    buffer orch ->> buffer orch: Fetch the OID of buffer profile
    loop for queue in list
    Note over buffer orch, SAI: attr.id = SAI_QUEUE_ATTR_BUFFER_PROFILE_ID
    Note over buffer orch, SAI: attr.value.oid = OID of corresponding buffer profile;
    buffer orch ->>+ SAI: sai_queue_api->set_queue_attribute(queue, &attr)
    SAI ->>+ SDK: Set parameters of the queue according to buffer profile
    SDK ->>- SAI: Finish
    SAI ->>- buffer orch: Finish
    end
    buffer orch ->>- DATABASE: Finish
```

```mermaid
%Create port profile list flow

sequenceDiagram
    participant User
    participant DATABASE
    participant buffer orch
    participant SAI
    participant SDK
    User ->> DATABASE: Configure an entry in BUFFER_PORT_INGRESS/EGRESS_PROFILE_LIST
    DATABASE ->>+ buffer orch: Update notification
    loop for profile in profile_list
    buffer orch ->> buffer orch: Fetch the OID of buffer profile
    buffer orch ->> buffer orch: Insert the OID to oid_list
    end
    loop for queue in list
    alt BUFFER_PORT_INGRESS_PROFILE_LIST
    Note over buffer orch, SAI: attr.id = SAI_PORT_ATTR_QOS_INGRESS_BUFFER_PROFILE_LIST
    else BUFFER_PORT_EGRESS_PROFILE_LIST
    Note over buffer orch, SAI: attr.id = SAI_PORT_ATTR_QOS_EGRESS_BUFFER_PROFILE_LIST
    end
    Note over buffer orch, SAI: attr.value.oid = oid_list
    buffer orch ->>+ SAI: sai_port_api-->set_port_attribute(port, &attr)
    loop for each OID in oid_list
    SAI ->>+ SDK: Set parameters of the port buffer pool according to buffer profile
    SDK ->>- SAI: Finish
    end
    SAI ->>- buffer orch: Finish
    end
    buffer orch ->>- DATABASE: Finish
```

```mermaid
%Startup SAI flow
sequenceDiagram
    participant User
    participant DATABASE
    participant port manager
    participant ports orch
    participant SAI
    participant SDK
    User ->> DATABASE: Startup a port
    DATABASE ->> port manager: Update notification
    port manager ->> DATABASE: Update APPL_DB.PORT.admin_status
    DATABASE ->>+ ports orch: Update notification
    Note over ports orch, SAI: attr.id = SAI_PORT_ATTR_ADMIN_STATE
    Note over ports orch, SAI: attr.value.booldata = whether the admin state is up
    ports orch ->>+ SAI: sai_port_api->set_port_attribute(port, attr)
    rect rgb(0, 128, 255)
        alt Port state is admin up
            SAI ->>+ SDK: Set headroom size of management PG to the original value
        else
            SAI ->>+ SDK: Set headroom size of management PG to 0
        end
        SDK ->>- SAI: Finish
    end
    SAI ->>- ports orch: Finish
    ports orch ->>- DATABASE: Finish
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
    rect rgb(0, 255, 0)
    buffer manager ->> DATABASE: Remove the buffer PG 3-4
    end
    DATABASE ->>+ buffer orch: Update notification
    rect rgb(0, 255, 0)
    loop for each priority-group in the list [3, 4]
    Note over buffer orch, SAI: attr.id = SAI_INGRESS_PRIORITY_GROUP_ATTR_BUFFER_PROFILE
    Note over buffer orch, SAI: attr.value.oid = SAI_NULL_OBJECT_ID;
    buffer orch ->>+ SAI: sai_buffer_api->set_ingress_priority_group_attribute(attr)
    rect rgb(255, 255, 255)
    SAI ->>+ SDK: Set headroom size of PG to 0
    SDK ->>- SAI: Finish
    end
    SAI ->>- buffer orch: Finish
    end
    end
    buffer orch ->>- DATABASE: Finish```

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
    rect rgb(0, 255, 0)
    loop for each queue in the list
    Note over buffer orch, SAI: attr.id = SAI_QUEUE_ATTR_BUFFER_PROFILE_ID
    Note over buffer orch, SAI: attr.value.oid = SAI_NULL_OBJECT_ID;
    buffer orch ->>+ SAI: sai_queue_api->set_queue_attribute(queue_id, &attr)
    rect rgb(255, 255, 255)
    SAI ->>+ SDK: Set reserved size of queue to 0
    SDK ->>- SAI: Finish
    end
    SAI ->>- buffer orch: Finish
    end
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
    rect rgb(0, 255, 0)
    Note over buffer orch, SAI: attr.id = SAI_PORT_ATTR_QOS_INGRESS/EGRESS_BUFFER_PROFILE_LIST
    Note over buffer orch, SAI: attr.value.objlist.list = [SAI_NULL_OBJECT_ID]
    buffer orch ->>+ SAI: sai_port_api->set_port_attribute(port.m_port_id, &attr)
    rect rgb(0, 128, 255)
    loop for each port buffer pool originally in the list
    SAI ->>+ SDK: Set reserved size of the port buffer pool to 0
    SDK ->>- SAI: Finish
    end
    end
    SAI ->>- buffer orch: 
    end
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

```mermaid
%Shutdown SAI flow
sequenceDiagram
    participant User
    participant DATABASE
    participant port manager
    participant ports orch
    participant SAI
    participant SDK
    User ->> DATABASE: Shutdown a port
    DATABASE ->> port manager: Update notification
    port manager ->> DATABASE: Update APPL_DB.PORT.admin_status
    DATABASE ->>+ ports orch: Update notification
    Note over ports orch, SAI: attr.id = SAI_PORT_ATTR_ADMIN_STATE
    Note over ports orch, SAI: attr.value.booldata = false;
    ports orch ->>+ SAI: sai_port_api->set_port_attribute(port, attr)
    rect rgb(0, 128, 255)
    SAI ->>+ SDK: Set headroom size of management PG to 0
    SDK ->>- SAI: Finish
    end
    SAI ->>- ports orch: Finish
    ports orch ->>- DATABASE: Finish
```

```mermaid
%Dynamic-original-flow
sequenceDiagram
    participant User
    participant CONFIG_DB
    participant buffer manager
    participant APPL_DB
    participant buffer orch
    participant SAI
    participant SDK
    User ->> CONFIG_DB: Shutdown the port
    CONFIG_DB ->> buffer manager: Update notification
    loop for each buffer PG object
        buffer manager ->> APPL_DB: remove the object from APPL_DB
        APPL_DB ->> buffer orch: Update notification
        Note over buffer orch, SAI: attr.id = SAI_INGRESS_PRIORITY_GROUP_ATTR_BUFFER_PROFILE
        Note over buffer orch, SAI: attr.value.oid = SAI_NULL_OBJECT_ID
        buffer orch ->>+ SAI: sai_buffer_api->set_ingress_priority_group_attribute
        SAI ->>+ SDK: Set the reserved size and headroom size to 0
        SDK ->>- SAI: Finish
        SAI ->>- buffer orch: Finish
    end
```

```mermaid
%Dynamic-new-flow
sequenceDiagram
    participant User
    participant CONFIG_DB
    participant buffer manager
    participant APPL_DB
    User ->> CONFIG_DB: Shutdown the port
    CONFIG_DB ->> buffer manager: Update notification
    rect rgb(255, 0, 255)
        buffer manager ->> buffer manager: Fetch the zero buffer profile on ingress side
        loop for each buffer PG object on the port
            alt zero ingress buffer profile exists
                buffer manager ->> APPL_DB: set the profile of the PG to corresponding zero buffer profile in BUFFER_PG
            else
                rect rgb(255, 255, 255)
                buffer manager ->> APPL_DB: Remove the buffer item from BUFFER_PG
                end
            end
        end
        buffer manager ->> buffer manager: Fetch the zero buffer profile on egress side
        loop for each buffer queue object on the port
            alt zero egress buffer profile exists
            buffer manager ->> APPL_DB: set the profile of the queue to corresponding zero buffer profile in BUFFER_QUEUE
            else
                rect rgb(255, 255, 255)
                buffer manager ->> APPL_DB: Remove the buffer item from BUFFER_QUEUE
                end
            end
        end
        opt zero ingress buffer profiles exist
            alt ingress_lossy_pool exists
                buffer manager ->> buffer manager: set ingress zero profile list to [ingress_zero_lossless_profile, ingress_zero_lossy_profile]
            else
                buffer manager ->> buffer manager: set ingress zero profile list to [ingress_zero_lossless_profile]
            end
            buffer manager ->> APPL_DB: set the profile_list of the port to egress zero buffer profile list in BUFFER_PORT_INGRESS_PROFILE_LIST
        end
        opt zero egress buffer profiles exist
            buffer manager ->> buffer manager: set egress zero profile list to [egress_zero_lossless_profile, egress_zero_lossy_profile]
            buffer manager ->> APPL_DB: set the profile_list of the port to egress zero buffer profile list in BUFFER_PORT_EGRESS_PROFILE_LIST
        end
    end
```
