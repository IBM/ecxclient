# Script to change default admin password in ECX/SCDM
# Sets admin password based on argument
# Use changedefaultpass.py -h for help
# example:
# python changedefaultpass.py --host="https://172.20.58.1:8443" --pass="newpass123"

import json
import logging
from optparse import OptionParser
import sys
import imp
import requests
import time
try:
    import urllib3
except ImportError:
    from requests.packages import urllib3
urllib3.disable_warnings()
logging.basicConfig()
logger = logging.getLogger('logger')
logger.setLevel(logging.INFO)

parser = OptionParser()
parser.add_option("--host", dest="host", help="ECX Host, (ex. https://172.20.58.1:8443)")
parser.add_option("--pass", dest="password", help="New ECX admin Password")
(options, args) = parser.parse_args()

def prettyprint(indata):
    print json.dumps(indata, sort_keys=True,indent=4, separators=(',', ': '))

def validate_input():
    if(options.host is None or options.password is None):
        print "Invalid input, use -h switch for help"
        sys.exit(2)

def wait_for_deployment():
    logger.info("Waiting for ECX/SCDM deployment")
    time.sleep(5)
    deployfinished = False
    while(deployfinished is False):
        deployfinished = check_deploy_status()
        time.sleep(5)

def check_deploy_status():
    hdrs = {'Content-Type': 'application/json','Accept': 'application/json'}
    r = requests.post(options.host + '/api/endeavour/session?screeninfo=1', timeout=None,
                      auth=requests.auth.HTTPBasicAuth('admin','fake'), verify=False)
    if(r.status_code != 401):
        return False
    else:
        return True
    
def change_password():
    logger.info("Setting admin password")
    hdrs = {'Content-Type': 'application/json','Accept': 'application/json'}
    payload = {'changePassword': 'true'}
    body = {"newPassword": options.password}
    r = requests.post(options.host + '/api/endeavour/session', json=body,
                      auth=requests.auth.HTTPBasicAuth('admin','password'),
                      verify=False, headers=hdrs, params=payload)
    logger.info("Default password changed succesfully")
    return r.json()['sessionid']

validate_input()
wait_for_deployment()
sessionid = change_password()
