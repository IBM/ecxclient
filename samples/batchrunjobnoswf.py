import json
import sys
import logging
import time
import ecxclient.sdk.client as client

logger = logging.getLogger('logger')
logger.setLevel(logging.INFO)

host = "https://172.20.58.1:8443"
username = "admin"
password = "catal0gic"
delay = 300

def get_jobs_list():
    jobs = client.EcxAPI(session, 'job').list()
    return jobs

def find_job_in_list(jobslist, jobname):
    for job in jobslist:
        if(job['name'].upper() == jobname.upper()):
            return job
    logger.info("No job found with name %d" % options.jobname)
    sys.exit(2)

def run_job(job):
    try:
        run = client.JobAPI(session).run(job['id'])
    except client.requests.exceptions.HTTPError as e:
        error = json.loads(e.response.content)
        print "Error running job: " + job['name'] + " " + error['id']
        return
        
    logger.info("Running job " + job['name'])
    logger.info("Please wait " + str(delay) + " seconds for next job...")
    time.sleep(300)

session = client.EcxSession(host, username, password)
session.login()
jobslist = get_jobs_list()

iterargs = iter(sys.argv)
next(iterargs)
for arg in iterargs:
    jobname = arg
    job = find_job_in_list(jobslist, jobname)
    run_job(job)
session.delete('endeavour/session/')
