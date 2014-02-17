from rq import Queue, get_current_job
from rq.job import Job
from worker import conn

import os
from flask import Flask
from scheduler import run_scheduler_OAuth, scheduler, testConnectToSpreadsheetsServiceOAuth, Combination, initializeDataOAuth, Character
#import sqlite3
from flask import Flask, request, session, g, redirect, url_for, \
     abort, render_template, flash
from contextlib import closing
from flask.ext.sqlalchemy import SQLAlchemy
from sqlalchemy import distinct, func, not_

import gdata.gauth
import gdata.docs.client

from parseurl import parseUrl
from oauth2client import client
from oauth2client.client import OAuth2WebServerFlow

import pickle
from google.appengine.api import memcache
from google.appengine.api import users

from google.appengine.ext import db
from oauth2client.appengine import CredentialsProperty
from credentialsmodel import CredentialsModel
from google.appengine.api import users
from oauth2client.appengine import StorageByKeyName
import datastorestub

from guildpoints import *
from marketscrape import *
from marketvalue import *
from mathutility import *
from items_map import *

import pygal
from pygal.style import LightStyle
from itertools import groupby

#import dev_appserver
#os.environ['PATH'] = str(dev_appserver.EXTRA_PATHS) + str(os.environ['PATH'])

#fill in by after registering application with google
CONSUMER_KEY = 'rosterrun.herokuapp.com'
CONSUMER_SECRET = 'RaWdj6OlSO36AReeLPiPx7Uc'
CLIENT_ID = '900730400111-npfbpmda6jtc8mmu7fn3ifm67fckim5b.apps.googleusercontent.com'
CLIENT_SECRET = 'RaWdj6OlSO36AReeLPiPx7Uc'
SCOPES = ['https://spreadsheets.google.com/feeds/']
REDIRECT_URI = 'http://rosterrun.herokuapp.com/auth_return'
#REDIRECT_URI = 'http://127.0.0.1:5000/auth_return'

flow = OAuth2WebServerFlow(client_id=CLIENT_ID, client_secret=CLIENT_SECRET, scope=SCOPES, redirect_uri=REDIRECT_URI)
# configuration
DATABASE = 'scheduler.db'
DEBUG = True
SECRET_KEY = 'development key'
USERNAME = 'admin'
PASSWORD = 'default'

app = Flask(__name__)
app.config.from_object(__name__)
#Heroku Postgres SQL url obtained when deployed
#app.config['SQLALCHEMY_DATABASE_URI'] = 'http://127.0.0.1:5000/auth_return'
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['DATABASE_URL']
db = SQLAlchemy(app)

q = Queue(connection=conn, default_timeout=3600)

class PartyCombo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    g_spreadsheet_id = db.Column(db.String(80))
    g_worksheet_id = db.Column(db.String(80))
    partyIndex = db.Column(db.String(80))
    instanceName = db.Column(db.String(80))
    playerName = db.Column(db.String(80))
    name = db.Column(db.String(80))
    className = db.Column(db.String(80))
    rolename = db.Column(db.String(80))

    def __init__(self, spreadsheet_id, worksheet_id, pIndex, iName, pName, cName, cClass, rName):
        self.g_spreadsheet_id = spreadsheet_id
        self.g_worksheet_id = worksheet_id
	self.partyIndex = pIndex
  	self.instanceName = iName
	self.playerName = pName
	self.name = cName
	self.className = cClass
	self.rolename = rName

    def __repr__(self):
        return '<PartyCombo %r>' % self.playerName

class MappedGuild(db.Model):
    __tablename__ = 'guild'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80))
    
    guildTreasures = db.relationship('MappedGuildTreasure', backref='guildTreasures', lazy='dynamic')
    guildPoints = db.relationship('MappedGuildPoint', backref='guildPoints', lazy='dynamic')
    chars = db.relationship('MappedCharacter')
    
    def __init__(self, name, chars, guildTreasures, guildPoints):
    	self.name = name
    	self.chars = chars
    	self.guildTreasures = guildTreasures
    	self.guildPoints = guildPoints
    
    def __repr__(self):
        return '<MappedGuild %r>' % self.name

