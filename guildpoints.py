from items_map import *
from scheduler import Character, Role, Instance
from datetime import datetime, timedelta
from marketscrape import *
from marketvalue import *
from mathutility import *
import getpass
#points calculator

#Cards will be treated according to TC * market  z / TC * expected drop rate
#Multiply market value by expected drop rate

def testGuildCalculator():
  g = Guild('KOH')
  c = Character('Andy', 'Champion', 'plooper')
  g.AddCharacter(c)
  c = Character('Andy', 'High Priest', 'kafra chan')
  g.AddCharacter(c)
  c = Character('Nick', 'Whitesmith', 'Encee')
  g.AddCharacter(c)
  c = Character('Joe', 'High Wizard', 'Kjata')
  g.AddCharacter(c)
  
  user = raw_input('User Name: ')
  pw = getpass.getpass('Password: ')
  g.loginScraper(user, pw)
  
  runname = 'Niddhogg'
  g.CalculatePoints(runname, mobs_in_run[runname], g.chars)

class Guild:
  def __init__(self, name = None, chars = [], guildTreasures = [], guildPoints = [], guildTransactions = []):
    self.name = name
    self.chars = chars
    self.guildTreasures = guildTreasures
    self.guildPoints = guildPoints
    self.guildTransactions = guildTransactions
    self.marketscraper = MarketScraper()
  
  def AddCharacter(self, char = Character()):
    #check if char in guild
    charInGuild = self.CheckInGuild(char.Name)
    
    if charInGuild == False:
      self.chars.append(char)
    else:
      print 'trying to add duplicate character'
  
  def RemoveCharacter(self, char = Character()):
    #check if char in guild
    charInGuild = self.CheckInGuild(char.Name)
    if charInGuild == True:
      self.chars.remove(charInGuild[0])
    else:
      print 'trying to remove nonexistent character'  
  
  def loginScraper(self, username, password):
    self.marketscraper.login(username, password)
  
  def refreshMarket(self, search_items = {}):
    print search_items
    item_results = self.marketscraper.get_scrape_results(search_items)
    mapped_results = self.marketscraper.map_prices_ignore_upgrades(item_results)
    return mapped_results    
    
  def CheckInGuild(self, player = None):
    if len(self.chars) == 0:
      return False
    playerInGuild = [c for c in self.chars if c.Name == player]
    if len(playerInGuild) == 0:
      print 'player not in guild'
      return False
    else:
      return True  
    
  def CalculatePoints(self, runname = None, mobs_killed = [], players = [], recent_market_results = {}): 
    #get relevant data for run 
    #assume that players conform to Character class
    print 'calculating points for %s ' % runname
    print 'assuming mobs killed %s ' % mobs_killed
    print 'with players %s ' % players
    median_party = median_party_size[runname]
    available_mobs = mobs_in_run[runname]
    successful_mobs = [am for am in available_mobs if am in mobs_killed]
    print 'successful mobs %s' % successful_mobs
    drop_rate = [mob_drop_rate[sm] for sm in successful_mobs]
    drop_rate = [item for sublist in drop_rate for item in sublist]
    items_to_search = { mdr[0] : search_items[mdr[0]] for mdr in drop_rate if mdr[0] in search_items }
    
    #add talon coin
    items_to_search[8900] = search_items[8900]
    #need to do something to track the market values, can this update a db?
    market_results = self.refreshMarket(items_to_search)
    
    #need to backfill results from recent market results if they are missing in market results, but current market rates takes precedence in case of tie
    market_results = merge_market_values(market_results, recent_market_results)
    
    min_market_results = min_values(market_results)
    median_market_results = median_values(market_results)
    max_market_results = max_values(market_results)
    
    print 'median market results %s' % median_market_results	
    
    #find median prices for drops
    expected_values = [item_drop_rate * median_market_results[[(x,y) for x,y in median_market_results.keys() if x == item_id][0]] for item_id, item_drop_rate in drop_rate if item_id in [x for x,y in median_market_results.keys() if x == item_id] and not item_id in cards_to_coins.keys()]
    #find coin price and use for cards
    coin_price = float(median_market_results[[(x,y) for x,y in median_market_results.keys() if x == 8900][0]])
    expected_values += [item_drop_rate * coin_price * float(cards_to_coins[item_id]) for item_id, item_drop_rate in drop_rate if item_id in cards_to_coins.keys()]
    #if not on market treat as 0
    expected_values += [0.0 for item_id, item_drop_rate in drop_rate if not item_id in [x for x,y in median_market_results.keys() if x == item_id] and not item_id in cards_to_coins.keys()]
    
    print 'expected_values is %s' % expected_values
    #points per player= sum expected values / median party size
    points_per_player = sum(expected_values) / median_party
    
    print 'points per player %s' % points_per_player
    #assign points
    [self.AddPoints(p, points_per_player) for p in players if self.CheckInGuild(p.Name)]
        
  #use negative amount to remove points
  def AddPoints(self, player = None, amount = 0.0):
    #assume that player conforms to Character class
    playerInGuild = self.CheckInGuild(player.Name)
    if playerInGuild == False:
      return  
    
    gp = [gp for gp in self.guildPoints if gp.player == player]
    if len(gp) > 0:
      gp[0].amount += amount
    else:
      self.guildPoints.append(GuildPoint(player, amount))
    
  def AddTreasure(self, itemid = 0, name = None, cards = None, amount = 0, minMarketPrice = 0, medianMarketPrice = 0, maxMarketPrice = 0, refreshDate = datetime.now()):
    #check if in stock already
    instock = [gt for gt in self.guildTreasures if itemid == gt.itemid]
    if len(instock) > 0:
      instock.amount += amount
      instock.minMarketPrice = minMarketPrice
      instock.medianMarketPrice = medianMarketPrice
      instock.maxMarketPrice = maxMarketPrice
      instock.refreshDate = refreshDate
    else:
      self.guildTreasures.append(Treasure(itemid, name, cards, amount, minMarketPrice, medianMarketPrice, maxMarketPrice, refreshDate))
  
  def RemoveTreasure(self, itemid = 0, name = None, cards = None, amount = 0, minMarketPrice = 0, medianMarketPrice = 0, maxMarketPrice = 0, refreshDate = datetime.now()):
    if amount <= 0:
      print 'trying to remove zero treasure'
      return
      
    #check if in stock already
    instock = [gt for gt in self.guildTreasures if itemid == gt.itemid]
    if len(instock) > 0:
      if instock.amount > amount:
        instock.amount -= amount
        instock.minMarketPrice = minMarketPrice
        instock.medianMarketPrice = medianMarketPrice
        instock.maxMarketPrice = maxMarketPrice
        instock.refreshDate = refreshDate
      else:
        print 'not enough treasure in inventory'
        return
    
  def BuyTreasure(self, itemid = 0, player = None, name = None, cards = None, amount = 0, minMarketPrice = 0, medianMarketPrice = 0, maxMarketPrice = 0, refreshDate = datetime.now()):
    #check if player in guild and assume player conforms to Character class
    playerInGuild = self.CheckInGuild(player.Name)
    if playerInGuild == False:
      return      
      
class GuildPoint:
  def __init__(self, player = None, amount = 0.0):
    self.player = player
    self.amount = amount
    
class Treasure:
  def __init__(self, itemid = 0, name = None, cards = None, amount = 0, minMarketPrice = 0, medianMarketPrice = 0, maxMarketPrice = 0, refreshDate = datetime.now()):
    self.itemid = itemid
    self.name = name
    self.cards = cards
    self.amount = amount
    self.minMarketPrice = minMarketPrice
    self.maxMarketPrice = maxMarketPrice
    self.medianMarketPrice = medianMarketPrice
    self.refreshDate = refreshDate
 
class GuildTransaction:
  def __init__(self, GuildPoint = None, Treasure = None, transType = 'Add', transDate = datetime.now()):
    self.GuildPoint = GuildPoint
    self.Treasure = Treasure
    self.transType = transType
    self.transDate = transDate

