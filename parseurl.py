from urlparse import urlparse, parse_qs

def parseUrl(request, findKey):
  res = urlparse(request.url)
  qs = parse_qs(res.query)
  if findKey in qs.keys() and len(qs[findKey]) > 0: 
    return qs[findKey][0]
  return ''
    