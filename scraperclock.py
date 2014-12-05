from apscheduler.scheduler import Scheduler
import logging
from marketscrape import *
from marketvalue import *
from mathutility import *
from items_map import *

from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy
from sqlalchemy import distinct, func, not_, or_, Table, Column, ForeignKey, desc

from rosterrun import q, db, MappedMarketResult, MappedMarketSearch, MappedGuildTransaction, MappedGuildTreasure

import sys

from rq import Queue, get_current_job
from rq.job import Job
from worker import conn
from datetime import datetime, timedelta

sched = Scheduler()
m = MarketScraper()
updated_search_items = search_items

user = sys.argv[1]
pw = sys.argv[2]

m.login(user, pw)

sched.scrapejob = None
sched.scrapejobid = None

#adding placeholders for points calculation
sched.pointscalcjob = None
sched.pointscalcjobid = None

logging.basicConfig()

@sched.interval_schedule(hours=12)
def interval_market_scrape():
  #send this to redis queue
  print 'This job runs every 12 hours.'
  
  updated_search_items = update_search_list()
  print 'searching for items'
  print updated_search_items
  print 'number of search items %s ' % len(updated_search_items)
  if len(updated_search_items) == 0:
    print 'no items to search'
    return
  
  sched.scrapejob = q.enqueue_call(func=m.get_scrape_results, args=(updated_search_items,), result_ttl=3000)
  print 'running calc %s ' % sched.scrapejob.id
  sched.scrapejobid = sched.scrapejob.id

def populate_search_list():
  ms = MappedMarketSearch.query.count()
  if ms > 0:
    return

  MappedMarketSearch.query.delete()
  db.session.commit()
  
  for k in search_items.keys():
    db.session.add(MappedMarketSearch(True, str(k), str(search_items[k])))
       
  db.session.commit()

def update_search_list():
  search_list = MappedMarketSearch.query.filter(MappedMarketSearch.search==True).all()	
  print 'reading search list from the db'
  print search_list
  return { i.itemid: i.name for i in search_list }
  
@sched.interval_schedule(minutes=1)
def retrieve_market_scrape():
  row_count = MappedMarketResult.query.count()
  #check row count to clean up market if it's over 9000 (dbz?)
  if row_count >= 9000:
    clean_up_market()
  
  #retrieve results from redis queue
  if sched.scrapejobid is None:
    print 'No scrape job found'
    return
  
  job_id = sched.scrapejobid
  currentjob = Job(connection=conn)
  
  try:
    currentjob = currentjob.fetch(job_id, connection=conn)
    print 'scrape job found'
  except:
    print 'job not available'
    sched.scrapejobid = None
    return
  
  print 'found job %s ' % currentjob
  print 'for job id %s ' % job_id
    
  if currentjob is not None:
    if currentjob.result is not None:
      marketresults = currentjob.result
      print 'found market results %s ' % marketresults
  
      #delete existing market results
         
      #cur = MappedMarketResult.query.filter_by(g_spreadsheet_id=str(session['g_spreadsheet_id']), g_worksheet_id=str(session['g_worksheet_id'])) 
    
      #[db.session.delete(c) for c in cur]  
      #db.session.commit()
      #mapped market result havs [itemid, name, cards, price, amount, title, vendor, coords, date]
      
      print 'adding to db'
      vals = marketresults.values()
      #flattenedvals = [item for sublist in vals for item in sublist]
      daterun = datetime.now()
      for k in marketresults.keys():
        [db.session.add(MappedMarketResult(str(mr.itemid), str(mr.name), str(mr.cards), str(mr.price), str(mr.amount), str(mr.title), str(mr.vendor), str(mr.coords), str(daterun))) for mr in marketresults[k]]
     
      db.session.commit()
      print 'added to db'
      print 'removing job results'
      currentjob.delete()
      print 'finished deleting job results'
      
      update_guild_treasure_with_market()
  else: 
    print 'current job is not ready %s' % job_id

def update_guild_treasure_with_market():
  print 'updating unpurchased guild treasure with market value if available'
  #get unpurchased treasures
  purchase_treasures_result = db.session.query(MappedGuildTransaction.guildtreasure_id).filter(MappedGuildTransaction.transType == u'purchase').all()
  purchase_treasures = [i[0] for i in purchase_treasures_result]
  unpurchased_guild_treasure = MappedGuildTreasure.query.filter(not_(MappedGuildTreasure.id.in_(purchase_treasures))).all()
  
  unpurchased_guild_treasure_ids = [u.itemid for u in unpurchased_guild_treasure]
  
  #get market results for unpurchased treasure
  d = datetime.now()
  latest_item = MappedMarketResult.query.order_by(MappedMarketResult.date.desc()).all()
  if len(latest_item) > 0:
    d = latest_item[0].date
  
  market_results = db.session.query(MappedMarketResult.itemid, func.min(MappedMarketResult.price)).filter(MappedMarketResult.itemid.in_(unpurchased_guild_treasure_ids)).filter(MappedMarketResult.date >= d).group_by(MappedMarketResult.itemid).all()
  
  #convert to a dictionary
  market_results_d = {}
  for mr in market_results:
    if market_results_d.has_key(mr[0]):
      market_results_d[mr[0]].append(mr[1])
    else:
      market_results_d[mr[0]] = [mr[1]]
    
  for k,v in market_results:
    market_results_d[k].append(v)
  
  #now dictionary
  market_results = min_values(market_results_d)
  
  #assign market results to unpurchased treasure
  for u in unpurchased_guild_treasure:
    k = u.itemid
    if market_results.has_key(k):
      price = market_results[k]
      u.minMarketPrice = price
      if price > u.maxMarketPrice:
        u.maxMarketPrice = price
      if price > u.medianMarketPrice:
        u.medianMarketPrice = price
  
  db.session.commit()
  print 'done updating unpurchased guild treasure with market value if available'
  
@sched.cron_schedule(day_of_week='sun', hour=5, minute=30)
def clean_up_market():
  #need to clean out database until expand number of rows.
  latest_item = MappedMarketResult.query.order_by(MappedMarketResult.date.desc()).all()
  if len(latest_item) > 0:
    d = latest_item[0].date
    
  d2 = d - timedelta(days = 7)
  print 'Clean up all but last 7 days of current market every last sunday of the month'
  rows = MappedMarketResult.query.filter(MappedMarketResult.date < d2).delete()
  print 'cleaning up %s rows' % rows
  db.session.commit()

@sched.cron_schedule(day='last sun')
def clean_up_market():
  latest_item = MappedMarketResult.query.order_by(MappedMarketResult.date.desc()).all()
  if len(latest_item) > 0:
    d = latest_item[0].date
    
  print 'Clean up all but current market every last sunday of the month'
  rows = MappedMarketResult.query.filter(MappedMarketResult.date < d).delete()
  print 'cleaning up %s rows' % rows
  db.session.commit()

populate_search_list()
interval_market_scrape()

sched.start()

while True:
  pass