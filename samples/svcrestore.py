#
# Script to update and run an existing SVC volume restore job
# Scirpt detects job type defined 
# --restore is always required (existing restore job name)
# --vols is optional, job will run as-is without it, use commas to seperate list of volumes
# --start and --end determine time window of copy to use, latest will be used if blank
# --target is optional and represents the destination of the restore
#       This is host name for Instant Disk Restore and storage pool name for Volume Restore
# --run is optional, if set to true job will be run after updating
# --cancel is optional, if set to true pending Instant Disk restore job will be cancelled and cleaned up
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
parser.add_option("--restore", dest="restore", help="Restore Job Name")
parser.add_option("--vols", dest="vols", help="List of volumes to restore (comma seperated)")
parser.add_option("--target", dest="target", help="Target storage pool or host (comma seperated for multiple)")
parser.add_option("--start", dest="start", help="Start date/time of copy to use")
parser.add_option("--end", dest="end", help="End date/time of copy to use")
parser.add_option("--run", dest="run", help="Set to \"True\" to run restore job")
parser.add_option("--cancel", dest="cancel", help="Set to \"True\" to cancel restore job")

(options, args) = parser.parse_args()
if(options.vols is not None):
    options.vols = options.vols.split(",")
if(options.target is not None):
    options.target = options.target.split(",")
if(options.cancel is None):
    options.cancel = ""
if(options.run is None):
    options.run = ""

def prettyprint(indata):
    print json.dumps(indata, sort_keys=True,indent=4, separators=(',', ': '))

def get_restore_job():
    jobs = client.EcxAPI(session, 'job').list()
    for job in jobs:
        if(job['name'].upper() == options.restore.upper()):
            return job
    logger.info("No job found with name %s" % options.restore)
    session.delete('endeavour/session/')
    sys.exit(2)

def get_policy_for_job(job):
    policy = client.EcxAPI(session, 'policy').get(resid=job['policyId'])
    return policy

def get_info_for_vols():
    logger.info("Getting information for volumes...")
    svcs = client.EcxAPI(session, 'ibmsvc').list()
    allvols = []
    selectedvols = []
    for svc in svcs:
        try:
            svcvols = client.EcxAPI(session, 'ibmsvc').get(url=svc['links']['volumes']['href'])['volumes']
            allvols.extend(svcvols)
        except:
            pass
    for vol in allvols:
        if (vol['name'] in options.vols):
            selectedvols.append(copy.deepcopy(vol))
    if(len(selectedvols) < 1):
        logger.info("No volumes found with provided name(s)")
        session.delete('endeavour/session/')
        sys.exit(2)
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
        volsource['metadata'] = volsourcemd
        volsource['version'] = build_version_for_vol(vol)
        source.append(copy.deepcopy(volsource))
    return source

def build_path_for_vol(vol):
    sitepath = vol['siteName'] + ":" + vol['siteId']
    svc = client.EcxAPI(session, 'ibmsvc').get(url=vol['links']['ibmsvc']['href'])
    svcpath = svc['name'] + ":" + svc['id']
    path = sitepath + "/" + svcpath
    return path

def build_version_for_vol(vol):
    volurl = vol['links']['self']['href']+"?time=0"
    volurlarray = [volurl]
    assdata = {'associatedWith': volurlarray,"resourceType": "site"}
    association = client.EcxAPI(session, 'ibmsvc').post(path="query", data=assdata)['sites'][0]
    versionurl = vol['links']['self']['href']+"/version"
    versionparams = {'time': 0, 'filter': '[{"property":"siteId","op":"=","value":"%s"}]'%association['id']}
    versions = client.EcxAPI(session, 'ibmsvc').get(url=versionurl, params=versionparams)['versions']
    version = {}
    metadata = {}
    # no copy filters supplied use latest
    if (options.end is None or options.start is None):
        version['href'] = vol['links']['self']['href']+"/version/latest?time=0"
        metadata['id'] = "latest"
        metadata['name'] = "Use Latest"
        version['metadata'] = metadata
        logger.info("Using latest backup copy version.")
        return version
    # match on dates
    else:
        start = int(datetime.datetime.strptime(options.start, '%m/%d/%Y %H:%M').strftime("%s"))*1000
        end = int(datetime.datetime.strptime(options.end, '%m/%d/%Y %H:%M').strftime("%s"))*1000
        for vers in versions:
            prottime = int(vers['protectionInfo']['protectionTime'])
            if (start < prottime and prottime < end):
                version['href'] = vers['links']['self']['href']
                metadata['id'] = vers['id']
                metadata['name'] = time.ctime(prottime/1000)[4:].replace("  "," ")
                version['metadata'] = metadata
                logger.info("Using backup copy version from: " + metadata['name'] + " for " + vol['name'])
                return version
    logger.info("No backup copy found with provided dates")
    session.delete('endeavour/session/')
    sys.exit(2)

