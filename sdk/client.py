
import ConfigParser
import json
import os
import time

import click
import requests
from requests.auth import HTTPBasicAuth

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

    def post(self, restype=None, resid=None, path=None, data={}, params={}, endpoint=None, url=None):
        if url is None:
            url = build_url(self.api_url, restype, resid, path, endpoint)

        r = self.conn.post(url, json=data, params=params)

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

    # TODO: Accept a callback that can be called every time job status is polled.
    # The process of job start is different depending on whether jobs have storage
    # workflows.
    def start(self, jobid):
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
                # TODO: This is really not an error. User needs to supply
                # workflow ID to be used in running the job.
                raise Exception("More than one workflow has been found for job: %d" % jobid)

            reqdata["actionname"] = workflows[0]['value']

        return self.ecx_session.post(url=start_link['href'], data=reqdata)

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

