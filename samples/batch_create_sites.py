# script to create multiple sites given a .csv file with parameters
# example:
# python batch_create_sites.py --user="admin" --pass="password123" --host="https://172.20.58.1:8443" --csv="/tmp/sites.csv"
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
        return list(csv.DictReader(csvfile, delimiter=','))

def create_sites(sites):
    for site in sites:
        body = {"name":site['name'],"description":site['desc'],"defaultSite":False}
        try:
            client.EcxAPI(session, 'site').post(data=body)
            print "Created site " + site['name']
        except:
            print "Failed to create the site:"
            prettyprint(body)

def run():
    session.login()
    sites = read_csv_into_list()
    print sites
    create_sites(sites)
    session.delete('endeavour/session/')

run()
