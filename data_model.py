from flask import Flask
from scheduler import run_scheduler_OAuth, scheduler, testConnectToSpreadsheetsServiceOAuth, Combination, initializeDataOAuth, Character, AllRoles
#import sqlite3
from flask import Flask, request, session, g, redirect, url_for, \
     abort, render_template, flash
from flask.ext.sqlalchemy import SQLAlchemy
from sqlalchemy import distinct, func, not_, or_, Table, Column, ForeignKey
from sqlalchemy.orm import relationship, backref

from rosterrun import db

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
    mapped_run_id = db.Column(db.Integer, ForeignKey('run.id'))
    mobs = relationship("MappedMob", backref="mob")
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

class MappedRun(db.Model):
    __tablename__ = 'run'
    id = db.Column(db.Integer, primary_key=True)
    evidence_url = db.Column(db.String(400))
    evidence_file_path = db.Column(db.String(400))
    date = db.Column(db.DateTime)
    chars = relationship("MappedCharacter", secondary=association_table, backref="runs")
    instance = relationship("MappedInstance", backref="instance", uselist=False)
    success = db.Column(db.Boolean)
    notes = db.Column(db.String(400))
    points = relationship("MappedGuildPoint", backref="run")
    credits = relationship("RunCredit", backref="run")
    mobs_killed = relationship("MappedMob", backref="run")
    
    def __init__(self, evidence_url, evidence_file_path, date, chars, instance, success, notes):
        self.evidence_url = evidence_url
        self.evidence_file_path = evidence_file_path
        self.date = date
        self.chars = chars
        self.instance = instance
        self.mobs_killed = instance.mobs
        self.success = success
    	self.notes = notes
    	
    def __repr__(self):
        return '<MappedRun %r>' % self.instance_name

class MappedMob(db.Model):
    __tablename__ = 'mob'
    id = db.Column(db.Integer, primary_key=True)
    mob_id = db.Column(db.Integer)
    mob_name = db.Column(db.String(80))
    items = relationship("MappedMobItem", backref="mob")
    mapped_run_id = db.Column(db.Integer, ForeignKey('run.id'))
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