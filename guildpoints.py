from items_map import *
from scheduler import Character, Role, Instance
from datetime import datetime, timedelta
from marketscrape import *
from marketvalue import *
from mathutility import *
import getpass

from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy
from sqlalchemy import distinct, func, not_, or_, Table, Column, ForeignKey

from rosterrun import db
#from rosterrun import PartyCombo, MappedGuild, MappedInstance, MappedQuest, MappedRun, MappedMob, MappedMobItem, MappedPlayer, MappedCharacter, MappedGuildTreasure, RunCredit, MappedGuildPoint, MappedGuildTransaction, MappedMarketResult, MappedMarketSearch
#points calculator

#Cards will be treated according to TC * market  z / TC * expected drop rate
#Multiply market value by expected drop rate

marketscraper = MarketScraper()
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
