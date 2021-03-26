#!/usr/bin/python

from sonic_py_common import device_info, logger
from swsssdk import ConfigDBConnector
import time

configdb = ConfigDBConnector(**{})
configdb.db_connect('CONFIG_DB')

def copy_profile_with_pool_replaced(profile, new_name, new_pool):
    profile['pool'] = '[BUFFER_POOL|{}]'.format(new_pool)
    configdb.set_entry('BUFFER_PROFILE', new_name, profile)


def copy_profile_list_with_profile_replaced(table, pl, port, profile_list):
    pl['profile_list'] = profile_list
    configdb.set_entry(table, port, pl)


# step 1: Create a new buffer pools for lossy and lossless: ingress_lossless_pool_new.
#         It can be copied from ingress_lossless_pool with size updated properly.
ingress_pool = {'type': 'ingress', 'mode': 'dynamic', 'size': '7719936'}
egress_lossy_pool = {'type': 'egress', 'mode': 'dynamic', 'size': '7719936'}
configdb.set_entry('BUFFER_POOL', 'ingress_pool', ingress_pool)
configdb.set_entry('BUFFER_POOL', 'egress_lossy_pool_new', egress_lossy_pool)

# step 2: Create the following new buffer profiles based on the new ingress pool
profiles = configdb.get_table('BUFFER_PROFILE')
for name, profile in profiles.iteritems():
    if name[0:12] == 'pg_lossless_' or name[0:12] == 'ingress_loss':
        copy_profile_with_pool_replaced(profile, name + '_new', 'ingress_pool')
    if name == 'egress_lossy_profile' or name == 'q_lossy_profile':
        copy_profile_with_pool_replaced(profile, name + '_new', 'egress_lossy_pool_new')

# step 3: Update the BUFFER_PG and BUFFER_QUEUE
pgs = configdb.get_table('BUFFER_PG')
for name, pg in pgs.iteritems():
    pg['profile'] = pg['profile'][:-1] + '_new]'
    configdb.set_entry('BUFFER_PG', name, pg)

queues = configdb.get_table('BUFFER_QUEUE')
for name, queue in queues.iteritems():
    port, tc = name
    if tc != '3-4':
        queue['profile'] = queue['profile'][:-1] + '_new]'
        configdb.set_entry('BUFFER_QUEUE', name, queue)

# step 4: Update the BUFFER_PORT_INGRESS_PROFILE_LIST and BUFFER_PORT_EGRESS_PROFILE_LIST
profile_lists = configdb.get_table('BUFFER_PORT_INGRESS_PROFILE_LIST')
for port, pl in profile_lists.iteritems():
    copy_profile_list_with_profile_replaced('BUFFER_PORT_INGRESS_PROFILE_LIST', pl, port, '[BUFFER_PROFILE|ingress_lossless_profile_new]')
profile_lists = configdb.get_table('BUFFER_PORT_EGRESS_PROFILE_LIST')
for port, pl in profile_lists.iteritems():
    copy_profile_list_with_profile_replaced('BUFFER_PORT_EGRESS_PROFILE_LIST', pl, port, '[BUFFER_PROFILE|egress_lossless_profile],[BUFFER_PROFILE|egress_lossy_profile_new]')

# step 5: now, we're safe to remove the old objects
for name in profiles.keys():
    if name[0:12] == 'pg_lossless_' or name[0:12] == 'ingress_loss' or name == 'egress_lossy_profile' or name == 'q_lossy_profile':
        configdb.set_entry('BUFFER_PROFILE', name, None)
configdb.set_entry('BUFFER_POOL', 'ingress_lossless_pool', None)
configdb.set_entry('BUFFER_POOL', 'ingress_lossy_pool', None)
configdb.set_entry('BUFFER_POOL', 'egress_lossy_pool', None)
# wait for some seconds to be sure that SAI finishes handling of removing

# setp 6: copy the ingress_pool to ingress_lossless_pool which is the original name
configdb.set_entry('BUFFER_POOL', 'ingress_lossless_pool', ingress_pool)
configdb.set_entry('BUFFER_POOL', 'egress_lossy_pool', egress_lossy_pool)

# setp 7: copy the buffer profiles with _new suffix to ones without the suffix with the pool replaced
profiles = configdb.get_table('BUFFER_PROFILE')
for name, profile in profiles.iteritems():
    if name == 'egress_lossy_profile_new' or name == 'q_lossy_profile_new':
        copy_profile_with_pool_replaced(profile, name[:-4], 'egress_lossy_pool')
    elif name[-4:] == '_new':
        copy_profile_with_pool_replaced(profile, name[:-4], 'ingress_lossless_pool')

# step 8: update the BUFFER_PG and BUFFER_QUEUE
pgs = configdb.get_table('BUFFER_PG')
for name, pg in pgs.iteritems():
    pg['profile'] = pg['profile'][:-5] + ']'
    configdb.set_entry('BUFFER_PG', name, pg)

queues = configdb.get_table('BUFFER_QUEUE')
for name, queue in queues.iteritems():
    port, tc = name
    if tc != '3-4':
        queue['profile'] = queue['profile'][:-5] + ']'
        configdb.set_entry('BUFFER_QUEUE', name, queue)

# step 9: update the buffer profile list
profile_lists = configdb.get_table('BUFFER_PORT_INGRESS_PROFILE_LIST')
for port, pl in profile_lists.iteritems():
    copy_profile_list_with_profile_replaced('BUFFER_PORT_INGRESS_PROFILE_LIST', pl, port, '[BUFFER_PROFILE|ingress_lossless_profile]')
profile_lists = configdb.get_table('BUFFER_PORT_EGRESS_PROFILE_LIST')
for port, pl in profile_lists.iteritems():
    copy_profile_list_with_profile_replaced('BUFFER_PORT_EGRESS_PROFILE_LIST', pl, port, '[BUFFER_PROFILE|egress_lossless_profile],[BUFFER_PROFILE|egress_lossy_profile]')

# step 10: remove the intermedia objects
for name in profiles.keys():
    if name[-4:] == '_new':
        configdb.set_entry('BUFFER_PROFILE', name, None)
configdb.set_entry('BUFFER_POOL', 'ingress_pool', None)
configdb.set_entry('BUFFER_POOL', 'egress_lossy_pool_new', None)
