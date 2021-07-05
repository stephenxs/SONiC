# Mellanox Buffer Checker #

## Scope ##

This is the high level design of the Mellanox buffer checker which is a tool checking the consistency between SONiC and SDK and providing valuable insight of what is happening in terms of buffer.

## Design ##

### The Flow ###

1. Load the SONiC buffer information from:
   - `APPL_DB` if `DEVICE_METADATA|local.buffer_model` is defined
   - `CONFIG_DB` otherwise
2. Generate internal representation of SONiC buffer information

   Type of objects:
   - BUFFER_POOL
   - PORT
   - BUFFER_PG
   - BUFFER_QUEUE

   Hierarchy among objects:

   `Buffer pool` contains

3. Load the SDK buffer information from sdkdump (in json)
   Add information into objects generated in step 2

## Global data ##

1. buffer pools configured by SONiC
   There can be buffer pools configured by sdk by default. We are not interested in them.
2. shared headroom pool object
3. buffer descriptor pool
4. list of all port buffer pools, regardless whether it's by SONiC or not
5. list of all PG, regardless whether it's by SONiC or not
6. list of all queue, regardless whether it's by SONiC or not
7. list of all objects configured by SONiC
8. list of all sdk objects
9. map: name to SONiC objects

### Object hierarchy ###

### SONiC buffer object ###

It includes the following fields and method

SONiC information:

- `name`: The name of the object. It can be the name of:
  - A buffer pool
  - A port
  - A number
- `os_size`: The size information in SONiC. It represents:
  - The size of buffer pool
  - The size of the shared headroom pool
  - The reserved size of PG, queue or the port pool
- `dynamic_th`: The dynamic threshold of a port, queue, or PG
- `xon_os`, `xoff_os`
- `buffer_pool`: The buffer pool where the buffer is allocated

SDK information:

- `sdk_size`: The size information in SDK. It is in cell. It can be
  - The size of buffer pool
  - The size of the shared headroom pool
  - The size of the descriptor pool
  - The reserved size of PG, queue or the port buffer pool
- `private_headroom`
- `alpha`: The ALPHA value in sdk
- `buffer pool id`: buffer pool id in sdk
- `buffer pool object`:
- `buffer port pool object`:

General information:

- `parent`: The parent object reference.
  - port for queue, PG

Statistics information:

- Buffer pool
  - current occupancy
  - maximum occupancy

- Buffer PG
  - rx buffer discard
  - rx shared discard
  - PFC sent

- Buffer queue
  - tx buffer discard
  - PFC received
  - wred marked
  - wred dropped
  - sll dropped
  - hll dropped

- Port
  - current occupancy
  - maximum occupancy
  - descriptor current occupancy
  - descriptor maximum occupancy

- Buffer descriptor pool
  - current occupancy
  - maximum occupancy

### SDK object ###

SDK object is a dict containing all information fetched from sdkdump. It can be a:

- Shared buffer pool
- Shared headroom pool
- Buffer port pool

Global information

- list of all shared buffer pools
- dict of all buffer port pools
- globals
  - shared headroom pool
  - ingress lossless pool
  - ingress lossy pool
  - egress lossless pool
  - egress lossy pool

## Flows ##

### Load SONiC configuration ###

1. Load all buffer pools and create objects
2. Load all buffer profiles and create objects. check whether the referenced buffer pool exists
3. Load all buffer PG/queue/profile_list and create objects. check whether the referenced buffer profile exists. extend the buffer profiles to the objects

SONiC objects are organized in this way:

|||||
|:-----:|:-----:|:-----:|:-----:|
|TABLE|generated dict name|index (if any)|comments|
|BUFFER_POOL|buffer_pool|name|
|BUFFER_PG|buffer_pg|port,pg|The index in SONiC is like 3-4 which repreents 2 PGs. It needs to be extended to two objects indexed by 3, 4 respectively.|
|BUFFER_QUEUE|buffer_queue|port,queue|Need to extend index. 0-2 to 0, 1, 2. 3-4 to 3, 4. 5-6 to 5, 6|
|BUFFER_INGRESS_PORT_PROFILE_LIST|port_buffer_pool_ing|port||
|BUFFER_EGRESS_PORT_PROFILE_LIST|port_buffer_pool_egr|port||

