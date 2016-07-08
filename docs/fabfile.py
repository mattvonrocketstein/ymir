# -*- coding: utf-8 -*-
from fabric import api
import os
import shutil
import sys
import SocketServer
from pelican.server import ComplexHTTPRequestHandler

PORT = 8000
PROJECT_NAME = 'ymir'
ROOT = os.path.dirname(__file__)
GEN_PATH = os.path.join(ROOT, 'output')
DEPLOY_PATH = "~/code/ghio/{0}".format(PROJECT_NAME)


def check_links():
    """ check the links wget.  """
    # fab run should already be started
    logfile = "link_check.log"
    base_url = 'http://localhost:'
    url = base_url + str(PORT)
    # wget_hint = "broken link!"
    wipe_logfile = lambda: api.local('rm -f "{0}"'.format(logfile))
    wipe_logfile()
    with api.settings(warn_only=True):
        api.local(
            ("wget -e robots=off --spider -r -nd "
             "-nv -o {1}  {0}").format(url, logfile))
    try:
        with open(logfile, 'r') as fhandle:
            lines = [x.strip() for x in fhandle.readlines()]
        for line in lines:
            if line.startswith('Found') and line.endswith(" broken links."):
                start = lines.index(line)
            if line.startswith('FINISHED') and line.endswith('--'):
                end = lines.index(line)
        lines = lines[start + 2:end - 1]
        print 'broken links:'
        links = [x.replace(url, '')[1:] for x in lines]
        from fabric.colors import red
        for link in links:
            print red(link)
            with api.settings(warn_only=True):
                z = api.local(
                    "find {0} -name *.md|xargs grep '{1}'".format(ROOT, link), capture=True)
                print str(z)
    finally:
        pass  # wipe_logfile()


def clean():
    """ Remove generated files """
    if os.path.isdir(GEN_PATH):
        shutil.rmtree(GEN_PATH)
        os.makedirs(GEN_PATH)


def build():
    """Build local version of site"""
    with api.lcd(os.path.dirname(__file__)):
        api.local('pelican -s pelicanconf.py')


def rebuild():
    """`clean` then `build`"""
    clean()
    build()


def regenerate():
    """Automatically regenerate site upon file modification"""
    with api.lcd(os.path.dirname(__file__)):
        api.local('pelican -r -s pelicanconf.py')


def serve():
    """Serve site at http://localhost:8000/"""
    os.chdir(GEN_PATH)

    class AddressReuseTCPServer(SocketServer.TCPServer):
        allow_reuse_address = True
    server = AddressReuseTCPServer(('', PORT), ComplexHTTPRequestHandler)
    sys.stderr.write('Serving on port {0} ...\n'.format(PORT))
    server.serve_forever()


def publish():
    """ publish everything to ghio """
    if os.path.exists(DEPLOY_PATH):
        with api.lcd(os.path.expanduser(DEPLOY_PATH)):
            api.local("find . -type f|xargs git rm")
    api.local("mkdir -p {0}".format(DEPLOY_PATH))
    api.local(
        "cp -rfv {0} {1}".format(
            os.path.join(GEN_PATH, '*'),
            DEPLOY_PATH))
    with api.lcd(os.path.expanduser(DEPLOY_PATH)):
        api.local("find . -type f|xargs git add")
        api.local("git commit . -m'publishing {0}'".format(PROJECT_NAME))
        api.local("git push")


def run():
    """ run simultaneously `regenerate` and `serve` """
    from littleworkers import Pool
    commands = [
        'fab regenerate',
        'fab serve'
    ]
    lil = Pool(workers=2)
    lil.run(commands)
