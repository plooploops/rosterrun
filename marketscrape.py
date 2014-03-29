import requests
from lxml import html
from items_map import search_items, test_file, test_items
from datetime import datetime, timedelta

#container classes    
class MarketResult(object):
  def __init__(self, itemid = 0, name = None, cards = None, price = None, amount = None, title = None, vendor = None, coords = None, date = datetime.now()):
    self.itemid = itemid
    self.name = name
    self.cards = cards
    self.price = price
    self.amount = amount
    self.title = title
    self.vendor = vendor 
    self.coords = coords
    self.date = date

items_to_search = search_items
sell_base_url = "https://panel.talonro.com/whosell,%s.html"
sell_request_result = "requests_results_sell_%s.html"
buy_base_url = "https://panel.talonro.com/whobuy,%s.html"
buy_request_result = "requests_results_buy_%s.html"
itemdb_base_url = "https://panel.talonro.com/itemdb,%s.html"
itemdb_request_result = "requests_results_itemdb_%s.html"


class MarketScraper: 
  #fields
  cookies = None
  
  #methods
  def login(self, username, password):
    
    print 'logging in with %s' % username
    login_url = "https://forum.talonro.com/index.php?action=login2"
    login_payload = {'user': username, 'passwrd':password}
    login_r = requests.post(login_url, login_payload)
    with open("requests_results_login.html", "w") as f:
      f.write(login_r.content)
    
    self.cookies = login_r.history[0].cookies
    plain_login_url = "https://forum.talonro.com/index.php"
    plain_login_r = requests.get(plain_login_url)
    print plain_login_r.cookies
    print self.cookies

  def write_file_scrape(self, search_items = items_to_search, base_url = sell_base_url, request_result = sell_request_result):
    if self.cookies is None:
      print 'Need to login first'
      return
  
    for i in items_to_search.keys():
      search_url = base_url %  i
      #run query
      req_res = requests.post(search_url, cookies=self.cookies)
   
      #write to file system for testing
      with open(request_result % items_to_search[i], "w") as f:
        f.write(req_res.content)

  def get_scrape_results_file(self, search_items = items_to_search, file = ''):
    items_to_search = search_items
    items_results = { }
   
    if len(file) == 0:
      return
  
    con = ''
    with open(file, "r") as f:
      con = f.read()
    for i in items_to_search.keys():
      #load results into tree
      tree = html.fromstring(con)
      #find search results
      vals = tree.xpath("//table[@class='table_data table_narrow']/tr/td[@style='vertical-align:top;']")
    
      #order of values (cycles):
      #name
      #cards
      #price
      #amount
      #title
      #vendor
      #coords

      results = []
      mr = MarketResult()
      mr.itemid = i
      #map values to result
      for j in range(len(vals)):
        val_found = str.join('', [c.strip() for c in vals[j].itertext()]).strip()
        if(j % 7 == 0):
          mr.name = val_found
        #might want to account for multiple cards here.  can convert to a list?
        if(j % 7 == 1):
          mr.cards = val_found
          if len(test_val) > 0:
	    val_found = val_found.lstrip().replace('Card', 'Card,')
            mr.cards = val_found
        if(j % 7 == 2):
          mr.price = float(val_found.replace('.',''))
        if(j % 7 == 3):
          mr.amount = int(val_found.replace('.',''))
        if(j % 7 == 4):
          mr.title = val_found
        if(j % 7 == 5):
          mr.vendor = val_found
        if(j % 7 == 6):
          v = vals[j].getchildren()[0].get('onclick')
	  coord = v.split('minimap,')[1].split('html')[0].replace('.','').replace(',',' ',1)
          mr.coords = coord
          mr.cards = mr.cards.rstrip(',')
          results.append(mr)
          mr = MarketResult()
          mr.itemid = i
  
      #map results back to item
      items_results[i] = results
   
    return items_results  

  def get_scrape_results(self, search_items = items_to_search, base_url = sell_base_url):
    if self.cookies is None:
      print 'Need to login first'
      return

    #items to scrape from market
    items_to_search = search_items
    items_results = { }
    for i in items_to_search.keys():
      sell_url = base_url %  i
      #run query
      sell_r = requests.post(sell_url, cookies=self.cookies)
      #load results into tree
      tree = html.fromstring(sell_r.content)
      #find search results
      vals = tree.xpath("//table[@class='table_data table_narrow']/tr/td[@style='vertical-align:top;']")
      #order of values (cycles):
      #name
      #cards
      #price
      #amount
      #title
      #vendor
      #coords

      results = []
      mr = MarketResult()
      mr.itemid = i
      #map values to result
      for j in range(len(vals)):
        #print vals[j]
        test_val = "".join(vals[j].itertext())
        #print test_val
        val_found = str.join('', [c.strip() for c in vals[j].itertext()]).strip()
        if(j % 7 == 0):
          mr.name = val_found
        #might want to account for multiple cards here.  can convert to a list?
        if(j % 7 == 1):
          mr.cards = val_found
          if len(test_val) > 0:
            val_found = val_found.lstrip().replace('Card', 'Card,')
            mr.cards = val_found
            
        if(j % 7 == 2):
          mr.price = float(val_found.replace('.',''))
        if(j % 7 == 3):
          mr.amount = int(val_found.replace('.',''))
        if(j % 7 == 4):
          mr.title = val_found
        if(j % 7 == 5):
          mr.vendor = val_found
        if(j % 7 == 6):
          v = vals[j].getchildren()[0].get('onclick')
          coord = v.split('minimap,')[1].split('html')[0].replace('.','').replace(',',' ',1)
          mr.coords = coord
          mr.cards = mr.cards.rstrip(',')
          results.append(mr)
          mr = MarketResult()
          mr.itemid = i
  
      #map results back to item
      items_results[i] = results
   
    return items_results
  
  def get_item_name_file(self, item_id, file = ''):
    #this should read outputs from the write_file_scrape with itemdb to get an item name for a given item id
    if len(file) == 0:
      return
    
    if len(item_id) == 0:
      print 'item id is empty'
      return
    
    con = ''
    with open(file, "r") as f:
      con = f.read()
    tree = html.fromstring(con)
    #item result on the page
    vals = tree.xpath("//table[@class='table_data table_narrow']/tbody/tr/td[@colspan='8']")
    #reform result
    val_found = str.join('', [c.strip() for c in vals[0].itertext()]).strip()
    #item name - item id - (item name)
    split_val = val_found.split('-')
      
    return split_val[0] 
  
  def get_item_name_scrape_results(self, search_items = [], base_url = itemdb_base_url):
    if self.cookies is None:
      print 'Need to login first'
      return
  
    #items to scrape from market
    items_to_search = search_items
    items_results = { }
    for i in items_to_search:
      sell_url = base_url %  i
      print sell_url
      #run query
      sell_r = requests.post(sell_url, cookies=self.cookies)
      #load results into tree
      tree = html.fromstring(sell_r.content)
      #find search results
      print 'searching for itemid %s' % i
      vals = tree.xpath("//table[@class='table_data table_narrow']/tbody/tr/td[@colspan='8']")
      print vals
      val_found = str.join('', [c.strip() for c in vals[0].itertext()]).strip()
      #item name - item id - (item name)
      split_val = val_found.split('-')
      #set key value pair for item to item name, not parsing anything else here
      items_results[i] = split_val[0]
        
    return items_results
      
  def map_prices_ignore_upgrades(self, mapped_values = {}):
    evaluated_results = {}
    if len(mapped_values) == 0:
      return {}
  
    #ignores items with upgrades in them.
    for i in mapped_values.keys():
      if len(mapped_values[i]) > 0:
        if not ('+' in mapped_values[i][0].name):
          evaluated_results[(i, mapped_values[i][0].name)] = [mr.price for mr in mapped_values[i]]
    
    return evaluated_results  
  
  def map_prices_include_upgrades(self, mapped_values = {}):
    evaluated_results = {}
    if len(mapped_values) == 0:
      return {}
  
    for i in mapped_values.keys():
      item_by_upgrade = {}
      for mr in mapped_values[i]:
        if not mr.name in item_by_upgrade.keys():
          item_by_upgrade[mr.name] = [mr.price]
        else:
          item_by_upgrade[mr.name].append(mr.price)
      
      for ibu in item_by_upgrade.keys():
        evaluated_results[(i, ibu)] = item_by_upgrade[ibu]
     
    return evaluated_results  

