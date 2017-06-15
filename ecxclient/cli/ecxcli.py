#!/usr/bin/env python
#-*- mode: Python;-*-

import ConfigParser
import json
import logging
import os
import sys
import tempfile
import traceback

import click
from requests.exceptions import HTTPError

from ecxclient.sdk import client
import util

cmd_folder = os.path.abspath(os.path.join(os.path.dirname(__file__), 'commands'))

class MyCLI(click.MultiCommand):
    def list_commands(self, ctx):
        rv = []
        for filename in os.listdir(cmd_folder):
            if filename.endswith('.py') and filename.startswith('cmd_'):
                rv.append(filename[4:-3])
        rv.sort()
        return rv

    def get_command(self, ctx, name):
        try:
            if sys.version_info[0] == 2:
                name = name.encode('ascii', 'replace')

            mod = __import__('ecxclient.cli.commands.cmd_' + name, None, None, ['cli'])
        except ImportError:
            logging.error(traceback.format_exc())
            return

        return mod.cli


@click.command(cls=MyCLI)
@click.option('--url', envvar='ECX_URL', default='http://localhost:8082', metavar='URL', help='ECX url.')
@click.option('--user', envvar='ECX_USER', default='admin', metavar='USERNAME', help='ECX user.')
@click.option('--passwd', envvar='ECX_PASSWD', default=None, metavar='PASSWORD', help='ECX password.')
@click.option('--json', is_flag=True, help='Show raw json.')
@click.option('--links', is_flag=True, help='Include links in output. Implies --json option.')
@click.version_option('1.0')
@util.pass_context
def cli(ctx, url, user, passwd, json, links):
    """ecx is a command line tool with which ECX operations
    can be carried out.
    """

    ctx.ecx_session = client.EcxSession(url, user, passwd)
    ctx.json = json
    ctx.links = links
    if ctx.links:
        ctx.json = True

# cli = MyCLI(help='Script to perform ECX operations. ')

def init_logging():
    fd, logfile = tempfile.mkstemp(suffix='.txt', prefix='ecxclient')
    os.close(fd)
    logging.basicConfig(filename=logfile, level=logging.DEBUG, format='%(asctime)-15s: %(levelname)s: %(message)s')

def process_http_error(e):
    if not isinstance(e, HTTPError):
        return

    if not e.response.content:
        return

    logging.error(e.response.content)

    try:
        d = json.loads(e.response.content)
        click.secho('%s (%s)' % (d.get('id', 'Unknown'), d.get('description', 'Unknown')), fg='red')
    except Exception:
        pass

def main():
    init_logging()

    try:
        cli()
    except Exception as e:
        logging.error(traceback.format_exc())

        exctype, value = sys.exc_info()[:2]
        click.secho(traceback.format_exception_only(exctype, value)[0], fg='red')

        process_http_error(e)
