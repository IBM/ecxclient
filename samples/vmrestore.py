#
# Script to update and run an existing VMWare restore job
# --restore is always required (existing restore job name)
# --desttype corresponds to the type of restore being performed
#       1 = use orig host/cluster with sys defined IP (default)
#       2 = use orig host/cluster with original IP
#       3 = use alternate host/cluster (requires destination hostdest,
#           pvlan, tvlan, and dsdest to be defined)
#           Note: all source datastores will be mapped to single defined target datastore
# --vms is optional, job will run as-is without it, use commas to seperate list of VMs
# --start and --end determine time window of copy to use, latest will be used if blank
#

import json
import sys
import time
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
parser.add_option("--vms", dest="vms", help="List of VMs to restore (comma seperated)")
parser.add_option("--start", dest="start", help="Start date/time of copy to use")
parser.add_option("--end", dest="end", help="End date/time of copy to use")
parser.add_option("--desttype", dest="desttype", default="1", help="Destination type (1|2|3)")
parser.add_option("--hostdest", dest="hostdest", help="Destination host/cluster (requireed for type 3)")
parser.add_option("--pvlan", dest="pvlan", help="Destination prod. VLAN (requireed for type 3)")
parser.add_option("--tvlan", dest="tvlan", help="Destination test VLAN (requireed for type 3)")
parser.add_option("--dsdest", dest="dsdest", help="Destination datastore (requireed for type 3)")
(options, args) = parser.parse_args()
if(options.vms is not None):
    options.vms = options.vms.split(",")

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

def get_info_for_vms():
    vspheres = client.EcxAPI(session, 'vsphere').list()
    allvms = []
    selectedvms = []
    for vsphere in vspheres:
        vspherevms = client.EcxAPI(session, 'vsphere').get(url=vsphere['links']['vms']['href'])['vms']
        allvms.extend(vspherevms)
    for vm in allvms:
        if (vm['name'] in options.vms):
            selectedvms.append(vm.copy())
    return selectedvms

def build_source_info_for_vms(vmlist):
    source = []
    vmsource = {}
    vmsourcemd = {}
    for vm in vmlist:
        vmsource['href'] = vm['links']['self']['href']
        vmsource['resourceType'] = "vm"
        vmsource['id'] = vm['id']
        vmsource['include'] = True
        vmsourcemd['id'] = vm['id']
        vmsourcemd['path'] = build_path_for_vm(vm)
        vmsourcemd['name'] = vm['name']
        vmsourcemd['resourceType'] = "vm"
        vmsource['metadata'] = vmsourcemd
        vmsource['version'] = build_version_for_vm(vm)
        source.append(vmsource.copy())
    return source

def build_version_for_vm(vm):
    vsphere = client.EcxAPI(session, 'vsphere').get(url=vm['links']['vsphere']['href'])
    versionurl = vm['links']['self']['href']+"/version"
    versionparams = {'time': 0, 'filter': '[{"property":"siteId","op":"=","value":"%s"}]'%vsphere['siteId']}
    versions = client.EcxAPI(session, 'vsphere').get(url=versionurl, params=versionparams)['versions']

    version = {}
    metadata = {}
    # no copy filters supplied use latest
    if (options.end is None or options.start is None):
        version['href'] = vm['links']['self']['href']+"/version/latest"
        metadata['id'] = "latest"
        metadata['name'] = "Use Latest"
        version['metadata'] = metadata
        logger.info("Using latest backup copy version.")
        return version
    # match on dates
    else:
        start = int(datetime.datetime.strptime(options.start, '%m/%d/%Y %M:%S').strftime("%s"))*1000
        end = int(datetime.datetime.strptime(options.end, '%m/%d/%Y %M:%S').strftime("%s"))*1000
        for vers in versions:
            prottime = int(vers['protectionInfo']['protectionTime'])
            if (prottime > start and prottime < end):
                version['href'] = vers['links']['self']['href']
                metadata['id'] = vers['id']
                metadata['name'] = time.ctime(prottime/1000)[4:].replace("  "," ")
                version['metadata'] = metadata
                logger.info("Using backup copy version from: %s" % metadata['name'])
                return version
    logger.info("No backup copy found with provided dates or backup copy name")
    session.delete('endeavour/session/')
    sys.exit(2)

def build_path_for_vm(vm):
    vsphere = client.EcxAPI(session, 'vsphere').get(url=vm['links']['vsphere']['href'])
    dc = client.EcxAPI(session, 'vsphere').get(url=vm['links']['datacenter']['href'])
    sitepath = vsphere['siteName'] + ":" + vsphere['siteId']
    vcpath = vsphere['name'] + ":" + vsphere['id']
    dcpath = dc['name'] + ":" + dc['id']
    # seems like we're unable to build folder path without iterating through all of them
    # this causes minor issue with autodirect to selected VMs in folders in the ECX UI
    # not needed for succesful updating of the policy or running it, leaving it out for performance
    folderpath = "folder"
    path = sitepath + "/" + vcpath + "/" + dcpath + "/" + folderpath
    return path

def build_policy_for_update(policy, sourceinfo, vmlist):
    policy['spec']['source'] = sourceinfo
    if(options.desttype == "1"):
        policy['spec']['subpolicy'][0]['destination'] = {"systemDefined": True}
        policy['spec']['subpolicy'][0]['option']['poweron'] = True
    elif(options.desttype == "2"):
        policy['spec']['subpolicy'][0].pop('destination', None)
        policy['spec']['subpolicy'][0]['option']['poweron'] = False
    elif(options.desttype == "3"):
        policy['spec']['subpolicy'][0]['destination'] = build_alt_dest(policy, vmlist)
    return policy

def build_alt_dest(policy, vmlist):
    destination = {}
    destination['target'] = build_alt_dest_target()
    destination['mapvirtualnetwork'] = build_alt_dest_vlan()
    destination['mapRRPdatastore'] = build_alt_dest_ds()
    destination['mapsubnet'] = {"systemDefined": True}
    return destination

def build_alt_dest_target():
    target = {}
    targetmd = {}
    vspheres = client.EcxAPI(session, 'vsphere').list()
    for vsphere in vspheres:
        hosts = client.EcxAPI(session, 'vsphere').get(url=vsphere['links']['hosts']['href'])['hosts']
        for host in hosts:
            if(host['name'] == options.hostdest):
                targethost = host
                targetvsphere = vsphere
                targetdc = client.EcxAPI(session, 'vsphere').get(url=host['links']['datacenter']['href'])
                break
    target['href'] = targethost['links']['self']['href']
    target['resourceType'] = targethost['resourceType']
    targetmd['path'] = targetvsphere['siteName'] + ":" + targetvsphere['siteId'] + "/" + targethost['name'] + ":"
    targetmd['path'] += targethost['id'] + "/" + targetdc['name'] + ":" + targetdc['id']
    targetmd['name'] = targethost['name']
    target['metadata'] = targetmd
    return target

def build_alt_dest_vlan():
    return None

def build_alt_dest_ds():
    return None

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

def run_restore_job(job, swfid=None):
    run = client.JobAPI(session).run(job['id'])
    return run

def update_policy_and_run_restore():
    job = get_restore_job()
    policy = get_policy_for_job(job)
    vmlist = get_info_for_vms()
    sourceinfo = build_source_info_for_vms(vmlist)
    updatedpolicy = build_policy_for_update(policy, sourceinfo, vmlist)
    prettyprint(updatedpolicy)

session = client.EcxSession(options.host, options.username, options.password)
session.login()
update_policy_and_run_restore()

session.delete('endeavour/session/')

