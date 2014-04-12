from rq import Queue, get_current_job
from rq.job import Job
from worker import conn

import os
from flask import Flask
from scheduler import run_scheduler_OAuth, scheduler, testConnectToSpreadsheetsServiceOAuth, Combination, initializeDataOAuth, Character, AllRoles, roleUnmapped
from scheduler import Character, Role, Instance
#import sqlite3
from flask import Flask, request, session, g, redirect, url_for, \
     abort, render_template, flash
from contextlib import closing
from flask.ext.sqlalchemy import SQLAlchemy
from sqlalchemy import distinct, func, not_, or_, Table, Column, ForeignKey
from sqlalchemy.orm import relationship, backref
import getpass

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

from marketscrape import *
from marketvalue import *
from mathutility import *
from items_map import *
from char_class_map import *

import pygal
from pygal.style import LightStyle
from itertools import groupby

from datetime import datetime, timedelta
import boto
from boto.s3.key import Key
import uuid
from werkzeug import secure_filename

#from data_model import *

#import dev_appserver
#os.environ['PATH'] = str(dev_appserver.EXTRA_PATHS) + str(os.environ['PATH'])

#fill in by after registering application with google
CONSUMER_KEY = os.environ['CONSUMER_KEY']
CONSUMER_SECRET = os.environ['CONSUMER_SECRET']
CLIENT_ID = os.environ['CLIENT_ID']
CLIENT_SECRET = os.environ['CLIENT_SECRET']
SCOPES = ['https://spreadsheets.google.com/feeds/']
REDIRECT_URI = os.environ['REDIRECT_URI']
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

app.config['UPLOAD_FOLDER'] = 'tmp/'
app.config['ALLOWED_EXTENSIONS'] = set(['txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'])

m_user = os.environ['M_User']
m_password = os.environ['M_Pass']

sched = scheduler()
marketscraper = MarketScraper()

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
    
    guildTreasures = db.relationship('MappedGuildTreasure', backref='guild', lazy='dynamic')
    guildPoints = db.relationship('MappedGuildPoint', backref='guild', lazy='dynamic')
    guildTransactions = db.relationship('MappedGuildTransaction', backref='guild', lazy='dynamic')
    guildChars = db.relationship("MappedCharacter", backref="guild")
    
    def __init__(self, name, guildChars, guildTreasures, guildPoints, guildTransactions):
    	self.name = name
    	self.guildChars = guildChars
    	self.guildTreasures = guildTreasures
    	self.guildPoints = guildPoints
    	self.guildTransactions = guildTransactions
    
    def __repr__(self):
        return '<MappedGuild %r>' % self.name        
        
association_table = db.Table('run_to_characters', db.metadata,
    db.Column('run_id', db.Integer, ForeignKey('run.id')),
    db.Column('guild_characters_id', db.Integer, ForeignKey('guild_characters.id'))
)

#do we need a mapped instance type?

class MappedInstance(db.Model):
    __tablename__ = 'instance'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80))
    quests = relationship("MappedQuest", backref="instance")
    mobs = relationship("MappedMob", backref="instance")
    median_players = db.Column(db.Integer)
    #placeholder for now.  will update.
    
    def __init__(self, name, median_players):
        self.name = name
        self.median_players = median_players
        	
    def __repr__(self):
        return '<MappedInstance %r>' % self.name

association_table_quests_characters = Table('quests_to_characters', db.metadata,
    db.Column('quest_id', db.Integer, ForeignKey('quest.id')),
    db.Column('guild_characters_id', db.Integer, ForeignKey('guild_characters.id'))
)

class MappedQuest(db.Model):
    __tablename__ = 'quest'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255))
    internal_name = db.Column(db.String(255))
    mapped_instance_id = db.Column(db.Integer, ForeignKey('instance.id'))
    
    def __init__(self, name):
        self.name = name
        self.internal_name = name.replace(' ', '').lower()
            	
    def __repr__(self):
        return '<MappedQuest %r>' % self.name

run_to_mobs = db.Table('run_to_mobs', db.metadata,
    db.Column('run_id', db.Integer, ForeignKey('run.id')),
    db.Column('mob_id', db.Integer, ForeignKey('mob.id'))
)

run_to_instance = db.Table('run_to_instance', db.metadata,
    db.Column('run_id', db.Integer, ForeignKey('run.id')),
    db.Column('instance_id', db.Integer, ForeignKey('instance.id'))
)

class MappedRun(db.Model):
    __tablename__ = 'run'
    id = db.Column(db.Integer, primary_key=True)
    evidence_url = db.Column(db.String(400))
    evidence_file_path = db.Column(db.String(400))
    name = db.Column(db.String(400))
    date = db.Column(db.DateTime)
    chars = relationship("MappedCharacter", secondary=association_table, backref="runs")
    instance = relationship("MappedInstance", secondary=run_to_instance, backref="instance", uselist=False)
    success = db.Column(db.Boolean)
    notes = db.Column(db.String(400))
    points = relationship("MappedGuildPoint", backref="run")
    credits = relationship("RunCredit", backref="run")
    mobs_killed = relationship("MappedMob", secondary=run_to_mobs, backref="run")
    
    def __init__(self, evidence_url, evidence_file_path, name, date, chars, instance, mobs_killed, success, notes):
        self.evidence_url = evidence_url
        self.evidence_file_path = evidence_file_path
        self.date = date
        self.chars = chars
        self.name = name
        self.instance = instance
        self.mobs_killed = mobs_killed
        self.success = success
    	self.notes = notes
    	
    def __repr__(self):
        return '<MappedRun %r>' % self.name

class MappedMob(db.Model):
    __tablename__ = 'mob'
    id = db.Column(db.Integer, primary_key=True)
    mob_id = db.Column(db.Integer)
    mob_name = db.Column(db.String(80))
    items = relationship("MappedMobItem", backref="mob")
    mapped_instance_id = db.Column(db.Integer, ForeignKey('instance.id'))
    
    def __init__(self, mob_id):
        self.mob_id = mob_id
    	
    def __repr__(self):
        return '<MappedMob %r>' % self.mob_id

class MappedMobItem(db.Model):
    __tablename__ = 'mob_item'
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer)
    item_name = db.Column(db.String(80))
    item_drop_rate = db.Column(db.Float)
    mapped_mob_id = db.Column(db.Integer, ForeignKey('mob.id'))
    
    def __init__(self, item_id):
        self.item_id = item_id
        
    def __repr__(self):
        return '<MappedMobItem %r>' % self.item_id

class MappedPlayer(db.Model):
    __tablename__ = 'player'
    id = db.Column(db.Integer, primary_key=True)
    Name = db.Column(db.String(80))
    Email = db.Column(db.String(250))
    Chars = db.relationship("MappedCharacter", backref="player")
    Points = db.relationship("MappedGuildPoint", backref="player")
    Credits = db.relationship("RunCredit", backref="player")
    Transactions = db.relationship("MappedGuildTransaction", backref="player")
    
    def __init__(self, Name, Email):
        self.Name = Name
	self.Email = Email
    
    def __repr__(self):
        return '<MappedPlayer %r>' % self.Name

class MappedCharacter(db.Model):
    __tablename__ = 'guild_characters'
    id = db.Column(db.Integer, primary_key=True)
    g_spreadsheet_id = db.Column(db.String(80))
    g_worksheet_id = db.Column(db.String(80))
    Class = db.Column(db.String(80))
    Name = db.Column(db.String(80))
    Role = db.Column(db.String(80))
    Quests = db.relationship("MappedQuest", secondary=association_table_quests_characters, backref="guild_characters")
    LastRun = db.Column(db.String(80))
    PlayerName = db.Column(db.String(80))
    Present = db.Column(db.String(80))
    mappedguild_id = db.Column(db.Integer, ForeignKey('guild.id'))
    mappedplayer_id = db.Column(db.Integer, ForeignKey('player.id'))
    
    def __init__(self, spreadsheet_id, worksheet_id, characterClass, characterName, role, lastRun, playerName, present):
        self.g_spreadsheet_id = spreadsheet_id
        self.g_worksheet_id = worksheet_id
	self.Class = characterClass
	self.Name = characterName
	self.Role = role
	self.LastRun = lastRun
	self.PlayerName = playerName
	self.Present = present
    
    def __repr__(self):
        return '<MappedCharacter %r>' % self.PlayerName

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
    guild_id = db.Column(db.Integer, ForeignKey('guild.id'))
    guildtransaction = db.relationship("MappedGuildTransaction", uselist=False, backref="guild_treasures")
  
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

class RunCredit(db.Model):
    __tablename__ = 'run_credits'
    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'))
    run_id = db.Column(db.Integer, db.ForeignKey('run.id'))
    factor = db.Column(db.Float)

    def __init__(self, factor):
        self.factor = factor
            
    def __repr__(self):
        return '<RunCredit %r>' % self.id

class MappedGuildPoint(db.Model):
    __tablename__ = 'guild_points'
    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'))
    run_id = db.Column(db.Integer, db.ForeignKey('run.id'))
    amount = db.Column(db.Float)
    guild_id = db.Column(db.Integer, db.ForeignKey('guild.id'))
    guildtransaction = db.relationship("MappedGuildTransaction", uselist=False, backref="guild_points")
 
    def __init__(self, amount):
        self.amount = amount
        
    def __repr__(self):
        return '<MappedGuildPoint %r>' % self.id

class MappedGuildTransaction(db.Model):
    __tablename__ = 'guild_transactions'
    id = db.Column(db.Integer, primary_key=True)
    guildpoint_id = db.Column(db.Integer, db.ForeignKey('guild_points.id'))
    guildtreasure_id = db.Column(db.Integer, db.ForeignKey('guild_treasures.id'))
 
    transType = db.Column(db.String(16))
    transDate = db.Column(db.DateTime)
    guild_id = db.Column(db.Integer, db.ForeignKey('guild.id'))
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'))
    to_player_name = db.Column(db.String(80))
    
    def __init__(self, transType, transDate):
        self.transType = transType
        self.transDate = transDate
        
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

def resetParameters():
  session['user'] = None
  session['pw'] = None
  session['doc'] = None

def resetLookupParameters():
  session['g_spreadsheet_id'] = None
  session['g_worksheet_id'] = None