### Load SDK information ###

1. Load port mapping information. Assume there is no port split.
   Generate a map from fpport to sdk port id.
2. Load pool information. Create objects. Insert all the objects into the list according to the pool id.
3. Load port information. Create objects. Insert all objects into a dict indexed by the port name. All information relevant to a port should be combined into one object.
4. Check buffer oversubscription.
5. Check Identify buffer pool configured by SONiC
6. Combine SDK objects into SONiC objects

#### Buffer pool example ####

Buffer pool information are in `Pools Settings` section of the sdkdump. The hierarchy is like this:

```
	"Shared Buffers module":	{
		"Shared Buffers DB Dump":	{
			"Pools Settings":	{
				"table 0":	[{
						"Pool":	"0",
						"HW ID":	"0",
						"Direction":	"Ingress",
						"Size":	"96810",
						"Pool mode":	"Dynamic",
						"Buffer type":	"Data",
						"Infinite":	"FALSE",
						"Pool type":	"Default data ingress",
						"Cur occupancy":	"0",
						"MAX occupancy":	"0"
					}, {
                        "Pool": "1",
                        ...
                    }
            }
        }
    }
```

The generated buffer pool object should be like this:

```
sdk_pool_list = {
    "0": {
        # The same info as the items whose "Pool" is "0" in "table 0"
        "HW ID":	"0",
        "Direction":	"Ingress",
        "Size":	"96810",
        "Pool mode":	"Dynamic",
        "Buffer type":	"Data",
        "Infinite":	"FALSE",
        "Pool type":	"Default data ingress",
        "Cur occupancy":	"0",
        "MAX occupancy":	"0"
    }
}
```

The same logic should be applied to all items in `Shared Buffers DB Dump` section but different dicts will be generated based on different tables in sdkdump.

| | | |
|:---------:|:--------:|:------:|
|section in sdkdump|generated dict name|index(if any)|
|Shared Headroom Pools Settings|shared_headroom_pool|
|Multicast Settings|Not used for now|
|Ports Settings->"Port xxxx"->"Port Data Pools xxx"->"table x"|port_buffer_pools|port,pool|
|Ports Settings->"Port xxxx"->"Port Data PGs xxx"->"table x"|port_pg_sdk|port,pg|
|Ports Settings->"Port xxxx"->"Port Shared Headroom xxx"->"table x"|port_shp_sdk|port|
|Ports Settings->"Port xxxx"->"Port Data TCs xxx"->"table x"|port_queue_sdk|port,queue|
|Ports Settings->"Port xxxx"->"Port MC xxx"->"table x"|port_mc_sdk|port|
|Ports Settings->"Port xxxx"->"Port Descriptor Pools xxx"->"table x"|port_descriptor_sdk|port|

#### Port information example ####

Port information are in `Port Performance Counters` section of the sdkdump. The hierarchy of this section is like this:

```
		"Port Performance Counters":	{
			"Device 1":	{
				"SWID 0":	{
					"Port 0x10100 - IEEE 802.3 Counters Group":	{
                        ...
                    },
					"Port 0x10100 - RFC 2863 Counters Group":	{
                        ...
                    },
					"Port 0x10100 - RFC 2819 Counters Group":	{
                        ...
                    },
                    "Port 0x10100 - RFC 3635 Counters Group":	{
                        ...
                    },
					"Port 0x10100 - CLI Counters Group":	{
                        ...
                    },
					"Port 0x10100 - EXTENDED Counters Group":	{
                        ...
                    },
					"Port 0x10100 - DISCARD Counters Group":	{
                        ...
                    },
					"Port 0x10100 - PER PRIO Counters Group":	{
                        ...
					},
					"Port 0x10100 - PER BUFF Counters Group":	{
                        ...
					},
					"Port 0x10100 - PER TC Counters Group":	{
                        ...
					}
                }
            }
        }
```

The port sdk object should like this:

```
port_performance_objects = {
    '0x10100': {
        "IEEE 802.3 Counters Group":{
            ...
        },
        "RFC 2863 Counters Group":{
            ...
        },
        "RFC 2819 Counters Group":{
            ...
        },
        "RFC 3635 Counters Group":{
            ...
        },
        "CLI Counters Group":{
            ...
        },
        "EXTENDED Counters Group":{
            ...
        },
        "DISCARD Counters Group":{
            ...
        },
        "PER PRIO Counters Group":{
            ...
        },
        "PER BUFF Counters Group":{
            ...
        },
        "PER TC Counters Group":{
            ...
        }
    }
}
```

