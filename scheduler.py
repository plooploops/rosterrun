import gdata.docs
import gdata.docs.service
import gdata.spreadsheet.service
import re
import os
import getpass
from flask import Flask
import itertools
import operator
from itertools import chain, combinations
from datetime import datetime, timedelta

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
roleLurer = Role('Lurer', ['Lord Knight', 'Paladin'])
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
    
    #print parties
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

def testConnectToSpreadsheetsService(user, pw, docName):
  gd_client = gdata.spreadsheet.service.SpreadsheetsService()
  gd_client.email = user
  gd_client.password = pw
  gd_client.source = 'scheduler'
  spreadsheet_id = -1
  worksheet_id = -1

  try:
    gd_client.ProgrammaticLogin()  
    q = gdata.spreadsheet.service.DocumentQuery()
    q['title'] = docName
    q['title-exact'] = 'true'
    feed = gd_client.GetSpreadsheetsFeed(query=q)
    spreadsheet_id = feed.entry[0].id.text.rsplit('/',1)[1]
    feed = gd_client.GetWorksheetsFeed(spreadsheet_id) 
    worksheet_id = feed.entry[0].id.text.rsplit('/',1)[1]
  except:
    gd_client = None

  return (spreadsheet_id, worksheet_id)  

def initializeData(userName, passWord, docName, quests):
  username        = userName
  passwd          = passWord
  doc_name        = docName

  # Connect to Google
  gd_client = gdata.spreadsheet.service.SpreadsheetsService()
  gd_client.email = username
  gd_client.password = passwd
  gd_client.source = 'scheduler'
  gd_client.ProgrammaticLogin()

  q = gdata.spreadsheet.service.DocumentQuery()
  q['title'] = doc_name
  q['title-exact'] = 'true'
  feed = gd_client.GetSpreadsheetsFeed(query=q)
  spreadsheet_id = feed.entry[0].id.text.rsplit('/',1)[1]
  feed = gd_client.GetWorksheetsFeed(spreadsheet_id) 
  worksheet_id = feed.entry[0].id.text.rsplit('/',1)[1]

  g_spreadsheet_id = spreadsheet_id
  g_worksheet_id = worksheet_id
  rows = gd_client.GetListFeed(spreadsheet_id, worksheet_id).entry
  
  for row in rows:
    charac = Character()
    charac.Quests = []
    for key in row.custom:
      
      #pick out relevant keys
      if key == 'playername':
        charac.PlayerName = row.custom[key].text
      if key == 'name':
        charac.Name = row.custom[key].text
      if key == 'characterclass':
        charac.Class = row.custom[key].text
	roleMap = [r for r in AllRoles if charac.Class in r.Classes]
        if len(roleMap) > 0:
          charac.Role = roleMap[0]
      if key in quests:
        if row.custom[key].text == '1':
          if key in charac.Quests:
            continue
          charac.Quests.append(key)
      if key == 'lastrun':
        if row.custom[key].text is not None:
          dt = parser.parse(row.custom[key].text)
          if dt is not None:
	    charac.LastRun = dt
        else:
          charac.LastRun = datetime.min
      if key == 'present':
        if row.custom[key].text == '1':
          charac.Present = True
        else:
          charac.Present = False 
    characters.append(charac)
  #chars = [[c.PlayerName, c.Name, c.Class, c.Role.Name, c.LastRun, len(c.Quests)] for c in characters]
  #print chars

