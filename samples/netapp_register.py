# script to register multiple netapp providers given a .csv file with parameters
# example:
# python netapp_register.py --user="admin" --pass="password123" --host="https://172.20.58.1:8443" --csv="/tmp/provs.csv"

import sys
import json
import logging
from optparse import OptionParser
import csv
import ecxclient.sdk.client as client

logger = logging.getLogger('logger')
logger.setLevel(logging.INFO)

parser = OptionParser()
parser.add_option("--user", dest="username", help="ECX Username")
parser.add_option("--pass", dest="password", help="ECX Password")
parser.add_option("--host", dest="host", help="ECX Host, (ex. https://172.20.58.10:8443)")
parser.add_option("--csv", dest="csv", help="Full path to .csv providers file")

(opt, args) = parser.parse_args()

session = client.EcxSession(opt.host, opt.username, opt.password)

def prettyprint(indata):
    print json.dumps(indata, sort_keys=True,indent=4, separators=(',', ': '))

def read_csv_into_list():
    with open(opt.csv) as csvfile:
        provs = list(csv.DictReader(csvfile, delimiter=','))
    return provs

def get_site_data():
    return client.EcxAPI(session, 'site').list()

def get_user_data():
    return client.EcxAPI(session, 'identityuser').list()

def register_providers(providers, sites, users):
    for provider in providers:
        registration = {}
        registration['name'] = provider['name']
        registration['hostAddress'] = provider['host']
        registration['portNumber'] = int(provider['port'])
        if registration['portNumber'] == 80:
            registration['sslConnection'] = False
        else:
            registration['sslConnection'] = True
        registration['addToCatJob'] = True
        registration['startCatalog'] = False
        for site in sites:
            if provider['site'].upper() == site['name'].upper():
                registration['siteId'] = site['id']
        for user in users:
            if provider['user'].upper() == user['name'].upper():
                registration['user'] = {}
                registration['user']['href'] = user['links']['self']['href']
        try:
            client.EcxAPI(session, '').post(path='netapp',data=registration)
        except:
            print "Failed to register the provider"
            prettyprint(registration)

def run():
    session.login()
    providers = read_csv_into_list()
    sites = get_site_data()
    users = get_user_data()
    register_providers(providers, sites, users)
    session.delete('endeavour/session/')

run()
