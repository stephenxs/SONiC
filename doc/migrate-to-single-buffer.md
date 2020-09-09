## Background

Recently the requirement of supporting single ingress buffer pool has been opened. An import part of the requirement is to transmit a system running with two-ingress-pool mode into the one with single-ingress-pool mode with as less traffic penalty as possible. In this document, we will describe the steps by which we can achive this goal.

These steps can be done by running a script. In general, the script will:

- Merge ingress buffer pools to single one
- Update the related parameters, like pool sizes, headroom sizes.

## Design

### When should the script run?

The script should run after the system is updated to 201911 and stable.

### Steps in theory

To merge two ingress pools into one requires update the following entries:

- `BUFFER_POOL` table: update the size in `ingress_lossless_pool` and `egress_lossy_pool` pool and destroy `ingress_lossy_pool`
- `BUFFER_PROFILE` table: update `ingress_lossy_profile` by make it reference `ingress_lossless_pool`
- `BUFFER_PORT_INGRESS_PROFILE_LIST` table: remove the `ingress_lossy_profile` from the profile list of all ports because:
  - there is only 1 profile for each pool at most and `ingress_lossy_profile`
  - `ingress_lossless_profile` are pointing to the same pool now.

However, we can't update single field only of an object due to the limitation [issue #3971 redis sends unchanged field to orchagent when updating dynamic_th ](https://github.com/Azure/sonic-buildimage/issues/3971). We have two options to address the limitation.

1. To re-create the objects. As the `BUFFER_POOL` is the highest level of the dependent chain, the following objects need to be affected:

   - `BUFFER_POOL` table: update `ingress_lossless_pool` and `egress_lossy_pool`, and remove `ingress_lossy_pool`
   - `BUFFER_PROFILE` table: all profiles except `egress_lossless_profile`
   - `BUFFER_PG` table: all objects, because they are referencing the objects in `BUFFER_PROFILE` table
   - `BUFFER_QUEUE` table: all queue objects for lossy queue
   - `BUFFER_PORT_INGRESS_PROFILE_LIST` table: all objects
   - `BUFFER_QUEUE` and `BUFFER_PORT_EGRESS_PROFILE_LIST` table
2. To address the limitation and then update the entries in order.

Hence, we have two options for the steps. Option 1 is the steps without resolving the limitation and option 2 is the one with it.

Option 2 is preferred.

### Option 1

#### Steps in high level

In the high level, the steps should be like this:

1. Create a set of new objects of `BUFFER_POOL`, `BUFFER_PROFILE` tables.
2. Make the objects in `BUFFER_PG`, `BUFFER_QUEUE` `BUFFER_PORT_INGRESS_PROFILE_LIST` and `BUFFER_PORT_EGRESS_PROFILE_LIST` table point to the new buffer profile objects created in step 1.
3. Now we are safe to remove the original objects in `BUFFER_POOL` and `BUFFER_PROFILE` tables.
4. In theory, the system is working with single ingress pool now except that the names of buffer pools and buffer profiles are not the default ones.
    - This can cause a further issue when a new speed, cable length tuple occur for the first time in the system because the `buffermgrd` assume the lossless pool name as the original one.
    - We need to duplicate the objects created in step 1 and update objects updated in step 2.

5. Duplcate the objects created in step 1 in `BUFFER_POOL` and `BUFFER_PROFILE` tables.
6. Update the objects in `BUFFER_PG`, `BUFFER_QUEUE` `BUFFER_PORT_INGRESS_PROFILE_LIST` and `BUFFER_PORT_EGRESS_PROFILE_LIST` tables.
7. Remove objects created in step 1.

Notes:
1. In step 4 we can run into the issue [#5157 Orchagent received notifications in an order different from the order in which other daemons sent them](https://github.com/Azure/sonic-buildimage/issues/5157)
   We can delay some seconds between removing the profiles and pools, but it's still risky.
   Suggest to cherry-pick the fix of the issue to 201911 when it's available.
2. If PFC storm occurs and PFC zero buffer handler is used before step 2, 6, the `BUFFER_PG` table update can be stalled, thus failing the following steps.
   Suggest to turned off during the upgrading.

#### Detailed steps

1. Create a set of new objects in `BUFFER_POOL`:
    - `ingress_lossless_pool_new` for both lossless and lossy pools:
      - copied from `ingress_lossless_pool` with `size` updated to the new size
    - `egress_lossy_pool_new` with `size` updated:
      - copied from `egress_lossy_pool` with `size` updated to the new size
2. Create a set of profiles in `BUFFER_PROFILE` table for ingress lossless/lossy and egress lossy profile with the buffer pools to the ones created in step 1:
    - `ingress_lossless_profile_new`, `ingress_lossy_profile_new` and `pg_lossless_<speed>_<cable-length>_profile_new`
      - copied from the profiles without `_new` suffix, with `pool` pointing to `ingress_lossless_pool_new`
      - `xoff` and `size` updated accordingly for the profiles for lossless headroom
    - `egress_lossy_profile_new`, `q_lossy_profile_new`: copied from the profiles without `_new` suffix with `pool` pointing to `egress_lossy_pool_new`
3. Update the BUFFER_PG and BUFFER_QUEUE, making them reference the buffer profiles created in step 2
4. Update the BUFFER_PORT_INGRESS_PROFILE_LIST and BUFFER_PORT_EGRESS_PROFILE_LIST with the referenced profile replaced
5. Now we are safe to remove the old pools, profiles. Remove them.
6. Copy the buffer pools created in step 1 to their original names.
7. Copy the buffer profiles created in step 2 to their original names
8. Update the BUFFER_PG and BUFFER_QUEUE with the profiles replaced with the ones created in step 7
9. Update the BUFFER_PORT_INGRESS_PROFILE_LIST and BUFFER_PORT_EGRESS_PROFILE_LIST
10. Remove the immediate objects.

### Option 2

#### Resolve the limitation

The root cause of the issue is the orchagent tries modifying the SAI attributes which are create-only. So the solution is straightforward: for `SET` command, check whether the object has already been created:

- if yes, skip the create-only attributes.
- else, pass all the attributes to SAI.

#### Update the objects in a specific order

Limitations:

1. At any time, for any pool, only one profile using that pool can be in the `BUFFER_PORT_INGRESS_PROFILE_LIST`.
2. The `pool` attribute of a profile can not be changed. We need to create a temporary pool for lossy traffic to update its pool.
3. The total pool size can't exceed the maximum accumulative memory.

So the steps should be like this:

1. Copy `ingress_lossy_profile` to a new one named `ingress_lossy_profile_temp` with pool updated to `ingress_lossless_pool`.
2. Update `BUFFER_PG|<port>|0` with the `profile` updated to `ingress_lossy_profile_temp`.
3. Update `BUFFER_PORT_INGRESS_PROFILE_LIST` with `ingress_lossy_profile` removed.
4. Remove `ingress_lossy_profile` and recreate it by duplicating it from `ingress_lossy_profile_temp`.
5. Enlarge the size of `BUFFER_POOL.ingress_lossless_pool`.
6. Enlarge the size of `BUFFER_POOL.egress_lossy_pool`.
7. Update `BUFFER_PG|<port>|0` with the `profile` updated to `ingress_lossy_profile`.
8. Update other profiles.
