from mathutility import median, min, max

def median_values(items = {}):
  if len(items) == 0:
    return None
  
  results = {}
  for k in items.keys():
    results[k] = median(items[k])
  
  return results

def min_values(items = {}):
  if len(items) == 0:
    return None
  
  results = {}
  for k in items.keys():
    results[k] = min(items[k])
  
  return results

def max_values(items = {}):
  if len(items) == 0:
    return None
  
  results = {}
  for k in items.keys():
    results[k] = max(items[k])
  
  return results
  
def merge_market_values(current_items = {}, recent_items = {}):
  if len(recent_items) == 0:
    return current_items
  
  if len(current_items) == 0:
    return recent_items
  
  merged_items = dict({ k : v for (k, v) in recent_items.items() if v > 0 }.items() + { k : v for (k, v) in current_items.items() if v > 0 }.items())
  
  return merged_items
  
