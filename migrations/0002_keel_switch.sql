create table if not exists keel_switch (
  id int primary key,
  enabled boolean not null default true
);

insert into keel_switch (id, enabled)
values (1, true)
on conflict (id) do nothing;
