#
# Script to do an Oracle restore given an optional date range of the copy
# An existing restore job is required, copy version of that job will be updated if applicable
# If no date range is provided the latest copy will be used
# Set the cancel parameter = true if using this script to cancel/clean up an existing restore job
#

import json
import sys
import time
import datetime
from optparse import OptionParser
import logging
import ecxclient.sdk.client as client

logger = logging.getLogger('logger')
logger.setLevel(logging.INFO)

parser = OptionParser()
parser.add_option("--user", dest="username", help="ECX Username")
parser.add_option("--pass", dest="password", help="ECX Password")
parser.add_option("--host", dest="host", help="ECX Host, (ex. https://172.20.58.10:8443)")
parser.add_option("--restore", dest="restore", help="Restore Job Name")
parser.add_option("--start", dest="start", help="Start Date filter for backup version (optional)")
parser.add_option("--end", dest="end", help="End Date filter for backup version (optional)")
parser.add_option("--cancel", dest="cancel", help="Enter 'true' for Cancel/Cleanup restore (optional)")
(options, args) = parser.parse_args()

def prettyprint(indata):
    print json.dumps(indata, sort_keys=True,indent=4, separators=(',', ': '))

def get_restore_job():
    jobs = client.EcxAPI(session, 'job').list()
    for job in jobs:
        if(job['name'].upper() == options.restore.upper()):
            return job
    logger.info("No job found with name %d" % options.restore)
    sys.exit(2)

def get_policy_for_job(job):
    policy = client.EcxAPI(session, 'policy').get(resid=job['policyId'])
    return policy

def get_version_for_policy(policy):
    version = {}
    metadata = {}
    sourceurl = policy['spec']['source'][0]['href']
    source = client.EcxAPI(session, 'oracle').get(url=sourceurl)
    if (options.end is None or options.start is None):
        version['href'] = source['links']['latestversion']['href']
        metadata['id'] = "latest"
        metadata['name'] = "Use Latest"
        version['metadata'] = metadata
        return version
    else:
        start = int(datetime.datetime.strptime(options.start, '%m/%d/%Y').strftime("%s"))*1000
        end = int(datetime.datetime.strptime(options.end, '%m/%d/%Y').strftime("%s"))*1000
        versionsurl = source['links']['versions']['href']
        versions = client.EcxAPI(session, 'oracle').get(url=versionsurl)['versions']
        for vers in versions:
            prottime = int(vers['protectionInfo']['protectionTime'])
            if (prottime > start and prottime < end):
                version['href'] = vers['links']['self']['href']
                metadata['id'] = vers['id']
                metadata['name'] = time.ctime(prottime/1000)[4:]
                version['metadata'] = metadata
                return version
    logger.info("No backup copy found with provided dates")
    sys.exit(2)

def update_restore_policy(policy):
    polid = policy['id']
    del policy['id']
    del policy['links']
    del policy['lastUpdated']
    del policy['creationTime']
    del policy['logicalDelete']
    del policy['rbacPath']
    del policy['tenantId']
    policy = client.EcxAPI(session, 'policy').put(resid=polid, data=policy)
    return policy

def get_pending_job_session(job):
    sessionurl = job['links']['pendingjobsessions']['href']
    jobsession = client.EcxAPI(session, 'jobsession').get(url=sessionurl)
    return jobsession['sessions'][0]

def cancel_restore_job(session):
    cancelurl = session['links']['cancel_ra']['href']
    return client.EcxAPI(session, 'jobsession').post(url=cancelurl, data={})

def run_restore_job(job):
    return client.JobAPI(session).run(job['id'])

def run_restore():
    job = get_restore_job()
    if (options.cancel is not None):
        jobsession = get_pending_job_session(job)
        cancel_restore_job(jobsession)
    else:
        policy = get_policy_for_job(job)
        version = get_version_for_policy(policy)
        policy['spec']['source'][0]['version'] = version
        policy = update_restore_policy(policy)
        run_restore_job(job)

session = client.EcxSession(options.host, options.username, options.password)
session.login()

run_restore()

session.delete('endeavour/session/')

