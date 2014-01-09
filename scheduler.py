import gdata.docs
import gdata.docs.service
import gdata.spreadsheet.service
import gdata.spreadsheets.client
import re
import os
import getpass
from flask import Flask
import itertools
import operator
from itertools import chain, combinations
from datetime import datetime, timedelta

#should match from application registration with google
CONSUMER_KEY = 'rosterrun.herokuapp.com'
CONSUMER_SECRET = 'RaWdj6OlSO36AReeLPiPx7Uc'
APP_NAME = 'roster run'

class Instance:
  def __init__(self, instanceName, quests, cooldown, roles):
    self.Name = instanceName
    self.Quests = quests
    self.Cooldown = cooldown
    self.Roles = roles

class Role:
  def __init__(self, roleName, characterClasses, canDualRole = None):
    self.Name = roleName
    self.Classes = characterClasses
    self.CanDualClientRole = canDualRole

class Character:
  def __init__(self, playerName = None, characterClass = None, characterName = None, role = None, quests = [], lastRun = datetime.now(), present = False):
    self.Class = characterClass
    self.Name = characterName
    self.Role = role
    self.Quests = quests
    self.LastRun = lastRun
    self.PlayerName = playerName
    self.Present = present

class Combination:
  def __init__(self, partyIndex = -1, instanceName = None, playerName = None, characterName = None, characterClass = None, roleName = None):
    self.PartyIndex = partyIndex
    self.InstanceName = instanceName 
    self.PlayerName = playerName 
    self.CharacterName = characterName 
    self.CharacterClass = characterClass 
    self.RoleName = roleName

#establish roles
roleHealer = Role('Healer', ['High Priest', 'Priest'])
roleKiller = Role('Killer', ['Creator'])
roleSPKiller = Role('SPKiller', ['Champion', 'Sniper'])
roleLurer = Role('Lurer', ['Lord Knight', 'Paladin', 'Whitesmith'])
roleSupport = Role('Support', ['Bard', 'Clown'])
roleSPBoost = Role('SPBoost', ['Dancer', 'Gypsy'])
roleSPActive = Role('SPActive', ['Professor'])
roleFreezer = Role('Freezer', ['Wizard', 'High Wizard'])

#establish relationships, can check later but for now use party configurations
roleHealer.CanDualClientRole = [roleSupport, roleSPBoost]
roleKiller.CanDualClientRole = [roleSupport, roleSPBoost]
roleLurer.CanDualClientRole = [roleSupport, roleSPBoost]
roleSupport.CanDualClientRole = [roleHealer, roleKiller, roleLurer, roleSPBoost, roleFreezer, roleSPKiller]
roleSPBoost.CanDualClientRole = [roleHealer, roleKiller, roleLurer, roleSupport, roleFreezer, roleSPKiller]
roleSPKiller.CanDualClientRole = [roleSupport, roleSPBoost, roleSPActive]
roleSPActive.CanDualClientRole = [roleSupport, roleSPBoost, roleSPKiller]
roleFreezer.CanDualClientRole = [roleSupport, roleSPBoost]

AllRoles = [roleHealer, roleKiller, roleLurer, roleSupport, roleFreezer, roleSPKiller, roleSPBoost, roleSPActive]
niddhoggQuests = ['tripatriateunionsfeud', 'attitudetothenewworld', 'ringofthewiseking', 'newsurroundings', 'twotribes', 'pursuingrayanmoore', 'reportfromthenewworld', 'guardianofyggsdrasilstep9', 'onwardtothenewworld']
niddhoggRolesSPKiller = [roleHealer, roleHealer, roleSPKiller, roleLurer, roleSupport, roleFreezer, roleSPActive]
niddhoggRolesKiller = [roleHealer, roleHealer, roleKiller, roleSupport, roleFreezer]
niddhoggRolesNoFreezeSPKiller = [roleHealer, roleHealer, roleSPKiller, roleLurer, roleSupport, roleSPActive]

