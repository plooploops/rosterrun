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

from rosterrun import db, MappedMarketResult, MappedMarketSearch, MappedPlayer, MappedGuildPoint, MappedRun, RunCredit, MappedGuildTransaction

from collection import defaultdict
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
  def __init__(self, name = None):
    self.name = name
    self.marketscraper = MarketScraper()
  
  def points_status(self):
    return db.session.query(MappedPlayer.Name, MappedPlayer.Email, func.sum(MappedGuildPoint.amount)).join(MappedGuildPoint).group_by(MappedPlayer.Name).all()
  
  def give_points_to_player(self, from_player, to_player, amount):
    #check if player has enough points to give
    if(from_player.id == to_player.id):
      print 'cannot give points to same player'
      return
    
    check_player_point_amount = db.session.query(MappedPlayer.Name, MappedPlayer.Email, func.sum(MappedGuildPoint.amount)).join(MappedGuildPoint).filter(MappedPlayer.id == from_player.id).group_by(MappedPlayer.Name)
    mps = db.session.query(RunCredit.id, RunCredit.run_id, MappedRun.instance_name, RunCredit.factor, MappedPlayer.Name, MappedPlayer.Email, func.sum(MappedGuildPoint.amount)).join(MappedPlayer).join(MappedGuildPoint).join(MappedRun).filter(MappedRun.success == True).filter(MappedPlayer.id == from_player.id).group_by(MappedPlayer.Name)
    print check_player_point_amount.count()
    if check_player_point_amount.count() == 0:
      print 'not enough points'
      return
    mp = check_player_point_amount.all()[0]
    #all runs
    #mp = db.session.query(MappedPlayer.Name, MappedPlayer.Email, func.sum(MappedGuildPoint.amount)).join(MappedGuildPoint).filter(MappedPlayer.id == from_player.id).group_by(MappedPlayer.Name).one()
    print mp
    if (mp[2] < amount):
      print 'not enough points'
      return
    
    #reassign credit
    relevant_runs = db.session.query(RunCredit.id, RunCredit.run_id, MappedRun.instance_name, RunCredit.factor, MappedPlayer.id, MappedPlayer.Name, MappedPlayer.Email, MappedGuildPoint.amount).join(MappedPlayer).join(MappedGuildPoint).join(MappedRun).filter(MappedRun.success == True).filter(MappedPlayer.id==from_player.id).filter(RunCredit.factor > 0).all()
    run_to_points = [(rr[0], rr[4], rr[7]) for rr in relevant_runs]
    print run_to_points
    
    run_credits = RunCredit.query.filter(RunCredit.id.in_([rp[0] for rp in run_to_points])).all()
    rcs = {rc.id : rc for rc in run_credits}
    print run_credits
    
    subtotal = 0
    for r in run_to_points:
      if subtotal > amount:
        return
      
      subtotal += r[2]
      run_credit = rcs[r[0]]
      run_credit.player_id = to_player.id
      
    #reassign credit
    relevant_runs = db.session.query(RunCredit.id, RunCredit.run_id, MappedRun.instance_name, RunCredit.factor, MappedPlayer.id, MappedPlayer.Name, MappedPlayer.Email, MappedGuildPoint.amount).join(MappedPlayer).join(MappedGuildPoint).join(MappedRun).filter(MappedRun.success == True).filter(MappedPlayer.id==to_player.id).filter(RunCredit.factor > 0).all()
    run_to_points = [(rr[0], rr[4], rr[7]) for rr in relevant_runs]
    print run_to_points
    
    run_credits = RunCredit.query.filter(RunCredit.id.in_([rp[0] for rp in run_to_points])).all()
    rcs = {rc.id : rc for rc in run_credits}
    print run_credits
    
    subtotal = 0
    for r in run_to_points:
      if subtotal > amount:
        break
      
      subtotal += r[2]
      run_credit = rcs[r[0]]
      run_credit.factor = 0
      run_credit.player_id = from_player.id
    
    db.session.commit()
    
    #calc points
    mgp_from_player = MappedGuildPoint(-1 * amount)
    from_player.Points.append(mgp_from_player)
    mgp_to_player = MappedGuildPoint(amount)
    to_player.Points.append(mgp_to_player)
  
    #need to link to guild transaction
    mgt = MappedGuildTransaction('gift', datetime.now())
    mgt.gift_to_player_id = to_player.id
    mgt.player_id = from_player.id
    mgt.to_player_name = to_player.Name
    from_player.Transactions.append(mgt)
    mgp_to_player.guildtransaction = mgt
    
    mg = MappedGuild.query.one()
    mg.guildTransactions.append(mgt)
    
    db.session.commit()
    
    print db.session.query(RunCredit.id, RunCredit.run_id, MappedRun.instance_name, RunCredit.factor, MappedPlayer.Name, MappedPlayer.Email, func.sum(MappedGuildPoint.amount)).join(MappedPlayer).join(MappedGuildPoint).join(MappedRun).filter(MappedRun.success == True).group_by(MappedPlayer.Name).all()
    
    #get the player to points total
    print db.session.query(MappedPlayer.Name, MappedPlayer.Email, func.sum(MappedGuildPoint.amount)).join(MappedGuildPoint).group_by(MappedPlayer.Name).all()
    
    print db.session.query(MappedPlayer.Name, MappedGuildTransaction.transType, MappedGuildTransaction.transDate, MappedGuildPoint.amount).join(MappedGuildPoint).join(MappedGuildTransaction).group_by(MappedPlayer).all()
    
    #who gave anything to anyone
    players_gifts = db.session.query(MappedPlayer.Name, MappedPlayer.Email, MappedGuildTransaction.transType, MappedGuildTransaction.transDate, MappedGuildTransaction.to_player_name, MappedGuildPoint.amount).join(MappedGuildTransaction).join(MappedGuildPoint).all()
    print players_gifts
  
  def loginScraper(self, username, password):
    self.marketscraper.login(username, password)
  
  def refreshMarket(self, search_items = {}):
    print search_items
    item_results = self.marketscraper.get_scrape_results(search_items)
    mapped_results = self.marketscraper.map_prices_ignore_upgrades(item_results)
    return mapped_results    
    
  def CalculatePoints(self, run = None, mobs_killed = [], players = [], market_results = {}): 
    #get relevant data for run 
    #assume that players conform to Character class
    runname = run.instance_name
    mobs_killed = run.mobs_killed
    print 'calculating points for %s ' % runname
    print 'assuming mobs killed %s ' % mobs_killed
    print 'with players %s ' % players
    median_party = median_party_size[runname]
    successful_mobs = run.mobs_killed
    mob_items = [m.items for m in mobs_killed]
    drop_items = [mob_item.item_id for mob_item in mob_items]
    
    drop_rate = [(mi.item_id, mi.item_drop_rate) for mi in mob_items]
    drop_rate = [item for sublist in drop_rate for item in sublist]
    #distinct item drop rate
    drop_rate = list(set(drop_rate))
    
    #find median prices for drops
    expected_values = [item_drop_rate * market_results[[(x,y) for x,y in market_results.keys() if x == item_id][0]] for item_id, item_drop_rate in drop_rate if item_id in [x for x,y in market_results.keys() if x == item_id] and not item_id in cards_to_coins.keys()]
    #find coin price and use for cards
    coin_price = float(market_results[[(x,y) for x,y in market_results.keys() if x == 8900][0]])
    expected_values += [item_drop_rate * coin_price * float(cards_to_coins[item_id]) for item_id, item_drop_rate in drop_rate if item_id in cards_to_coins.keys()]
    #if not on market treat as 0
    expected_values += [0.0 for item_id, item_drop_rate in drop_rate if not item_id in [x for x,y in market_results.keys() if x == item_id] and not item_id in cards_to_coins.keys()]
    
    print 'expected_values is %s' % expected_values
    #points per player= sum expected values / median party size
    points_per_player = sum(expected_values) / median_party
    
    print 'points per player %s' % points_per_player
    #assign points
    
    #if this is reassignment
    player_ids = [p.id for p in players]
    relevant_runs_query = db.session.query(RunCredit, MappedPlayer, MappedGuildPoint, MappedRun).join(MappedPlayer).join(MappedGuildPoint).join(MappedRun).filter(MappedRun.success == True).filter(MappedRun.id==run.id).filter(RunCredit.factor > 0).filter(MappedPlayer.id.in_(player_ids))
    if relevant_runs_query.count() > 0:
      relevant_runs = relevant_runs_query.all()
      
      run.points = []
      for rr in relevant_runs:
        rc = rr[0]
        mp = rr[1]
        mgp = rr[2]
        mgp.amount = rc.factor * points_per_player
        run.points.append(mgp)
    else:
      #if this is a new run
      mapped_points = []
      for p in players:
        mgp = MappedGuildPoint(points_per_player)
        mapped_points.append(mgp)
        p.Points.append(mgp)
        run.points.append(mgp)
        rc = RunCredit(1.0)
        run.credits.append(rc)
        p.Credits.append(rc)
     
    db.session.commit()
    
    return mapped_points	
  
  def RefreshMarketWithMobDrops(self):
    #aggregate item drop rates with market 
    mapped_runs = MappedRun.query.filter(MappedRun.success == True).all()
    mobs = [mr.mobs_killed for mr in mapped_runs]
    mob_items = [m.items for m in mobs_killed]
    drop_rate = [(mi.item_id, mi.item_drop_rate) for mi in mob_items]
    drop_rate = [item for sublist in drop_rate for item in sublist]
    #distinct item drop rate
    drop_rate = list(set(drop_rate))
    items_to_search = { mdr[0] : search_items[mdr[0]] for mdr in drop_rate if mdr[0] in search_items }
    
    ms = MappedMarketSearch.query.filter(MappedMarketSearch.search == True).all()
    drop_items = [mdr[0] for mdr in drop_rate]
    mapped_search_items = [search_item for search_item in ms if search_item.itemid in drop_items]
    items_to_search = { msi[0] : msi[1] for msi in mapped_search_items }
    
    #add talon coin
    items_to_search[8900] = search_items[8900]
    #need to do something to track the market values, can this update a db?
    market_results = self.refreshMarket(items_to_search)
    #refresh db
    vals = marketresults.values()
    #flattenedvals = [item for sublist in vals for item in sublist]
    daterun = datetime.now()
    for k in marketresults.keys():
      [db.session.add(MappedMarketResult(str(mr.itemid), str(mr.name), str(mr.cards), str(mr.price), str(mr.amount), str(mr.title), str(mr.vendor), str(mr.coords), str(daterun))) for mr in marketresults[k]]
           
    db.session.commit()
  
  def RecalculatePoints(self):
    #aggregate item drop rates with market 
    self.RefreshMarketWithMobDrops()
    
    mapped_runs = MappedRun.query.filter(MappedRun.success == True).all()
    mobs = [mr.mobs_killed for mr in mapped_runs]
    mob_items = [m.items for m in mobs_killed]
    drop_items = [mi.item_id for mi in mob_items]
    drop_items = list(set(drop_items))
    
    #recalculate the points for the guild including run credit factors
    d = datetime.now()
    latest_item = MappedMarketResult.query.order_by(MappedMarketResult.date.desc()).all()
    if len(latest_item) > 0:
      d = latest_item[0].date
    market_results = db.session.query(MappedMarketResult.itemid, func.min(MappedMarketResult.price)).filter(MappedMarketResult.itemid.in_(drop_items)).filter(MappedMarketResult.date >= d).group_by(MappedMarketResult.itemid).all()
    guild_treasure = db.session.query(MappedGuildTreasure.itemid, func.min(MappedGuildTreasure.minMarketPrice)).filter(MappedGuildTreasure.itemid.in_(drop_items)).group_by(MappedGuildTreasure.itemid).all()
    
    #guild treasure results take precedence over market results
    market_results_d = defaultdict(market_results)    
    for k,v in market_results:
      market_results_d[k].append(v)
    for k, v in guild_treasure:
      market_results_d[k] = []
    for k,v in guild_treasure:
      market_results_d[k].append(v)
      
    market_results = min_values(market_results)
    
    relevant_runs_query = MappedRun.query.filter(MappedRun.success == True).all()
    for run in relevant_runs_query:
      players = [c.mappedplayer_id for c in mr.chars] 
      players = list(set(players))
      self.CalculatePoints(run, run.mobs_killed, players, market_results) 
  
  def BuyTreasure(self, mappedGuildTreasure, mappedPlayer):
    player_points = db.session.query(MappedPlayer.Name, MappedPlayer.Email, func.sum(MappedGuildPoint.amount)).join(MappedGuildPoint).filter(MappedPlayer.id == mappedPlayer.id).group_by(MappedPlayer.Name).all()[0]
    total_points = player_points[2]
    price = mappedGuildTreasure.minMarketPrice * mappedGuildTreasure.amount
    
    if total_points < price:
      #not enough points
      print 'not enough points'
      return
    
    #reduce the credit for each of the points until reaching the price.  remaining credit becomes a fraction
    #1.0 - 2 1.0 - 2 1.0 - 4
    #7 points is price
    #5 points remaining
    #0.0 - 0 0.0 - 0 .25 - 1
    
    run_credit_points = db.session.query(RunCredit, MappedGuildPoint, MappedPlayer.Email, MappedPlayer.Name).join(MappedPlayer).join(MappedGuildPoint).join(MappedRun).filter(MappedPlayer.id == mappedPlayer.id).filter(RunCredit.factor > 0).filter(MappedRun.success == True).all()
    for rcp in run_credit_points:
      if total_points > rcp[1].amount: 
        rcp[0].factor = 0.0
        total_points -= rcp[1].amount
        #rcp[1].amount = 0.0
      elif total_points > 0:
        remaining_amount = float(rcp[1].amount) - float(total_points)
        remaining_factor = float(remaining_amount) / float(rcp[0].factor) 
        rcp[0].factor = remaining_factor
        #rcp[1].amount = remaining_amount
      else:
        #no more points
        break
     
    db.session.commit()
    
    #calc points
    mgp_from_player = MappedGuildPoint(-1 * price)
    mappedPlayer.Points.append(mgp_from_player)
      
    #need to link to guild transaction
    mgt = MappedGuildTransaction('purchase', datetime.now())
    mgt.player_id = mappedPlayer.id
    mappedPlayer.Transactions.append(mgt)
    mgp_from_player.guildtransaction = mgt
    
    mappedGuildTreasure.guildtransaction = mgt
        
    mg = MappedGuild.query.one()
    mg.guildTransactions.append(mgt)
        
    db.session.commit()
    
    print db.session.query(RunCredit.id, RunCredit.run_id, MappedRun.instance_name, RunCredit.factor, MappedPlayer.Name, MappedPlayer.Email, func.sum(MappedGuildPoint.amount)).join(MappedPlayer).join(MappedGuildPoint).join(MappedRun).filter(MappedRun.success == True).group_by(MappedPlayer.Name).all()
    
    #get the player to points total
    print db.session.query(MappedPlayer.Name, MappedPlayer.Email, func.sum(MappedGuildPoint.amount)).join(MappedGuildPoint).group_by(MappedPlayer.Name).all()    
    
