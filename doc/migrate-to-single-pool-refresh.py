#!/usr/bin/python

from sonic_py_common import device_info, logger
from swsssdk import ConfigDBConnector
import time
import json
import subprocess

configdb = ConfigDBConnector(**{})
configdb.db_connect('CONFIG_DB')

def copy_profile_with_pool_replaced(profile, new_name, new_pool):
    profile['pool'] = '[BUFFER_POOL|{}]'.format(new_pool)
    configdb.set_entry('BUFFER_PROFILE', new_name, profile)


def copy_profile_list_with_profile_replaced(table, pl, port, profile_list):
    pl['profile_list'] = profile_list
    configdb.set_entry(table, port, pl)


def update_buffer_pool_size(poolname, default_config):
    pool = configdb.get_entry('BUFFER_POOL', poolname)
    pool['size'] = buffers['BUFFER_POOL'][poolname]['size']
    configdb.set_entry('BUFFER_POOL', poolname, pool)

# step 0: preparation: get all the necessary info
# fetch the meta data
metadata = configdb.get_entry('DEVICE_METADATA', 'localhost')
platform = metadata['platform']
hwsku = metadata['hwsku']

# fetch the default buffer configuration
_, skudir = device_info.get_paths_to_platform_and_hwsku_dirs()
buffer_file = '/tmp/buffers.json'
RENDER_BUFFER_CONF_CMD = '/usr/local/bin/sonic-cfggen -d -t {}/buffers.json.j2 > {}'.format(skudir, buffer_file)
p = subprocess.Popen(RENDER_BUFFER_CONF_CMD, shell=True, stdout=subprocess.PIPE)
out, err = p.communicate()
with open(buffer_file) as bf:
    buffers = json.load(bf)

# fetch the lossless pg profiles
pg_lossless_lookup_file = '{}/pg_profile_lookup.ini'.format(skudir)
with open(pg_lossless_lookup_file) as pf:
    lines = pf.readlines()

for line in lines:
    if line[0] == '#':
        continue
    speed, cable_length, size, xon, xoff, threshold = line.split()
    lossless_profile_key = 'pg_lossless_{}_{}_profile'.format(speed, cable_length)
    profile = {'size': size, 'xon': xon, 'xoff': xoff, 'dynamic_th': threshold, 'pool': '[BUFFER_POOL|ingress_lossless_pool]'}
    buffers['BUFFER_PROFILE'][lossless_profile_key] = profile

# step 1: Copy ingress_lossy_profile to ingress_lossy_profile_temp with pool updated to ingress_lossless_pool
ingress_lossy_profile_temp = configdb.get_entry('BUFFER_PROFILE', 'ingress_lossy_profile')
copy_profile_with_pool_replaced(ingress_lossy_profile_temp, 'ingress_lossy_profile_temp', 'ingress_lossless_pool')

# step 2: Update BUFFER_PG|<port>|0 with profile updated to ingress_lossy_profile_temp
pgs = configdb.get_table('BUFFER_PG')
for name, pg in pgs.iteritems():
    if pg['profile'] == '[BUFFER_PROFILE|ingress_lossy_profile]':
        pg['profile'] = '[BUFFER_PROFILE|ingress_lossy_profile_temp]'
        configdb.set_entry('BUFFER_PG', name, pg)

# step 3: Update BUFFER_PORT_INGRESS_PROFILE_LIST with ingress_lossy_profile removed.
profile_lists = configdb.get_table('BUFFER_PORT_INGRESS_PROFILE_LIST')
for port, pl in profile_lists.iteritems():
    copy_profile_list_with_profile_replaced('BUFFER_PORT_INGRESS_PROFILE_LIST', pl, port, '[BUFFER_PROFILE|ingress_lossless_profile]')

# step 4: Remove ingress_lossy_profile and recreate it by duplicating it from ingress_lossy_profile_temp
configdb.set_entry('BUFFER_PROFILE', 'ingress_lossy_profile', None)
time.sleep(60)
configdb.set_entry('BUFFER_PROFILE', 'ingress_lossy_profile', ingress_lossy_profile_temp)

# step 5: Enlarge the size of BUFFER_POOL.egress_lossy_pool
update_buffer_pool_size('egress_lossy_pool', buffers)

# step 6: Enlarge the size of BUFFER_POOL.ingress_lossless_pool
update_buffer_pool_size('ingress_lossless_pool', buffers)

# step 7: Update BUFFER_PG|<port>|0 with the profile updated to ingress_lossy_profile
pgs = configdb.get_table('BUFFER_PG')
for name, pg in pgs.iteritems():
    if pg['profile'] == '[BUFFER_PROFILE|ingress_lossy_profile_temp]':
        pg['profile'] = '[BUFFER_PROFILE|ingress_lossy_profile]'
        configdb.set_entry('BUFFER_PG', name, pg)

# step 8: Update all other profiles
profiles = configdb.get_table('BUFFER_PROFILE')
for name, profile in profiles.iteritems():
    if name in buffers['BUFFER_PROFILE'].keys():
        configdb.set_entry('BUFFER_PROFILE', name, buffers['BUFFER_PROFILE'][name])

# step 9: Remove the lossy pool
configdb.set_entry('BUFFER_POOL', 'ingress_lossy_pool', None)
configdb.set_entry('BUFFER_PROFILE', 'ingress_lossy_profile_temp', None)