#### Port map example ####

Example in sdkdump
```
		"Port DB Dump":	{
			"Device 1":	{
				"SWID 0":	{
					"SWID TYPE":	"ETHERNET",
					"table 451":	[{
							"Slot":	"0",
							"Panel":	"33",
							"Port ID":	"0x10100",
							"Admin":	"Down",
							"Oper":	"Down",
							"Module state":	"Unplugged",
							"Speed api":	"Speed",
							"Ad. Speed":	"0x38000000",
							"Op. Speed":	"0x0",
							"Speed":	"N/A",
							"FEC":	"Post-FEC",
							"MTU":	"9122",
							"MAC":	"98:03:9B:F3:F5:00",
							"Base UC-Rte":	"0x1",
							"sFlow ratio":	"0",
							"width":	"1",
							"lanes":	"0x1",
							"label":	"0x210"
						}, {
                            ...
                        }]
                }
            }
        }
```

Generated global map:

```
port_map_sdk_to_sonic{'0x10100': 'Ethernet128'}
where 128 = ('Panel' - 1) * 4 = (33 - 1) * 4
```
### Identify Buffer pool configured by SONiC ###

A buffer pool is configured by SONiC if and only if the description is "user".

Organize all pools configured by SONiC into two lists: ingress and egress.

Identify each buffer pool

Hacking:

Use MSFT SKU. There is only 1 ingress pool and 2 egress pools.
The egress pool with larger size should be egress_lossless_pool and theother should be egress_lossy_pool.
The egress_lossy_pool and ingress_lossless_pool share the same size.

Normal way to do that:
Go over each of the PGs.

- If the PG is lossless (`xon` and `xoff` is configured),
  - `ingress_lossless_candidate` is None
    - The pool referenced by the PG is `ingress_lossless_candidate`
  - The pool referenced by the PG isn't equal to `ingress_lossless_candidate`
    - Fatal error: more than one ingress lossless pool
  - Otherwise:
    - Do nothing
- If the PG is lossy with non-zero headroom:
  - `ingress_lossy_candidate` is None
    - The pool referenced by the PG is `ingress_lossy_candidate`
  - The pool referenced by the PG isn't equal to `ingress_lossy_candidate`
    - Fatal error: more than one ingress lossy pool
  - Otherwise:
    - Do nothing

The `ingress_lossless_candidate` and `ingress_lossy_candidate` are `ingress_lossless_pool` and `ingress_lossy_pool` respectively.

Go over each of the queues and execute a similar deduction. There is not a way to detect which queue is lossy and which is lossless from sdkdump only. We need to leverage SONiC configuration to achieve that.

### Buffer oversubscription check ###

1. `accumulative size` = 0
2. For each port object:
   - accumulate all reserved sizes to `accumulative size`
   - accumulate all private headroom sizes to `accumulative size`
3. For each PG object: accumulate all reserved sizes and headroom sizes to `accumulative size`
4. For each queue object: accumulative all reserved sizes to `accumulative size`
5. Add `shared headroom pool size` to `accumulative size`
6. Add headroom for egress mirror to `accumulative size`
7. We have `accumulative size` now.
8. Calculate buffer over subscription:
   `accumulative size` + `ingress lossless pool size` * `number of ingress pools` - `total size`

### Buffer information consistency check ###

For each object in OS list, compare the following items:

1. `os_size` against `sdk_size`
2. `dynamic_th` against `alpha`
3. `buffer_pool` against `buffer pool id` in sdk
4. `xon` against `xon_sdk`
5. checking `xoff` is a bit complicated:
   - if `private_headroom`:
     - `xoff` should be equal to (`private_headroom` + `max_loan`) / 2
   - else:
     - `xoff` should be equal to `size` - `xon`

### Combine SDK objects into SONiC objects ###

buffer pools: combine SDK objects into SONiC objects by name

for each port object:

1. map the port logic id to port name
2. combine sdk port object into SONiC object