""" ymir.commands
"""

import os

import boto
import addict
import voluptuous, demjson

from fabric.colors import red, green
from fabric.contrib.console import confirm

from ymir.base import report
from ymir.util import copytree
from ymir import schema as yschema
from ymir.service import AbstractService
from ymir.beanstalk import ElasticBeanstalkService
from ymir.schema import SGFileSchema, _choose_schema
from ymir.security_groups import sg_sync

OK = green('  ok')
YMIR_SRC = os.path.dirname(__file__)

import logging
logger = logging.getLogger(__name__)


def ymir_sg(args):
    def unpack_rule(r):
        return addict.Dict(
            ip_protocol=r[0],
            from_port=r[1],
            to_port=r[2],
            cidr_ip=r[3])
    def supports_ssh(_rules):
        """ FIXME: dumb heuristic """
        for _rule in _rules:
            _rule = unpack_rule(_rule)
            if _rule.to_port==22:
                return True
        return False

    force = args.force
    fname = os.path.abspath(args.sg_json)
    if not os.path.exists(fname):
        err = 'security group json @ "{0}" does not exist'.format(fname)
        raise SystemExit(err)
    with open(fname) as fhandle:
        json = demjson.decode(fhandle.read())
    logger.debug("loaded json from {0}".format(fname))
    logger.debug(json)
    SGFileSchema(json)
    logger.debug("validated json from {0}".format(fname))

    # one last sanity check
    rules = [entry['rules'] for entry in json]
    if not force and not \
       any([supports_ssh(x) for x in rules]):
        raise SystemExit("No security group mentions ssh!  "
                         "Unless you pass --force "
                         "ymir assumes this is an error")
    for entry in json:
        name = entry['name']
        descr = entry['description']
        rules = entry['rules']
        vpc = entry.get('vpc', None)
        sg_sync(name=name, description=descr, rules=rules,
                #vpc=vpc
                )

def _load_json(fname):
    """ loads json and allows for
        templating / value reflection
    """
    with open(fname) as fhandle:
        tmp = demjson.decode(fhandle.read())
        return _reflect(service_json=tmp)

def _validate_file(fname):
    """ simple schema validation, this
        returns error message or None """
    tmp = _load_json(fname)
    schema = _choose_schema(tmp)
    is_eb = schema.schema_name == 'eb_schema'
    #print 'Chose schema:\n ',schema.schema_name
    try:
        schema(tmp)
    except voluptuous.Invalid, e:
        msg = "error validating {0}\n\t{1}"
        msg = msg.format(os.path.abspath(fname), e)
        return msg
    SERVICE_ROOT = os.path.dirname(fname)
    SERVICE_ROOT = os.path.abspath(SERVICE_ROOT)
    tmp.update(dict(SERVICE_ROOT=SERVICE_ROOT))
    if is_eb:
        return []
    files = tmp['setup_list'] + tmp['provision_list']
    for _file in files:
        if not os.path.exists(os.path.join(SERVICE_ROOT, _file)):
            err= ('Files mentioned in service json '
                  'must exist relative to {0}, but {1}'
                  ' was not found').format(
                SERVICE_ROOT, _file)
            return [err]
    return []

def _ymir_load(args, interactive=True, simple=False):
    """ load service obj from service json """
    SERVICE_ROOT = os.path.dirname(args.service_json)
    SERVICE_ROOT = os.path.abspath(SERVICE_ROOT)
    service_json = _load_json(args.service_json)
    if interactive:
        lint = demjson.jsonlint()
        print red("Service root: "), '\n  ', SERVICE_ROOT
        print red("Service JSON: ")
        rc = lint.main(['-S', '--format', args.service_json])
    dct = dict([
        [x.upper(), y] for x, y in service_json.items()])
    dct.update(SERVICE_ROOT=SERVICE_ROOT)
    classname = str(service_json.name).lower()
    chosen_schema = _choose_schema(service_json)
    if chosen_schema == yschema.eb_schema:
        from ymir.beanstalk import ElasticBeanstalkService
        BaseService = ElasticBeanstalkService
    else:
        BaseService = AbstractService
    #print 'Chose service-class:\n ',BaseService.__name__
    ServiceFromJSON = type(classname, (BaseService,), dct)
    obj = ServiceFromJSON()
    obj._schema = chosen_schema
    obj = _reflect(service_obj=obj, simple=simple)
    if interactive:
        print red("Service definition loaded from JSON")
    return obj

