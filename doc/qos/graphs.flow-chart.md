# Flow charts

```mermaid
%Allocate a New Profile
% allocate-profile.png
sequenceDiagram
  participant System
  participant Buffer Manager
  participant Database Service
  participant Buffer Orch
  participant SAI

  System -->>+ Buffer Manager: Allocate a profile
  Note over System, Buffer Manager: parameter: (speed, length)
  Buffer Manager -->> Database Service: Check whether there has already been a profile for the (speed, length) tuple
  opt if there isn't one existing
  Buffer Manager ->> Buffer Manager: [Create only] Calculate the headroom size via the well-known formula
  Buffer Manager ->> Buffer Manager: Create an entry in BUFFER_PROFILE table
  Buffer Manager -->> Database Service: Insert the profile into APPL_DB.BUFFER_PROFILE
  par Notify orchagent in another thread
  Database Service -->>+ Buffer Orch: Create a profile
  Buffer Orch -->>+ SAI: create_buffer_profile
  Buffer Orch -->>- Database Service: Finish
  end
  end
  Buffer Manager -->>- System: Finish
```

```mermaid
%Release a profile
%release-profile.png
sequenceDiagram
  participant System
  participant Buffer Manager
  participant Database Service
  participant Buffer Orch
  participant SAI

  System -->>+ Buffer Manager: Release a profile
  Note over System, Buffer Manager: parameter: (speed, length)
  Buffer Manager ->>+ Database Service: Check whether the profile is derived from CONFIG_DB.BUFFER_PROFILE
  Database Service ->>- Buffer Manager: Result
  Buffer Manager ->>+ Database Service: Check whether the profile is referenced any longer
  Database Service ->>- Buffer Manager: Result
  opt the profile isn't derived from CONFIG_DB nor referenced any longer
  Buffer Manager -->> Database Service: Destroy an entry in BUFFER_PROFILE table
  par Notify orchagent in another thread
  Database Service -->>+ Buffer Orch: Remove a profile
  Buffer Orch -->>+ SAI: remove_buffer_profile
  Buffer Orch -->>- Database Service: Finish
  end
  end
  Buffer Manager -->>- System: Finish
```

```meimaid
%Calculate shared buffer pool size
sequenceDiagram
  participant System
  participant Buffer Manager
  participant Database Service
  participant Buffer Orch
  participant SAI

  System -->>+ Buffer Manager: Recalculate shared buffer pool size
  loop Iterate all port
  opt Port is admin up
  Buffer Manager ->> Buffer Manager: Accumulate the headroom size of all lossless PGs
  Buffer Manager ->> Buffer Manager: Accumulate the reserved size of all lossy PGs
  Buffer Manager ->> Buffer Manager: Accumulate the reserved size for egress traffic
  end
  end
  loop for each buffer pool
  opt buffer pool needs to be update size dynamically
  Buffer Manager -->> Database Service: Update BUFFER_POOL
  par Notify orchagent in another thread
  Database Service -->>+ Buffer Orch: Notify BUFFER_POOL updated
  Buffer Orch -->>+ SAI: set_buffer_pool_attribute
  Buffer Orch -->>- Database Service: Finish
  end
  end
  end
  Buffer Manager -->>- System: Finish
```

```meimaid
%Calculate the headroom for a port, PG tuple
%recalculate.png
sequenceDiagram
  participant System
  participant Buffer Manager
  participant Database Service
  participant Buffer Orch
  participant SAI

  System -->>+ Buffer Manager: Recalculate a port's headroom with new parameters
  Note over System, Database Service: parameter: (speed, length, lossless_pg), current value: (speed_old, length_old, lossless_pg_old)
  opt speed or length updated
  Buffer Manager ->> Buffer Manager: Allocate a profile for (speed, length)
  end
  opt lossless_pg != lossless_pg_old
  Buffer Manager ->> Buffer Manager: Remove the port's BUFFER_PG table entry indexed by (port, lossless_pg_old)
  Buffer Manager -->> Database Service: Notify BUFFER_PG|<port>|lossless_pg_old removed
  par Notify orchagent in another thread
  Database Service -->>+ Buffer Orch: Notify BUFFER_PG|<port>|lossless_pg_old removed
  Buffer Orch -->> SAI: set_ingress_priority_group_attribute(attribute = null oid)
  Buffer Orch -->>- Database Service: Finish
  end
  end
  opt headroom increased and not warm-reboot
  Buffer Manager ->> Buffer Manager: Recalculate shared buffer pools size and program to ASIC
  end
  opt lossless_pg != empty set
  Buffer Manager ->> Buffer Manager: Update the port's BUFFER_PG table entry indexed by (port, lossless_pg)
  Buffer Manager -->> Database Service: Update BUFFER_PG
  par Notify orchagent in another thread
  Database Service -->>+ Buffer Orch: Notify BUFFER_PG updated
  Buffer Orch -->> SAI: set_ingress_priority_group_attribute
  Buffer Orch -->>- Database Service: Finish
  end
  end
  opt headroom decreased and not warm-reboot
  Buffer Manager ->> Buffer Manager: Recalculate shared buffer pools size and program to ASIC
  end
  opt speed or length updated
  Buffer Manager ->> Buffer Manager: Release profile for (speed_old, length_old)
  end
  Buffer Manager -->>- System: Finish
```

