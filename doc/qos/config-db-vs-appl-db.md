### Database design principles -- CONFIG_DB vs APPL_DB

In the current solution all buffer relavent tables are stored in CONFIG_DB which is supposed to contain the configuration supplied by user. However, some buffer data, including some entries in the BUFFER_PROFILE table and all entries in the BUFFER_PG table, are dynamically generated when ports' speed or cable length updated and will be cleared during `config qos reload`, which means they are not real configuration.

To have dynamic entries in CONFIG_DB is confusing. But a user is able to distinguish dynamic one from static one easily considering the following two points:

1. There are only limit number of combinations of speed, cable length pair, the number of dynamically generated entries in BUFFER_PROFILE table is small.
2. All entries in BUFFER_PG table are dynamically generated.

In this sense, to have dynamic and static entries mixed together mixed together isn't a big problem for now.

However, in this design the above 2 points will no longer be true because:

1. The variant cable length will be supported, which means the number of dynamically generated entries in BUFFER_PROFILE table which related to cable length can be much larger.
2. There is going to be headroom override which means BUFFER_PG and BUFFER_PROFILE table will contain both dynamic and static entries.

These will confuse user, making them difficult to distinguish static and dynamic entries and understand the configuration. In addition, this makes the logic of `config qos reload` more complicated, because it has to remain user supplied configuration while clearing all the dynamic entries.

To resolve the issue, we have the following principles in the database schema design:

1. All the configuration are stored in CONFIG_DB, including BUFFER_PG, BUFFER_POOL and BUFFER_PROFILE tables.
2. Dynamically generated tables are stored in APPL_DB.

