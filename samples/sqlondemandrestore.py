#
# Script to restore a SQL database on demand and remove backup job once restored
# The workflow of the script is as follows:
#    Create temp backup job for provided database name
#    Run backup job (wait for completion)
#    Create temp restore job (using backup we just took as source)
#    Run restore job in make permanent mode
#    Delete backup and restore jobs
#    Run maintenance policy (to remove snapshots)
# The script requires "seed" jobs be defined for backup and restore
# The backup seed job must have only one SLA policy associated with it
# The temporary jobs will be a copy of this seed with the corresponding
# source and target information changed
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
parser.add_option("--db", dest="db", help="Source database name")
parser.add_option("--inst", dest="inst", help="Source instance name")
parser.add_option("--seedbu", dest="seedbu", help="Seed Backup Job Name")
parser.add_option("--seedres", dest="seedres", help="Seed Restore Job Name")
parser.add_option("--tinst", dest="tinst", help="Target instance name")
parser.add_option("--tdb", dest="tdb", help="Target database name")
(options, args) = parser.parse_args()

def prettyprint(indata):
    print json.dumps(indata, sort_keys=True,indent=4, separators=(',', ': '))

def get_backup_seed_pol():
    jobs = client.EcxAPI(session, 'job').list()
    for job in jobs:
        if(job['name'].upper() == options.seedbu.upper()):
            pol = client.EcxAPI(session, 'policy').get(resid=job['policyId'])
            if(pol['type'] == "protection" and pol['subType'] == "application"):
                if(pol['applicationType'] == "sql"):
                    return pol
    logger.info("No backup seed policy found, please check name exists")
    session.delete('endeavour/session/')
    sys.exit(2)

def get_source_info():
    sourceinsdbinfo = {}
    instances = client.EcxAPI(session, 'application').get(path="/sql/instance")['instances']
    for instance in instances:
        if(instance['name'].upper() == options.inst.upper()):
            sourcedbs = client.EcxAPI(session, 'application').get(url=instance['links']['databases']['href'])['databases']
            for sourcedb in sourcedbs:
                if (sourcedb['name'].upper() == options.db.upper()):
                    sourceinsdbinfo['instance'] = instance
                    sourceinsdbinfo['database'] = sourcedb
                    return sourceinsdbinfo
    logger.info("No source db found with name %s" % options.db)
    session.delete('endeavour/session/')
    sys.exit(2)

def create_backup_job(buseedpol, busource):
    logger.info("Creating backup job")
    newpol = buseedpol
    newjob = {}
    jobname = "SQL On-Demand Backup " + str(int(time.time()))
    del newpol['id']
    del newpol['links']
    del newpol['lastUpdated']
    del newpol['creationTime']
    del newpol['logicalDelete']
    del newpol['rbacPath']
    del newpol['tenantId']
    newpol['name'] = jobname
    newpol['spec']['source'] = []
    newpol['spec']['source'].append({})
    newpol['spec']['source'][0]['href'] = busource['database']['links']['self']['href']
    newpol['spec']['source'][0]['id'] = busource['database']['id']
    newpol['spec']['source'][0]['include'] = True
    newpol['spec']['source'][0]['resourceType'] = "database"
    newpol['spec']['source'][0]['metadata'] = {}
    newpol['spec']['source'][0]['metadata']['id'] = busource['database']['id']
    newpol['spec']['source'][0]['metadata']['name'] = busource['database']['name']
    #since this job is temporary we don't need to worry about getting path data for UI
    newpol['spec']['source'][0]['metadata']['path'] = "PATH"
    polresp = client.EcxAPI(session, 'policy').post(data=newpol)
    newjob['description'] = "Temporary job"
    newjob['name'] = jobname
    newjob['policyId'] = polresp['id']
    newjob['triggerIds'] = []
    jobresp = client.EcxAPI(session, 'job').post(data=newjob)
    return jobresp    

def run_backup_job_and_wait_for_completion(bujob):
    logger.info("Running backup job... please wait.")
    run = client.JobAPI(session).run(bujob['id'])
    time.sleep(10)
    job = client.EcxAPI(session, 'job').get(resid=bujob['id'])
    while (job['lastrun']['status'] == "RUNNING"):
        time.sleep(10)
        job = client.EcxAPI(session, 'job').get(resid=bujob['id'])
    if (job['lastrun']['status'] == "COMPLETED"):
        return job
    logger.error("Job did not complete, please log in to UI to view logs.")
    session.delete('endeavour/session/')
    sys.exit(2)

def get_restore_seed_pol():
    jobs = client.EcxAPI(session, 'job').list()
    for job in jobs:
        if(job['name'].upper() == options.seedres.upper()):
            pol = client.EcxAPI(session, 'policy').get(resid=job['policyId'])
            if(pol['type'] == "recovery" and pol['subType'] == "application"):
                if(pol['applicationType'] == "sql"):
                    return pol
    logger.info("No restore seed policy found, please check name exists")
    session.delete('endeavour/session/')
    sys.exit(2)

def get_target_info():
    instances = client.EcxAPI(session, 'application').get(path="/sql/instance")['instances']
    for instance in instances:
        if (instance['name'].upper() == options.tinst.upper()):
            return instance
    logger.info("No target instance found with name %s" % options.tinst)
    session.delete('endeavour/session/')
    sys.exit(2)

