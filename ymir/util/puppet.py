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


def run_puppet(_fname, parser=None, debug=False,
               hiera_config=None, puppet_dir=None, facts={}):
    """ NB: must be run within a fabric ssh context """
    _facts = {}
    for fact_name, val in facts.items():
        if isinstance(val, dict):
            continue
        if not fact_name.startswith('FACTER_'):
            _facts['FACTER_' + fact_name] = val
        else:
            _facts[fact_name] = val
    api.run("sudo -E echo `which puppet`")
    with api.shell_env(**_facts):
        # sudo -E preserves the invoking enviroment,
        # thus we are able to pass through the facts
        puppet_cmd = ("sudo -E `which puppet` "
                      "apply {parser} {debug} "
                      "--hiera_config {hiera_config} "
                      "--modulepath={pdir}/modules {fname}")
        pdir = puppet_dir or os.path.dirname(_fname)
        hconfig = hiera_config or '{pdir}/hiera.yaml'.format(pdir=pdir)
        api.run(
            puppet_cmd.format(
                parser='',  # ('--parser ' + parser) if parser else '',
                debug='--debug' if debug else '',
                pdir=pdir,
                fname=_fname,
                hiera_config=hconfig))
