from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy
from sqlalchemy import Table, Column, ForeignKey, func
from sqlalchemy.orm import relationship, backref
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
  mi.mobs = mobs_for_instance
  populate_quests(mi, quests)
  db.session.commit()

def populate_data_model():
  for imi in instance_mob_item_mapping:
    populate_instances(imi[0], imi[1], imi[2], imi[3], imi[4], imi[5])
  
  MappedGuild.query.delete()
  db.session.commit()
 
  #add placeholder guild
  mg = MappedGuild('Knights of Hyrule', [], [], [], [])
  db.session.add(mg)
  
  db.session.commit()