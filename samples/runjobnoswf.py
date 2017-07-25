import json
import sys
import logging
import ecxclient.sdk.client as client

logger = logging.getLogger('logger')
logger.setLevel(logging.INFO)

jobname = sys.argv[1]
host = "https://172.20.58.1:8443"
username = "admin"
password = "catal0gic"

session = client.EcxSession(host, username, password)

def validate_input():
    if(jobname is None):
        print "Please enter ECX job name as argument."
        sys.exit(2)

def get_jobs_list():
    jobs = client.EcxAPI(session, 'job').list()
    return jobs

def find_job_in_list(jobslist):
    for job in jobslist:
        if(job['name'] is not None):
            if(job['name'].upper() == jobname.upper()):
                return job
    logger.info("No job found with name %d" % options.jobname)
    sys.exit(2)

def run_job(job):
    run = client.JobAPI(session).run(job['id'])
    logger.info("Running job " + job['name'])
    

session.login()
validate_input()
jobslist = get_jobs_list()
job = find_job_in_list(jobslist)
run_job(job)

session.delete('endeavour/session/')
