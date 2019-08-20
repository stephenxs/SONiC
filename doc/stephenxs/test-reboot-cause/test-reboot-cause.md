# purpose
to test whether the command "show reboot-cause" contains the correct reboot cause after the DUT underwent variant kinds of reboot like power off and watchdog.
# reboot by power off
The main idea of power-off test case is to power off and on a DUT's PSUs and then check its reboot cause by using command "show reboot-cause".
At lease two cases should be covered: 
1. All PSUs being powered on simultaneously,
2. Only one PSUs being powered on.
## high level design
### the possible sequences in which PSUs being powered off and on
For any testbed that has two PSUs and whose DUT's PSUs can be operated independently, the PSUs are going to be operated in the following sequence.
1. turn off all PSUs, delay <N> seconds, turn on all PSUs simultaneously
2. turn off all PSUs, delay <N> seconds, turn on PSU 1
3. turn off all PSUs, delay <N> seconds, turn on PSU 2
The seconds delayed in all sequences should be the following value:
    - 5 seconds, to simulate a automatic reboot
    - 20 seconds, to simulate a manual reboot

## detailed design
The reboot-cause test is going to be implemented under the pytest framework. A new file will be introduced to contain all the testcases.
### pseudo code
#### preparation
1. get psu object for all PSUs, comprising a list all_psu, which can be implemented via the following snippet of code:

        psu_controller.get_psu_status()

2. make a list with each element representing a sequence of PSUs required to be powered on in the testcase:

        all_power_on_list = [[item] for item in all_psu]
        all_power_on_list.append(all_psu)

   after that, the all_power_on_list should be [[psu1], [psu2], [psu1, psu2]] (for two-PSU devices). the last element in the list represents the case which turns on all PSUs.
3. make a list called "delay_seconds" where each element represent a possible delay time between the PSUs being powered off and on.
#### main procedure
    for each power_on_seq in all_power_on_list, do
        for each delay_time in dely_seconds, do
            verify the DUT is reachable, fail the test if not
            for psu in all_psu do
                psu_controller.turn_off_psu(psu["psu_id"])
            time.sleep(delay_time)
            for psu in power_on_seq do
                psu_controller.turn_on_psu(psu["psu_id"])
            time.sleep(120)
            verify the DUT is reachable, fail the test if not
            execute "show reboot-cause", verify the output, fail the test if not "Power Loss"

# reboot by watch dog
The main idea of watch test case is to arm the watchdog for some seconds and check the reboot cause after system reloaded.
to arm the watchdog can be done by the following command:

    python -c "import sonic_platform.platform as P; P.Platform().get_chassis().get_watchdog().arm(5)"

The main procedure of the test:

    verify the DUT is reachable, fail the test if not
    arm the watchdog for 5 seconds
    time.sleep(130)
    verify the DUT is reachable, fail the test if not
    execute "show reboot-cause", verify the output, fail the test if not "Watchdog"


# reboot by commands
The main idea of reboot by command test is to reboot the DUT by command "reboot", "warm-reboot" and "fast-reboot" and then check reboot cause after system restarted.

    command_list = ["reboot", "warm-reboot", "fast-reboot"]
    expected
    for command in command_list do
        verify the DUT is reachable, fail the test if not
        issue the command
        time.sleep(120)
        verify the DUT is reachable, fail the test if not
        execute "show reboot-cause", verify the output, fail the test if not "user issue " + command + "command"

