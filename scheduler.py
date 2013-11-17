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
from dateutil import parser
from datetime import datetime, timedelta

app = Flask(__name__)

@app.route('/')

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
  def __init__(self, playerName = None, characterClass = None, characterName = None, role = None, quests = [], lastRun = datetime.now()):
    self.Class = characterClass
    self.Name = characterName
    self.Role = role
    self.Quests = quests
    self.LastRun = lastRun
    self.PlayerName = playerName

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
niddhoggRolesKiller = [roleHealer, roleHealer, roleKiller, roleLurer, roleSupport, roleFreezer]

characters = []
availableCharacters = []
quests = []
instance = ""
lastrun = None

def scheduler():
    niddhoggInstance = Instance('Niddhogg', niddhoggQuests, 3, niddhoggRolesSPKiller)
    instance = niddhoggInstance
    quests = niddhoggQuests

    userName = raw_input("Gmail User Name: ")
    password = getpass.getpass("Password: ")
    docName = raw_input("Document Name: ")
    lastrun = raw_input("Last Run: ")
    initializeData(userName, password, docName, quests)
    avChar = computeRequirements(characters, instance, quests, lastrun)
    spKillerCombinations = combineByRoleAssignment(avChar, instance, quests, lastrun)
    niddhoggInstance = Instance('Niddhogg', niddhoggQuests, 3, niddhoggRolesKiller)
    instance = niddhoggInstance
    killerCombinations = combineByRoleAssignment(avChar, instance, quests, lastrun) 
    return [spKillerCombinations, killerCombinations]

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
    characters.append(charac)
  chars = [[c.PlayerName, c.Name, c.Class, c.Role.Name, c.LastRun, len(c.Quests)] for c in characters]
  #print chars

def computeRequirements(characters, instance, quests, lastrun):
    now = datetime.now()

    #precompute requirements
    availableCharacters = characters
    notEnoughCooldown = [c for c in characters if (now - c.LastRun) < timedelta (days = instance.Cooldown)]
    availableCharacters = [c for c in characters if not c in notEnoughCooldown]
    notEnoughQuest = [c for c in characters if len(c.Quests) < len(quests)]    
    availableCharacters = [c for c in availableCharacters if not c in notEnoughQuest]
    chars = [[c.PlayerName, c.Name, c.Class, c.Role.Name, c.LastRun, len(c.Quests)] for c in availableCharacters]
    #print 'Available Characters', chars

    return availableCharacters
    
def combineByRoleAssignment(availableCharacters, instance, quests, lastrun):
    if (len(instance.Roles) > len(availableCharacters)):
	return []

    validcombinations = []
    now = datetime.now()

    for comb in chain.from_iterable(combinations(availableCharacters, n) for n in range(len(instance.Roles), len(availableCharacters)+1)):                
      chars = [[c.PlayerName, c.Name, c.Class, c.Role.Name] for c in comb]
      #print 'attempting combination', chars
      #checks for last run date and quest status already precomputed

      #check role fufillment
      roleInstance = list(set([(c.Name, instance.Roles.count(c)) for c in instance.Roles]))
      #print 'role instance', roleInstance
      roleCharacters = [c.Role for c in comb if c.Role in instance.Roles]
      #print 'role characters',[r.Name for r in roleCharacters]
      roleCountToCharacters = list(set([(c.Name, roleCharacters.count(c)) for c in roleCharacters]))
      #print 'role count to characters', roleCountToCharacters
      roleDelta = list(set(roleInstance) - set(roleCountToCharacters))

      if(len(instance.Roles) > len(roleCharacters)):
        #print 'have more roles than characters'
        continue
  
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
      #print 'dual client assignment', [(c[0], c[1].Name) for c in DualClientPlayersAssignment]
      mergedClientPlayerAssignment = list(accumulate(DualClientPlayersAssignment))
      badDualClientPlayers = [(c[0], [r.Name for r in c[1]]) for c in mergedClientPlayerAssignment if c[1][1] not in c[1][0].CanDualClientRole]
      if(len(badDualClientPlayers) > 0):
        #print 'players have bad assigment for roles', badDualClientPlayers
        continue
 
      validcombinations.append(chars)
      break
    print validcombinations
    return validcombinations

def accumulate(l):
    it = itertools.groupby(l, operator.itemgetter(0))
    for key, subiter in it:
       yield key, [item[1] for item in subiter]

scheduler()

#if __name__ == "__main__":
#    app.run()