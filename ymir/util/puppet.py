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
        api.run("sudo -E puppet apply {parser} {debug} --modulepath={pdir}/modules {fname}".format(
            parser=('--parser ' + parser) if parser else '',
            debug='--debug' if debug else '',
            pdir=puppet_dir or os.path.dirname(_fname),
            fname=_fname))


def validate_metadata_file(metadata_f):
    """ returns a list of errors encountered while validating
        a puppet metadata.json file
    """
    errors, warnings, messages = [], [], []
    if not os.path.exists(metadata_f):
        errors.append('{0} does not exist!'.format(metadata_f))
    else:
        if util.has_gem('metadata-json-lint'):
            cmd_t = 'metadata-json-lint {0}'
            with api.quiet():
                x = api.local(cmd_t.format(metadata_f), capture=True)
            error = x.return_code != 0
            if error:
                errors.append('could not validate {0}'.format(metadata_f))
                errors.append(x.stderr.strip())
        else:
            errors.append(
                'cannot validate.  '
                'run "gem install metadata-json-lint" first')
    return errors, warnings, messages
