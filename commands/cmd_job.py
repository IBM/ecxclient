import sys
import click

from util.util import EcxCmd

class JobCmd(EcxCmd):
    def __init__(self, *args, **kwargs):
        super(JobCmd, self).__init__(*args, **kwargs)

    def list(self, **kwargs):
        self.invoke_get("%s/api/endeavour/job" % self.ecx_session.url)

@click.command()
@click.argument('op')
@click.pass_obj
def cli(ctx, **kwargs):
    """Job resource.
    """

    getattr(JobCmd(ecx_session=ctx.ecx_session), kwargs['op'])(**kwargs)

