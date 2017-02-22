import sys
import click

from src.util import EcxCmd
from src.client import pass_context

class JobCmd(EcxCmd):
    def __init__(self, *args, **kwargs):
        super(JobCmd, self).__init__(*args, **kwargs)

    def list(self, **kwargs):
        self.invoke_get("%s/api/endeavour/job" % self.ecx_session.url)

    def get(self, jobid, **kwargs):
        self.invoke_get("%s/api/endeavour/job/%d" % (self.ecx_session.url, jobid))

@click.group()
@pass_context
def cli(ctx, **kwargs):
    """Job resource.
    """

    pass

@cli.command()
@pass_context
def list(ctx, **kwargs):
    print "list command called"
    JobCmd(ecx_session=ctx.ecx_session).list(**kwargs)

@cli.command()
@click.argument('jobid', type=click.INT)
@pass_context
def info(ctx, jobid, **kwargs):
    JobCmd(ecx_session=ctx.ecx_session).get(jobid, **kwargs)

