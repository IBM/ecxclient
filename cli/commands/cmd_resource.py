
import click
from tabulate import tabulate

import util
from sdk.client import EcxAPI

@click.group()
@click.option('--type', help='Resource type.')
@click.option('--endpoint', help='Top level end point, not including "api". E.g. "endeavour/policy"')
@util.pass_context
def cli(ctx, type, endpoint, **kwargs):
    """generic resource.
    """

    ctx.restype = type
    ctx.endpoint = endpoint

@cli.command()
@click.option('--fields', help='Fields to print as comma separated values.')
@click.option('--listfield', help='Name of the field containing list of resources.')
@util.pass_context
def list(ctx, **kwargs):
    resp = ctx.ecx_session.get(restype=ctx.restype, endpoint=ctx.endpoint)

    list_field = kwargs.get('listfield') or (ctx.restype + 's')

    if ctx.json or list_field not in resp:
        util.print_response(resp)
        return

    resources = resp[list_field]
    if kwargs['fields']:
        fields = [x.strip() for x in kwargs['fields'].split(',')]
    else:
        fields = ["name", "id"]

    table_data = []
    for res in resources:
        row = []
        for field in fields:
            row.append(res.get(field, None))

        table_data.append(row)

    if not table_data:
        return

    print
    click.echo_via_pager(tabulate(table_data, headers=fields))
    print

@cli.command()
@click.argument('id', type=click.INT)
@util.pass_context
def info(ctx, id, **kwargs):
    resp = ctx.ecx_session.get(restype=ctx.restype, resid=id, endpoint=ctx.endpoint)
    util.print_response(resp)