def ymir_shell(args):
    """ """
    wd_json = os.path.join(os.getcwd(),'service.json')
    if os.path.exists(wd_json):
        print 'found service.json import working directory, loading service..'
        fake_args = addict.Dict(service_json=wd_json)
        user_ns = dict(
            service=ymir_load(fake_args))
    from smashlib import embed; embed(user_ns=user_ns)

def ymir_load(args, interactive=True):
    """ """
    report('profile', os.environ.get('AWS_PROFILE','default'))
    ymir_validate(args, simple=True, interactive=False)
    return _ymir_load(args, interactive=interactive)

def _reflect(service_json=None, service_obj=None, simple=True):
    """ """
    assert service_json or service_obj
    if service_obj:
        tdata = service_obj._template_data(simple=simple)
        for k, v in tdata['service_defaults'].items():
            tmp = service_obj.SERVICE_DEFAULTS[k]
            if isinstance(tmp, basestring):
                service_obj.SERVICE_DEFAULTS[k] = tmp.format(
                    tdata)
        return service_obj
    if service_json:
        for k,v in service_json.items():
            if isinstance(v, basestring) and '{' in v:
                service_json[k] = v.format(**service_json)
        return addict.Dict(service_json)

def ymir_init(args):
    """ responsible for executing the 'ymir init' command. """
    init_dir = os.path.abspath(args.init_dir)
    if os.path.exists(init_dir) and not args.force:
        err = ('this command is used to initialize a '
               'ymir project, the directory should'
               ' not already exist.')
        raise SystemExit(err)
    using_dot = init_dir == os.getcwd()
    if os.path.exists(init_dir) and args.force:
        folder = init_dir
        for the_file in os.listdir(folder):
            file_path = os.path.join(folder, the_file)
            try:
                if os.path.isfile(file_path):
                    os.unlink(file_path)
            except Exception, e:
                print e
    skeleton_dir = os.path.join(YMIR_SRC, 'skeleton')
    if not os.path.exists(skeleton_dir):
        err = ('cannot find ymir skeleton project.  '
               'your ymir installation might be broken :(')
        raise SystemExit(err)
    print red('creating directory: ') + init_dir
    print red('copying ymir skeleton: '), skeleton_dir
    copytree(skeleton_dir, init_dir)

def ymir_validate(args, simple=True, interactive=True):
    """ """
    def print_errs(msg, _errs, die=False):
        assert isinstance(_errs, list), str(_errs)
        if interactive:
            print msg
        if not _errs:
            print OK
            return
        for e in _errs:
            print red('  ERROR: ')+str(e)
        if die:
            raise SystemExit(str(_errs))

    errs = _validate_file(args.service_json)
    if interactive:
        print_errs(
            'Validating the overall file schema..',
            errs, die=True)

    if simple:
        return True

    # simple validation has succeded, begin second phase.
    # the schema can be loaded, so build a service object.
    # the service object can then begin to validate itself

    print 'Instantiating service to scrutinize it..'
    service = _ymir_load(args, interactive=False, simple=True)
    print OK
    errs = service._validate_health_checks()
    print_errs(
        'Validating content in `health_checks` field..',
        errs)
    if not isinstance(service, ElasticBeanstalkService):
        errors = service._validate_keypairs()
        print_errs('Validating AWS keypair at field `key_name`..',
                   errors)
        errs = service._validate_puppet_librarian()
        print_errs('Validating puppet-librarian\'s metadata.json', errs)
        errs = service._validate_named_sgs()
        print_errs(
            'Validating simple AWS security groups in field `security_groups`..',
            errs)
        errs = service._validate_puppet()
        print_errs(
            'Validating puppet code..',
            errs)

def ymir_keypair(args):
    """ """
    name = args.keypair_name
    ec2 = boto.connect_ec2()
    if not args.force:
        q = ('\nCreate new AWSkeypair "{0}" (the '
             'results will be saved to "{1}.pem" '
             'in the working directory)?\n\n')
        try:
            result = confirm(q.format(name, name))
        except KeyboardInterrupt:
            return
        if not result:
            return
        #boto.ec2.keypair.KeyPair
    key = ec2.create_key_pair(name)
    key.save(os.getcwd())

def ymir_eip(args):
    ec2 = boto.connect_ec2()
    if not args.force:
        q = ('\nCreate new elastic ip (the '
             'ID for the result will be shown on stdout)?\n\n')
        try:
            result = confirm(q.format())
        except KeyboardInterrupt:
            return
        if not result:
            return
    addr = ec2.allocate_address()
    print addr.allocation_id

def ymir_freeze(args):
    msg = 'not implemented yet'
    print msg
    raise SystemExit(msg)