class MappedCharacter(db.Model):
    __tablename__ = 'guild_characters'
    id = db.Column(db.Integer, primary_key=True)
    g_spreadsheet_id = db.Column(db.String(80))
    g_worksheet_id = db.Column(db.String(80))
    Class = db.Column(db.String(80))
    Name = db.Column(db.String(80))
    Role = db.Column(db.String(80))
    Quests = db.Column(db.String(280))
    LastRun = db.Column(db.String(80))
    PlayerName = db.Column(db.String(80))
    Present = db.Column(db.String(80))
    guild_id = db.Column(db.Integer, db.ForeignKey('guild.id'))
    guild = db.relationship('MappedGuild', backref='characters', uselist=False)
    
    def __init__(self, spreadsheet_id, worksheet_id, characterClass, characterName, role, quests, lastRun, playerName, present):
        self.g_spreadsheet_id = spreadsheet_id
        self.g_worksheet_id = worksheet_id
	self.Class = characterClass
	self.Name = characterName
	self.Role = role
	self.Quests = quests
	self.LastRun = lastRun
	self.PlayerName = playerName
	self.Present = present
    
    def __repr__(self):
        return '<MappedCharacter %r>' % self.playerName

class MappedGuildTreasure(db.Model):
    __tablename__ = 'guild_treasures'
    id = db.Column(db.Integer, primary_key=True)
    itemid = db.Column(db.Integer)
    name = db.Column(db.String(80))
    cards = db.Column(db.String(160))
    amount = db.Column(db.Float)
    minMarketPrice = db.Column(db.Float)
    maxMarketPrice = db.Column(db.Float)
    medianMarketPrice = db.Column(db.Float)
    refreshDate = db.Column(db.DateTime)
    guild_id = db.Column(db.Integer, db.ForeignKey('guild.id'))
    guild = db.relationship('MappedGuild', backref='treasures', uselist=False)
  
    def __init__(self, itemid, name, cards, amount, minMarketPrice, maxMarketPrice, medianMarketPrice, refreshDate):
        self.itemid = itemid
        self.name = name
        self.cards = cards
        self.amount = amount
        self.minMarketPrice = minMarketPrice
        self.maxMarketPrice = maxMarketPrice
        self.medianMarketPrice = medianMarketPrice
        self.refreshDate = refreshDate
        
    def __repr__(self):
        return '<MappedGuildTreasure %r>' % self.name   

class MappedGuildPoint(db.Model):
    __tablename__ = 'guild_points'
    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer)
    amount = db.Column(db.Float)
    guild_id = db.Column(db.Integer, db.ForeignKey('guild.id'))
    guild = db.relationship('MappedGuild', backref='points', uselist=False)
    guildtransaction = db.relationship("MappedGuildTransaction", uselist=False, backref="transactions")
 
    def __init__(self, playerid, amount):
        self.player_id = playerid
        self.amount = amount
        
    def __repr__(self):
        return '<MappedGuildPoint %r>' % self.id

class MappedGuildTransaction(db.Model):
    __tablename__ = 'guild_transactions'
    id = db.Column(db.Integer, primary_key=True)
    guildpoint_id = db.Column(db.Integer, db.ForeignKey('guild_points.id'))
    guildtreasure_id = db.Column(db.Integer, db.ForeignKey('guild_treasures.id'))
    guildtreasure = db.relationship('MappedGuildTreasure', backref='transactions')
 
    transType = db.Column(db.String(16))
    transDate = db.Column(db.DateTime)
    guild_id = db.Column(db.Integer, db.ForeignKey('guild.id'))
    guild = db.relationship('MappedGuild', backref='transactions', uselist=False)
 
    def __init__(self, playerid, amount):
        self.player_id = playerid
        self.amount = amount
        
    def __repr__(self):
        return '<MappedGuildTransaction %r>' % self.id     

class MappedMarketResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    itemid = db.Column(db.Integer)
    name = db.Column(db.String(80))
    cards = db.Column(db.String(160))
    price = db.Column(db.Float)
    amount = db.Column(db.Float)
    title = db.Column(db.String(280))
    vendor = db.Column(db.String(80))
    coords = db.Column(db.String(80))
    date = db.Column(db.DateTime)
        
    def __init__(self, itemid, name, cards, price, amount, title, vendor, coords, date):
        self.itemid = itemid
        self.name = name
	self.cards = cards
	self.price = price
	self.amount = amount
	self.title = title
	self.vendor = vendor
	self.coords = coords
	self.date = date
    
    def __repr__(self):
        return '<MappedMarketResult %r>' % self.name

class MappedMarketSearch(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    search = db.Column(db.Boolean)
    itemid = db.Column(db.Integer)
    name = db.Column(db.String(80))
        
    def __init__(self, search, itemid, name):
        self.search = search
        self.itemid = itemid
        self.name = name
	
    def __repr__(self):
        return '<MappedMarketSearch %r>' % self.name

sched = scheduler()

def resetParameters():
    session['user'] = None
    session['pw'] = None
    session['doc'] = None

def resetLookupParameters():
    session['g_spreadsheet_id'] = None
    session['g_worksheet_id'] = None

@app.route('/', methods=['GET', 'POST'])
def show_entries():   
    if not session.get('logged_in'):
      #abort(401)
      flash('Please login again')
      session.pop('logged_in', None)
      return redirect(url_for('login'))
 
    action = None
    availableParties = []
    chars = []
    checkCalculation()    
    
    try:
      session['doc'] = request.form['gdocname'].strip()
      action = request.form['action']
    except:
      print 'cannot find gdoc name'
    if action == u"Import":
      import_characters()
    elif action == u"Calculate":
      flash('Running Calculation')
      run_calculation()
    elif action == u"Reset":
      reset()
    elif action == u"Refresh":
      checkCalculation()
    else:
      print 'show entries'
    
    try:
      if 'g_spreadsheet_id' in session and 'g_worksheet_id' in session:
        print 'already have ids in session ', session['g_spreadsheet_id'], session['g_worksheet_id']
        cur = PartyCombo.query.filter_by(g_spreadsheet_id=session['g_spreadsheet_id'], g_worksheet_id=session['g_worksheet_id'])
        availableParties = [Combination(c.partyIndex, c.instanceName, c.playerName, c.name, c.className, c.rolename) for c in cur]
        curChars = MappedCharacter.query.filter_by(g_spreadsheet_id=session['g_spreadsheet_id'], g_worksheet_id=session['g_worksheet_id'])
        chars = [Character(c.PlayerName, c.Class, c.Name, c.Role, c.Quests.split('|'), c.LastRun, c.Present) for c in curChars]
        print 'AVAILABLE PARTIES %s ' % len(availableParties)  
      else:
        print 'could not find the spreadsheet id'
        #try to retrieve the token from the db
        loginConfiguration(session['user'])
        user = users.get_current_user()
        storage = StorageByKeyName(CredentialsModel, str(user), 'credentials')
        credentials = storage.get()   
        if credentials is None:
          flash('Please login again')
          session.pop('logged_in', None)
          return redirect(url_for('login'))
        (g_s_id, g_w_id) = testConnectToSpreadsheetsServiceOAuth(credentials, session['doc'])
        session['g_spreadsheet_id'] = g_s_id
        session['g_worksheet_id'] = g_w_id    
        cur = PartyCombo.query.filter_by(g_spreadsheet_id=str(session['g_spreadsheet_id']), g_worksheet_id=str(session['g_worksheet_id'])) 
        availableParties = [Combination(c.partyIndex, c.instanceName, c.playerName, c.name, c.className, c.rolename) for c in cur]
        curChars = MappedCharacter.query.filter_by(g_spreadsheet_id=session['g_spreadsheet_id'], g_worksheet_id=session['g_worksheet_id'])
        chars = [Character(c.PlayerName, c.Class, c.Name, c.Role, c.Quests.split('|'), c.LastRun, c.Present) for c in curChars]
        
        print 'now found available parties %s' % len(availableParties)  
    except:
      print 'issue finding the available parties'
      resetLookupParameters()
      
    if len(availableParties) == 0:
      print 'get all combinations'
      cur = PartyCombo.query.all()
      availableParties = [Combination(c.partyIndex, c.instanceName, c.playerName, c.name, c.className, c.rolename) for c in cur]    
      curChars = MappedCharacter.query.all()
      chars = [Character(c.PlayerName, c.Class, c.Name, c.Role, c.Quests.split('|'), c.LastRun, c.Present) for c in curChars]
    
    #map points back from characters and guild?
    
    
    return render_template('show_entries.html', combinations=availableParties, characters=chars)

@app.route('/market_results', methods=['GET', 'POST'])
def market_results():
  if not session.get('logged_in'):
    #abort(401)
    flash('Please login again')
    session.pop('logged_in', None)
    return redirect(url_for('login'))
    
  d = datetime.now()
  latest_item = MappedMarketResult.query.order_by(MappedMarketResult.date.desc()).all()
  if len(latest_item) > 0:
    d = latest_item[0].date
  mr = MappedMarketResult.query.filter(MappedMarketResult.date >= d).all()
  
  #format data
  mrs = [MarketResult(m.itemid, m.name, m.cards.split(',')[:-1], m.price, m.amount, m.title, m.vendor, m.coords, m.date) for m in mr]
  return render_template('market_results.html', marketresults=mrs)

@app.route('/market_current_results', methods=['GET', 'POST'])
def market_current_results():
  if not session.get('logged_in'):
    #abort(401)
    flash('Please login again')
    session.pop('logged_in', None)
    return redirect(url_for('login'))
    
  #how to get latest?
  d = datetime.now()
  latest_item = MappedMarketResult.query.order_by(MappedMarketResult.date.desc()).all()
  if len(latest_item) > 0:
    d = latest_item[0].date
  mr = MappedMarketResult.query.filter(MappedMarketResult.date >= d).all()
  
  #format data
  mrs = [MarketResult(m.itemid, m.name, m.cards.split(',')[:-1], m.price, m.amount, m.title, m.vendor, m.coords, m.date) for m in mr]
  return render_template('market_results.html', marketresults=mrs)

def convert_to_key(itemid = None, name = None, cards = []):
  res = ""
  res = str(itemid) + "_" + str(name)
  if len(cards) == 0:
    return res
  
  res = res + "_" + "".join(cards)
  return res

@app.route('/market_history', methods=['GET', 'POST'])
def market_history():
  if not session.get('logged_in'):
    #abort(401)
    flash('Please login again')
    session.pop('logged_in', None)
    return redirect(url_for('login'))
    
  mr = MappedMarketResult.query.order_by(MappedMarketResult.itemid.asc(), MappedMarketResult.price.asc(), MappedMarketResult.date.desc()).all()
  
  #format data
  mrs = [MarketResult(m.itemid, m.name, m.cards.split(',')[:-1], m.price, m.amount, m.title, m.vendor, m.coords, m.date) for m in mr]
  
  projected_results = [(convert_to_key(m.itemid, m.name, m.cards), (m.date, int(m.price))) for m in mrs]  
  #print projected_results

  res_dict = {}
  for key, group in groupby(projected_results, lambda x: x[0]):
    for pr in group:
      if key in res_dict.keys():
        res_dict[key].append(pr[1])
      else:
        res_dict[key] = [pr[1]]
  
  datey = pygal.DateY(x_label_rotation=20, human_readable=True, stroke=False, style=LightStyle, truncate_legend=200, truncate_label=200, legend_font_size=12, tooltip_font_size=16, legend_at_bottom=True, y_title='Price', x_title='Date')
  datey.title = "Market History Overview"
  [datey.add(k, res_dict[k]) for k in res_dict.keys()]
  histchart = datey.render()
  
  return render_template('market_history.html', marketresults=mrs, histchart=histchart)

@app.route('/market_search_list', methods=['GET', 'POST'])
def market_search_list():
  if not session.get('logged_in'):
    #abort(401)
    flash('Please login again')
    session.pop('logged_in', None)
    return redirect(url_for('login'))
  
  #way to manage item search list  
  ms = MappedMarketSearch.query.order_by(MappedMarketSearch.itemid.asc()).all()
  
  return render_template('market_search.html', marketsearchs=ms)
  
@app.route('/treasury', methods=['GET', 'POST'])
def treasury():
  if not session.get('logged_in'):
    #abort(401)
    flash('Please login again')
    session.pop('logged_in', None)
    return redirect(url_for('login'))
    
  t = MappedGuildTreasure.query.all()
  
  return render_template('treasury.html', treasures=t)
  
@app.route('/points', methods=['GET', 'POST'])
def points():
  if not session.get('logged_in'):
    #abort(401)
    flash('Please login again')
    session.pop('logged_in', None)
    return redirect(url_for('login'))
    
  action = None
  p = []
  try:
    sesson = request.form['action']
  except:
    print 'cannot bind action'
  
  p = MappedGuildPoint.query.all()
  
  return render_template('points.html', points=p)

def use_default_search_list():
  if not session.get('logged_in'):
    #abort(401)
    flash('Please login again')
    session.pop('logged_in', None)
    return redirect(url_for('login'))
    
  MappedMarketSearch.query.delete()
  db.session.commit()
  
  for k in search_items.keys():
    db.session.add(MappedMarketSearch(True, str(k), str(search_items[k])))
       
  db.session.commit()

@app.route('/update_search_list', methods=['GET', 'POST'])
def update_search_list():
  if not session.get('logged_in'):
    #abort(401)
    flash('Please login again')
    session.pop('logged_in', None)
    return redirect(url_for('login'))
  
  action = None
  try:
    action = request.form['action']
  except:
    print 'cannot bind action'
  print action
  
  if action == u"Use Default":
    use_default_search_list()
    print 'used default search list'
  elif action == u"Save":
    search_itemids = request.form.getlist("cbsearch")
    search_itemids = [int(si) for si in search_itemids]
  
    nosearch = MappedMarketSearch.query.filter(~MappedMarketSearch.itemid.in_(search_itemids)).all()
    for ns in nosearch:
      ns.search = False
  
    exists = MappedMarketSearch.query.filter(MappedMarketSearch.itemid.in_(search_itemids)).all()
    for e in exists:
      e.search = True
        
    db.session.commit()
    
    print 'saved search list'
  
  ms = MappedMarketSearch.query.order_by(MappedMarketSearch.itemid.asc()).all()
    
  return render_template('market_search.html', marketsearchs=ms)

@app.route('/add_to_search_list', methods=['GET', 'POST'])
def add_to_search_list():
  if not session.get('logged_in'):
    #abort(401)
    flash('Please login again')
    session.pop('logged_in', None)
    return redirect(url_for('login'))
  
  itemid = request.form['nitemid'].strip()
  itemname = request.form['nname'].strip()
  exists = MappedMarketSearch.query.filter(MappedMarketSearch.itemid==itemid).all()
  if len(exists) == 0:
    #can add item to search list
    db.session.add(MappedMarketSearch(True, itemid, itemname))
  else:
    for se in exists:
      se.search = True
      se.name = itemname
      
  db.session.commit()
  ms = MappedMarketSearch.query.order_by(MappedMarketSearch.itemid.asc()).all()
    
  return render_template('market_search.html', marketsearchs=ms)

@app.route('/update_chars', methods=['GET', 'POST'])
def update_chars():
  if not session.get('logged_in'):
    #abort(401)
    flash('Please login again')
    session.pop('logged_in', None)
    return redirect(url_for('login'))
  
  
  #do something to populate fields with current character
  action = None
  p = []
  try:
    sesson = request.form['action']
  except:
    print 'cannot bind action'
  
  mc = MappedCharacter.query.all()
  
  return render_template('show_entries.html')

@app.route('/add_character', methods=['GET', 'POST'])
def add_character():
  if not session.get('logged_in'):
    #abort(401)
    flash('Please login again')
    session.pop('logged_in', None)
    return redirect(url_for('login'))
  
  #do something to save / edit current character
  action = None
  p = []
  try:
    sesson = request.form['action']
  except:
    print 'cannot bind action'
  
  mc = MappedCharacter.query.all()
  
  return render_template('show_entries.html')

@app.route('/import_characters', methods=['POST'])
def import_characters():
    try:
      if not session.get('logged_in'):
        #abort(401)
        flash('Please login again')
        session.pop('logged_in', None)
        return redirect(url_for('login'))
    
      if(len(session['doc']) <= 0):
          flash('Must include relevant document name')
          return redirect(url_for('show_entries'))

      if('g_spreadsheet_id' in session.keys() and 'g_worksheet_id' in session.keys()):
        cur = MappedCharacter.query.filter_by(g_spreadsheet_id=str(session['g_spreadsheet_id']), g_worksheet_id=str(session['g_worksheet_id'])) 
        [db.session.delete(c) for c in cur]  
        db.session.commit()
    
      loginConfiguration(session['user'])
      user = users.get_current_user()
      storage = StorageByKeyName(CredentialsModel, str(user), 'credentials')
      credentials = storage.get()   
      if credentials is None:
        flash('Please login again')
        session.pop('logged_in', None)
        return redirect(url_for('login'))
     
      (g_s_id, g_w_id) = testConnectToSpreadsheetsServiceOAuth(credentials, session['doc'])
      if(g_s_id == -1 or g_w_id == -1):
        flash('Cannot connect to google document.  Please check spreadsheet name, google credentials and connectivity.')
        return redirect(url_for('show_entries'))
 
      session['g_spreadsheet_id'] = g_s_id
      session['g_worksheet_id'] = g_w_id
      basequests = ['tripatriateunionsfeud', 'attitudetothenewworld', 'ringofthewiseking', 'newsurroundings', 'twotribes', 'pursuingrayanmoore', 'reportfromthenewworld', 'guardianofyggsdrasilstep9', 'onwardtothenewworld']
      chars = initializeDataOAuth(credentials, session['doc'], basequests)
      print 'FOUND %s CHARS' % len(chars)
      #parties combinations have [PartyIndex,InstanceName,PlayerName,CharacterName,CharacterClass,RoleName']
      [db.session.add(MappedCharacter(str(session['g_spreadsheet_id']), str(session['g_worksheet_id']), str(c.Class), str(c.Name), str(c.Role.Name), str('|'.join(c.Quests)), str(c.LastRun), str(c.PlayerName), str(c.Present))) for c in chars]
      
      db.session.commit()
      flash('Import finished')
    except Exception,e: 
      print str(e)
      print 'error importing'
    return redirect(url_for('show_entries'))

@app.route('/runcalc', methods=['POST'])
def run_calculation():
    try:
      if not session.get('logged_in'):
        #abort(401)
        flash('Please login again')
        session.pop('logged_in', None)
        return redirect(url_for('login'))
    
      if(len(session['doc']) <= 0):
          flash('Must include relevant document name')
          return redirect(url_for('show_entries'))

      if('g_spreadsheet_id' in session.keys() and 'g_worksheet_id' in session.keys()):
        cur = PartyCombo.query.filter_by(g_spreadsheet_id=str(session['g_spreadsheet_id']), g_worksheet_id=str(session['g_worksheet_id'])) 
        [db.session.delete(c) for c in cur]  
        db.session.commit()
    
      loginConfiguration(session['user'])
      user = users.get_current_user()
      storage = StorageByKeyName(CredentialsModel, str(user), 'credentials')
      credentials = storage.get()   
      if credentials is None:
        flash('Please login again')
        session.pop('logged_in', None)
        return redirect(url_for('login'))
    
      (g_s_id, g_w_id) = testConnectToSpreadsheetsServiceOAuth(credentials, session['doc'])
      if(g_s_id == -1 or g_w_id == -1):
        flash('Cannot connect to google document.  Please check spreadsheet name, google credentials and connectivity.')
        return redirect(url_for('show_entries'))

      session['g_spreadsheet_id'] = g_s_id
      session['g_worksheet_id'] = g_w_id
      
      #consider calculating from imported results if possible
      calcjob = q.enqueue_call(func=run_scheduler_OAuth, args=(credentials, session['doc'],), result_ttl=3000)
      print 'running calc %s ' % calcjob.id
      session['job_id'] = calcjob.id
      
    except:
      print 'error running calculation'
    return redirect(url_for('show_entries'))

@app.route('/checkcalc', methods=['POST'])
def checkCalculation():
  if not session.get('logged_in'):
    #abort(401)
    flash('Please login again')
    session.pop('logged_in', None)
    return redirect(url_for('login'))
  
  try:
    if 'job_id' in session.keys():
      job_id = session['job_id']
      print 'using job id %s ' % job_id
      currentjob = Job(connection=conn)
      currentjob = currentjob.fetch(job_id, connection=conn)
      print 'found job %s ' % currentjob
      
      if currentjob is not None:
        if currentjob.result is not None:
          parties = currentjob.result
          print parties
          
          cur = PartyCombo.query.filter_by(g_spreadsheet_id=str(session['g_spreadsheet_id']), g_worksheet_id=str(session['g_worksheet_id'])) 
	         
	  [db.session.delete(c) for c in cur]  
          db.session.commit()
          #parties combinations have [PartyIndex,InstanceName,PlayerName,CharacterName,CharacterClass,RoleName']
          for i in range(0, len(parties) - 1):
            [db.session.add(PartyCombo(str(session['g_spreadsheet_id']), str(session['g_worksheet_id']), str(c.PartyIndex), str(c.InstanceName), str(c.PlayerName), str(c.CharacterName), str(c.CharacterClass), str(c.RoleName))) for c in parties[i]]
       
          db.session.commit()
          
      else: 
        flash('Calculation not finished yet.')
        print 'current job is not ready %s' % job_id
    else:
      flash('Please recalculate before refresh')
      print 'No job in session'
  except:
    print 'error occurred trying to fetch job'
    session.pop('job_id', None)
  return redirect(url_for('show_entries'))

@app.route('/reset', methods=['POST'])
def reset():
    try:
      if not session.get('logged_in'):
        #abort(401)
        flash('Please login again')
        session.pop('logged_in', None)
        return redirect(url_for('login'))

      if(len(session['doc']) <= 0):
        flash('Must include relevant document name')
        return redirect(url_for('show_entries'))
  
      loginConfiguration(session['user'])
      user = users.get_current_user()
      storage = StorageByKeyName(CredentialsModel, str(user), 'credentials')
      credentials = storage.get()    
      if credentials is None:
        flash('Cannot log in to spreadsheet')
        session.pop('logged_in', None)
        return redirect(url_for('login'))
    
      (g_s_id, g_w_id) = testConnectToSpreadsheetsServiceOAuth(credentials, session['doc'])
      if(g_s_id == -1 or g_w_id == -1):
        flash('Cannot connect to google document.  Please check spreadsheet name, google credentials and connectivity.')
        return redirect(url_for('show_entries'))
  
      session['g_spreadsheet_id'] = g_s_id
      session['g_worksheet_id'] = g_w_id
         
      cur = PartyCombo.query.filter_by(g_spreadsheet_id=str(session['g_spreadsheet_id']), g_worksheet_id=str(session['g_worksheet_id'])) 
       
      [db.session.delete(c) for c in cur]  
      db.session.commit()

      cur = MappedCharacter.query.filter_by(g_spreadsheet_id=str(session['g_spreadsheet_id']), g_worksheet_id=str(session['g_worksheet_id'])) 
      [db.session.delete(c) for c in cur]  
      db.session.commit()  
    
      flash('Reset party combinations')
    except:
      print 'error reseting'
      
    return redirect(url_for('show_entries')) 

@app.route('/auth_return', methods=['GET', 'POST'])
def oauth2callback():
    try:
      codeValue = parseUrl(request, 'code')
      if len(codeValue) > 0:
        #Store credentials
        credentials = flow.step2_exchange(codeValue)
        user = users.get_current_user()
        storage = StorageByKeyName(CredentialsModel, str(user), 'credentials')
        storage.put(credentials)    
        session['logged_in'] = True
        #credentials stored
        flash('You were logged in')
        return redirect(url_for('show_entries'))
    except: 
      print 'error with oauth2callback'
 
@app.route('/login', methods=['GET', 'POST'])
def login():
    try:
      resetParameters()
      error = None    
    
      if request.method == 'POST':
          if len(request.form['username']) == 0:
              error = 'Invalid username'
          else:
              username = request.form['username'].strip()
              session['user'] = username

              loginConfiguration(username)
              flow = OAuth2WebServerFlow(client_id=CLIENT_ID, client_secret=CLIENT_SECRET, scope=SCOPES, redirect_uri=REDIRECT_URI)
              #print flow
  #            user = users.get_current_user()
  #            print user.user_id()
       #       memcache.set(user.user_id(), pickle.dumps(flow))
            
              auth_uri = flow.step1_get_authorize_url()
              #print auth_uri
            
    #          flow = pickle.loads(memcache.get(user.user_id()))            
              #print flow
            
              return redirect(auth_uri)
              #
              #If the user has previously granted your application access, the authorization server immediately redirects again to redirect_uri. If the user has not yet granted access, the authorization server asks them to grant your application access. If they grant access, they get redirected to redirect_uri with a code query string parameter similar to the following:
	      #
	      #http://example.com/auth_return/?code=kACAH-1Ng1MImB...AA7acjdY9pTD9M
	      #If they deny access, they get redirected to redirect_uri with an error query string parameter similar to the following:
	      #
	      #http://example.com/auth_return/?error=access_denied
	      #
      return render_template('login.html', error=error)
    except:
      print 'error with login'
      return render_template('login.html', error='Please give permissions to log in')

@app.route('/logout')
def logout():
    try:
      session.pop('logged_in', None)
      flash('You were logged out')
      return redirect(url_for('show_entries'))
    except:
      print 'error with logout'
      return redirect(url_for('show_entries'))  

def loginConfiguration(username, userid=1):
  try:
    print 'running with user %s ' % username
    os.environ['USER_EMAIL'] = username
    #can this a default?
    os.environ['USER_ID'] = str(userid)
    os.environ['AUTH_DOMAIN'] = 'testbed'
    os.environ['APPLICATION_ID'] = 'roster run'
  except:
    print 'error with login configuration'

if __name__ == "__main__":
  db.create_all()
  db.session.commit()
  app.run()