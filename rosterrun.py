from rq import Queue, get_current_job
from rq.job import Job
from worker import conn

import os
from flask import Flask
from scheduler import run_scheduler_OAuth, scheduler, testConnectToSpreadsheetsServiceOAuth, Combination, initializeDataOAuth, Character, AllRoles
#import sqlite3
from flask import Flask, request, session, g, redirect, url_for, \
     abort, render_template, flash
from contextlib import closing
from flask.ext.sqlalchemy import SQLAlchemy
from sqlalchemy import distinct, func, not_, or_, Table, Column, ForeignKey
from sqlalchemy.orm import relationship, backref

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

from datetime import datetime, timedelta
import boto
from boto.s3.key import Key
import uuid
from werkzeug import secure_filename

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

app.config['UPLOAD_FOLDER'] = 'tmp/'
app.config['ALLOWED_EXTENSIONS'] = set(['txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'])

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

class MappedInstance(db.Model):
    __tablename__ = 'instance'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80))
    #placeholder for now.  will update.
    
    def __init__(self, name):
        self.name = name
        	
    def __repr__(self):
        return '<MappedInstance %r>' % self.name

class MappedRun(db.Model):
    __tablename__ = 'run'
    id = db.Column(db.Integer, primary_key=True)
    evidence_url = db.Column(db.String(400))
    evidence_file_path = db.Column(db.String(400))
    date = db.Column(db.DateTime)
    chars = relationship("MappedCharacter", secondary=association_table, backref="runs")
    instance_name = db.Column(db.String(80))
    success = db.Column(db.Boolean)
    notes = db.Column(db.String(400))
    
    def __init__(self, evidence_url, evidence_file_path, date, chars, instance_name, success, notes):
        self.evidence_url = evidence_url
        self.evidence_file_path = evidence_file_path
        self.date = date
        self.chars = chars
        self.instance_name = instance_name
        self.success = success
    	self.notes = notes
    	
    def __repr__(self):
        return '<MappedRun %r>' % self.instance_name

class MappedPlayer(db.Model):
    __tablename__ = 'player'
    id = db.Column(db.Integer, primary_key=True)
    Name = db.Column(db.String(80))
    Email = db.Column(db.String(250))
    Chars = db.relationship("MappedCharacter", backref="player")
    Points = db.relationship("MappedGuildPoint", backref="player")

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
    Quests = db.Column(db.String(280))
    LastRun = db.Column(db.String(80))
    PlayerName = db.Column(db.String(80))
    Present = db.Column(db.String(80))
    mappedguild_id = db.Column(db.Integer, ForeignKey('guild.id'))
    mappedplayer_id = db.Column(db.Integer, ForeignKey('player.id'))
    
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

class MappedGuildPoint(db.Model):
    __tablename__ = 'guild_points'
    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'))
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
guild = Guild()

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

    ec = MappedCharacter(session['g_spreadsheet_id'], session['g_worksheet_id'], 'High Wizard', 'Billdalf', None, 'twotribes,attitudetothenewworld', None, 'Billy', 1)
    
    #map points back from characters and guild?
    
    return render_template('show_entries.html', combinations=availableParties, characters=curChars, editcharacter=ec)

@app.route('/viable_parties', methods=['GET', 'POST'])
def viable_parties():   
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
    except Exception,e: 
      print str(e)
      print 'issue finding the available parties'
      resetLookupParameters()
      
    if len(availableParties) == 0:
      print 'get all combinations'
      cur = PartyCombo.query.all()
      availableParties = [Combination(c.partyIndex, c.instanceName, c.playerName, c.name, c.className, c.rolename) for c in cur]    
      curChars = MappedCharacter.query.all()
      chars = [Character(c.PlayerName, c.Class, c.Name, c.Role, c.Quests.split('|'), c.LastRun, c.Present) for c in curChars]
    
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
  if not session.get('logged_in'):
    #abort(401)
    flash('Please login again')
    session.pop('logged_in', None)
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
  if not session.get('logged_in'):
    #abort(401)
    flash('Please login again')
    session.pop('logged_in', None)
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
  if not session.get('logged_in'):
    #abort(401)
    flash('Please login again')
    session.pop('logged_in', None)
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
  if not session.get('logged_in'):
    #abort(401)
    flash('Please login again')
    session.pop('logged_in', None)
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
  if not session.get('logged_in'):
    #abort(401)
    flash('Please login again')
    session.pop('logged_in', None)
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
  
  gt = MappedGuildTreasure(1560, 'Sages Diary [2]', 'Doppelganger Card, Turtle General Card', 1, 0, 0, 0, datetime.now())
  t = MappedGuildTreasure.query.all()
  
  return render_template('treasury.html', treasures=t, edittreasure=gt)

