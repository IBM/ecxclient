
import json

import click

def remove_links(obj):
    if type(obj) is dict:
        if obj.has_key("links"):
            del obj["links"]

        for k, v in obj.iteritems():
            remove_links(v)

        return

    if type(obj) is list:
        for item in obj:
            remove_links(item)

        return

    return

def raise_response_error(r, *args, **kwargs):
    r.raise_for_status()
    obj = json.loads(r.content)
    remove_links(obj)
    r.resp_without_links = obj

class EcxCmd(object):
    def __init__(self, *args, **kwargs):
        self.ecx_session = kwargs.pop('ecx_session')
        super(EcxCmd, self).__init__()

    def invoke_get(self, url):
        r = self.ecx_session.conn.get(url)
        click.echo_via_pager(json.dumps(r.resp_without_links, indent=4))