@app.route('/', methods=['GET', 'POST'])
def show_entries():   
  if not session.get('logged_in') or not session.get('user'):
    #abort(401)
    clear_session()
    return redirect(url_for('login'))
 
  action = None
  availableParties = []
  chars = []
  checkCalculation() 
  ec = None
  
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
      chars = [Character(c.PlayerName, c.Class, c.Name, c.Role, [q.name for q in c.Quests], c.LastRun, c.Present) for c in curChars]
      print 'AVAILABLE PARTIES %s ' % len(availableParties)  
    else:
      print 'could not find the spreadsheet id'
      #try to retrieve the token from the db
      loginConfiguration(session['user'])
      user = users.get_current_user()
      storage = StorageByKeyName(CredentialsModel, str(user), 'credentials')
      credentials = storage.get()   
      if credentials is None:
        session.pop('logged_in', None)
        return redirect(url_for('login'))
      (g_s_id, g_w_id) = testConnectToSpreadsheetsServiceOAuth(credentials, session['doc'])
      session['g_spreadsheet_id'] = g_s_id
      session['g_worksheet_id'] = g_w_id    
      cur = PartyCombo.query.filter_by(g_spreadsheet_id=str(session['g_spreadsheet_id']), g_worksheet_id=str(session['g_worksheet_id'])) 
      availableParties = [Combination(c.partyIndex, c.instanceName, c.playerName, c.name, c.className, c.rolename) for c in cur]
      curChars = MappedCharacter.query.filter_by(g_spreadsheet_id=session['g_spreadsheet_id'], g_worksheet_id=session['g_worksheet_id'])
      chars = [Character(c.PlayerName, c.Class, c.Name, c.Role, [q.name for q in c.Quests], c.LastRun, c.Present) for c in curChars]
      
      print 'now found available parties %s' % len(availableParties)  
  except:
    print 'issue finding the available parties'
    resetLookupParameters()
    
  if len(availableParties) == 0:
    print 'get all combinations'
    cur = PartyCombo.query.all()
    availableParties = [Combination(c.partyIndex, c.instanceName, c.playerName, c.name, c.className, c.rolename) for c in cur]    
    curChars = MappedCharacter.query.all()
    chars = [Character(c.PlayerName, c.Class, c.Name, c.Role, [q.name for q in c.Quests], c.LastRun, c.Present) for c in curChars]

  all_quest_names = db.session.query(MappedQuest.name, func.max(MappedQuest.id)).group_by(MappedQuest.name).all()
  aqns = [aqn[1] for aqn in all_quest_names]
  quests = MappedQuest.query.filter(MappedQuest.id.in_(aqns)).all()
  ec = MappedCharacter(session['g_spreadsheet_id'], session['g_worksheet_id'], 'High Wizard', 'Billdalf', None, datetime.now(), 'Billy', 'true')
  ec.Quests = quests
  ecq = [q.id for q in ec.Quests]
  
  #map points back from characters and guild?
  
  return render_template('show_entries.html', combinations=availableParties, characters=curChars, editcharacter=ec, edit_character_quests=ecq, mappedquests=quests)

@app.route('/viable_parties', methods=['GET', 'POST'])
def viable_parties():   
  if not session.get('logged_in') or not session.get('user'):
    #abort(401)
    clear_session()
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
      chars = [Character(c.PlayerName, c.Class, c.Name, c.Role, [q.name for q in c.Quests], c.LastRun, c.Present) for c in curChars]
      print 'AVAILABLE PARTIES %s ' % len(availableParties)  
    else:
      print 'could not find the spreadsheet id'
      #try to retrieve the token from the db
      loginConfiguration(session['user'])
      user = users.get_current_user()
      storage = StorageByKeyName(CredentialsModel, str(user), 'credentials')
      credentials = storage.get()   
      if credentials is None:
        session.pop('logged_in', None)
        return redirect(url_for('login'))
      (g_s_id, g_w_id) = testConnectToSpreadsheetsServiceOAuth(credentials, session['doc'])
      session['g_spreadsheet_id'] = g_s_id
      session['g_worksheet_id'] = g_w_id    
      cur = PartyCombo.query.filter_by(g_spreadsheet_id=str(session['g_spreadsheet_id']), g_worksheet_id=str(session['g_worksheet_id'])) 
      availableParties = [Combination(c.partyIndex, c.instanceName, c.playerName, c.name, c.className, c.rolename) for c in cur]
      curChars = MappedCharacter.query.filter_by(g_spreadsheet_id=session['g_spreadsheet_id'], g_worksheet_id=session['g_worksheet_id'])
      chars = [Character(c.PlayerName, c.Class, c.Name, c.Role, [q.name for q in c.Quests], c.LastRun, c.Present) for c in curChars]
      
      print 'now found available parties %s' % len(availableParties)  
  except Exception,e: 
    print str(e)
    print 'issue finding the available parties'
    resetLookupParameters()
    
  if len(availableParties) == 0:
    print 'get all combinations'
    cur = PartyCombo.query.all()
    availableParties = [Combination(c.partyIndex, c.instanceName, c.playerName, c.name, c.className, c.rolename) for c in cur]    
    curChars = MappedCharacter.query.all()
    chars = [Character(c.PlayerName, c.Class, c.Name, c.Role, [q.name for q in c.Quests], c.LastRun, c.Present) for c in curChars]
  
  #map points back from characters and guild?
  
  return render_template('viable_parties.html', combinations=availableParties, characters=chars)

def convert_to_key(itemid = None, name = None, cards = None, date = None, amount = None):
  res = ""
  if itemid is not None:
    res = str(itemid)
  if name is not None:
    res = res + " " + str(name)
  if cards is not None:
    res = res + " " + "".join(cards)
  if date is not None:
    res = res + " " + date
  if amount is not None:
    res = res + " " + amount
  
  return res

@app.route('/market_results', methods=['GET', 'POST'])
def market_results():
  if not session.get('logged_in') or not session.get('user'):
    #abort(401)
    clear_session()
    return redirect(url_for('login'))
    
  d = datetime.now()
  latest_item = MappedMarketResult.query.order_by(MappedMarketResult.date.desc()).all()
  if len(latest_item) > 0:
    d = latest_item[0].date
    
  mr = []
  #mr = MappedMarketResult.query.filter(MappedMarketResult.date >= d).all()
  ms = MappedMarketSearch.query.order_by(MappedMarketSearch.name.asc()).all()

  #format data
  mrs = [MarketResult(m.itemid, m.name, m.cards.split(','), m.price, m.amount, m.title, m.vendor, m.coords, m.date) for m in mr]
  
  #prices
  datey = pygal.DateY(x_label_rotation=20, no_data_text='No result found', disable_xml_declaration=True, dots_size=5, legend_font_size=18, legend_box_size=18, value_font_size=16, label_font_size=14, tooltip_font_size=18, human_readable=True, style=LightStyle, truncate_legend=200, truncate_label=200, legend_at_bottom=True, y_title='Price', x_title='Date', x_labels_major_every=2)
  datey.title = "Current Prices"
  datey.x_label_format = "%Y-%m-%d"
    
  pricechart = datey.render()
    
  #volumes
      
  bar_chart = pygal.StackedBar(x_label_rotation=20, no_data_text='No result found', disable_xml_declaration=True, dots_size=5, legend_font_size=18, legend_box_size=18, value_font_size=16, label_font_size=14, tooltip_font_size=18, human_readable=True, stroke=False, style=LightStyle, truncate_legend=200, truncate_label=200, legend_at_bottom=True, y_title='Quantity', x_title='Items', x_labels_major_every=2)
  bar_chart.title = "Current Selling Volume"
  
  volumechart = bar_chart.render()
  
  return render_template('market_results.html', marketsearchs=ms, marketresults=mrs, pricechart=pricechart, volumechart=volumechart)

@app.route('/market_current_results', methods=['GET', 'POST'])
def market_current_results():
  if not session.get('logged_in') or not session.get('user'):
    #abort(401)
    clear_session()
    return redirect(url_for('login'))
    
  d = datetime.now()
  latest_item = MappedMarketResult.query.order_by(MappedMarketResult.date.desc()).all()
  if len(latest_item) > 0:
    d = latest_item[0].date
  
  mr = []
  #mr = MappedMarketResult.query.filter(MappedMarketResult.date >= d).all()
  ms = MappedMarketSearch.query.order_by(MappedMarketSearch.name.asc()).all()
  
  #format data
  mrs = [MarketResult(m.itemid, m.name, m.cards.split(','), m.price, m.amount, m.title, m.vendor, m.coords, m.date) for m in mr]
  
  #prices
  datey = pygal.Bar(x_label_rotation=20, no_data_text='No result found', disable_xml_declaration=True, dots_size=5, human_readable=True, style=LightStyle, y_title='Price', x_title='Date')
  datey.title = "Current Prices"
      
  pricechart = datey.render()
    
  #volumes
      
  bar_chart = pygal.StackedBar(x_label_rotation=20, no_data_text='No result found', disable_xml_declaration=True, human_readable=True, style=LightStyle, y_title='Quantity', x_title='Items')
  bar_chart.title = "Current Selling Volume"
  
  volumechart = bar_chart.render()
  
  return render_template('market_results.html', marketsearchs=ms, marketresults=mrs, pricechart=pricechart, volumechart=volumechart)

@app.route('/item_current_results', methods=['GET', 'POST'])
def item_current_results():
  if not session.get('logged_in') or not session.get('user'):
    #abort(401)
    clear_session()
    return redirect(url_for('login'))
  
  print 'in item current results'
  val = None
  try:
    val = request.form['itemslist']
    print val
  except:
    print 'value not found'
    val = None
    
  d = datetime.now()
  latest_item = MappedMarketResult.query.order_by(MappedMarketResult.date.desc()).all()
  if len(latest_item) > 0:
    d = latest_item[0].date
  
  ms = MappedMarketSearch.query.order_by(MappedMarketSearch.name.asc()).all()
  itemname = None
  mr = []
  if val is not None:
    itemname = MappedMarketSearch.query.filter(MappedMarketSearch.itemid==val).all()[0].name
    itemname = itemname.replace(' ','')
    mr = MappedMarketResult.query.filter(or_(MappedMarketResult.itemid==val,MappedMarketResult.cards.contains(itemname))).filter(MappedMarketResult.date >= d).order_by(MappedMarketResult.itemid.asc(), MappedMarketResult.price.asc(), MappedMarketResult.date.desc()).all()
  else:
    mr = MappedMarketResult.query.filter(MappedMarketResult.itemid==val).filter(MappedMarketResult.date >= d).order_by(MappedMarketResult.itemid.asc(), MappedMarketResult.price.asc(), MappedMarketResult.date.desc()).all()
  
  #format data
  mrs = [MarketResult(m.itemid, m.name, m.cards.split(','), m.price, m.amount, m.title, m.vendor, m.coords, m.date) for m in mr]
  
  #prices
  projected_results = [(convert_to_key(None, m.name, m.cards), {'value':int(m.price), 'label':convert_to_key(None, m.name, m.cards)}) for m in mrs]  
  
  res_dict = {}
  for key, group in groupby(projected_results, lambda x: x[0]):
    for pr in group:
      if key in res_dict.keys():
        res_dict[key].append(pr[1])
      else:
        res_dict[key] = [pr[1]]
  
  datey = pygal.Bar(x_label_rotation=20, no_data_text='No result found', stroke=False, disable_xml_declaration=True, dots_size=5, legend_font_size=18, legend_box_size=18, value_font_size=16, label_font_size=14, tooltip_font_size=18, human_readable=True, style=LightStyle, truncate_legend=15, truncate_label=200, y_title='Price', x_title='Item %s' % val)
  datey.title = "Current Prices for %s as of %s" % (val, d.strftime('%d %b %Y'))
  
  [datey.add(k, res_dict[k]) for k in res_dict.keys()]
    
  pricechart = datey.render()
  
  #volumes
  mr_dates = MappedMarketResult.query.filter(MappedMarketResult.date >= d).filter(MappedMarketResult.itemid==val).distinct().all()
  dates = [mrd.date.strftime('%d, %b %Y') for mrd in mr_dates]
  dates = list(set(dates))
  print dates
  mrs = [MarketResult(m.itemid, m.name, m.cards.split(','), m.price, m.amount, m.title, m.vendor, m.coords, m.date) for m in mr]
  
  projected_results = [(convert_to_key(None, m.name, m.cards, m.date.strftime('%d, %B %Y')), {'value': int(m.amount), 'label':convert_to_key(None, m.name, m.cards, m.date.strftime('%d, %b %Y'))}) for m in mrs]
  res_dict = {}
  for key, group in groupby(projected_results, lambda x: x[0]):
    for pr in group:
      if key in res_dict.keys():
        res_dict[key].append(pr[1])
      else:
        res_dict[key] = [pr[1]]
    
  bar_chart = pygal.StackedBar(x_label_rotation=20, no_data_text='No result found', disable_xml_declaration=True, dots_size=5, legend_font_size=18, legend_box_size=18, value_font_size=16, label_font_size=14, tooltip_font_size=18, human_readable=True, stroke=False, style=LightStyle, truncate_legend=15, truncate_label=200, y_title='Quantity', x_title='Item %s' % val)
  bar_chart.title = "Current Selling Volume for %s as of %s" % (val, d.strftime('%d %b %Y'))
  [bar_chart.add(k, res_dict[k]) for k in res_dict.keys()]

  volumechart = bar_chart.render()
  
  return render_template('market_results.html', marketsearchs=ms, marketresults=mrs, pricechart=pricechart, volumechart=volumechart)