@app.route('/modify_treasure', methods=['GET', 'POST'])
def modify_treasure():
  if not session.get('logged_in'):
    #abort(401)
    flash('Please login again')
    session.pop('logged_in', None)
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
  
  if len(delete_treasures) > 0:
    dt_ids = [int(str(dt)) for dt in delete_treasures]
    #check if the mapped guild treasure is in list
    del_count = MappedGuildTreasure.query.filter(MappedGuildTreasure.id == dt_ids[0]).delete()
    print 'deleted %s items' % del_count
  if len(edit_treasures) > 0:
    et_ids = [int(str(dt)) for dt in edit_treasures]
    gt = MappedGuildTreasure.query.filter(MappedGuildTreasure.id == et_ids[0]).all()[0]
    print 'edit'
  if len(buy_treasures) > 0: 
    #link to guild treasure / guild points
    #who is logged in and do they have enough points?
  #  session['user']
    print 'buy'
  
  db.session.commit()
  
  t = MappedGuildTreasure.query.all()
    
  return render_template('treasury.html', treasures=t, edittreasure=gt)
  
@app.route('/add_treasure', methods=['GET', 'POST'])
def add_treasure():
  if not session.get('logged_in'):
    #abort(401)
    flash('Please login again')
    session.pop('logged_in', None)
    return redirect(url_for('login'))
    
  item_id = request.form['nitemid']
  item_name = request.form['nitemname']
  item_amount = request.form['nitemamount']
  item_cards = request.form['nitemcards']
  
  try:
    add_treasures = request.form.getlist("submit")
    for a in add_treasures:
      print a
  except:
    print 'could not map action for modifying treasury'
  
  minMarketPrice = None
  maxMarketPrice = None
  medianMarketPrice = None
  suggestedMinMarketPrice = request.form['nitemminprice']
  suggestedMaxMarketPrice = request.form['nitemmaxprice']
  suggestedMedianMarketPrice = request.form['nitemmedianprice']

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
  if suggestedMaxMarketPrice > 0:
    maxMarketPrice = suggestedMaxMarketPrice
  if suggestedMedianMarketPrice > 0:
    medianMarketPrice = suggestedMedianMarketPrice
  
  if len(add_treasures) > 0:
    et_ids = [int(str(dt)) for dt in add_treasures]
    gt = MappedGuildTreasure.query.filter(MappedGuildTreasure.id == et_ids[0]).all()[0]
    gt.minMarketPrice = minMarketPrice
    gt.maxMarketPrice = maxMarketPrice
    gt.medianMarketPrice = medianMarketPrice
    gt.cards = item_cards.replace(',', '|')
  else:
    gt = MappedGuildTreasure(item_id, item_name, item_cards, item_amount, minMarketPrice, maxMarketPrice, medianMarketPrice, datetime.now())
    db.session.add(gt)
    
  db.session.commit()
  
  t = MappedGuildTreasure.query.all()
    
  return render_template('treasury.html', treasures=t, edittreasure=gt)

@app.route('/treasury', methods=['GET', 'POST'])
def treasury():
  if not session.get('logged_in'):
    #abort(401)
    flash('Please login again')
    session.pop('logged_in', None)
    return redirect(url_for('login'))
  
  er = MappedRun('', '', datetime.now(), [], 'Endless Tower', False, 'got to level 75')
  mrs = MappedRun.query.all()
  mc = MappedCharacter.query.all()  
    
  return render_template('runs.html', runs=mrs, editrun=er, mappedcharacters=mc)

