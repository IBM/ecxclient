import sys
import click

from util.util import EcxCmd

class UserCmd(EcxCmd):
    def __init__(self, *args, **kwargs):
        super(UserCmd, self).__init__(*args, **kwargs)

    def list(self, **kwargs):
        self.invoke_get("%s/api/security/user" % self.ecx_session.url)

@click.command()
@click.argument('op')
@click.pass_obj
def cli(ctx, **kwargs):
    """User resource.
    """

    getattr(UserCmd(ecx_session=ctx.ecx_session), kwargs['op'])(**kwargs)

