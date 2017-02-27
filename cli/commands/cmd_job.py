
import json
import logging
import sys
import time

import click

import util
from sdk.client import JobAPI

def print_job_log(log_entries):
    for entry in log_entries:
        logtype = entry['type']
        line = '%s %s' % (time.ctime(entry['logTime']/1000).strip(), entry['message'])

        if logtype == 'ERROR':
            click.secho(line, fg='red')
        elif logtype == 'WARN':
            click.secho(line, fg='magenta')
        else:
            click.echo(line)

def monitor(jobapi, job, interval_sec=10):
    status = job['status']
    logging.info("job status: %s" % status)
    
    active = False
    counter = 0

    jobsession_id = int(job['lastrun']['sessionId'])
    log_entries_index = 0
    page_size = 25
    while True:
        if active and (status == "PENDING"):
            # Job moved from active state(s) to PENDING so
            # it should be treated as done.
            break

        if status == "IDLE":
            break

        if (not active) and (status != "PENDING"):
            # Job moved from PENDING to other active states.
            active = True

        log_entries = jobapi.get_log_entries(jobsession_id, page_size, log_entries_index)
        log_entries_index += len(log_entries)
        print_job_log(log_entries)

        time.sleep(interval_sec)
        counter = counter + 1

        status = jobapi.status(job['id'])['currentStatus']
        logging.info("job status: %s" % status)

    print_job_log(jobapi.get_log_entries(jobsession_id, page_size, log_entries_index))

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
@click.option('-i', type=click.INT, metavar='interval_sec', default=10, help='Interval, in seconds, for polling.')
@click.option('--mon', is_flag=True, help='Enables job monitoring.')
@click.argument('jobid', type=click.INT)
@util.pass_context
def start(ctx, jobid, **kwargs):
    jobapi = JobAPI(ecx_session=ctx.ecx_session)
    job = jobapi.start(jobid)
    if kwargs['mon']:
        monitor(jobapi, job, kwargs['i'])
    else:
        util.print_response(job)
