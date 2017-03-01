
import click
from tabulate import tabulate

import util
from sdk.client import VsphereAPI

@click.group()
@util.pass_context
def cli(ctx, **kwargs):
    """Vsphere resource.
    """

    pass

@cli.command()
@util.pass_context
def list(ctx, **kwargs):
    resources = VsphereAPI(ecx_session=ctx.ecx_session).list()
    if ctx.json:
        util.print_response(resources)
        return

    table_data = [(x['name'], x['id'], x['hostAddress']) for x in resources]
    if not table_data:
        return

    print
    click.echo_via_pager(tabulate(table_data, headers=["Name","ID", "Host Address"]))
    print

@cli.command()
@click.argument('id', type=click.INT)
@util.pass_context
def info(ctx, id, **kwargs):
    resp = VsphereAPI(ecx_session=ctx.ecx_session).get(id)
    util.print_response(resp)

