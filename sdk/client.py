
import ConfigParser
import json
import os

import click
import requests
from requests.auth import HTTPBasicAuth

resource_to_endpoint = {
    'job': 'endeavour/job',
    'log': 'endeavour/log',
    'user': 'security/user',
    'identityuser': 'identity/user',
    'appserver': 'appserver',
}

resource_to_listfield = {
    'identityuser': 'users',
}

def build_url(baseurl, restype=None, resid=None, path=None):
    url = baseurl

    if restype is not None:
        url = url + "/" + resource_to_endpoint.get(restype, restype)

    if resid is not None:
        url = url + "/" + str(resid)

    if path is not None:
        if not path.startswith('/'):
            path = '/' + path
        url = url + path

    return url

def raise_response_error(r, *args, **kwargs):
    r.raise_for_status()

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

    def get(self, restype=None, resid=None, path=None, params={}):
        url = build_url(self.api_url, restype, resid, path)

        return json.loads(self.conn.get(url, params=params).content)

    def post(self, restype=None, resid=None, path=None, data={}, params={}):
        url = build_url(self.api_url, restype, resid, path)
        r = self.conn.post(url, data=data, params=params)

        if r.content:
            return json.loads(r.content)

        return {}

class EcxAPI(object):
    def __init__(self, ecx_session, restype=None):
        self.ecx_session = ecx_session
        self.restype = restype
        self.list_field = resource_to_listfield.get(restype, self.restype + 's')

    def get(self, resid):
         return self.ecx_session.get(restype=self.restype, resid=resid)

    def list(self):
        return self.ecx_session.get(restype=self.restype)[self.list_field]

class JobAPI(EcxAPI):
    def __init__(self, ecx_session):
        super(JobAPI, self).__init__(ecx_session, 'job')

    def status(self, jobid):
        return self.ecx_session.get(restype=self.restype, resid=jobid, path='status')

    # Accept a callback that can be called every time job status is polled.
    def start(self, jobid):
        return self.ecx_session.post(restype=self.restype, resid=jobid, params={'action': 'start'})

    def get_log_entries(self, jobsession_id, page_size=25, page_start_index=0):
        resp = self.ecx_session.get(restype='log', path='job',
                                    params={'pageSize': page_size, 'pageStartIndex': page_start_index,
                                            'sort': '[{"property":"logTime","direction":"ASC"}]',
                                            'filter': '[{"property":"jobsessionId","value":"%d"}]'%jobsession_id})

        return resp['logs']

class UserIdentityAPI(EcxAPI):
    def __init__(self, ecx_session):
        super(UserIdentityAPI, self).__init__(ecx_session, 'identityuser')

class AppserverAPI(EcxAPI):
    def __init__(self, ecx_session):
        super(AppserverAPI, self).__init__(ecx_session, 'appserver')

class VsphereAPI(EcxAPI):
    def __init__(self, ecx_session):
        super(VsphereAPI, self).__init__(ecx_session, 'vsphere')