def computeRequirements(characters, instance, quests):
    now = datetime.now()

    #precompute requirements
    availableCharacters = characters
    presentCharacters = [c for c in characters if c.Present == True]
    #chars = [[c.PlayerName, c.Name, c.Class, c.Role.Name] for c in presentCharacters]
    #print 'present chars', chars
    notEnoughCooldown = [c for c in presentCharacters if (now - c.LastRun) < timedelta (days = instance.Cooldown)]
    #chars = [[c.PlayerName, c.Name, c.Class, c.Role.Name] for c in notEnoughCooldown]
    #print 'not enough cooldown', chars
    availableCharacters = [c for c in presentCharacters if not c in notEnoughCooldown]
    #chars = [[c.PlayerName, c.Name, c.Class, c.Role.Name] for c in availableCharacters]
    #print 'available characters', chars
    notEnoughQuest = [c for c in presentCharacters if len(c.Quests) < len(quests)]    
    #chars = [[c.PlayerName, c.Name, c.Class, c.Role.Name] for c in presentCharacters]
    #print 'not enough quest characters', chars
    availableCharacters = [c for c in availableCharacters if not c in notEnoughQuest]
    #chars = [[c.PlayerName, c.Name, c.Class, c.Role.Name, c.LastRun, len(c.Quests)] for c in availableCharacters]
    #print 'Available Characters', chars

    return availableCharacters
    
def combineByRoleAssignment(availableCharacters, instance, quests, viablePartyIndex):
    if (len(instance.Roles) > len(availableCharacters)):
	return []

    validcombinations = []
    now = datetime.now()
    chars = [[c.PlayerName, c.Name, c.Class, c.Role.Name, c.LastRun, len(c.Quests)] for c in availableCharacters]
    #print 'Available Characters', chars
    #print 'Number of available characters', len(chars)
    #print 'number roles', len(instance.Roles)

    for comb in combinations(availableCharacters, len(instance.Roles)):                
      chars = [[c.PlayerName, c.Name, c.Class, c.Role.Name] for c in comb]
      #print 'attempting combination', chars
      #print 'number chars', len(chars)
      #checks for last run date and quest status already precomputed

      #check role fufillment
      roleInstance = list(set([(c.Name, instance.Roles.count(c)) for c in instance.Roles]))
      #print 'role instance', roleInstance
      roleCharacters = [c.Role for c in comb if c.Role in instance.Roles]

      if(len(instance.Roles) > len(roleCharacters)):
        #print 'don't have character to role coverage'
        continue

      #print 'role characters',[r.Name for r in roleCharacters]
      roleCountToCharacters = list(set([(c.Name, roleCharacters.count(c)) for c in roleCharacters]))
      #print 'role count to characters', roleCountToCharacters
      roleDelta = list(set(roleInstance) - set(roleCountToCharacters))
  
      if(len(roleDelta) > 0):
        #print 'role delta', roleDelta
        continue
      
      playersToCharacters = [c.PlayerName for c in comb]
      playersCountToCharacters = list(set([(pName, playersToCharacters.count(pName)) for pName in playersToCharacters]))
      #print playersCountToCharacters
      playerMapping = [pc for pc in playersCountToCharacters if pc[1] > 2]
      if(len(playerMapping) > 0):
        #print 'too many clients for a player', playerMapping
        continue
      
      #check improper dual role assignment
      dualClientPlayers = [c[0] for c in [pc for pc in playersCountToCharacters if pc[1] == 2]]
      DualClientPlayersAssignment = [(c.PlayerName, c.Role) for c in comb if c.PlayerName in dualClientPlayers]
      print 'dual client assignment', [(c[0], c[1].Name) for c in DualClientPlayersAssignment]
      mergedClientPlayerAssignment = list(accumulate(DualClientPlayersAssignment))
      badDualClientPlayers = [(c[0], [r.Name for r in c[1]]) for c in mergedClientPlayerAssignment if c[1][1] not in c[1][0].CanDualClientRole]
      if(len(badDualClientPlayers) > 0):
        #print 'players have bad assigment for roles', badDualClientPlayers
        continue
 
      chars = [Combination(viablePartyIndex, instance.Name, c.PlayerName, c.Name, c.Class, c.Role.Name) for c in comb]
      validcombinations.append(chars)
      viablePartyIndex += 1
      #break
    #print validcombinations
    return validcombinations

def accumulate(l):
    it = itertools.groupby(l, operator.itemgetter(0))
    for key, subiter in it:
       yield key, [item[1] for item in subiter]

#scheduler()