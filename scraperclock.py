from apscheduler.scheduler import Scheduler
import logging
from marketscrape import *
from items_map import *

from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy

from rosterrun import q, db, MappedMarketResult, MappedMarketSearch

import sys

from rq import Queue, get_current_job
from rq.job import Job
from worker import conn
from datetime import datetime

sched = Scheduler()
m = MarketScraper()
updated_search_items = search_items

user = sys.argv[1]
pw = sys.argv[2]

print user
print pw
m.login(user, pw)

sched.scrapejob = None
sched.scrapejobid = None
logging.basicConfig()

@sched.interval_schedule(hours=12)
def interval_market_scrape():
  #send this to redis queue
  updated_search_items = update_search_list()
  sched.scrapejob = q.enqueue_call(func=m.get_scrape_results, args=(search_items,), result_ttl=3000)
  print 'running calc %s ' % sched.scrapejob.id
  print 'This job runs every 12 hours.'
  sched.scrapejobid = sched.scrapejob.id

def populate_search_list():
  MappedMarketSearch.query.delete()
  db.session.commit()
  
  for k in search_items.keys():
    db.session.add(MappedMarketSearch(True, str(k), str(search_items[k]))
       
  db.session.commit()

def update_search_list():
  search_list = MappedMarketSearch.query.filter(MappedMarketSearch.search==True).all()	
  return { i.itemid: i.name for i in search_list }
  
@sched.interval_schedule(minutes=1)
def retrieve_market_scrape():
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
  else: 
    print 'current job is not ready %s' % job_id
  

#@sched.cron_schedule(day_of_week='mon-fri', hour=17)
#def scheduled_job():
#    print 'This job is run every weekday at 5pm.'

populate_search_list()
interval_market_scrape()

sched.start()

while True:
    pass