characters = []
availableCharacters = []
quests = []
instance = ""
parties = []
viablePartyIndex = 0

#google doc properties
g_spreadsheet_id = None
g_worksheet_id = None

def run_scheduler(user, pw, doc):
    niddhoggInstance = Instance('Niddhogg', niddhoggQuests, 3, niddhoggRolesSPKiller)
    instance = niddhoggInstance
    quests = niddhoggQuests
    parties = []
    viablePartyIndex = 0

    userName = user
    password = pw
    docName = doc
    initializeData(userName, password, docName, quests)
    avChar = computeRequirements(characters, instance, quests)
    parties += combineByRoleAssignment(avChar, instance, quests, viablePartyIndex)
    niddhoggInstance = Instance('Niddhogg', niddhoggQuests, 3, niddhoggRolesKiller)
    instance = niddhoggInstance
    parties += combineByRoleAssignment(avChar, instance, quests, viablePartyIndex) 

    niddhoggInstance = Instance('Niddhogg', niddhoggQuests, 3, niddhoggRolesNoFreezeSPKiller)
    instance = niddhoggInstance
    parties += combineByRoleAssignment(avChar, instance, quests, viablePartyIndex) 
    
    #print parties
    return parties    

def run_scheduler_OAuth(credentials, doc):
    niddhoggInstance = Instance('Niddhogg', niddhoggQuests, 3, niddhoggRolesSPKiller)
    instance = niddhoggInstance
    quests = niddhoggQuests
    parties = []
    viablePartyIndex = 0

    docName = doc
    initializeDataOAuth(credentials, docName, quests)
    avChar = computeRequirements(characters, instance, quests)
    print 'viable party index %s ' % viablePartyIndex
    parties += combineByRoleAssignment(avChar, instance, quests, viablePartyIndex, 'SP Killer')
    print 'viable party index %s ' % viablePartyIndex
    niddhoggInstance = Instance('Niddhogg', niddhoggQuests, 3, niddhoggRolesKiller)
    instance = niddhoggInstance
    parties += combineByRoleAssignment(avChar, instance, quests, viablePartyIndex, 'No SP Killer') 
    print 'viable party index %s ' % viablePartyIndex
    niddhoggInstance = Instance('Niddhogg', niddhoggQuests, 3, niddhoggRolesNoFreezeSPKiller)
    instance = niddhoggInstance
    parties += combineByRoleAssignment(avChar, instance, quests, viablePartyIndex, 'No Freezer SP Killer') 
    print 'viable party index %s ' % viablePartyIndex
    
    return parties    

def raw_test():
    user = raw_input('User Name: ')
    pw = getpass.getpass('Password: ')
    docName = raw_input('doc name: ')
    #lastRun = raw_input('last run: ')
    run_scheduler(user, pw, docName)
    return 'Hello world'

def scheduler():
    return 'Hello world'
    
def authorizeClient(credentials, client):
  auth2token = gdata.gauth.OAuth2TokenFromCredentials(credentials)
  #print 'authentication token %s' % auth2token
  gd_client = client
  gd_client.auth_token = auth2token
  gd_client = auth2token.authorize(gd_client)
  
  #print 'authorized client %s' % gd_client
  
  return gd_client

def testConnectToSpreadsheetsServiceOAuth(credentials, docName):
  gd_client = gdata.spreadsheets.client.SpreadsheetsClient(source=APP_NAME)
  spreadsheet_id = -1
  worksheet_id = -1

  gd_client = authorizeClient(credentials, gd_client)
  
  #print 'logged in client %s' % gd_client  
  q = gdata.spreadsheet.service.DocumentQuery()    
 
  q['title'] = docName
  q['title-exact'] = 'true'
  feed = gd_client.GetSpreadsheets(query=q)	
  print 'trying to find the spreadsheet named %s ' % docName
  relevantSpreadsheet = [e for e in feed.entry if e.title.text == docName]
  friendlyName = [rs.title.text for rs in relevantSpreadsheet]
  print friendlyName
  spreadsheet_id = relevantSpreadsheet[0].id.text.rsplit('/',1)[1]
  print spreadsheet_id
  feed = gd_client.GetWorksheets(spreadsheet_id) 
  worksheet_id = feed.entry[0].id.text.rsplit('/',1)[1]
  
  return (spreadsheet_id, worksheet_id)  