@app.route('/item_history', methods=['GET', 'POST'])
def item_history():
  if not session.get('logged_in') or not session.get('user'):
    #abort(401)
    clear_session()
    return redirect(url_for('login'))
  
  print 'in item history'
  val = None
  try:
    val = request.form['itemslist']
    print val
  except:
    print 'value not found'
  
  time_delta = datetime.now() - timedelta(weeks=4)
  
  ms = MappedMarketSearch.query.order_by(MappedMarketSearch.name.asc()).all()
  itemname = None
  mr = []
  if val is not None:
    itemname = MappedMarketSearch.query.filter(MappedMarketSearch.itemid==val).all()[0].name
    itemname = itemname.replace(' ','')
    mr = MappedMarketResult.query.filter(or_(MappedMarketResult.itemid==val,MappedMarketResult.cards.contains(itemname))).order_by(MappedMarketResult.itemid.asc(), MappedMarketResult.price.asc(), MappedMarketResult.date.desc()).limit(30)
  else:
    mr = MappedMarketResult.query.filter(MappedMarketResult.itemid==val).order_by(MappedMarketResult.itemid.asc(), MappedMarketResult.price.asc(), MappedMarketResult.date.desc()).limit(30)

  if mr.count() > 0:
    time_delta = mr[-1].date    
  
  #format data
  mrs = [MarketResult(m.itemid, m.name, m.cards.split(','), m.price, m.amount, m.title, m.vendor, m.coords, m.date) for m in mr]
  
  #prices
  #can convert date values for daily, weekly, monthly?
  projected_results = [(convert_to_key(None, m.name, m.cards), {'value':(datetime.strptime(m.date.strftime('%d %B %Y'), '%d %B %Y'), int(m.price)), 'label':convert_to_key(None, m.name, m.cards, m.date.strftime('%d, %b %Y'))}) for m in mrs]  
  
  res_dict = {}
  for key, group in groupby(projected_results, lambda x: x[0]):
    for pr in group:
      if key in res_dict.keys():
        res_dict[key].append(pr[1])
      else:
        res_dict[key] = [pr[1]]
  
  datey = pygal.DateY(x_label_rotation=20, no_data_text='No result found', disable_xml_declaration=True, dots_size=5, legend_font_size=18, legend_box_size=18, value_font_size=16, label_font_size=14, tooltip_font_size=18, human_readable=True, style=LightStyle, truncate_legend=15, truncate_label=200, y_title='Price', x_title='Date', x_labels_major_every=2)
  datey.title = "Historical Selling Price for %s since %s" % (val, time_delta.strftime('%d %B %Y'))
  datey.x_label_format = "%d-%B-%Y"
  [datey.add(k, res_dict[k]) for k in res_dict.keys()]

  pricechart = datey.render()
    
  #volumes
  mr_dates = MappedMarketResult.query.filter(MappedMarketResult.date >= time_delta).filter(MappedMarketResult.itemid==val).distinct().all()
  dates = [mrd.date.strftime('%d, %b %Y') for mrd in mr_dates]
  dates = list(set(dates))
  print dates
  mrs = [MarketResult(m.itemid, m.name, m.cards.split(','), m.price, m.amount, m.title, m.vendor, m.coords, m.date) for m in mr]
  projected_results = [(convert_to_key(None, m.name, m.cards, m.date.strftime('%d, %B %Y')), {'value': int(m.amount), 'label':convert_to_key(None, m.name, m.cards, m.date.strftime('%d, %b %Y'))}) for m in mrs]
  res_dict = {}
  for key, group in groupby(projected_results, lambda x: x[0]):
    for pr in group:
      if key in res_dict.keys():
        res_dict[key].append(pr[1])
      else:
        res_dict[key] = [pr[1]]
        
  bar_chart = pygal.StackedBar(x_label_rotation=20, no_data_text='No result found', disable_xml_declaration=True, dots_size=5, legend_font_size=18, legend_box_size=18, value_font_size=16, label_font_size=14, tooltip_font_size=18, human_readable=True, stroke=False, style=LightStyle, truncate_legend=15, truncate_label=200, y_title='Quantity', x_title='Item %s' % val, x_labels_major_every=2)
  bar_chart.title = "Historical Selling Volume for %s since %s" % (val, time_delta.strftime('%d %B %Y'))
  [bar_chart.add(k, res_dict[k]) for k in res_dict.keys()]

  volumechart = bar_chart.render()
  
  return render_template('market_history.html', marketsearchs=ms, marketresults=mrs, pricechart=pricechart, volumechart=volumechart)

@app.route('/market_history', methods=['GET', 'POST'])
def market_history():
  if not session.get('logged_in') or not session.get('user'):
    #abort(401)
    clear_session()
    return redirect(url_for('login'))
  
  time_delta = datetime.now() - timedelta(weeks=4)
  
  ms = MappedMarketSearch.query.order_by(MappedMarketSearch.name.asc()).all()
  mr = []
  #mr = MappedMarketResult.query.order_by(MappedMarketResult.itemid.asc(), MappedMarketResult.price.asc(), MappedMarketResult.date.desc()).limit(30)
  
  #format data
  mrs = [MarketResult(m.itemid, m.name, m.cards.split(','), m.price, m.amount, m.title, m.vendor, m.coords, m.date) for m in mr]
  
  #prices
  
  datey = pygal.DateY(x_label_rotation=20, no_data_text='No result found', disable_xml_declaration=True, dots_size=5, legend_font_size=18, legend_box_size=18, value_font_size=16, label_font_size=14, tooltip_font_size=18, human_readable=True, style=LightStyle, truncate_legend=200, truncate_label=200, legend_at_bottom=True, y_title='Price', x_title='Date', x_labels_major_every=2)
  datey.title = "Historical Selling Price"
  datey.x_label_format = "%Y-%m-%d"
  
  pricechart = datey.render()
  
  #volumes
  
  bar_chart = pygal.StackedBar(x_label_rotation=20, no_data_text='No result found', disable_xml_declaration=True, dots_size=5, legend_font_size=18, legend_box_size=18, value_font_size=16, label_font_size=14, tooltip_font_size=18, human_readable=True, stroke=False, style=LightStyle, truncate_legend=200, truncate_label=200, legend_at_bottom=True, y_title='Quantity', x_title='Item', x_labels_major_every=2)
  bar_chart.title = "Historical Selling Volume"
  volumechart = bar_chart.render()
  
  return render_template('market_history.html', marketsearchs=ms, marketresults=mrs, pricechart=pricechart, volumechart=volumechart)

@app.route('/market_search_list', methods=['GET', 'POST'])
def market_search_list():
  if not session.get('logged_in') or not session.get('user'):
    #abort(401)
    clear_session()
    return redirect(url_for('login'))
    
  not_named = db.session.query(MappedMarketSearch.itemid, MappedMarketSearch).filter(MappedMarketSearch.name==None).all()
  not_named_item_ids = [nn[0] for nn in not_named]
  if len(not_named_item_ids) > 0:
    not_named_item_ids = list(set(not_named_item_ids))
    if marketscraper.cookies is None:
      loginScraper(m_user, m_password)
    item_id_name = marketscraper.get_item_name_scrape_results(not_named_item_ids)
    print item_id_name
    #save names for the ones with incorrect name
    for ns in not_named:
      ns[1].name = item_id_name[ns[0]]
    db.session.commit()
  
  #way to manage item search list  
  ms = MappedMarketSearch.query.order_by(MappedMarketSearch.itemid.asc()).all()
  
  return render_template('market_search.html', marketsearchs=ms)
  
@app.route('/treasury', methods=['GET', 'POST'])
def treasury():
  if not session.get('logged_in') or not session.get('user'):
    #abort(401)
    clear_session()
    return redirect(url_for('login'))
  
  gt = MappedGuildTreasure(1560, 'Sages Diary [2]', 'Doppelganger Card, Turtle General Card', 1, 0, 0, 0, datetime.now())
  treasures_transactions = db.session.query(MappedGuildTreasure, MappedGuildTransaction, MappedPlayer).outerjoin(MappedGuildTransaction).outerjoin(MappedPlayer).all()
  
  player_amount = get_points_status(session['user'])
  
  return render_template('treasury.html', treasures=treasures_transactions, edittreasure=gt, points_amount=player_amount)

@app.route('/modify_treasure', methods=['GET', 'POST'])
def modify_treasure():
  if not session.get('logged_in') or not session.get('user'):
    #abort(401)
    clear_session()
    return redirect(url_for('login'))

  delete_treasures = []
  edit_treasures = []
  buy_treasures = []
  gt = MappedGuildTreasure(1560, 'Sages Diary [2]', 'Doppelganger Card, Turtle General Card', 1, 0, 0, 0, datetime.now())
  try:
    delete_treasures = request.form.getlist("delete")
    for a in delete_treasures:
      print a
    edit_treasures = request.form.getlist("edit")
    for a in edit_treasures:
      print a
    buy_treasures = request.form.getlist("buy")
    for a in buy_treasures:
      print a
  except:
    print 'could not map action for modifying treasury'
  mg = MappedGuild.query.one()
  if len(delete_treasures) > 0:
    dt_ids = [int(str(dt)) for dt in delete_treasures]
    #check if the mapped guild treasure is in list
    mgt_del = MappedGuildTreasure.query.filter(MappedGuildTreasure.id == dt_ids[0]).all()
    for mgt_d in mgt_del:
      mg.guildTreasures.remove(mgt_d)  
    del_count = MappedGuildTreasure.query.filter(MappedGuildTreasure.id == dt_ids[0]).delete()
    print 'deleted %s items' % del_count
  if len(edit_treasures) > 0:
    et_ids = [int(str(dt)) for dt in edit_treasures]
    gt = MappedGuildTreasure.query.filter(MappedGuildTreasure.id == et_ids[0]).all()[0]
    print 'edit'
  if len(buy_treasures) > 0: 
    bt_ids = [int(str(dt)) for dt in buy_treasures]
    gt = MappedGuildTreasure.query.filter(MappedGuildTreasure.id == bt_ids[0]).all()[0]
    players_who_match = MappedPlayer.query.filter(MappedPlayer.Email == session['user'])
    if players_who_match.count() == 0:
      print 'no player mapped for buying'
      flash('Unable to buy.  Need to make sure correct player logged in')
      session.pop('logged_in', None)
      return redirect(url_for('login'))
    
    player_points = db.session.query(MappedPlayer.Name, MappedPlayer.Email, func.sum(MappedGuildPoint.amount)).join(MappedGuildPoint).filter(MappedPlayer.id == players_who_match.all()[0].id).group_by(MappedPlayer.Name).group_by(MappedPlayer.Email)
    if player_points.count() == 0:
      print 'no points mapped to player'
      flash('No points mapped to player.  Please add runs and calculate points first.')
      return redirect(url_for('treasury'))
    total_points = player_points.all()[0][2]
    price = gt.minMarketPrice * gt.amount
      
    if total_points < price:
      #not enough points
      print 'not enough points'
      flash('Not enough points to purchase item from treasury')
      return redirect(url_for('treasury'))
    
    BuyTreasure(gt, players_who_match.all()[0])
    #link to guild treasure / guild points
    #who is logged in and do they have enough points?
  #  session['user']
    print 'buy'
  
  db.session.commit()
  
  treasures_transactions = db.session.query(MappedGuildTreasure, MappedGuildTransaction, MappedPlayer).outerjoin(MappedGuildTransaction).outerjoin(MappedPlayer).all()
  
  player_amount = get_points_status(session['user'])
    
  return render_template('treasury.html', treasures=treasures_transactions, edittreasure=gt, points_amount=player_amount)
  
