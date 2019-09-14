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
3. The flow config reload should be also adjusted. As pmon service is stopped and started by syncd automatically, "config reload" should not start and stop it explicitly any more.
- pros
  - "warm-restart" can be handled specifically to avoid hurt convergence time.
- cons
  - implicit dependency.

# analyze the 3rd solution for variant flows
Eventually we decide to choice option 3, stop pmon ahead of syncd for flows except warm-reboot. In this chapter we are going to analyze all the flows.
## config reload
In config reload flow, the services are firstly stopped in the following order:
1. swss
   1. stop orchagent docker
   2. stop syncd service
      - stop pmon first and then stop syncd
   3. stop services depending on swss, including teamd and radv
2. lldp
3. bgp
4. hostcfgd

And then the services are started in the following order:
1. hostname-config
2. interfaces-config
3. ntp-config
4. rsyslog-config
5. swss
   1. syncd is started after swss fully started
   2. we should ensure that pmon is not active when "chipdown" is called. there are two options to do so:
      - stop pmon if it is active when "chipdown"
      - syncd.service is add as "After" of pmon so that pmon won't start ahead of syncd.
6. bgp
7. lldp
8. hostcfgd

difference compared to the original flow:
Stopping phase:
Originally pmon is stopped after syncd, now ahead of syncd.
Starting phase:
Originally pmon is started after lldp, now ahead of syncd.

## systemctl restart swss
In this follow only swss and services depending it are restarted.
Stopping phase:
1. swss stopped
2. syncd stopped
   1. pmon stopped during syncd stopping, ahead of sdk shutdown
3. teamd stopped
4. radv stopped

Starting phase:
1. swss started
2. after swss fully started, syncd, teamd, radv are started
3. during syncd starting, pmon started


## warm-reboot
Stooping phase:
no difference

Starting phase:

    If pmon starts ahead of syncd calling chipdown, no difference from the original flow. The pmon has to be stopped and then restarted.
    Otherwise, pmon will start immediate after "chipdown". This may differ from the original flow since in the latter pmon won't start so early.

## reboot
Stooping phase:
no related service is stopped during this phase.

Starting phase:
Similar to "reboot". 