def initializeDataOAuth(credentials, docName, quests):
  # Connect to Google
  gd_client = gdata.spreadsheets.client.SpreadsheetsClient(source=APP_NAME)
  gd_client = authorizeClient(credentials, gd_client)
  
  q = gdata.spreadsheet.service.DocumentQuery()
  q['title'] = docName
  q['title-exact'] = 'true'
  feed = gd_client.GetSpreadsheets(query=q)
  
  print 'trying to find the spreadsheet named %s ' % docName
  relevantSpreadsheet = [e for e in feed.entry if e.title.text == docName]
  friendlyName = [rs.title.text for rs in relevantSpreadsheet]
  print friendlyName
  spreadsheet_id = relevantSpreadsheet[0].id.text.rsplit('/',1)[1]
  print spreadsheet_id
  feed = gd_client.GetWorksheets(spreadsheet_id) 
  worksheet_id = feed.entry[0].id.text.rsplit('/',1)[1]

  g_spreadsheet_id = spreadsheet_id
  g_worksheet_id = worksheet_id
  rows = gd_client.GetListFeed(spreadsheet_id, worksheet_id).entry
  for row in rows:
    charac = Character()
    charac.Quests = []
    rowDictionary = row.to_dict()
    for key in rowDictionary.keys():
      key = key.lower().strip()
      #print 'Mapped key %s' % key
      #pick out relevant keys
      if key == 'playername' or key == 'player name':
        charac.PlayerName = str(rowDictionary[key])
      if key == 'name':
        charac.Name = str(rowDictionary[key])
      if key == 'characterclass' or key == 'character class':
        charac.Class = str(rowDictionary[key])
	roleMap = [r for r in AllRoles if charac.Class in r.Classes]
        if len(roleMap) > 0:
          charac.Role = roleMap[0]
      if key in quests:
        if str(rowDictionary[key]) == '1':
          if key in charac.Quests:
            continue
          charac.Quests.append(key)
      if key == 'lastrun':
        if str(rowDictionary[key]) != 'None':
          try:
            dt = datetime.strptime(str(rowDictionary[key]), '%m/%d/%Y')
            if dt is not None:
	      charac.LastRun = dt
	  except:
	    print 'failed to convert: %s to date' % rowDictionary[key]
        else:
          charac.LastRun = datetime.min
      if key == 'present':
        if str(rowDictionary[key]) == '1':
          charac.Present = True
        else:
          charac.Present = False 
    characters.append(charac)
  return characters
  #chars = [[c.PlayerName, c.Name, c.Class, c.Role.Name, c.LastRun, len(c.Quests)] for c in characters]
  #print chars

def computeRequirements(characters, instance, quests):
    now = datetime.now()

    #precompute requirements
    availableCharacters = characters
    presentCharacters = [c for c in characters if c.Present == True]
    notEnoughCooldown = [c for c in presentCharacters if (now - c.LastRun) < timedelta (days = instance.Cooldown)]
    availableCharacters = [c for c in presentCharacters if not c in notEnoughCooldown]
    notEnoughQuest = [c for c in presentCharacters if len(c.Quests) < len(quests)]    
    availableCharacters = [c for c in availableCharacters if not c in notEnoughQuest]
    
    return availableCharacters
    
