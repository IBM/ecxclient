
import click
from tabulate import tabulate

import util
from sdk.client import UserIdentityAPI

@click.group()
@util.pass_context
def cli(ctx, **kwargs):
    """Useridentity resource.
    """

    pass

@cli.command()
@util.pass_context
def list(ctx, **kwargs):
    identities = UserIdentityAPI(ecx_session=ctx.ecx_session).list()
    if ctx.json:
        util.print_response(identities)
        return

    table_data = [(x['name'], x['id'], x['type']) for x in identities]
    if not table_data:
        return

    print
    click.echo_via_pager(tabulate(table_data, headers=["Name","ID", "Type"]))
    print

@cli.command()
@click.argument('id', type=click.INT)
@util.pass_context
def info(ctx, id, **kwargs):
    resp = UserIdentityAPI(ecx_session=ctx.ecx_session).get(id)
    util.print_response(resp)

