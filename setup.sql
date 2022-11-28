
create table motion_events (
    ts timestamptz not null,
    device_id text not null,
    motion bool
);