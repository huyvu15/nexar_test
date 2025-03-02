bq load \
    --source_format=NEWLINE_DELIMITED_JSON \
    --json_extension=GEOJSON \
    game_analytics.game_events \
    gs://your-bucket/path/to/event_dump_*.json.gz \
    schema.json