@app.route('/add_treasure', methods=['GET', 'POST'])
def add_treasure():
  if not session.get('logged_in') or not session.get('user'):
    #abort(401)
    clear_session()
    return redirect(url_for('login'))
    
  item_id = request.form['nitemid']
  item_name = request.form['nitemname']
  item_amount = request.form['nitemamount']
  item_cards = request.form['nitemcards']
  
  item_id = int(str(item_id))
  item_amount = int(str(item_amount))
  try:
    add_treasures = request.form.getlist("add")
  except:
    print 'could not map action for modifying treasury'
  
  minMarketPrice = 0
  maxMarketPrice = 0
  medianMarketPrice = 0
  
  suggestedMinMarketPrice = 0
  suggestedMaxMarketPrice = 0
  suggestedMedianMarketPrice = 0
  
  try:
    suggestedMinMarketPrice = request.form['nitemminprice']
    suggestedMaxMarketPrice = request.form['nitemmaxprice']
    suggestedMedianMarketPrice = request.form['nitemmedianprice']
  
    suggestedMinMarketPrice = int(str(suggestedMinMarketPrice))
    suggestedMaxMarketPrice = int(str(suggestedMaxMarketPrice))
    suggestedMedianMarketPrice = int(str(suggestedMedianMarketPrice))
  except Exception,e: 
    print str(e)

  #check db or scrape again?
  latest_res = MappedMarketResult.query.filter(MappedMarketResult.itemid == item_id).order_by(MappedMarketResult.date.desc())
  if(latest_res.count() > 0):
    latest_date = latest_res[0].date
    mrs = MappedMarketResult.query.filter(MappedMarketResult.itemid == item_id).filter(MappedMarketResult.date >= latest_date).all()
    prices = [mr.price for mr in mrs]
    minMarketPrice = min(prices)
    maxMarketPrice = max(prices)
    medianMarketPrice = median(prices)
  else:
    #add it as a search item
    ms = MappedMarketSearch.query.filter(MappedMarketSearch.itemid == item_id)
    if ms.count() == 0:
      db.session.add(MappedMarketSearch(True, item_id, item_name))
  
  #if the user makes a suggested market price then run with it
  if suggestedMinMarketPrice > 0:
    minMarketPrice = suggestedMinMarketPrice
  if len(str(minMarketPrice)) == 0:
    minMarketPrice = 0
  if suggestedMaxMarketPrice > 0:
    maxMarketPrice = suggestedMaxMarketPrice
  if len(str(maxMarketPrice)) == 0:
    maxMarketPrice = 0
  if suggestedMedianMarketPrice > 0:
    medianMarketPrice = suggestedMedianMarketPrice
  if len(str(medianMarketPrice)) == 0:
    medianMarketPrice = 0
  
  edit_ids = [dt for dt in add_treasures if dt != u'None']
  print edit_ids
  et_ids = []
  if len(edit_ids) > 0:
    et_ids = [int(str(dt)) for dt in edit_ids]
    
  mg = MappedGuild.query.one()
  if len(et_ids) > 0:
    print 'trying to edit guild treasure'
    gt = MappedGuildTreasure.query.filter(MappedGuildTreasure.id == et_ids[0]).all()[0]
    gt.minMarketPrice = minMarketPrice
    gt.maxMarketPrice = maxMarketPrice
    gt.medianMarketPrice = medianMarketPrice
    gt.cards = item_cards.replace(',', '|')
  else:
    print 'trying to add guild treasure'
    gt = MappedGuildTreasure(item_id, item_name, item_cards, item_amount, minMarketPrice, maxMarketPrice, medianMarketPrice, datetime.now())
    mg.guildTreasures.append(gt)
    db.session.add(gt)
    
  db.session.commit()
  
  treasures_transactions = db.session.query(MappedGuildTreasure, MappedGuildTransaction, MappedPlayer).outerjoin(MappedGuildTransaction).outerjoin(MappedPlayer).all()
  gt = MappedGuildTreasure(item_id, item_name, item_cards, item_amount, minMarketPrice, maxMarketPrice, medianMarketPrice, datetime.now())
  
  player_amount = get_points_status(session['user'])
    
  return render_template('treasury.html', treasures=treasures_transactions, edittreasure=gt, points_amount=player_amount)
  
@app.route ('/transaction', methods=['GET', 'POST'])
def transaction():
  if not session.get('logged_in') or not session.get('user'):
    #abort(401)
    clear_session()
    return redirect(url_for('login'))
      
  ps = gt
 
  return render_template('transaction.html', statement=mgt, playerstatement =gt)

        
'''
  transaction_statement = []
  try:
      transaction_statement = request.form.getlist("statement")

      for s in transaction_statement:
          print s
  except:
        print 'no file on transaction statement'
'''

@app.route('/runs', methods=['GET', 'POST'])
def runs():
  if not session.get('logged_in') or not session.get('user'):
    #abort(401)
    clear_session()
    return redirect(url_for('login'))
  
  mi = None
  mi = MappedInstance.query.all()[0]
  er = MappedRun('', '', 'Test', datetime.now(), [], mi, mi.mobs, True, 'Got good drops')
  ermk = [mk.id for mk in er.mobs_killed]
  erc = [c.id for c in er.chars]
  mrs = MappedRun.query.all()
  mc = MappedCharacter.query.order_by(MappedCharacter.Name).all()  
  
  mis = MappedInstance.query.order_by(MappedInstance.name).all()
  s_run = None
  s_run = int(str(mi.id))
  sr = [s_run]
  
  return render_template('runs.html', selected_run = sr, runs=mrs, editrun=er, edit_run_mobs_killed=ermk, edit_run_chars=erc, mappedcharacters=mc, mappedinstances=mis)

@app.route('/add_run', methods=['GET', 'POST'])
def add_run():
  if not session.get('logged_in') or not session.get('user'):
    #abort(401)
    clear_session()
    return redirect(url_for('login'))
  
  action = None
  try:
    action = request.form['action']
  except:
    print 'cannot map action'
  
  val = None
  s_run = None
  mi = None
  
  try:
    val = request.form['instancelist']
    print val
    s_run = int(str(val))
  except:
    print 'value not found'
    
  if action == u"LoadInstance":
    if val is not None:
      mi = MappedInstance.query.filter(MappedInstance.id==val).all()[0]
    else: 
      mi = MappedInstance.query.all()[0]
    
    add_runs = request.form.getlist("add")
    name = ''
    file = request.files['nrunscreenshot']
    
    char_ids = request.form.getlist('cbsearch')
    mobs_ids = request.form.getlist("cbmobkill")
    mobs_ids = [int(si) for si in mobs_ids]
    mobs_killed = MappedMob.query.filter(MappedMob.mob_id.in_(mobs_ids)).all()
    run_date = request.form['nrundate']
    run_success = request.form.getlist('cbsuccess')
    success = False
    if len(run_success) > 0:
      success = True
    
    notes = request.form['nrunnotes']
    
    char_ids = [int(si) for si in char_ids]
    chars = MappedCharacter.query.filter(MappedCharacter.id.in_(char_ids)).all()
    
    er = MappedRun('', '', name, run_date, chars, mi, mobs_killed, success, notes)
    
    ermk = [mk.id for mk in er.mobs_killed]
    erc = [c.id for c in er.chars]
    
    mrs = MappedRun.query.all()
    mc = MappedCharacter.query.order_by(MappedCharacter.Name).all()  
    mm = mi.mobs
    
    mis = MappedInstance.query.order_by(MappedInstance.name).all()
    
    sr = [s_run]
    
    return render_template('runs.html', selected_run = sr, runs=mrs, editrun=er, edit_run_mobs_killed=ermk, edit_run_chars=erc, mappedcharacters=mc, mappedmobs=mm, mappedinstances=mis)
  
  mapped_instance = MappedInstance.query.filter(MappedInstance.id==s_run)
  if mapped_instance.count() == 0:
    flash('Instance not found, please select a different one')
    return redirect(url_for('runs'))
  mi = MappedInstance.query.filter(MappedInstance.id==s_run)[0]
  mm = mi.mobs
  url = None
  
  try:
    #check if the run is already part of the db before adding again else edit
    s3 = boto.connect_s3(os.environ['AWS_ACCESS_KEY_ID'], os.environ['AWS_SECRET_ACCESS_KEY'])
    bucket = s3.get_bucket(os.environ['S3_BUCKET_NAME'])
    bucket.set_acl('public-read')
    
    add_runs = request.form.getlist("add")
    name = ''
    file = request.files['nrunscreenshot']
    char_ids = request.form.getlist('cbsearch')
    mobs_ids = request.form.getlist("cbmobkill")
    print mobs_ids
    run_date = request.form['nrundate']
    run_success = request.form.getlist('cbsuccess')
    
    success = False
    if len(run_success) > 0:
      success = True
    
    notes = request.form['nrunnotes']
    url = None
    k = Key(bucket)
    er = None

    edit_ids = [dt for dt in add_runs if dt != 'None']
    et_ids = []
    if len(edit_ids) > 0:
      et_ids = [int(str(dt)) for dt in edit_ids]
    if len(et_ids) > 0:
      er = MappedRun.query.filter(MappedRun.id == et_ids[0]).all()[0]
      k.key = er.evidence_file_path
    else:
      k.key = "rr-%s" % uuid.uuid4()
    if file and allowed_file(file.filename):
      try:
        k.set_contents_from_file(file)
        k.set_acl('public-read')
        print 'saved file by file'
      except:
        print 'error sending to s3 by file'
    
    k.key = k.key.encode('ascii', 'ignore')
    url = 'http://{0}.s3.amazonaws.com/{1}'.format(os.environ['S3_BUCKET_NAME'], k.key)
    url = url.encode('ascii', 'ignore')
    char_ids = [int(si) for si in char_ids]
    chars = MappedCharacter.query.filter(MappedCharacter.id.in_(char_ids)).all()
    
    mobs_ids = [int(si) for si in mobs_ids]
    mobs_killed = MappedMob.query.filter(MappedMob.mob_id.in_(mobs_ids)).all()
    
    run_date = run_date.split(".")
    run_date = run_date[0]
    run_date = datetime.strptime(run_date, '%Y-%m-%d %H:%M:%S')
    name = str(name)
    notes = str(notes)
    
    if len(et_ids) > 0:
      er.evidence_url = url
      er.evidence_file_path = k.key
      er.name = name
      er.date = run_date  
      er.chars = chars
      er.instance = mi
      er.mobs_killed = mobs_killed
      er.success = success
      er.notes = notes
      db.session.commit()
      #finished making edits, prepare to add a new run
      return redirect(url_for('runs'))
    else:
      er = MappedRun(url, k.key, name, run_date, chars, mi, mobs_killed, success, notes)
      db.session.add(er)
    db.session.commit()
  except Exception,e:
    print str(e)
    print 'error adding a run'
  
  s_run = int(str(mi.id))
  sr = [s_run]
  #check if run is already part of DB for edit, else add a new one.
  mm = mi.mobs
  ermk = [mk.id for mk in er.mobs_killed]
  erc = [c.id for c in er.chars]
  
  mrs = MappedRun.query.all()
  mc = MappedCharacter.query.order_by(MappedCharacter.Name).all()  
  
  mis = MappedInstance.query.order_by(MappedInstance.name).all()
  
  return render_template('runs.html', selected_run = sr, runs=mrs, editrun=er, edit_run_mobs_killed=ermk, edit_run_chars=erc, mappedcharacters=mc, mappedmobs=mm, mappedinstances=mis)

