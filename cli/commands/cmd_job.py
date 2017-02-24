
import json
import sys
import time

import click

import util
from sdk.client import JobAPI

def poll(self, job):
    jobapi = JobAPI(self.ecx_session)

    status = job.status
    print "job status: %s" % status
    
    active = False
    counter = 0

    while True:
        if active and (status == "PENDING"):
            # Job moved from active state(s) to PENDING so
            # it should be treated as done.
            break

        if status == "IDLE":
            break

        if (not active) and (status != "PENDING"):
            # Job moved from PENDING to other active states.
            jobIsActive = true

        print "    %d: Sleeping for 30 seconds..." % counter
        time.sleep(30)
        counter = counter + 1

        status = jobapi.status(job['id'])['currentStatus']
        print "job status: %s" % status

    return status

    # Job is done so it is now guaranteed to have "lastrun" field.
    # jobStatus = JobsessionAPI.monitor(JobAPI.get(job.id).lastrun.sessionId).status
    # println "jobStatus 3 (${job.id}): ${jobStatus}"
    # return jobStatus

@click.group()
@util.pass_context
def cli(ctx, **kwargs):
    """Job resource.
    """

    pass

@cli.command()
@util.pass_context
def list(ctx, **kwargs):
    resp = JobAPI(ecx_session=ctx.ecx_session).list()
    util.print_response(resp)

@cli.command()
@click.argument('jobid', type=click.INT)
@util.pass_context
def info(ctx, jobid, **kwargs):
    resp = JobAPI(ecx_session=ctx.ecx_session).get(jobid)
    util.print_response(resp)

@cli.command()
@click.argument('jobid', type=click.INT)
@click.option('--resp/--no-resp', default=False, help='Show POST response.')
@util.pass_context
def start(ctx, jobid, **kwargs):
    resp = JobAPI(ecx_session=ctx.ecx_session).start(jobid)
    util.print_response(resp)
