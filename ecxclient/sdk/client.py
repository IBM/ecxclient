
import ConfigParser
import json
import logging
import os
import re
import tempfile
import time

import click
import requests
from requests.auth import HTTPBasicAuth

try:
    import urllib3
except ImportError:
    from requests.packages import urllib3

try:
    import http.client as http_client
except ImportError:
    # Python 2
    import httplib as http_client

# http://stackoverflow.com/questions/10588644/how-can-i-see-the-entire-http-request-thats-being-sent-by-my-python-application
# Uncomment this to see requests and responses.
# TODO: We need better way and we should log requests and responses in
# log file.
# http_client.HTTPConnection.debuglevel = 1
urllib3.disable_warnings()

resource_to_endpoint = {
    'job': 'endeavour/job',
	'jobsession': 'endeavour/jobsession',
    'log': 'endeavour/log',
    'association': 'endeavour/association',
    'workflow': 'spec/storageprofile',
    'policy': 'endeavour/policy',
    'user': 'security/user',
    'resourcepool': 'security/resourcepool',
    'role': 'security/role',
    'identityuser': 'identity/user',
    'identitycredential': 'identity/user',
    'appserver': 'appserver',
    'oracle': 'application/oracle',
    'site': 'site',
}

resource_to_listfield = {
    'identityuser': 'users',
    'identitycredential': 'users',
    'policy': 'policies',
    'ldap': 'ldapServers',
    'pure': 'purestorages',
    'workflow': 'storageprofiles',
    'resourcepool': 'resourcePools',
}

def build_url(baseurl, restype=None, resid=None, path=None, endpoint=None):
    url = baseurl

    if restype is not None:
        ep = resource_to_endpoint.get(restype, None)
        if not ep:
            if endpoint is not None:
                ep = endpoint
            else:
                ep = restype

        url = url + "/" + ep

    if resid is not None:
        url = url + "/" + str(resid)

    if path is not None:
        if not path.startswith('/'):
            path = '/' + path
        url = url + path

    return url

def raise_response_error(r, *args, **kwargs):
    r.raise_for_status()

def pretty_print(data):
    return logging.info(json.dumps(data, sort_keys=True,indent=4, separators=(',', ': ')))
    