def build_vol_destination(policy):
    destination = policy['spec']['subpolicy'][0]['destination']
    svcs = client.EcxAPI(session, 'ibmsvc').list()
    selectedsps = []
    selectedsvc = {}
    resourceinfo = []
    foundspsvc = False
    for svc in svcs:
        try:
            sps = client.EcxAPI(session, 'ibmsvc').get(url=svc['links']['mdiskgroups']['href'])['mdiskgroups']
            for sp in sps:
                if(sp['name'] in options.target):
                    selectedsps.append(copy.deepcopy(sp))
                    selectedsvc = svc
                    foundspsvc = True
            # dest storage pools can only be selected for one SVC
            if (foundspsvc is True):
                break
        except:
            pass
    if(len(selectedsps) < 1):
        logger.info("No targets found with provided name(s)")
        session.delete('endeavour/session/')
        sys.exit(2)
        
    destination['target']['href'] = selectedsvc['links']['self']['href']
    destination['target']['resourceType'] = "ibmsvc"
    destination['target']['id'] = selectedsvc['id']
    destination['target']['metadata']['path'] = selectedsvc['siteName'] + ":" + selectedsvc['siteId']
    destination['target']['metadata']['name'] = selectedsvc['name']

    for selectedsp in selectedsps:
        spinfo = {}
        spinfo['href'] = selectedsp['links']['self']['href']
        spinfo['resourceType'] = selectedsp['resourceType']
        spinfo['id'] = selectedsp['id']
        spinfo['metadata'] = {"name": selectedsp['name']}
        resourceinfo.append(copy.deepcopy(spinfo))

    destination['resource'] = resourceinfo
    return destination

def build_host_destination(policy):
    #TODO
    destination = policy['spec']['subpolicy'][0]['destination']
    return destination

def build_subpol_source_site(sourceinfo):
    siteinfo = {}
    siteid = sourceinfo[0]['metadata']['path'].split("/")[0].split(":")[1]
    site = client.EcxAPI(session, 'site').get(resid=siteid)
    siteinfo['href'] = site['links']['self']['href']
    siteinfo['metadata'] = {"name": site['name']}
    return siteinfo

def build_policy_for_update(policy, sourceinfo, vollist):
    policy['spec']['source'] = sourceinfo
    if(policy['spec']['subpolicy'][0]['type'].upper() == "RESTORE_VOL"):
        policy['spec']['subpolicy'][0]['destination'] = build_vol_destination(policy)
    else:
        policy['spec']['subpolicy'][0]['destination'] = build_host_destination(policy)
    policy['spec']['subpolicy'][0]['source']['copy']['site'] = build_subpol_source_site(sourceinfo)
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

def get_pending_job_session(job):
    sessionurl = job['links']['pendingjobsessions']['href']
    jobsession = client.EcxAPI(session, 'jobsession').get(url=sessionurl)
    if (len(jobsession['sessions']) < 1):
        logger.info("No pending job sessions found.")
        session.delete('endeavour/session/')
        sys.exit(2)
    return jobsession['sessions'][0]

def run_restore_job(job):
    if(options.cancel.upper() == "TRUE"):
        jobsession = get_pending_job_session(job)
        logger.info("Cleaning up job %s" % job['name'])
        sessioninfo = jobsession['id'] + "?action=resume&actionname=end_iv"
        return client.EcxAPI(session, 'jobsession').post(path=sessioninfo)
    if(options.run.upper() == "TRUE"):
        logger.info("Running job %s" % job['name'])
        return client.JobAPI(session).run(job['id'], "start_test_iv")

def update_policy_and_run_restore():
    job = get_restore_job()
    policy = get_policy_for_job(job)
    
    if(options.vols is not None and options.cancel.upper() != "TRUE"):
        vollist = get_info_for_vols()
        sourceinfo = build_source_info_for_vols(vollist)
        updatedpolicy = build_policy_for_update(policy, sourceinfo, vollist)
        prettyprint(updatedpolicy)
        #newpolicy = update_policy(updatedpolicy)
        #logger.info("Updating job %s" % job['name'])
    #run_restore_job(job)

session = client.EcxSession(options.host, options.username, options.password)
session.login()
update_policy_and_run_restore()

session.delete('endeavour/session/')

