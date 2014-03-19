def median(list_val = []):
  
  if len(list_val) == 0: 
    return None
  
  list_val.sort()
  
  #odd number of items, return middle
  if len(list_val) % 2 == 1:
    return float(list_val[(len(list_val) / 2)])
  #even number of items, return average of 2 middle numbers
  else:
    a = list_val[(len(list_val) / 2)]
    b = list_val[(len(list_val) / 2) - 1]
    return float(( a + b) / 2.0)

def min(list_val = []):
  if len(list_val) == 0:
    return None
  
  list_val.sort()
  return list_val[0]

def max(list_val = []):
  if len(list_val) == 0:
    return None
    
  list_val.sort()
  return list_val[-1]