class EcxSession(object):
    def __init__(self, url, username, password):
        self.url = url
        self.api_url = url + '/api'
        self.username = username
        self.password = password
        self.sessionid = None
        self.cfgfile = os.path.join(click.get_app_dir("ecxcli"), 'config.ini')
        self.cfgdir = os.path.dirname(self.cfgfile)
        if not os.path.exists(self.cfgdir):
            os.makedirs(self.cfgdir)

        self.conn = requests.Session()
        self.conn.verify = False
        self.conn.hooks.update({'response': raise_response_error})

        if self.password is None:
            self.use_existing_session()
        else:
            self.login()

        self.conn.headers.update({'X-Endeavour-Sessionid': self.sessionid})
        self.conn.headers.update({'Content-Type': 'application/json'})
        self.conn.headers.update({'Accept': 'application/json'})

    def use_existing_session(self):
        parser = ConfigParser.RawConfigParser()
        parser.read([self.cfgfile])

        try:
            self.sessionid = parser.get(self.username, 'sessionid')
        except ConfigParser.NoSectionError:
            raise Exception('Please provide login credentials.')

    def login(self):
        r = self.conn.post("%s/endeavour/session" % self.api_url, auth=HTTPBasicAuth(self.username, self.password))
        self.sessionid = r.json()['sessionid']
        self.save_config()

    def save_config(self):
        parser = ConfigParser.RawConfigParser()
        parser.add_section(self.username)
        parser.set(self.username, 'sessionid', self.sessionid)

        parser.write(open(self.cfgfile, 'wb'))

    def __repr__(self):
        return 'EcxSession: user: %s' % self.username

    def get(self, restype=None, resid=None, path=None, params={}, endpoint=None, url=None):
        if url is None:
            url = build_url(self.api_url, restype, resid, path, endpoint)

        return json.loads(self.conn.get(url, params=params).content)

    def stream_get(self, restype=None, resid=None, path=None, params={}, endpoint=None, url=None, outfile=None):
        if url is None:
            url = build_url(self.api_url, restype, resid, path, endpoint)

        r = self.conn.get(url, params=params)
        logging.info("headers: %s" % r.headers)

        # The response header Content-Disposition contains default file name
        #   Content-Disposition: attachment; filename=log_1490030341274.zip
        default_filename = re.findall('filename=(.+)', r.headers['Content-Disposition'])[0]

        if not outfile:
            if not default_filename:
                raise Exception("Couldn't get the file name to save the contents.")

            outfile = os.path.join(tempfile.mkdtemp(), default_filename)

        with open(outfile, 'wb') as fd:
            for chunk in r.iter_content(chunk_size=64*1024):
                fd.write(chunk)

        return outfile

    def delete(self, restype=None, resid=None, path=None, params={}, endpoint=None, url=None):
        if url is None:
            url = build_url(self.api_url, restype, resid, path, endpoint)

        resp = self.conn.delete(url, params=params)

        return json.loads(resp.content) if resp.content else None

    def post(self, restype=None, resid=None, path=None, data={}, params={}, endpoint=None, url=None):
        if url is None:
            url = build_url(self.api_url, restype, resid, path, endpoint)

        logging.info(json.dumps(data, indent=4))
        r = self.conn.post(url, json=data, params=params)

        if r.content:
            return json.loads(r.content)

        return {}
    
    def put(self, restype=None, resid=None, path=None, data={}, params={}, endpoint=None, url=None):
        if url is None:
            url = build_url(self.api_url, restype, resid, path, endpoint)

        logging.info(json.dumps(data, indent=4))
        r = self.conn.put(url, json=data, params=params)

        if r.content:
            return json.loads(r.content)

        return {}

class EcxAPI(object):
    def __init__(self, ecx_session, restype=None, endpoint=None):
        self.ecx_session = ecx_session
        self.restype = restype
        self.endpoint = endpoint
        self.list_field = resource_to_listfield.get(restype, self.restype + 's')

    def get(self, resid=None, path=None, params={}, url=None):
        return self.ecx_session.get(restype=self.restype, resid=resid, path=path, params=params, url=url)

    def stream_get(self, resid=None, path=None, params={}, url=None, outfile=None):
        return self.ecx_session.stream_get(restype=self.restype, resid=resid, path=path,
                                           params=params, url=url, outfile=outfile)

    def delete(self, resid):
         return self.ecx_session.delete(restype=self.restype, resid=resid)

    def list(self):
        return self.ecx_session.get(restype=self.restype)[self.list_field]

    def post(self, resid=None, path=None, data={}, params={}, url=None):
        return self.ecx_session.post(restype=self.restype, resid=resid, path=path, data=data,
                                     params=params, url=url)
                                     
    def put(self, resid=None, path=None, data={}, params={}, url=None):
        return self.ecx_session.put(restype=self.restype, resid=resid, path=path, data=data,
                                     params=params, url=url)