@app.route('/modify_runs', methods=['GET', 'POST'])
def modify_runs():
  if not session.get('logged_in') or not session.get('user'):
    #abort(401)
    clear_session()
    return redirect(url_for('login'))
  
  delete_id = None
  edit_id = None
  mi = MappedInstance.query.all()[0]
  mm = mi.mobs
  
  val = None
  s_run = None
  
  try:
    val = request.form['instancelist']
    print val
    s_run = int(str(val))
    mi = MappedInstance.query.filter(MappedInstance.id==s_run)[0]
  except:
    print 'value not found'
  
  try:
    delete_id = request.form.getlist("delete")
    print delete_id
    edit_id = request.form.getlist("edit")
    print edit_id
  except:
    print 'cannot find gdoc name'
  
  try:
    d_ids = [int(str(dt)) for dt in delete_id]
    dt_ids = []
    e_ids = [et for et in edit_id if et != 'None']
    et_ids = []
    if len(d_ids) > 0:
      dt_ids = [int(str(dt)) for dt in d_ids]
      er = MappedRun.query.filter(MappedRun.id == dt_ids[0]).first()
      db.session.delete(er)
      db.session.commit()
    elif len(e_ids) > 0:
      print 'trying to edit'
      et_ids = [int(str(ed)) for ed in edit_id]
      er = MappedRun.query.filter(MappedRun.id == et_ids[0]).first()
      
      mm = er.instance.mobs
      mi = er.instance
    else:
      er = MappedRun('', '', 'Test', datetime.now(), [], mi, mi.mobs, True, 'Got good drops')
      mm = er.instance.mobs
      mi = er.instance
      
      print 'no action to map'
  except Exception,e:
    print str(e)
    print 'issue modifying a run'
  
  ermk = [mk.id for mk in er.mobs_killed]
  erc = [c.id for c in er.chars]
  mrs = MappedRun.query.all()
  mc = MappedCharacter.query.order_by(MappedCharacter.Name).all()
  mis = MappedInstance.query.order_by(MappedInstance.name).all()
  
  s_run = int(str(mi.id))
  sr = [s_run]
  
  return render_template('runs.html', selected_run = sr, runs=mrs, editrun=er, edit_run_mobs_killed=ermk, edit_run_chars=erc, mappedcharacters=mc, mappedmobs=mm, mappedinstances=mis)

@app.route('/points', methods=['GET', 'POST'])
def points():
  if not session.get('logged_in') or not session.get('user'):
    #abort(401)
    clear_session()
    return redirect(url_for('login'))
    
  action = None
  p = []
  try:
    action = request.form['action']
  except:
    print 'cannot bind action'
  
  p = db.session.query(MappedPlayer.Name, MappedPlayer.id, func.sum(MappedGuildPoint.amount)).join(MappedGuildPoint).group_by(MappedPlayer.Name).group_by(MappedPlayer.id).all()
  current_user = session['user']
  
  return render_template('points.html', points=p, current_user=current_user)

@app.route('/points_actions', methods=['GET', 'POST'])
def points_actions():   
  if not session.get('logged_in') or not session.get('user'):
    #abort(401)
    clear_session()
    return redirect(url_for('login'))
 
  action = None
  availableParties = []
  chars = []
  checkPointsCalculation()    
  
  try:    
    action = request.form['action']
    
  except:
    print 'cannot get action'
 
  if action == u"Calculate":
    flash('Running Points Calculation')
    run_points_calculation()
  elif action == u"Refresh":
    checkPointsCalculation()
  else:
    print 'points'
  
  return redirect(url_for('points'))

@app.route('/gift_points_to', methods=['GET', 'POST'])
def gift_points_to():   
  if not session.get('logged_in') or not session.get('user'):
    #abort(401)
    clear_session()
    return redirect(url_for('login'))
  
  gift = None
  
  current_user = session['user']
  selected_player = []
  mps = []
  player_amount = 0
  selected_player = []
  if current_user:
    mps = MappedPlayer.query.filter(MappedPlayer.Email!=current_user).all()
  else:
    mps = MappedPlayer.query.all()
  try:
    gift = request.form['gift']
    gift = int(str(gift))
  except Exception,e:
    print str(e)
    print 'player not found for gifting'
  
  try:
    player_amount = get_points_status(session['user'])
    selected_player = [gift]
  except Exception,e:
    print str(e)
    print 'error giving gift to player'
 
  return render_template('give_points.html', points_amount=player_amount, selected_player=selected_player, mappedplayers=mps)
  
@app.route('/gift_points', methods=['GET', 'POST'])
def gift_points():   
  if not session.get('logged_in') or not session.get('user'):
    #abort(401)
    clear_session()
    return redirect(url_for('login'))
  
  current_user = session['user']
  selected_player = []
  mps = []
  if current_user:
    mps = MappedPlayer.query.filter(MappedPlayer.Email!=current_user).all()
  else:
    mps = MappedPlayer.query.all()
  try:
    selected_player_id = session['gift_player_id']
    selected_player = [selected_player_id] 
  except Exception,e:
    print str(e)
    print 'player not found for gifting'
    
  player_amount = get_points_status(session['user'])
 
  return render_template('give_points.html', points_amount=player_amount, selected_player=selected_player, mappedplayers=mps)
  
@app.route('/gift_points_actions', methods=['GET', 'POST'])
def gift_points_actions():   
  if not session.get('logged_in') or not session.get('user'):
    #abort(401)
    clear_session()
    return redirect(url_for('login'))
 
  action = None
  amount = None
  gift_player = None
  
  try:    
    action = request.form['action']
    amount = request.form['ngiftamount']
    val = request.form['playerlist']
    gift_player = int(str(val))    
  except:
    print 'cannot get action'
    return redirect(url_for('gift_points'))
  
  amount = 0 if not amount else int(amount)
  player_amount = get_points_status(session['user'])
  player_amount = int(player_amount)
  if (player_amount == 0):
    flash('No points to give!')
    return redirect(url_for('gift_points'))
  
  if amount > player_amount or amount <= 0:
    flash('Not enough points to give')
    return redirect(url_for('gift_points'))
  
  if not gift_player:
    flash('No player selected to give points!')
    return redirect(url_for('gift_points'))
  
  from_player = MappedPlayer.query.filter(MappedPlayer.Email==session['user'])
  if from_player.count() == 0:
    flash('Could not find player points, please login again')
    clear_session()
    return redirect(url_for('login'))
    
  to_player = MappedPlayer.query.filter(MappedPlayer.id==gift_player)
  if to_player.count() == 0:
    flash('Player not found, please select a different player to give points to')
    return redirect(url_for('gift_points'))
  if from_player.all()[0].id == to_player.all()[0].id:
    flash('Please give points to a different player')
    return redirect(url_for('gift_points'))
  
  print 'trying to give points %s from %s to %s' % (amount, from_player.all()[0].Name, to_player.all()[0].Name)
  give_points_to_player(from_player.all()[0], to_player.all()[0], amount)
  
  return redirect(url_for('gift_points'))

def use_default_search_list():
  if not session.get('logged_in') or not session.get('user'):
    #abort(401)
    clear_session()
    return redirect(url_for('login'))
    
  MappedMarketSearch.query.delete()
  db.session.commit()
  
  for k in search_items.keys():
    db.session.add(MappedMarketSearch(True, str(k), str(search_items[k])))
       
  db.session.commit()

@app.route('/update_search_list', methods=['GET', 'POST'])
def update_search_list():
  if not session.get('logged_in') or not session.get('user'):
    #abort(401)
    clear_session()
    return redirect(url_for('login'))
  
  action = None
  try:
    action = request.form['action']
  except:
    print 'cannot bind action'
  print action
  
  not_named = db.session.query(MappedMarketSearch.itemid, MappedMarketSearch).filter(MappedMarketSearch.name==None).all()
  not_named_item_ids = [nn[0] for nn in not_named]
  if len(not_named_item_ids) > 0:
    not_named_item_ids = list(set(not_named_item_ids))
    if marketscraper.cookies is None:
      loginScraper(m_user, m_password)
    item_id_name = marketscraper.get_item_name_scrape_results(not_named_item_ids)
    print item_id_name
    #save names for the ones with incorrect name
    for ns in not_named:
      ns[1].name = item_id_name[ns[0]]
    db.session.commit()
  
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
  if not session.get('logged_in') or not session.get('user'):
    #abort(401)
    clear_session()
    return redirect(url_for('login'))
  
  itemid = ''
  try:
    itemid = str(request.form['nitemid'].strip())
    
    if marketscraper.cookies is None:
      loginScraper(m_user, m_password)
    item_id_name = marketscraper.get_item_name_scrape_results([itemid])
    print item_id_name
    itemname = item_id_name[itemid]
    exists = MappedMarketSearch.query.filter(MappedMarketSearch.itemid==itemid).all()
    if len(exists) == 0:
      #can add item to search list
      db.session.add(MappedMarketSearch(True, str(itemid), str(itemname)))
    else:
      for se in exists:
        se.search = True
        se.name = str(itemname)
  except Exception,e: 
    flash('Unable to add item %s to search list' % itemid)
    print str(e)
    print 'error adding item to search list'
      
  db.session.commit()
  ms = MappedMarketSearch.query.order_by(MappedMarketSearch.itemid.asc()).all()
    
  return render_template('market_search.html', marketsearchs=ms)

