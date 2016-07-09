# -*- coding: utf-8 -*-
from fabric import api
import os
import shutil
from fabric import colors

PORT = 8000
PROJECT_NAME = 'ymir'
DOC_ROOT = os.path.dirname(__file__)
SRC_ROOT = os.path.dirname(DOC_ROOT)
GEN_PATH = os.path.join(DOC_ROOT, 'ymir')
DEPLOY_PATH = "~/code/ghio/{0}".format(PROJECT_NAME)
DEPLOY_PATH = os.path.expanduser(DEPLOY_PATH)


def check_links_prod(url='/ymir'):
    return check_links(
        url=url,
        base_domain='mattvonrocketstein.github.io')


def check_links(url='', base_domain="localhost"):
    """ check the links wget.  """
    def parse_lines(lines):
        print colors.red('broken links:')
        links = [x.replace(url, '')[1:] for x in lines]
        for link in links:
            print colors.red(link)
            with api.quiet():  # (hide="warn_only=True):
                z = api.local(
                    "find {0} -name *.md|xargs grep '{1}'".format(DOC_ROOT, link), capture=True)
                if z.succeeded:
                    print str(z)
                else:
                    print "could not find any mention"
            print
    # fab run should already be started
    logfile = "link_check.log"
    base_url = 'http://{0}:'.format(base_domain)
    port = str((PORT if base_domain == 'localhost' else 80))
    url = base_url + port + url
    wipe_logfile = lambda: api.local('rm -f "{0}"'.format(logfile))
    wipe_logfile()
    with api.settings(warn_only=True):
        api.local(
            ("wget -e robots=off --spider -r -nd "
             "-nv -o {1}  {0}").format(url, logfile))
    with open(logfile, 'r') as fhandle:
        lines = [x.strip() for x in fhandle.readlines()]
    start = end = None
    for line in lines:
        if line.startswith('Found') and line.endswith(" broken links."):
            start = lines.index(line)
        if line.startswith('FINISHED') and line.endswith('--'):
            end = lines.index(line)
    if start is not None and end is not None:
        lines = lines[start + 2:end - 1]
        parse_lines(lines)
    else:
        print "no broken links found"


def add_coverage(_dir=GEN_PATH):
    print colors.red("adding coverage data")
    cdir = os.path.join(SRC_ROOT, 'htmlcov')
    if os.path.exists(cdir):
        api.local("cp -r {0} {1}".format(cdir, _dir))


def clean():
    """ Remove generated files """
    if os.path.isdir(GEN_PATH):
        shutil.rmtree(GEN_PATH)
        os.makedirs(GEN_PATH)


def build(conf='pelicanconf.py'):
    """Build local version of site"""
    with api.lcd(os.path.dirname(__file__)):
        api.local('pelican -s {0} -o {1}'.format(conf, GEN_PATH))


def rebuild():
    """`clean` then `build`"""
    clean()
    build()
    add_coverage(GEN_PATH)


def regenerate():
    """Automatically regenerate site upon file modification"""
    with api.lcd(os.path.dirname(__file__)):
        api.local('pelican -r -s pelicanconf.py -o {0}'.format(GEN_PATH))


def serve():
    """Serve site at http://localhost:8000/"""
    with api.lcd(os.path.dirname(GEN_PATH)):
        api.local("twistd -n web -p {0} --path .".format(PORT))


def push():
    if os.path.exists(DEPLOY_PATH):
        with api.lcd(DEPLOY_PATH):
            api.local("find . -type f|xargs git rm -f")
    api.local("mkdir -p {0}".format(DEPLOY_PATH))
    api.local(
        "cp -rfv {0} {1}".format(
            os.path.join(GEN_PATH, '*'),
            DEPLOY_PATH))
    with api.lcd(DEPLOY_PATH):
        api.local("find . -type f|xargs git add")
        api.local("git commit . -m'publishing {0}'".format(PROJECT_NAME))
        api.local("git push")


def build_prod():
    clean()
    build("pelican_publish.py")
    add_coverage(GEN_PATH)


def run():
    from littleworkers import Pool
    commands = [
        'fab regenerate',
        'fab serve'
    ]
    lil = Pool(workers=2)
    lil.run(commands)
