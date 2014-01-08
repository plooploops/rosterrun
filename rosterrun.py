import os
from flask import Flask
from scheduler import run_scheduler_OAuth, scheduler, testConnectToSpreadsheetsServiceOAuth, Combination, initializeDataOAuth, Character
#import sqlite3
from flask import Flask, request, session, g, redirect, url_for, \
     abort, render_template, flash
from contextlib import closing
from flask.ext.sqlalchemy import SQLAlchemy

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
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['DATABASE_URL']
db = SQLAlchemy(app)

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

class MappedCharacter(db.Model):
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
 
    try:
      session['doc'] = request.form['gdocname'].strip()
      action = request.form['action']
    except:
      print 'cannot find gdoc name'
    if action == u"Import":
      import_characters()
    elif action == u"Calculate":
      run_calculation()    
    elif action == u"Reset":
      reset()
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
    
    return render_template('show_entries.html', combinations=availableParties, characters=chars)

@app.route('/import_characters', methods=['POST'])
def import_characters():
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
    
    return redirect(url_for('show_entries'))

@app.route('/runcalc', methods=['POST'])
def run_calculation():
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
    parties = run_scheduler_OAuth(credentials, session['doc'])
    print 'FOUND %s PARTIES' % len(parties)
    #parties combinations have [PartyIndex,InstanceName,PlayerName,CharacterName,CharacterClass,RoleName']
    for i in range(0, len(parties) - 1):
      [db.session.add(PartyCombo(str(session['g_spreadsheet_id']), str(session['g_worksheet_id']), str(c.PartyIndex), str(c.InstanceName), str(c.PlayerName), str(c.CharacterName), str(c.CharacterClass), str(c.RoleName))) for c in parties[i]]
     
    db.session.commit()
    flash('Calculation finished')
    
    return redirect(url_for('show_entries'))

@app.route('/reset', methods=['POST'])
def reset():
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
      
    return redirect(url_for('show_entries')) 

@app.route('/auth_return', methods=['GET', 'POST'])
def oauth2callback():
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
 
@app.route('/login', methods=['GET', 'POST'])
def login():
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
#	    memcache.set(user.user_id(), pickle.dumps(flow))
            
            auth_uri = flow.step1_get_authorize_url()
            #print auth_uri
            
#            flow = pickle.loads(memcache.get(user.user_id()))            
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

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    flash('You were logged out')
    return redirect(url_for('show_entries'))

def loginConfiguration(username, userid=1):
  print 'running with user %s ' % username
  os.environ['USER_EMAIL'] = username
  #can this a default?
  os.environ['USER_ID'] = str(userid)
  os.environ['AUTH_DOMAIN'] = 'testbed'
  os.environ['APPLICATION_ID'] = 'roster run'

if __name__ == "__main__":
  db.create_all()
  db.session.commit()
  app.run()