# Root causes:
## when dockers stop
For any shutdown flow, which means all dockers are stopped in order, pmon docker often stops after syncd docker has stopped, causing pmon docker fail to release sx_core resources and leaving sx_core in a bad state. The related logs are like the following:

    INFO syncd.sh[23597]: modprobe: FATAL: Module sx_core is in use.
    INFO syncd.sh[23597]: Unloading sx_core[FAILED]
    INFO syncd.sh[23597]: rmmod: ERROR: Module sx_core is in use

## when dockers restart without reboot
In the flows like "config reload" and "service swss restart", the failure cause further consequences:
1. sx_core initialization error with error message like "sx_core: create EMAD sdq 0 failed. err: -16"
2. syncd fails to execute the create switch api with error message "syncd_main: Runtime error: :- processEvent: failed to execute api: create, key: SAI_OBJECT_TYPE_SWITCH:oid:0x21000000000000, status: SAI_STATUS_FAILURE"
3. swss fails to call SAI API "SAI_SWITCH_ATTR_INIT_SWITCH", which causes orchagent to restart.
This will introduce an extra 1 or 2 minutes for the system to be available, failing related test cases. In this sense, the issue should be solved for the flow.

## reboot flow
In the reboot flows including "reboot", "fast-reboot" and "warm-reboot" this failure doesn't have further negative effects since the system has already rebooted. In addition, "warm-reboot" requires the system to be shutdown as soon as possible to meet the GR time restriction of both BGP and LACP. "fast-reboot" also requires to meet the GR time restriction of BGP which is longer than LACP. In this sense, any unnecessary steps should be avoided. It's better to keep those flows untouched.

## summarize
To summarize, we have to come up with a way to ensure:
1. pmon docker shutdown ahead of syncd for "config reload" or "service swss restart" flow;
2. don't shutdown pmon docker ahead of syncd to save time for "fast-reboot" or "warm-reboot" flow.
3. for "reboot" flow, either way is acceptable.

# Solutions
There're the following options to do that. All of them are Mellanox-specific.
## just add "syncd" as "Requires" and "After" of pmon.service
- pros
  - simple and clear.
- cons
  - It force pmon to be shutdown ahead of syncd. For "reboot", "fast-reboot" and "warm-reboot", this introduces extra latency which possibly hurts the total convergence time.

## add "swss" as "Requires" and "After" of pmon.service
similar with 1.

## stop pmon ahead of syncd for flows except warm-reboot in syncd.sh
1. Shutdown pmon docker ahead of syncd has been shutdown for "cold" reboot which covers "reboot", "config reload" and "service swss restart".
2. In addition, originally the "service swss restart" doesn't require pmon to restart neither is there a way to make pmon start after swss has started. Now, as pmon has shutdown in the flow a way also required to make pmon start after syncd has started. There is no way to distinguish "config reload" and "service swss restart" from other shutdown flows but it's able to distinguish "warm-reboot" from others. Thus "warm-reboot" can be specifically handled.
This can be done by update syncd.sh
- pros
  - "warm-restart" can be handled specifically to avoid hurt convergence time.
- cons
  - implicit dependency.
