# -*- coding: utf-8 -*-
""" ymir.util.puppet
"""
import os
from fabric import api
from peak.util.imports import lazyModule
util = lazyModule('ymir.util')

DEFAULT_FACTS = [
    'domain', 'operatingsystem', 'memoryfree'
]


def run_puppet(_fname, parser=None, debug=False, puppet_dir=None, facts={}):
    """ NB: must be run within a fabric ssh context """
    _facts = {}
    for fact_name, val in facts.items():
        if isinstance(val, dict):
            continue
        if not fact_name.startswith('FACTER_'):
            _facts['FACTER_' + fact_name] = val
        else:
            _facts[fact_name] = val
    with api.shell_env(**_facts):
        # sudo -E preserves the invoking enviroment,
        # thus we are able to pass through the facts
        api.run("sudo -E `which puppet` apply {parser} {debug} --modulepath={pdir}/modules {fname}".format(
            parser='', #('--parser ' + parser) if parser else '',
            debug='--debug' if debug else '',
            pdir=puppet_dir or os.path.dirname(_fname),
            fname=_fname))