@app.route('/add_run', methods=['GET', 'POST'])
def add_run():
  if not session.get('logged_in'):
    #abort(401)
    flash('Please login again')
    session.pop('logged_in', None)
    return redirect(url_for('login'))
  print 'in add run'
  url = None
  er = MappedRun('', '', datetime.now(), [], 'Endless Tower', False, 'got to level 75')
  try:
    #check if the run is already part of the db before adding again else edit
    s3 = boto.connect_s3(os.environ['AWS_ACCESS_KEY_ID'], os.environ['AWS_SECRET_ACCESS_KEY'])
    bucket = s3.get_bucket(os.environ['S3_BUCKET_NAME'])
   
    run_id = request.form['add']
    print 'found run id %s ' % run_id
    name = request.form['nrunname']
    file = request.files['nrunscreenshot']
    char_ids = request.form.getlist('cbsearch')
    run_date = request.form['nrundate']
    success = request.form['cbsuccess']
    notes = request.form['nrunnotes']
    url = None
    k = Key(bucket)
    filepath = None
    er = None
    if run_id is not 'None':
      er = MappedRun.query.filter(MappedRun.id == run_id).all()[0]
      k.key = er.evidence_file_path
    else:
      k.key = "rr-%s" % uuid.uuid4()
    if file and allowed_file(file.filename):
      try:
        k.set_contents_from_file(file)
        print 'saved file by file'
      except:
        print 'error sending to s3 by file'
      
    url = k.generate_url(expires_in=None, query_auth=False)
    
    char_ids = [int(si) for si in char_ids]
    chars = MappedCharacter.query.filter(MappedCharacter.id.in_(char_ids)).all()
    if er is not None:
      er.evidence_url = url
      er.evidence_file_path = k.key()
      er.date = run_date
      er.chars = chars
      er.instance_name = name
      er.success = success
      er.notes = notes
    else:
      er = MappedRun(url, k.key, run_date, chars, name, success, notes)
      db.session.add(er)
    db.session.commit()
  except Exception,e:
    print str(e)
    print 'error adding a run'
  
  #check if run is already part of DB for edit, else add a new one.
  mrs = MappedRun.query.all()
  mc = MappedCharacter.query.all()  
  
  return render_template('runs.html', runs=mrs, editrun=er, mappedcharacters=mc)

@app.route('/modify_runs', methods=['GET', 'POST'])
def modify_runs():
  if not session.get('logged_in'):
    #abort(401)
    flash('Please login again')
    session.pop('logged_in', None)
    return redirect(url_for('login'))
  
  delete_id = None
  edit_id = None
    
  try:
    delete_id = request.form.getlist("delete")
    print delete_id
    edit_id = request.form.getlist("add")
    print edit_id
  except:
    print 'cannot find gdoc name'
    
  if delete_id is not 'None':
    dc_ids = [dt for dt in delete_id]
    mr = MappedRun.query.filter(MappedRun.id == dc_ids[0]).first()
    db.session.delete(mr)
    db.session.commit()
    er = MappedRun('', '', datetime.now(), [], 'Endless Tower', False, 'got to level 75')
  elif len(edit_id) > 0:
    ec_ids = [ed for ed in edit_id]
    ec = MappedRun.query.filter(MappedRun.id == ec_ids[0]).first()
  else:
    er = MappedRun('', '', datetime.now(), [], 'Endless Tower', False, 'got to level 75')
    print 'no action to map'
    
  mrs = MappedRun.query.all()
  mc = MappedCharacter.query.all()
  
  return render_template('runs.html', runs=mrs, editrun=er, mappedcharacters=mc)

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