class JobAPI(EcxAPI):
    def __init__(self, ecx_session):
        super(JobAPI, self).__init__(ecx_session, 'job')

    # TODO: May need to check this API seems to return null instead of current status
    # Can use lastSessionStatus property in the job object for now
    def status(self, jobid):
        return self.ecx_session.get(restype=self.restype, resid=jobid, path='status')

    # TODO: Accept a callback that can be called every time job status is polled.
    # The process of job start is different depending on whether jobs have storage
    # workflows.
    def run(self, jobid, workflowid=None):
        job = self.ecx_session.get(restype=self.restype, resid=jobid)

        links = job['links']
        if 'start' not in links:
            raise Exception("'start' link not found for job: %d" % jobid)

        start_link = links['start']
        reqdata = {}

        if 'schema' in start_link:
            # The job has storage profiles.
            schema_data = self.ecx_session.get(url=start_link['schema'])
            workflows = schema_data['parameter']['actionname']['values']
            if not workflows:
                raise Exception("No workflows for job: %d" % jobid)
            if len(workflows) > 1:
                if(workflowid is None):
                    raise Exception("Workflow ID not provided")
                else:
                    reqdata["actionname"] = workflowid
            else:
                reqdata["actionname"] = workflows[0]['value']

        return self.ecx_session.post(url=start_link['href'], data=reqdata)

    def get_log_entries(self, jobsession_id, page_size=1000, page_start_index=0):
        logging.info("*** get_log_entries: jobsession_id = %s, page_start_index: %s ***" % (jobsession_id, page_start_index))

        resp = self.ecx_session.get(restype='log', path='job',
                                    params={'pageSize': page_size, 'pageStartIndex': page_start_index,
                                            'sort': '[{"property":"logTime","direction":"ASC"}]',
                                            'filter': '[{"property":"jobsessionId","value":"%s"}]'%jobsession_id})

        logging.info("*** get_log_entries:     Received %d entries..." % len(resp['logs']))

        return resp['logs']

class UserIdentityAPI(EcxAPI):
    def __init__(self, ecx_session):
        super(UserIdentityAPI, self).__init__(ecx_session, 'identityuser')

    def create(self, data):
        return self.post(data=data)

class AppserverAPI(EcxAPI):
    def __init__(self, ecx_session):
        super(AppserverAPI, self).__init__(ecx_session, 'appserver')

class VsphereAPI(EcxAPI):
    def __init__(self, ecx_session):
        super(VsphereAPI, self).__init__(ecx_session, 'vsphere')

class ResProviderAPI(EcxAPI):
    # Credential info is passed in different field names so we need to maintain
    # the mapping.
    user_field_name_map = {"appserver": "osuser", "purestorage": "user", "emcvnx": "user"}

    # Resource type doesn't always correspond to API so we need a map.
    res_api_map = {"purestorage": "pure"}

    def __init__(self, ecx_session, restype):
        super(ResProviderAPI, self).__init__(ecx_session, ResProviderAPI.res_api_map.get(restype, restype))

    def register(self, name, host, osuser_identity, appType=None, osType=None, catalog=True, ssl=True, vsphere_id=None):
        osuser_field = ResProviderAPI.user_field_name_map.get(self.restype, 'user')
        reqdata = {
            "name": name, "hostAddress": host, "addToCatJob": catalog,
        }

        reqdata[osuser_field] = {
            "href": osuser_identity['links']['self']['href']
        }

        if vsphere_id:
            reqdata["serverType"] = "virtual"
            reqdata["vsphereId"] = vsphere_id

        if appType:
            reqdata["applicationType"] = appType
            reqdata["useKeyAuthentication"] = False

        if osType:
            reqdata["osType"] = osType

        return self.post(data=reqdata)

class AssociationAPI(EcxAPI):
    def __init__(self, ecx_session):
        super(AssociationAPI, self).__init__(ecx_session, 'association')

    def get_using_resources(self, restype, resid):
        return self.get(path="resource/%s/%s" % (restype, resid), params={"action": "listUsingResources"})

class LogAPI(EcxAPI):
    def __init__(self, ecx_session):
        super(LogAPI, self).__init__(ecx_session, 'log')

    def download_logs(self, outfile=None):
        return self.stream_get(path="download/diagnostics", outfile=outfile)

class OracleAPI(EcxAPI):
    def __init__(self, ecx_session):
        super(OracleAPI, self).__init__(ecx_session, 'oracle')
        
    def get_instances(self):
        return self.get(path="oraclehome")
        
    def get_databases_in_instance(self, instanceid):
        return self.get(path="oraclehome/%s/database" % instanceid)

    def get_database_copy_versions(self, instanceid, databaseid):
        return self.get(path="oraclehome/%s/database/%s" % (instanceid, databaseid) + "/version")