def combineByRoleAssignment(availableCharacters, instance, quests, viablePartyIndex, partyTypeName):
    if (len(instance.Roles) > len(availableCharacters)):
	return []

    combinationsMapping = {}
    validcombinations = []
    
    successfulteam = len(instance.Roles)
    now = datetime.now()
    chars = [[c.PlayerName, c.Name, c.Class, c.Role.Name, c.LastRun, len(c.Quests)] for c in availableCharacters]
    #print 'Available Characters', chars
    
    for comb in combinations(availableCharacters, len(instance.Roles)):                
      chars = [[c.PlayerName, c.Name, c.Class, c.Role.Name] for c in comb]
      
      #checks for last run date and quest status already precomputed

      #check role fufillment
      roleInstance = list(set([(c.Name, instance.Roles.count(c)) for c in instance.Roles]))
      roleCharacters = [c.Role for c in comb if c.Role in instance.Roles]

      if(len(instance.Roles) > len(roleCharacters)):
        combinationsMapping[comb] = 0
        continue

      roleCountToCharacters = list(set([(c.Name, roleCharacters.count(c)) for c in roleCharacters]))
      roleDelta = list(set(roleInstance) - set(roleCountToCharacters))
  
      if(len(roleDelta) > 0):
        combinationsMapping[comb] = 0
        continue
      
      playersToCharacters = [c.PlayerName for c in comb]
      playersCountToCharacters = list(set([(pName, playersToCharacters.count(pName)) for pName in playersToCharacters]))
      playerMapping = [pc for pc in playersCountToCharacters if pc[1] > 2]
      #check dual clienting
      if(len(playerMapping) > 0):
        combinationsMapping[comb] = 0
        #print 'too many clients for a player', playerMapping
        continue
      
      #check improper dual role assignment
      dualClientPlayers = [c[0] for c in [pc for pc in playersCountToCharacters if pc[1] == 2]]
      DualClientPlayersAssignment = [(c.PlayerName, c.Role) for c in comb if c.PlayerName in dualClientPlayers]
      mergedClientPlayerAssignment = list(accumulate(DualClientPlayersAssignment))
      
      try:
        badDualClientPlayers = [(c[0], [r.Name for r in c[1]]) for c in mergedClientPlayerAssignment if c[1][1] not in c[1][0].CanDualClientRole]
        if(len(badDualClientPlayers) > 0):
          combinationsMapping[comb] = 0
          continue
      except:
        combinationsMapping[comb] = 0
        print 'had an issue with finding bad dual clients %s' % mergedClientPlayerAssignment
        continue
 
      combinationsMapping[comb] = successfulteam
      viablePartyIndex += 1
    
    combinationsMapping = dict((k, v) for (k, v) in combinationsMapping.iteritems() if v == successfulteam)
    
    print 'found %s combinations' % len(combinationsMapping)
    #run through combinations of players
    currentcombinations = []
    usedChars = []
    maxmapping = [[0 for j in range(len(combinationsMapping.keys()) + 1)] for i in range(len(combinationsMapping.keys()))]
    for j in range(1, len(combinationsMapping.keys())):
      for k in range(0, len(combinationsMapping.keys())):
        comb = combinationsMapping.keys()[k]
        used = [c for c in comb if c in usedChars]
        if len(used) > 0:
          print 'characters already exists in prior parties'
          maxmapping[j][k] = maxmapping[j - 1][k]
          continue
        if combinationsMapping[comb] <= 0:
          maxmapping[j][k] = maxmapping[j - 1][k]
        else:
          if(maxmapping[j - 1][k] > combinationsMapping[comb] + maxmapping[j][k - 1]):
            maxmapping[j][k] = max(maxmapping[j - 1][k]
          else:
            maxmapping[j][k] = combinationsMapping[comb] + maxmapping[j][k - 1]
            [usedChars.append(c) for c in comb]
            currentcombinations.append(comb)
    
    for comb in currentcombinations:
      viablePartyIndex += 1
      chars = [Combination(viablePartyIndex, partyTypeName + ' ' + instance.Name, c.PlayerName, c.Name, c.Class, c.Role.Name) for c in comb]
      validcombinations.append(chars)
    
    print 'found %s ' % len(validcombinations)
    return validcombinations

def accumulate(l):
    it = itertools.groupby(l, operator.itemgetter(0))
    for key, subiter in it:
       yield key, [item[1] for item in subiter]

#scheduler()