```mermaid
%cable-length-speed-update.png
sequenceDiagram
  participant System
  participant Buffer Manager
  participant Database Service
  participant Syslog

  System -->>+ Buffer Manager: A port's speed or cable length updated
  Note over System, Buffer Manager: parameter (speed, cable length)
  Buffer Manager -->>+ Database Service: get CONFIG_DB.BUFFER_PG|<port>|<lossless PG>.headroom_type
  Database Service -->>- Buffer Manager: return
  opt headroom_type is dynamic
  Buffer Manager ->> Buffer Manager: Calculate new headroom size
  alt new headroom size <= max legal headroom
  Buffer Manager ->> Buffer Manager: Calculate and deploy the headroom for a port, PG tuple
  else headroom size exceeds the maxinum legal value
  Buffer Manager ->> Buffer Manager: Keep previous data in APPL_DB
  Buffer Manager -->> Syslog: Error message should be logged
  end
  end
  Buffer Manager -->>- System: Finish
```

```mermaid
%Admin Up/Down: 1. calculate or static, 2. deploy
sequenceDiagram
  participant System
  participant Buffer Manager

  System -->>+ Buffer Manager: A port's admin status is updated
  Buffer Manager ->> Buffer Manager: Recalculate the pool size
  Buffer Manager -->>- System: Finish
```

```mermaid
%Apply a new buffer PG
sequenceDiagram
  participant System
  participant Buffer Orch
  participant SAI

  System -->>+ Buffer Orch: Notify BUFFER_PG updated
  Buffer Orch -->> SAI: set_ingress_priority_group_attribute
  Buffer Orch ->> Buffer Orch: Recalculate buffer pool size
  Buffer Orch -->>- System: Finish
```

```mermaid
%Configure static headroom: 1. remove the profile current used 2. deploy the static profile
%add-headroom-override.png
sequenceDiagram
  participant System
  participant Buffer Manager
  participant Database Service
  participant Buffer Orch
  participant SAI

  System -->>+ Buffer Manager: Configure static headroom on a port (profile)
  opt profile existed (it's possible that database service notify profile creating later than buffer pg)
  Buffer Manager ->> Buffer Manager: Release the current applied profile for the port
  Buffer Manager -->> Database Service: Update BUFFER_PG table
  par Notify orchagent in another thread
  Database Service -->>+ Buffer Orch: Notify BUFFER_PG updated
  Buffer Orch -->> SAI: set_ingress_priority_group_attribute
  Buffer Orch -->>- Database Service: Finish
  end
  Buffer Manager ->> Buffer Manager: Recalculate the shared buffer pool size
  end
  Buffer Manager -->>- System: Finish
```

```mermaid
%De-configure static headroom:
sequenceDiagram
  participant System
  participant Buffer Manager

  System -->>+ Buffer Manager: Remove the static headroom on a port
  Buffer Manager ->> Buffer Manager: Allocate buffer profile according to port's speed and cable length
  Buffer Manager ->> Buffer Manager: Recalculate the shared buffer pool size
  Buffer Manager -->>- System: Finish
```

```mermaid
%Update static profile:
%static-profile-updated.png
sequenceDiagram
  participant System
  participant Buffer Manager
  participant Database Service
  participant Buffer Orch

  System -->>+ Buffer Manager: Update static profile
  Buffer Manager -->> Database Service: Update corresponding buffer profile in CONFIG_DB
  par Notify orchagent in another thread
  Database Service -->>+ Buffer Orch: Buffer profile updated
  Buffer Orch -->>+ SAI: set_buffer_pool_attribute
  Buffer Orch -->>- Database Service: Finish
  end
  opt headroom size updated
  Buffer Manager ->> Buffer Manager: Recalculate the buffer pool size and program ASIC
  end
  Buffer Manager -->>- System: Finish
```

```mermaid
stateDiagram
  [*] --> Initialization : System start
  Initialization --> Running : Initialization finished
  Initialization --> Initialization : Load data from db or predefined ini
  Running --> HandlePortSpeedUpdate : Port's Speed Updated
  HandlePortSpeedUpdate --> HandlePortSpeedUpdate : Update BUFFER_PG and BUFFER_PROFILE
  HandlePortSpeedUpdate --> Running
  Running --> HandleCableLengthUpdate : Port's Cable length updated
  HandleCableLengthUpdate --> HandleCableLengthUpdate : Update BUFFER_PROFILE
  HandleCableLengthUpdate --> Running
  HandleCableLengthUpdate --> HandlePortSpeedUpdate
```
