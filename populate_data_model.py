from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy
from sqlalchemy import Table, Column, ForeignKey, func
from sqlalchemy.orm import relationship, backref
from sqlalchemy.engine import reflection
from sqlalchemy import create_engine
from sqlalchemy.schema import (
    MetaData,
    Table,
    DropTable,
    ForeignKeyConstraint,
    DropConstraint,
    )
from datetime import datetime, timedelta

from items_map import *
from scheduler import *
from rosterrun import *

def populate_quests(mi, quest_list):
  for q in quest_list:
    mq = MappedQuest(q)
    mi.quests.append(mq)
    db.session.add(mq)
  db.session.commit()
  
def populate_mob_items(mm, mob_items):
  for miv in mob_items:
    mob_item = MappedMobItem(miv[0])
    mob_item.item_drop_rate = miv[1]
    mm.items.append(mob_item)
  db.session.commit()

def populate_instances(instance_name, median_party, mob_id_name_items = [], quests = []):
  mi = MappedInstance(instance_name, median_party)
  mobs_for_instance = []
  
  #mob_id_name_item: mob_id, mob_name, items
  for mob_id_name_item in mob_id_name_items:
    mm = MappedMob(mob_id_name_item[0])
    mm.mob_name = mob_id_name_item[1]
    populate_mob_items(mm, mob_id_name_item[2])
    mobs_for_instance.append(mm)
    db.session.add(mm)
  mi.mobs = mobs_for_instance
  populate_quests(mi, quests)
  db.session.commit()

def db_DropEverything(db):
  # From http://www.sqlalchemy.org/trac/wiki/UsageRecipes/DropEverything

  conn=db.engine.connect()
  
  # the transaction only applies if the DB supports
  # transactional DDL, i.e. Postgresql, MS SQL Server
  trans = conn.begin()

  inspector = reflection.Inspector.from_engine(db.engine)

  # gather all data first before dropping anything.
  # some DBs lock after things have been dropped in 
  # a transaction.
  metadata = MetaData()

  tbs = []
  all_fks = []

  for table_name in inspector.get_table_names():
    fks = []
    for fk in inspector.get_foreign_keys(table_name):
      if not fk['name']:
        continue
      fks.append(
        ForeignKeyConstraint((),(),name=fk['name'])
        )
    t = Table(table_name,metadata,*fks)
    tbs.append(t)
    all_fks.extend(fks)

  for fkc in all_fks:
    conn.execute(DropConstraint(fkc))

  for table in tbs:
    conn.execute(DropTable(table))

  trans.commit()

def populate_data_model():
  for imi in instance_mob_item_mapping:
    populate_instances(imi[0], imi[1], imi[2], imi[3])
  
  MappedGuild.query.delete()
  db.session.commit()
 
  #add placeholder guild
  mg = MappedGuild('Knights of Hyrule', [], [], [], [])
  db.session.add(mg)
  
  db.session.commit()

def clean_data_model():
  db.session.commit()
  db.drop_all()
  db.session.commit()
  db.create_all()
  db.session.commit()