@app.route('/update_chars', methods=['GET', 'POST'])
def update_chars():
  if not session.get('logged_in') or not session.get('user'):
    #abort(401)
    clear_session()
    return redirect(url_for('login'))
 
  action = None
  chars = []
  ec = None
  drop_id = None
  edit_id = None
  curChars = []
  
  try:
    drop_id = request.form.getlist("drop")
    print drop_id
    edit_id = request.form.getlist("edit")
    print edit_id
  except:
    print 'cannot find gdoc name'
  
  mi = MappedInstance.query.all()[0]
  
  if len(drop_id) > 0:
    dc_ids = [dt for dt in drop_id]
    mc_to_delete = MappedCharacter.query.filter(MappedCharacter.id == dc_ids[0]).all()
    for mcd in mc_to_delete:
      qs = [q.id for q in mcd.Quests]
      d = association_table_quests_characters.delete().where(association_table_quests_characters.c.quest_id.in_(qs))
      db.engine.execute(d)
      db.session.delete(mcd)
    db.session.commit()
    ec = MappedCharacter(session['g_spreadsheet_id'], session['g_worksheet_id'], 'High Wizard', 'Billdalf', None, datetime.now(), 'Billy', 'true')
    ec.Quests = mi.quests
  elif len(edit_id) > 0:
    ec_ids = [ed for ed in edit_id]
    ec = MappedCharacter.query.filter(MappedCharacter.id == ec_ids[0]).all()[0]
  else:
    ec = MappedCharacter(session['g_spreadsheet_id'], session['g_worksheet_id'], 'High Wizard', 'Billdalf', None, datetime.now(), 'Billy', 'true')
    ec.Quests = mi.quests
    print 'no action to map'
  
  all_quest_names = db.session.query(MappedQuest.name, func.max(MappedQuest.id)).group_by(MappedQuest.name).all()
  aqns = [aqn[1] for aqn in all_quest_names]
  mqs = MappedQuest.query.filter(MappedQuest.id.in_(aqns)).all()
    
  print 'mapped quests %s ' % mqs
  
  ecq = [q.id for q in ec.Quests]
  #map points back from characters and guild?
  
  curChars = MappedCharacter.query.all()
  ccs = character_classes
  selected_class = [str(ec.Class)]
  if len(edit_id) > 0:
    return render_template('add_char.html', selected_class = selected_class, charclasses = ccs, editcharacter=ec, edit_character_quests=ecq,mappedquests=mqs)
  else:
    return render_template('show_entries.html', characters=curChars, editcharacter=ec, edit_character_quests=ecq,mappedquests=mqs) 

@app.route('/add_char', methods=['GET', 'POST'])
def add_char():
  if not session.get('logged_in') or not session.get('user'):
    #abort(401)
    clear_session()
    return redirect(url_for('login'))
 
  action = None
  chars = []
  curChars = []
  ec = None
  char_id = None
  quests = []  
  ecq = []
  ec = MappedCharacter(session['g_spreadsheet_id'], session['g_worksheet_id'], 'High Wizard', 'Billdalf', None, datetime.now(), 'Billy', 'true')
    
  all_quest_names = db.session.query(MappedQuest.name, func.max(MappedQuest.id)).group_by(MappedQuest.name).all()
  aqns = [aqn[1] for aqn in all_quest_names]
  mqs = MappedQuest.query.filter(MappedQuest.id.in_(aqns)).all()
  
  print 'mapped quests %s ' % mqs
  
  print 'edit char mapped quests %s ' % ecq
  
  #map points back from characters and guild?
  ccs = character_classes
  selected_class = [str(ec.Class)]  
  return render_template('add_char.html', selected_class = selected_class, charclasses = ccs, editcharacter=ec, mappedquests=mqs, edit_character_quests=ecq)

@app.route('/add_character', methods=['GET', 'POST'])
def add_character():
  if not session.get('logged_in') or not session.get('user'):
    #abort(401)
    clear_session()
    return redirect(url_for('login'))
 
  action = None
  chars = []
  curChars = []
  ec = None
  char_id = None
  quests = []  
  ecq = []
  try:
    char_id = request.form.getlist("add")
    charquests = request.form.getlist("cbquests")
    print charquests
    #Update for quests
    print char_id
  except:
    print 'cannot find gdoc name'
  
  charclass_id = int(request.form['charclass'])
  charclass = character_classes[charclass_id]
  print charclass
  charrole = None
  roleMap = [r for r in AllRoles if charclass in r.Classes]
  if len(roleMap) > 0:
    charrole = roleMap[0]
  else:
    charrole = roleUnmapped
  charname = str(request.form['charname'])
  
  charquests = [int(str(cq)) for cq in charquests]
  quests = MappedQuest.query.filter(MappedQuest.id.in_(charquests)).all()
  charlastrun = str(request.form['charlastrun'])
  charplayername = str(request.form['charplayername'])
  charpresent_raw = request.form['charpresent']
  print charpresent_raw
  charpresent = str(True) if charpresent_raw == 1 else str(False)
  
  print charpresent
  
  g_spreadsheet_id = None
  g_worksheet_id = None
  
  try:
    if 'g_spreadsheet_id' in session and 'g_worksheet_id' in session:
      g_spreadsheet_id = session['g_spreadsheet_id']
      g_worksheet_id = session['g_worksheet_id']
    else:
      loginConfiguration(session['user'])
      user = users.get_current_user()
      storage = StorageByKeyName(CredentialsModel, str(user), 'credentials')
      credentials = storage.get()   
      if credentials is None:
        session.pop('logged_in', None)
        return redirect(url_for('login'))
      (g_s_id, g_w_id) = testConnectToSpreadsheetsServiceOAuth(credentials, session['doc'])
      session['g_spreadsheet_id'] = g_s_id
      session['g_worksheet_id'] = g_w_id    
      g_spreadsheet_id = session['g_spreadsheet_id']
      g_worksheet_id = session['g_worksheet_id']
  except:
    print 'issue finding the available parties'
    resetLookupParameters()
    
  if len(char_id) > 0:
    dc_ids = [str(dt) for dt in char_id]
  if dc_ids[0] == u'None':    
    #adding new character
    ec = MappedCharacter(g_spreadsheet_id, g_worksheet_id, charclass, charname, charrole.Name, charlastrun, charplayername, charpresent)
    ec.Quests = quests
     
    ecq = [q.id for q in ec.Quests]
      
    db.session.add(ec)
  else:
    #editing a character
    ec = MappedCharacter.query.filter(MappedCharacter.id == dc_ids[0]).all()[0]
    ec.Class = charclass
    ec.Role = charrole.Name
    ec.Name = charname
    ec.Quests = quests
    ec.LastRun = charlastrun
    ec.PlayerName = charplayername
    ec.Present = charpresent
    
    ecq = [q.id for q in ec.Quests]
    
  db.session.commit()
  
  all_quest_names = db.session.query(MappedQuest.name, func.max(MappedQuest.id)).group_by(MappedQuest.name).all()
  aqns = [aqn[1] for aqn in all_quest_names]
  mqs = MappedQuest.query.filter(MappedQuest.id.in_(aqns)).all()
  
  print 'mapped quests %s ' % mqs
  curChars = MappedCharacter.query.all()
  
  flash('Updated Character!')
  print 'edit char mapped quests %s ' % ecq
  
  #map points back from characters and guild?
    
  return render_template('show_entries.html', characters=curChars, editcharacter=ec, mappedquests=mqs, edit_character_quests=ecq)

@app.route('/import_characters', methods=['POST'])
def import_characters():
  try:
    if not session.get('logged_in') or not session.get('user'):
      #abort(401)
      clear_session()
      return redirect(url_for('login'))
  
    if(len(session['doc']) <= 0):
      flash('Must include relevant document name')
      return redirect(url_for('show_entries'))

    if('g_spreadsheet_id' in session.keys() and 'g_worksheet_id' in session.keys()):
      mcs = MappedCharacter.query.all()
      for mc in mcs:
        [db.session.delete(q) for q in mc.Quests]
      
      [db.session.delete(mc) for mc in mcs]
      db.session.commit()
  
    #Update for quests
    loginConfiguration(session['user'])
    user = users.get_current_user()
    storage = StorageByKeyName(CredentialsModel, str(user), 'credentials')
    credentials = storage.get()   
    if credentials is None:
      session.pop('logged_in', None)
      return redirect(url_for('login'))
   
    (g_s_id, g_w_id) = testConnectToSpreadsheetsServiceOAuth(credentials, session['doc'])
    if(g_s_id == -1 or g_w_id == -1):
      flash('Cannot connect to google document.  Please check spreadsheet name, google credentials and connectivity.')
      return redirect(url_for('show_entries'))
 
    session['g_spreadsheet_id'] = g_s_id
    session['g_worksheet_id'] = g_w_id
    g_s_id = str(g_s_id)
    g_w_id = str(g_w_id)
    
    quests = db.session.query(MappedQuest.internal_name).group_by(MappedQuest.internal_name).all()
    basequests = [q.internal_name for q in quests]
    print basequests
    
    chars = initializeDataOAuth(credentials, session['doc'], basequests)
    print 'FOUND %s CHARS' % len(chars)
    
    #parties combinations have [PartyIndex,InstanceName,PlayerName,CharacterName,CharacterClass,RoleName']
    for c in chars:
      cqs = [q for q in c.Quests]
      print 'from import quests %s' % cqs
      char_quests = MappedQuest.query.filter(MappedQuest.internal_name.in_(cqs)).all()
      print 'found quests %s' % char_quests
      mc = MappedCharacter(g_s_id, g_w_id, c.Class, c.Name, c.Role.Name, c.LastRun, c.PlayerName, c.Present)
      mc.Quests = char_quests
      db.session.add(mc)
      
    db.session.commit()
    flash('Import finished')
  except Exception,e: 
    print str(e)
    print 'error importing'
    session.pop('logged_in', None)
    return redirect(url_for('login'))
  
  return redirect(url_for('show_entries'))

@app.route('/runcalc', methods=['POST'])
def run_calculation():
  try:
    if not session.get('logged_in') or not session.get('user'):
      #abort(401)
      clear_session()
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
    
  except Exception,e: 
    print str(e)
    print 'error running calculation'
    session.pop('logged_in', None)
    return redirect(url_for('login'))
  return redirect(url_for('viable_parties'))

@app.route('/checkcalc', methods=['POST'])
def checkCalculation():
  if not session.get('logged_in') or not session.get('user'):
    #abort(401)
    clear_session()
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
      print 'No job in session'
  except:
    print 'error occurred trying to fetch job'
    session.pop('job_id', None)
  return redirect(url_for('viable_parties'))

@app.route('/reset', methods=['POST'])
def reset():
  try:
    if not session.get('logged_in') or not session.get('user'):
      #abort(401)
      clear_session()
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
       
    PartyCombo.query.delete() 
    db.session.commit()

    MappedCharacter.query.delete()
    db.session.commit()  
  
    flash('Reset party combinations')
  except:
    print 'error reseting'
    
  return redirect(url_for('show_entries')) 

@app.route('/run_points_calculation', methods=['POST'])
def run_points_calculation():
  try:
    if not session.get('logged_in') or not session.get('user'):
      #abort(401)
      clear_session()
      return redirect(url_for('login'))

    #mgps = MappedGuildPoint.query.all()
    #mg = MappedGuild.query.one()
    #mg.guildTransactions.delete()
    #mg.guildPoints.delete()
    #db.session.commit()
    
    #MappedGuildPoint.query.delete()
    #db.session.commit()
    
    loginConfiguration(session['user'])
    user = users.get_current_user()
    storage = StorageByKeyName(CredentialsModel, str(user), 'credentials')
    credentials = storage.get()   
    if credentials is None:
      session.pop('logged_in', None)
      return redirect(url_for('login'))
  
    #consider calculating from imported results if possible
    calcpointsjob = q.enqueue_call(func=RecalculatePoints, args=(), result_ttl=3000)
    print 'running calc %s ' % calcpointsjob.id
    session['points_job_id'] = calcpointsjob.id
    
  except Exception,e: 
    print str(e)
    print 'error running points calculation'
    #session.pop('logged_in', None)
    #return redirect(url_for('login'))
  return redirect(url_for('points'))

