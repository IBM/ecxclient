#
# Script to update and run an existing SVC volume backup job
# --backup is always required (existing back up job name)
# --vols is optional, job will run as-is without it, use commas to seperate list of volumes
# --sla is optional, must be selected as one of the optional SLAs in job defintion
#

import json
import sys
import time
import copy
import datetime
from optparse import OptionParser
import logging
import ecxclient.sdk.client as client

logger = logging.getLogger('logger')
logging.basicConfig()
logger.setLevel(logging.INFO)

parser = OptionParser()
parser.add_option("--user", dest="username", help="ECX Username")
parser.add_option("--pass", dest="password", help="ECX Password")
parser.add_option("--host", dest="host", help="ECX Host, (ex. https://172.20.58.10:8443)")
parser.add_option("--backup", dest="backup", help="Backup Job Name")
parser.add_option("--vols", dest="vols", help="List of volume(s) to backup/snapshot (comma seperated)")
parser.add_option("--sla", dest="sla", help="SLA Policy to use for backup (optional)")
(options, args) = parser.parse_args()
if(options.vols is not None):
    options.vols = options.vols.split(",")

def prettyprint(indata):
    print json.dumps(indata, sort_keys=True,indent=4, separators=(',', ': '))

def get_backup_job():
    jobs = client.EcxAPI(session, 'job').list()
    for job in jobs:
        if(job['name'].upper() == options.backup.upper()):
            return job
    logger.info("No job found with name %s" % options.backup)
    session.delete('endeavour/session/')
    sys.exit(2)

def get_policy_for_job(job):
    policy = client.EcxAPI(session, 'policy').get(resid=job['policyId'])
    return policy

def get_info_for_vols():
    svcs = client.EcxAPI(session, 'ibmsvc').list()
    allvols = []
    selectedvols = []
    for svc in svcs:
        try:
            svcvols = client.EcxAPI(session, 'ibmsvc').get(url=svc['links']['volumes']['href'])['volumes']
            allvols.extend(svcvols)
        except:
            print "Invalid provider " + svc['id']
    for vol in allvols:
        if (vol['name'] in options.vols):
            selectedvols.append(copy.deepcopy(vol))
    return selectedvols

def build_source_info_for_vols(vollist):
    source = []
    volsource = {}
    volsourcemd = {}
    for vol in vollist:
        volsource['href'] = vol['links']['self']['href']
        volsource['resourceType'] = "volume"
        volsource['id'] = vol['id']
        volsource['include'] = True
        volsourcemd['id'] = vol['id']
        volsourcemd['path'] = build_path_for_vol(vol)
        volsourcemd['name'] = vol['name']
        volsourcemd['resourceType'] = "volume"
        volsource['metadata'] = volsourcemd
        source.append(copy.deepcopy(volsource))
    return source
    

def build_path_for_vol(vol):
    sitepath = vol['siteName'] + ":" + vol['siteId']
    svc = client.EcxAPI(session, 'ibmsvc').get(url=vol['links']['ibmsvc']['href'])
    svcpath = svc['name'] + ":" + svc['id']
    path = sitepath + "/" + svcpath
    return path

def build_policy_for_update(policy, sourceinfo):
    policy['spec']['source'] = sourceinfo
    return policy

def update_policy(updatedpolicy):
    polid = updatedpolicy['id']
    del updatedpolicy['id']
    del updatedpolicy['links']
    del updatedpolicy['lastUpdated']
    del updatedpolicy['creationTime']
    del updatedpolicy['logicalDelete']
    del updatedpolicy['rbacPath']
    del updatedpolicy['tenantId']
    newpolicy = client.EcxAPI(session, 'policy').put(resid=polid, data=updatedpolicy)
    return newpolicy

def get_swf_id(policy):
    for swf in policy['spec']['storageworkflow']:
        if (swf['name'].upper() == options.sla.upper()):
            return swf['id']
    logger.info("No SLA found with name %s" % options.sla)
    session.delete('endeavour/session/')
    sys.exit(2)

def run_backup_job(job, swfid=None):
    run = client.JobAPI(session).run(job['id'], swfid)
    return run

def update_policy_and_run_backup():
    job = get_backup_job()
    policy = get_policy_for_job(job)
    if(options.vols is not None):
        logger.info("Getting Information for %s" % options.vols)
        vollist = get_info_for_vols()
        sourceinfo = build_source_info_for_vols(vollist)
        updatedpolicy = build_policy_for_update(policy, sourceinfo)
        newpolicy = update_policy(updatedpolicy)
        logger.info("Updating job %s" % job['name'])
    logger.info("Running job %s" % job['name'])
    if(options.sla is not None):
        swfid = get_swf_id(policy)
        run_backup_job(job, swfid)
    else:
        run_backup_job(job)


session = client.EcxSession(options.host, options.username, options.password)
session.login()
update_policy_and_run_backup()

session.delete('endeavour/session/')
