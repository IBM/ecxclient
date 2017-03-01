
import click
from tabulate import tabulate

import util
from sdk.client import AppserverAPI

@click.group()
@util.pass_context
def cli(ctx, **kwargs):
    """Appserver resource.
    """

    pass

@cli.command()
@util.pass_context
def list(ctx, **kwargs):
    appservers = AppserverAPI(ecx_session=ctx.ecx_session).list()
    if ctx.json:
        util.print_response(appservers)
        return

    table_data = [(x['name'], x['hostAddress'], x['id'], x['type'], x['vsphereId']) for x in appservers]
    if not table_data:
        return

    print
    click.echo_via_pager(tabulate(table_data, headers=["Name", "Host Address", "ID", "Type", "VsphereID"]))
    print

@cli.command()
@click.argument('id', type=click.INT)
@util.pass_context
def info(ctx, id, **kwargs):
    resp = AppserverAPI(ecx_session=ctx.ecx_session).get(id)
    util.print_response(resp)