@app.route('/checkpointscalc', methods=['POST'])
def checkPointsCalculation():
  if not session.get('logged_in') or not session.get('user'):
    #abort(401)
    clear_session()
    return redirect(url_for('login'))
  
  try:
    if 'points_job_id' in session.keys():
      job_id = session['points_job_id']
      print 'using job id %s ' % job_id
      currentjob = Job(connection=conn)
      currentjob = currentjob.fetch(job_id, connection=conn)
      print 'found job %s ' % currentjob
      
      if currentjob is not None:
        if currentjob.result is not None:
          currentjob.delete()         
      else: 
        flash('Points calculation not finished yet.')
        print 'current job is not ready %s' % job_id
    else:
      print 'No job in session'
  except:
    print 'error occurred trying to fetch job'
    session.pop('points_job_id', None)
  return redirect(url_for('points'))

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
      #map player in db?
      
      #credentials stored
      flash('You were logged in')
      return redirect(url_for('show_entries'))
  except: 
    print 'error with oauth2callback'

@app.route('/user_profile', methods=['GET', 'POST'])
def user_profile():
  if not session.get('logged_in') or not session.get('user'):
    #abort(401)
    clear_session()
    return redirect(url_for('login'))
  
  action = None
  user = session['user']
  name = None
  try:
    action = request.form['action']
  except:
    print 'cannot bind action'
  print action
  
  mp_exists = MappedPlayer.query.filter(MappedPlayer.Email==user)
  mp = None
  if mp_exists.count() > 0:
    mp = mp_exists.all()[0]
  else:
    mp = MappedPlayer(name, user)
    db.session.add(mp)
  db.session.commit()
    
  return render_template('profile.html', editplayer=mp)

@app.route('/update_profile', methods=['GET', 'POST'])
def update_profile():
  if not session.get('logged_in') or not session.get('user'):
    #abort(401)
    clear_session()
    return redirect(url_for('login'))
  
  action = None
  user = session['user']
  name = None
  mp = None
  try:
    action = request.form['action']
    name = request.form['nname']  
  except:
    print 'cannot bind action'
  print action
  
  if action == u"Update":
    name = str(name)
    
    mp_exists = MappedPlayer.query.filter(MappedPlayer.Email==user)
    if mp_exists.count() > 0:
      mp = mp_exists.all()[0]
      mp.Name = name
    else:
      mp = MappedPlayer(name, user)
      db.session.add(mp)
    db.session.commit()
    flash('Updated profile')
  else:
    print 'cannot map action'
    
  return render_template('profile.html', editplayer=mp)

@app.route('/login', methods=['GET', 'POST'])
def login():
    try:
      resetParameters()
      error = None    
      user = None
      if request.method == 'POST':
          if len(request.form['username']) == 0:
              error = 'Invalid username'
          else:
              username = request.form['username'].strip().lower()
              session['user'] = username
              
              #need to get mapped player by email?

              loginConfiguration(username)
              flow = OAuth2WebServerFlow(client_id=CLIENT_ID, client_secret=CLIENT_SECRET, scope=SCOPES, redirect_uri=REDIRECT_URI)
              #print flow
              user = users.get_current_user()
              nick = user.nickname().split('@')[0]	
              print 'nickname %s' % user.nickname()
              print nick
	      print user.email()
              print user.user_id()
              
              #add mapped players based on user information
              exists = MappedPlayer.query.filter(MappedPlayer.Email==user.email())
              mp = None
              if exists.count() == 0:
                #add mapped player
                mp = MappedPlayer(user.nickname(), user.email())
                db.session.add(mp)
              else:
                mp = exists.all()[0]
                #mp.Name = user.nickname()
              
              #link characters to player
              mc_exists = MappedCharacter.query.filter(MappedCharacter.PlayerName==mp.Name)
              if mc_exists.count() > 0:
                mp.Chars = mc_exists.all()
              db.session.commit()
              
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
    except Exception,e: 
      print str(e)
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
    
def allowed_file(filename):
  return '.' in filename and \
         filename.rsplit('.', 1)[1] in app.config['ALLOWED_EXTENSIONS']

#Guild Points

def get_points_status(player_email):
  player_points = db.session.query(func.sum(MappedGuildPoint.amount)).join(MappedPlayer).filter(MappedPlayer.Email==player_email).all()
  player_amount = 0 if len(player_points) == 0 else player_points[0][0]
  player_amount = float(player_amount) if player_amount else 0
  
  return player_amount

def points_status():
  return db.session.query(MappedPlayer.Name, MappedPlayer.Email, func.sum(MappedGuildPoint.amount)).join(MappedGuildPoint).join(MappedRun).group_by(MappedPlayer.Name).group_by(MappedPlayer.Email).all()
  
def give_points_to_player(from_player, to_player, amount):
  print 'trying to give %s points from %s to %s' % (amount, from_player.Name, to_player.Name)
  #check if player has enough points to give
  if(from_player.id == to_player.id):
    print 'cannot give points to same player'
    return
  
  check_player_point_amount = db.session.query(MappedPlayer.Name, MappedPlayer.Email, func.sum(MappedGuildPoint.amount)).join(MappedGuildPoint).filter(MappedPlayer.id == from_player.id).group_by(MappedPlayer.Name).group_by(MappedPlayer.Email)
  print check_player_point_amount.count()
  if check_player_point_amount.count() == 0:
    print 'not enough points'
    return
  mp = check_player_point_amount.all()[0]
  
  total_points = mp[2]
  total_points = int(total_points)
  #all runs
  #mp = db.session.query(MappedPlayer.Name, MappedPlayer.Email, func.sum(MappedGuildPoint.amount)).join(MappedGuildPoint).filter(MappedPlayer.id == from_player.id).group_by(MappedPlayer.Name).one()
  #print mp
  if (total_points < amount):
    print 'not enough points'
    return
  
  #reassign credit
  print 'total points %s ' % total_points
  
  original_amount = amount
  print 'original_amount %s ' % original_amount
  run_credit_points = db.session.query(RunCredit, MappedGuildPoint, MappedPlayer.Email, MappedPlayer.Name).join(MappedPlayer).join(MappedGuildPoint).join(MappedRun).filter(MappedPlayer.id == from_player.id).filter(RunCredit.factor > 0).filter(MappedRun.success == True).all()
  for rcp in run_credit_points:
    if float(rcp[0].factor) == 0 or float(rcp[1].amount) == 0:
      print 'credit points are 0 here'
      continue
    
    print 'amount %s' % amount
    
    if amount <= 0:
      print 'done gifting %s remaining points to gift %s' % (original_amount, amount)
      #no more points
      break
    
    if amount > rcp[1].amount: 
      print 'amount > credit points'
      print 'reassigning points to new player %s %s' % (rcp, amount)
      rcp[0].player_id = to_player.id
      amount -= rcp[1].amount
      print 'reassigned points to new player %s %s' % (rcp, amount)
    else:
      print 'amount <= credit points'
      
      remaining_amount = float(rcp[1].amount) - float(amount)
      remaining_factor = (float(remaining_amount) / float(rcp[1].amount)) * (float(rcp[0].factor))
      diff_factor = float(rcp[0].factor) - float(remaining_factor)
      rc_exists = RunCredit.query.filter(RunCredit.player_id==to_player.id).filter(RunCredit.run_id==rcp[0].run_id)
      
      if rc_exists.count() > 0:
        rc = rc_exists.all()[0]
        rc.factor += diff_factor
      else:
        #reallocate points to new run credit
        rc = RunCredit(diff_factor)
        rc.player_id = to_player.id
        rc.run_id = rcp[0].run_id
        db.session.add(rc)
      
      #should we reassign guild points here?
      #use factor for reallocation purposes.  bulk points into one big guild point
      print 'remaining amount %s' % remaining_amount
      print 'remaining factor %s' % remaining_factor
      rcp[0].factor = remaining_factor
      db.session.commit()
      #update points
      #rcp[1].amount = remaining_amount
      
      amount = 0 
      
  db.session.commit()
  
  #calc points
  mgp_from_player = MappedGuildPoint(-1 * original_amount)
  from_player.Points.append(mgp_from_player)
  mgp_to_player = MappedGuildPoint(original_amount)
  to_player.Points.append(mgp_to_player)

  d = datetime.now()
  #need to link to guild transaction
  mgt = MappedGuildTransaction('gift', d)
  mgt.gift_to_player_id = to_player.id
  mgt.player_id = from_player.id
  mgt.to_player_name = to_player.Name
  mgp_from_player.Transaction = mgt
  from_player.Transactions.append(mgt)
  mgp_to_player.guildtransaction = mgt
  
  mg = MappedGuild.query.one()
  mg.guildTransactions.append(mgt)
  
  db.session.commit()
  
  #print db.session.query(RunCredit, MappedRun, MappedPlayer.Name, func.sum(MappedGuildPoint.amount)).join(MappedRun).join(MappedPlayer).join(MappedGuildPoint).filter(MappedRun.success == True).group_by(MappedPlayer.Name).group_by(RunCredit).group_by(MappedRun).all()
  
  #get the player to points total
  #print db.session.query(MappedPlayer.Name, MappedPlayer.Email, func.sum(MappedGuildPoint.amount)).join(MappedGuildPoint).group_by(MappedPlayer.Name).group_by(MappedPlayer.Email).all()
  
  print db.session.query(MappedPlayer.Name, MappedGuildTransaction.transType, MappedGuildTransaction.transDate, func.sum(MappedGuildPoint.amount)).join(MappedGuildPoint).join(MappedGuildTransaction).group_by(MappedPlayer).group_by(MappedGuildTransaction.transType).group_by(MappedGuildTransaction.transDate).all()
  
  #who gave anything to anyone
  players_gifts = db.session.query(MappedPlayer.Name, MappedPlayer.Email, MappedGuildTransaction.transType, MappedGuildTransaction.transDate, MappedGuildTransaction.to_player_name, MappedGuildPoint.amount).join(MappedGuildTransaction).join(MappedGuildPoint).all()
  #print players_gifts

def loginScraper(username, password):
  marketscraper.login(username, password)

def refreshMarket(search_items = {}):
  print search_items
  item_results = marketscraper.get_scrape_results(search_items)
  return item_results    
  
