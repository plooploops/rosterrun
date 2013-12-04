datastore_file = '/dev/null'
from google.appengine.api import apiproxy_stub_map,datastore_file_stub
apiproxy_stub_map.apiproxy = apiproxy_stub_map.APIProxyStubMap()
stub = datastore_file_stub.DatastoreFileStub('roster run', datastore_file, '/')
apiproxy_stub_map.apiproxy.RegisterStub('datastore_v3', stub)