def create_restore_job(resseedpol, restarget, busource):
    logger.info("Creating restore job")
    newpol = resseedpol
    newjob = {}
    jobname = "SQL On-Demand Restore " + str(int(time.time()))
    del newpol['id']
    del newpol['links']
    del newpol['lastUpdated']
    del newpol['creationTime']
    del newpol['logicalDelete']
    del newpol['rbacPath']
    del newpol['tenantId']
    newpol['name'] = jobname
    newpol['spec']['source'] = []
    newpol['spec']['source'].append({})
    newpol['spec']['source'][0]['href'] = busource['database']['links']['self']['href'] + "?time=0"
    newpol['spec']['source'][0]['id'] = busource['database']['id']
    newpol['spec']['source'][0]['include'] = True
    newpol['spec']['source'][0]['resourceType'] = "database"
    newpol['spec']['source'][0]['metadata'] = {}
    newpol['spec']['source'][0]['metadata']['id'] = busource['database']['id']
    newpol['spec']['source'][0]['metadata']['name'] = busource['database']['name']
    newpol['spec']['source'][0]['metadata']['path'] = "PATH"
    newpol['spec']['source'][0]['version'] = {}
    newpol['spec']['source'][0]['version']['href'] = busource['database']['links']['self']['href'] + "/version/latest"
    newpol['spec']['source'][0]['version']['metadata'] = {}
    newpol['spec']['source'][0]['version']['metadata']['id'] = "latest"
    newpol['spec']['source'][0]['version']['metadata']['name'] = "Use Latest"
    newpol['spec']['subpolicy'][0]['description'] = ""
    newpol['spec']['subpolicy'][0]['destination']['mapdatabase'] = {}
    mdkey = busource['database']['links']['self']['href'] + "?time=0"
    newpol['spec']['subpolicy'][0]['destination']['mapdatabase'][mdkey] = {"name": options.tdb}
    newpol['spec']['subpolicy'][0]['destination']['target']['href'] = restarget['links']['self']['href']
    newpol['spec']['subpolicy'][0]['destination']['target']['metadata']['id'] = restarget['id']
    newpol['spec']['subpolicy'][0]['destination']['target']['metadata']['name'] = restarget['name']
    newpol['spec']['subpolicy'][0]['destination']['target']['metadata']['path'] = "PATH"
    newpol['spec']['subpolicy'][0]['name'] = jobname
    newpol['spec']['subpolicy'][0]['option']['makepermanent'] = "enabled"
    newpol['spec']['subpolicy'][0]['source']['copy']['site']['href'] = busource['database']['links']['site']['href']
    newpol['spec']['subpolicy'][0]['source']['copy']['site']['metadata']['name'] = "TEMP"
    newpol['spec']['subpolicy'][0]['source']['copy']['site']['metadata']['pointintime'] = False
    polresp = client.EcxAPI(session, 'policy').post(data=newpol)
    newjob['description'] = "Temporary job"
    newjob['name'] = jobname
    newjob['policyId'] = polresp['id']
    newjob['triggerIds'] = []
    jobresp = client.EcxAPI(session, 'job').post(data=newjob)
    return jobresp

def run_restore_job_and_wait_for_completion(resjob):
    logger.info("Running restore job... please wait.")
    run = client.JobAPI(session).run(resjob['id'])
    time.sleep(10)
    job = client.EcxAPI(session, 'job').get(resid=resjob['id'])
    # Note: We need to also wait here on RESOURCE ACTIVE state as job goes into that
    # status during the "Make Permanent" operation
    # However, if this step fails, we are then stuck in that state until restore is cancelled
    # may want to introduce some sort of timeout failure here
    while (job['lastrun']['status'] == "RUNNING" or job['lastrun']['status'] == "RESOURCE ACTIVE"):
        time.sleep(10)
        job = client.EcxAPI(session, 'job').get(resid=resjob['id'])
    if (job['lastrun']['status'] == "COMPLETED"):
        return job
    logger.error("Job did not complete, please log in to UI to view logs.")
    session.delete('endeavour/session/')
    sys.exit(2)

def delete_temp_jobs(bujob, resjob):
    logger.info("Deleting temporary jobs.")
    client.EcxAPI(session, 'job').delete(resid=bujob['id'])
    client.EcxAPI(session, 'policy').delete(resid=bujob['policyId'])
    client.EcxAPI(session, 'job').delete(resid=resjob['id'])
    client.EcxAPI(session, 'policy').delete(resid=resjob['policyId'])

def run_maint_job():
    logger.info("Running maintenance job.")
    jobs = client.EcxAPI(session, 'job').list()
    for job in jobs:
        if(job['type'] == "maintenance"):
            client.JobAPI(session).run(job['id'])
    

def run():
    buseedpol = get_backup_seed_pol()
    busource = get_source_info()
    resseedpol = get_restore_seed_pol()
    restarget = get_target_info()
    bujob = create_backup_job(buseedpol, busource)
    run_backup_job_and_wait_for_completion(bujob)
    resjob = create_restore_job(resseedpol, restarget, busource)
    run_restore_job_and_wait_for_completion(resjob)
    delete_temp_jobs(bujob, resjob)
    run_maint_job()

session = client.EcxSession(options.host, options.username, options.password)
session.login()
run()
session.delete('endeavour/session/')