@app.route('/calculate_points', methods=['GET', 'POST'])
def calculate_points():
  if not session.get('logged_in'):
    #abort(401)
    flash('Please login again')
    session.pop('logged_in', None)
    return redirect(url_for('login'))
    
  #need to link to guild points calculation
  
  #also take into account existing runs (update existing runs with guild points)
  
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
  
  itemid = str(request.form['nitemid'].strip())
  itemname = str(request.form['nname'].strip())
  exists = MappedMarketSearch.query.filter(MappedMarketSearch.itemid==itemid).all()
  if len(exists) == 0:
    #can add item to search list
    db.session.add(MappedMarketSearch(True, str(itemid), str(itemname)))
  else:
    for se in exists:
      se.search = True
      se.name = str(itemname)
      
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
 
  action = None
  chars = []
  ec = None
  drop_id = None
  edit_id = None
  
  try:
    drop_id = request.form.getlist("drop")
    print drop_id
    edit_id = request.form.getlist("edit")
    print edit_id
  except:
    print 'cannot find gdoc name'
  
  if len(drop_id) > 0:
    dc_ids = [dt for dt in drop_id]
    MappedCharacter.query.filter(MappedCharacter.id == dc_ids[0]).delete()
    db.session.commit()
    ec = MappedCharacter(session['g_spreadsheet_id'], session['g_worksheet_id'], 'High Wizard', 'Billdalf', None, 'twotribes,attitudetothenewworld', None, 'Billy', 1)
  elif len(edit_id) > 0:
    ec_ids = [ed for ed in edit_id]
    ec = MappedCharacter.query.filter(MappedCharacter.id == ec_ids[0]).all()[0]
  else:
    ec = MappedCharacter(session['g_spreadsheet_id'], session['g_worksheet_id'], 'High Wizard', 'Billdalf', None, 'twotribes,attitudetothenewworld', None, 'Billy', 1)
    print 'no action to map'
  
  try:
    if 'g_spreadsheet_id' in session and 'g_worksheet_id' in session:
      print 'already have ids in session ', session['g_spreadsheet_id'], session['g_worksheet_id']
      curChars = MappedCharacter.query.filter_by(g_spreadsheet_id=session['g_spreadsheet_id'], g_worksheet_id=session['g_worksheet_id'])
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
      curChars = MappedCharacter.query.filter_by(g_spreadsheet_id=session['g_spreadsheet_id'], g_worksheet_id=session['g_worksheet_id'])
  except:
    print 'issue finding the available parties'
    resetLookupParameters()
    
    
  #map points back from characters and guild?
    
  return render_template('show_entries.html', characters=curChars, editcharacter=ec)

@app.route('/add_character', methods=['GET', 'POST'])
def add_character():
  if not session.get('logged_in'):
    #abort(401)
    flash('Please login again')
    session.pop('logged_in', None)
    return redirect(url_for('login'))
 
  action = None
  chars = []
  ec = None
  char_id = None
    
  try:
    char_id = request.form.getlist("add")
    print char_id
  except:
    print 'cannot find gdoc name'
  
  charclass = str(request.form['charclass'])
  charrole = None
  roleMap = [r for r in AllRoles if charclass in r.Classes]
  if len(roleMap) > 0:
    charrole = roleMap[0]
  charname = str(request.form['charname'])
  charquests = str(request.form['charquests'].replace(',','|'))
  charlastrun = str(request.form['charlastrun'])
  charplayername = str(request.form['charplayername'])
  charpresent = str(request.form['charpresent'])
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
        flash('Please login again')
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
      ec = MappedCharacter(g_spreadsheet_id, g_worksheet_id, charclass, charname, charrole.Name, charquests, charlastrun, charplayername, charpresent)
      db.session.add(ec)
  else:
    #editing a character
    ec = MappedCharacter.query.filter(MappedCharacter.id == dc_ids[0]).all()[0]
    ec.Class = charclass
    ec.Role = charrole.Name
    ec.Name = charname
    ec.Quests = charquests
    ec.LastRun = charlastrun
    ec.PlayerName = charplayername
    ec.Present = charpresent
  
  db.session.commit()
    
  curChars = MappedCharacter.query.filter_by(g_spreadsheet_id=session['g_spreadsheet_id'], g_worksheet_id=session['g_worksheet_id'])
  chars = [Character(c.PlayerName, c.Class, c.Name, c.Role, c.Quests.split('|'), c.LastRun, c.Present) for c in curChars]
  
  #map points back from characters and guild?
    
  return render_template('show_entries.html', characters=chars, editcharacter=ec)

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
        MappedCharacter.query.delete()
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
      flash('Please login again')
      session.pop('logged_in', None)
      return redirect(url_for('login'))
      
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
      
    except Exception,e: 
      print str(e)
      print 'error running calculation'
      flash('Please login again')
      session.pop('logged_in', None)
      return redirect(url_for('login'))
    return redirect(url_for('viable_parties'))

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
  return redirect(url_for('viable_parties'))

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
         
      PartyCombo.query.delete() 
      db.session.commit()

      MappedCharacter.query.delete()
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
    
def allowed_file(filename):
  return '.' in filename and \
         filename.rsplit('.', 1)[1] in app.config['ALLOWED_EXTENSIONS']

if __name__ == "__main__":
  db.create_all()
  db.session.commit()
  app.run()