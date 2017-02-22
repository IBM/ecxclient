
import ConfigParser
import os

import click
import requests

import util

class Context(object):
    def __init__(self):
        pass

pass_context = click.make_pass_decorator(Context, ensure=True)

class EcxSession(object):
    def __init__(self, url, username, password):
        self.url = url
        self.username = username
        self.password = password
        self.sessionid = None
        self.cfgfile = os.path.join(click.get_app_dir("ecxcli"), 'config.ini')
        self.cfgdir = os.path.dirname(self.cfgfile)
        if not os.path.exists(self.cfgdir):
            os.makedirs(self.cfgdir)

        self.conn = requests.Session()
        self.conn.verify = False
        self.conn.hooks.update({'response': util.raise_response_error})

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
        r = self.conn.post("%s/api/endeavour/session" % self.url, auth=HTTPBasicAuth(self.username, self.password))
        self.sessionid = r.json()['sessionid']
        self.save_config()

    def save_config(self):
        parser = ConfigParser.RawConfigParser()
        parser.add_section(self.username)
        parser.set(self.username, 'password', self.password)
        parser.set(self.username, 'sessionid', self.sessionid)

        parser.write(open(self.cfgfile, 'wb'))

    def __repr__(self):
        return 'EcxSession: user: %s' % self.username

