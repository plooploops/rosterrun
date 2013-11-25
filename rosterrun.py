import os
from flask import Flask
from scheduler import run_scheduler, scheduler, testConnectToSpreadsheetsService, Combination
#import sqlite3
from flask import Flask, request, session, g, redirect, url_for, \
     abort, render_template, flash
from contextlib import closing
from flask.ext.sqlalchemy import SQLAlchemy

# configuration
DATABASE = 'scheduler.db'
DEBUG = True
SECRET_KEY = 'development key'
USERNAME = 'admin'
PASSWORD = 'default'

app = Flask(__name__)
app.config.from_object(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['DATABASE_URL']
db = SQLAlchemy(app)

class PartyCombination(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    g_spreadsheet_id = db.Column(db.String(80), unique=True)
    g_worksheet_id = db.Column(db.String(80), unique=True)
    partyIndex = db.Column(db.Integer, unique=False)
    instanceName = db.Column(db.String(80), unique=False)
    playerName = db.Column(db.String(80), unique=False)
    name = db.Column(db.String(80), unique=False)
    className = db.Column(db.String(80), unique=False)
    rolename = db.Column(db.String(80), unique=False)

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
        return '<PartyCombination %r>' % self.playerName

sched = scheduler()

#def connect_db():
#    return sqlite3.connect(app.config['DATABASE'])
#def init_db():
#    with closing(connect_db()) as db:
#        with app.open_resource('schema.sql', mode='r') as f:
#            db.cursor().executescript(f.read())
#        db.commit()

def resetParameters():
    session['user'] = None
    session['pw'] = None
    session['doc'] = None

#@app.before_request
#def before_request():
    #g.db = connect_db()

#@app.teardown_request
#def teardown_request(exception):
    #db = getattr(g, 'db', None)
    #if db is not None:
        #db.close()

@app.route('/')
def show_entries():
    #session['doc'] = request.form['docname']
    availableParties = []
    #print 'doc name', session['doc']
    if('doc' in session.keys() and session['doc'] is not None and len(session['doc']) > 0):
      (g_s_id, g_w_id) = testConnectToSpreadsheetsService(session['user'], session['pw'], session['doc'])
      #print g_s_id, g_w_id
      session['g_spreadsheet_id'] = g_s_id
      session['g_worksheet_id'] = g_w_id    
      cur = PartyCombination.query.filter_by(g_spreadsheet_id=session['g_spreadsheet_id'], g_worksheet_id=session['g_worksheet_id']) 
      #g.db.execute('select partyIndex, instanceName, playername, name, class, rolename from combinations where g_spreadsheet_id = ? and g_worksheet_id = ? order by partyIndex, instanceName desc', \
      #  (session['g_spreadsheet_id'], session['g_worksheet_id']))
      #availableParties = [Combination(row[0], row[1], row[2], row[3], row[4], row[5]) for row in cur.fetchall()]
      availableParties = [Combination(c.partyIndex, c.instanceName, c.playerName, c.name, c.className, c.rolename) for c in cur]
    #print 'availble parties', availableParties
    return render_template('show_entries.html', combinations=availableParties)

@app.route('/runcalc', methods=['POST'])
def run_calculation():
    if not session.get('logged_in'):
        abort(401)
    session['doc'] = request.form['docname']
    if(len(session['doc']) <= 0):
        flash('Must include relevant document name')
        return redirect(url_for('show_entries'))

    cur = PartyCombination.query.filter_by(g_spreadsheet_id=session['g_spreadsheet_id'], g_worksheet_id=session['g_worksheet_id']) 
    [db.session.delete(c) for c in cur]  
    db.session.commit()
    #g.db.execute('delete from combinations where g_spreadsheet_id = ? and g_worksheet_id = ?', \
    #  (session['g_spreadsheet_id'], session['g_worksheet_id']))
    #g.db.commit()

    (g_s_id, g_w_id) = testConnectToSpreadsheetsService(session['user'], session['pw'], session['doc'])
    #print g_s_id, g_w_id
    if(g_s_id == -1 or g_w_id == -1):
      flash('Cannot connect to google document.  Please check spreadsheet name, google credentials and connectivity.')
      return redirect(url_for('show_entries'))

    session['g_spreadsheet_id'] = g_s_id
    session['g_worksheet_id'] = g_w_id    
    parties = run_scheduler(session['user'], session['pw'], session['doc'])
    
    #parties combinations have [PartyIndex,InstanceName,PlayerName,CharacterName,CharacterClass,RoleName']
    for i in range(0, len(parties) - 1):
      #print [(c.PartyIndex, c.InstanceName, c.PlayerName, c.CharacterName, c.CharacterClass, c.RoleName) for c in parties[i]]
      [db.session.add(PartyCombination(session['g_spreadsheet_id'], session['g_worksheet_id'], c.PartyIndex, c.InstanceName, c.PlayerName, c.CharacterName, c.CharacterClass, c.RoleName)) for c in parties[i]]
      #[g.db.execute('insert into combinations (g_spreadsheet_id, g_worksheet_id, partyIndex, instanceName, playername, name, class, rolename) values (?, ?, ?, ?, ?, ?, ?, ?)', \
        #(session['g_spreadsheet_id'], session['g_worksheet_id'], c.PartyIndex, c.InstanceName, c.PlayerName, c.CharacterName, c.CharacterClass, c.RoleName)) for c in parties[i]]
#    g.db.commit()
    db.session.commit()
    flash('Calculation finished')
    return redirect(url_for('show_entries'))

@app.route('/reset', methods=['POST'])
def reset():
    if not session.get('logged_in'):
        abort(401)
    session['doc'] = request.form['docname']
    if(len(session['doc']) <= 0):
        flash('Must include relevant document name')
        return redirect(url_for('show_entries'))
    sched.testConnectToSpreadsheetsService(session['user'], session['pw'], session['doc'])
    session['g_spreadsheet_id'] = sched.g_spreadsheet_id
    session['g_worksheet_id'] = sched.g_worksheet_id    
#    g.db.execute('delete from combinations where g_spreadsheet_id = ? and g_worksheet_id = ?', \
#      (session['g_spreadsheet_id'], session['g_worksheet_id']))
#    g.db.commit()
    cur = PartyCombination.query.filter_by(g_spreadsheet_id=session['g_spreadsheet_id'], g_worksheet_id=session['g_worksheet_id']) 
    
    [db.session.delete(c) for c in cur]  
    db.session.commit()

    flash('Reset party combinations')
    return redirect(url_for('show_entries'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    resetParameters()
    error = None
    if request.method == 'POST':
        if len(request.form['username']) == 0:
            error = 'Invalid username'
        elif len(request.form['password']) == 0:
            error = 'Invalid password'
        else:
            user = request.form['username']
            pw = request.form['password']
            session['user'] = user
            session['pw'] = pw
            session['logged_in'] = True
            flash('You were logged in')
            return redirect(url_for('show_entries'))
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    flash('You were logged out')
    return redirect(url_for('show_entries'))

if __name__ == "__main__":
    app.run()