def CalculatePoints(run = None, mobs_killed = [], players = [], market_results = {}, d = datetime.now()): 
  #get relevant data for run 
  #assume that players conform to Character class
  runname = run.instance.name
  mobs_killed = run.mobs_killed
  print 'calculating points for %s ' % runname
  print 'assuming mobs killed %s ' % mobs_killed
  print 'with players %s ' % players
  median_party = run.instance.median_players
  mobs = run.mobs_killed
  mob_items = [m.items for m in mobs]
  mob_items = [item for sublist in mob_items for item in sublist]
  drop_items = [mob_item.item_id for mob_item in mob_items]
  
  drop_rate = [(mi.item_id, mi.item_drop_rate) for mi in mob_items]
  #distinct item drop rate
  drop_rate = list(set(drop_rate))
  
  #find median prices for drops
  expected_values = [item_drop_rate * market_results[[x for x in market_results.keys() if x == item_id][0]] for item_id, item_drop_rate in drop_rate if item_id in [x for x in market_results.keys() if x == item_id] and not item_id in cards_to_coins.keys()]
  #find coin price and use for cards
  coin_price = float(market_results[[x for x in market_results.keys() if x == 8900][0]])
  expected_values += [item_drop_rate * coin_price * float(cards_to_coins[item_id]) for item_id, item_drop_rate in drop_rate if item_id in cards_to_coins.keys()]
  #if not on market treat as 0
  expected_values += [0.0 for item_id, item_drop_rate in drop_rate if not item_id in [x for x in market_results.keys() if x == item_id] and not item_id in cards_to_coins.keys()]
  
  print 'expected_values is %s' % expected_values
  #points per player= sum expected values / median party size
  points_per_player = sum(expected_values) / median_party
  
  print 'points per player %s' % points_per_player
  #assign points
  
  #if this is reassignment
  mps = MappedPlayer.query.filter(MappedPlayer.id.in_(players)).all()
  player_ids = [p.id for p in mps]
  relevant_runs_query = db.session.query(RunCredit, MappedPlayer, MappedGuildPoint, MappedRun).join(MappedPlayer).join(MappedGuildPoint).join(MappedRun).filter(MappedRun.success == True).filter(MappedRun.id==run.id).filter(RunCredit.factor > 0)
  mg = MappedGuild.query.one()
  mapped_points = []
  rrq = relevant_runs_query.filter(MappedPlayer.id.in_(player_ids))
  if rrq.count() > 0:
    print 'found relevant runs'
    relevant_runs = rrq.all()
    
    run.points = []
    for rr in relevant_runs:
      rc, mp, mgp = rr[0], rr[1], rr[2]
      mgp.amount = rc.factor * points_per_player
      print 'existing assigning %s' % mgp.amount
      run.points.append(mgp)
  
  check_existing = db.session.query(RunCredit, MappedPlayer).join(MappedPlayer).join(MappedGuildPoint).join(MappedRun).filter(MappedRun.success == True).filter(MappedRun.id==run.id).filter(RunCredit.factor > 0)
  ces = check_existing.filter(MappedPlayer.id.in_(player_ids))
  found_players = [ce[1].id for ce in ces.all()]
  found_players = list(set(found_players))
  not_found_players = list(set(player_ids) - set(found_players))
  if len(not_found_players) > 0:
    not_found_players_query = MappedPlayer.query.filter(MappedPlayer.id.in_(not_found_players)).all()  
    
    print 'adding points for a new run'
    #if this is a new run
    mapped_points = []
    for p in not_found_players_query:
      rc = RunCredit(1.0)
      mgp = MappedGuildPoint(rc.factor * points_per_player)
      print 'new assigning %s' % mgp.amount
      mapped_points.append(mgp)
      p.Points.append(mgp)
      run.points.append(mgp)
      run.credits.append(rc)
      mg.guildPoints.append(mgp)
      p.Credits.append(rc)
      db.session.add(mgp)
      db.session.add(rc)
   
  db.session.commit()
  
  return mapped_points	

def AddMissingSearchItems(mob_items, drop_items):
  #notify which items are not part of the market search
  mob_items_dict = dict([(mi.item_id, mi.item_name) for mi in mob_items])
  mms = MappedMarketSearch.query.all()
  mms_item_ids = [m.itemid for m in mms]
         
  #add missing item ids to search list
  not_searched = list(set(drop_items) - set(mms_item_ids))
  if len(not_searched) == 0:
    print 'nothing to add'
    return
  
  #get the missing item names from items db
  item_id_name = marketscraper.get_item_name_scrape_results(not_searched)
  print item_id_name
  for ns in not_searched:
    if ns in item_id_name:
      db.session.add(MappedMarketSearch(True, ns, item_id_name[ns]))
  db.session.commit()
  
  #update market results takes place by market scraper (scraperclock)
  search_list = MappedMarketSearch.query.filter(MappedMarketSearch.search==True).all()	
  search_items_dict = { i.itemid: i.name for i in search_list }
  
  marketresults = marketscraper.get_scrape_results(search_items_dict)
  if len(marketresults) == 0:
    return
    
  vals = marketresults.values()
  daterun = datetime.now()
  for k in marketresults.keys():
    [db.session.add(MappedMarketResult(str(mr.itemid), str(mr.name), str(mr.cards), str(mr.price), str(mr.amount), str(mr.title), str(mr.vendor), str(mr.coords), str(daterun))) for mr in marketresults[k]]
  db.session.commit()

def RefreshMarketWithMobDrops():
  #aggregate item drop rates with market 
  mapped_runs = MappedRun.query.filter(MappedRun.success == True).all()
  mobs = [mr.mobs_killed for mr in mapped_runs]
  mobs = [item for sublist in mobs for item in sublist]
  mob_items = [m.items for m in mobs]
  mob_items = [item for sublist in mob_items for item in sublist]
  drop_rate = [(mi.item_id, mi.item_drop_rate) for mi in mob_items]
  #distinct item drop rate
  drop_rate = list(set(drop_rate))
  items_to_search = { mdr[0] : search_items[mdr[0]] for mdr in drop_rate if mdr[0] in search_items }
  
  ms = MappedMarketSearch.query.filter(MappedMarketSearch.search == True).all()
  drop_items = [mdr[0] for mdr in drop_rate]
  
  AddMissingSearchItems(mob_items, drop_items)
  
  mapped_search_items = [search_item for search_item in ms if search_item.itemid in drop_items]
  items_to_search = { msi.itemid : msi.name for msi in mapped_search_items }
  
  #add talon coin
  items_to_search[8900] = search_items[8900]
  #need to do something to track the market values, can this update a db?
  marketresults = refreshMarket(items_to_search)
  #refresh db
  if marketresults is not None:
    vals = marketresults.values()
    daterun = datetime.now()
    for k in marketresults.keys():
      [db.session.add(MappedMarketResult(str(mr.itemid), str(mr.name), str(mr.cards), str(mr.price), str(mr.amount), str(mr.title), str(mr.vendor), str(mr.coords), str(daterun))) for mr in marketresults[k]]
         
    db.session.commit()
  
  #include talon coin
  drop_items.append(8900)
  
  return drop_items

def RecalculatePoints():
  if marketscraper.cookies is None:
    loginScraper(m_user, m_password)
  #aggregate item drop rates with market 
  drop_items = RefreshMarketWithMobDrops()
  
  #recalculate the points for the guild including run credit factors
  d = datetime.now()
  latest_item = MappedMarketResult.query.order_by(MappedMarketResult.date.desc()).all()
  if len(latest_item) > 0:
    d = latest_item[0].date
  market_results = db.session.query(MappedMarketResult.itemid, func.min(MappedMarketResult.price)).filter(MappedMarketResult.itemid.in_(drop_items)).filter(MappedMarketResult.date >= d).group_by(MappedMarketResult.itemid).all()
  guild_treasure = db.session.query(MappedGuildTreasure.itemid, func.min(MappedGuildTreasure.minMarketPrice)).filter(MappedGuildTreasure.itemid.in_(drop_items)).group_by(MappedGuildTreasure.itemid).all()
  
  #guild treasure results take precedence over market results
  #convert to a dictionary
  market_results_d = {}
  for mr in market_results:
    if market_results_d.has_key(mr[0]):
      market_results_d[mr[0]].append(mr[1])
    else:
      market_results_d[mr[0]] = [mr[1]]
  
  for k,v in market_results:
    market_results_d[k].append(v)
  for k, v in guild_treasure:
    market_results_d[k] = []
  for k,v in guild_treasure:
    market_results_d[k].append(v)
    
  market_results = min_values(market_results_d)
  
  relevant_runs_query = MappedRun.query.filter(MappedRun.success == True).all()
  
  rcs = [rrq.chars for rrq in relevant_runs_query]
  rcs = [item for sublist in rcs for item in sublist]
  players_not_mapped_characters = [pc for pc in rcs if pc.mappedplayer_id is None] 
  player_names = [pc.PlayerName for pc in players_not_mapped_characters]
  player_names = list(set(player_names))
  for pn in player_names:
    #players who have points and unclaimed emails will have their points calculated but they won't be able to use them.  
    #players will need to register.  Perhaps this players can get an invite?
    mp_exists = MappedPlayer.query.filter(MappedPlayer.Name==pn)
    mp = None
    if mp_exists.count() == 0:
      continue
      #removing placeholder characters for now.
      #mp = MappedPlayer(pn, 'NEED_EMAIL')
    else:
      mp = mp_exists.all()[0]
    db.session.add(mp)
    chars_to_map = [pc for pc in players_not_mapped_characters if pc.PlayerName == pn]
    mp.Chars = chars_to_map
    db.session.commit()
    
  for run in relevant_runs_query:
    players = [c.mappedplayer_id for c in run.chars] 
    players = list(set(players))
    CalculatePoints(run, run.mobs_killed, players, market_results, d) 

def BuyTreasure(mappedGuildTreasure, mappedPlayer):
  player_points = db.session.query(MappedPlayer.Name, MappedPlayer.Email, func.sum(MappedGuildPoint.amount)).join(MappedGuildPoint).join(MappedRun).filter(MappedPlayer.id == mappedPlayer.id).group_by(MappedPlayer.Name).group_by(MappedPlayer.Email).all()[0]
  total_points = player_points[2]
  price = mappedGuildTreasure.minMarketPrice * mappedGuildTreasure.amount
  
  if price > total_points:
    #not enough points
    print 'not enough points'
    return
  
  #reduce the credit for each of the points until reaching the price.  remaining credit becomes a fraction
  #1.0 - 2 1.0 - 2 1.0 - 4
  #7 points is price
  #5 points remaining
  #0.0 - 0 0.0 - 0 .25 - 1
  
  original_price = price
  run_credit_points = db.session.query(RunCredit, MappedGuildPoint, MappedPlayer.Email, MappedPlayer.Name).join(MappedPlayer).join(MappedGuildPoint).join(MappedRun).filter(MappedPlayer.id == mappedPlayer.id).filter(RunCredit.factor > 0).filter(MappedRun.success == True).all()
  for rcp in run_credit_points:
    if float(rcp[0].factor) == 0 or float(rcp[1].amount) == 0:
      print 'credit points are 0 here'
      continue
    
    print 'total points %s ' % total_points
    print 'price %s' % price
    
    if price <= 0:
      #no more points
      break
    
    if price > rcp[1].amount: 
      rcp[0].factor = 0
      price -= rcp[1].amount
      rcp[1].amount = 0
    else:
      remaining_amount = float(rcp[1].amount) - float(price)
      remaining_factor = (float(remaining_amount) / float(rcp[1].amount)) * (float(rcp[0].factor))
      
      print 'remaining amount %s' % remaining_amount
      print 'remaining factor %s' % remaining_factor
      rcp[0].factor = remaining_factor
      #update points
      rcp[1].amount = remaining_amount
      price -= remaining_amount
    
  db.session.commit()
  
  #calc points
  mgp_from_player = MappedGuildPoint(-1 * original_price)
  mappedPlayer.Points.append(mgp_from_player)
    
  #need to link to guild transaction but not to run
  mgt = MappedGuildTransaction('purchase', datetime.now())
  mgt.player_id = mappedPlayer.id
  mappedPlayer.Transactions.append(mgt)
  mgp_from_player.guildtransaction = mgt
  
  mappedGuildTreasure.guildtransaction = mgt
      
  mg = MappedGuild.query.one()
  mg.guildTransactions.append(mgt)
      
  db.session.commit()
  
  print db.session.query(func.sum(RunCredit.factor), MappedPlayer.Name, MappedPlayer.Email, func.sum(MappedGuildPoint.amount)).join(MappedPlayer).join(MappedGuildPoint).join(MappedRun).filter(MappedRun.success == True).group_by(MappedPlayer.Name).group_by(MappedPlayer.Email).all()
  
  #get the player to points total
  print db.session.query(MappedPlayer.Name, MappedPlayer.Email, func.sum(MappedGuildPoint.amount)).join(MappedGuildPoint).group_by(MappedPlayer.Name).join(MappedRun).filter(MappedRun.success == True).group_by(MappedPlayer.Email).all()    

def clear_session():
  session.pop('logged_in', None)
  session.pop('user', None)
  

if __name__ == "__main__":
  db.create_all()
  db.session.commit()
  app.run()
