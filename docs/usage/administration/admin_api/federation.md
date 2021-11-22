# Federation API

This API allows a server administrator to manage the federation.

**Note**: This API is new, experimental and "subject to change".

## List of destinations

This API gets the current status of the destinations of federation.


The API is:

```
GET /_synapse/admin/v1/federation/destinations
```

Returning:

```json
{
    "enabled": true,
    "current_updates": {
        "<db_name>": {
            "name": "<background_update_name>",
            "total_item_count": 50,
            "total_duration_ms": 10000.0,
            "average_items_per_ms": 2.2,
        },
    }
}
```

`enabled` whether the background updates are enabled or disabled.

`db_name` the database name (usually Synapse is configured with a single database named 'master').

For each update:

`name` the name of the update.
`total_item_count` total number of "items" processed (the meaning of 'items' depends on the update in question).
`total_duration_ms` how long the background process has been running, not including time spent sleeping.
`average_items_per_ms` how many items are processed per millisecond based on an exponential average.
