drop table if exists combinations;
create table combinations (
  id integer primary key autoincrement,
  g_spreadsheet_id integer not null,
  g_worksheet_id integer not null,
  partyIndex integer not null,
  instanceName text not null,
  playername text not null,
  name text not null,
  class text not null,
  rolename text not null
); 