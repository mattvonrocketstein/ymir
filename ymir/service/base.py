# -*- coding: utf-8 -*-
""" ymir.service.base
"""
import os
import time
import pprint
import logging

import demjson
import fabric
from fabric import api
from fabric.colors import blue, yellow
from peak.util.imports import lazyModule

from ymir import util
from ymir import mixins
from ymir import data as ydata
from ymir.base import Reporter
from ymir.util import puppet
from ymir.caching import cached

yapi = lazyModule('ymir.api')


# capture warnings because Fabric and
# it's dependencies can be pretty noisy
logger = logging.getLogger(__name__)
logging.captureWarnings(True)

# disable stricthostkey checking everywhere in fabric
api.env.disable_known_hosts = True


class AbstractService(Reporter,
                      mixins.PuppetMixin,
                      mixins.AnsibleMixin,
                      mixins.PackageMixin,
                      mixins.FabricMixin):
    _schema = None
    _ymir_service_root = None
    _status_computed = False

    def __str__(self):  # pragma:nocover
        """ """
        try:
            return "<Service:{0}>".format(self._report_name())
        except:
            return super(AbstractService, self).__str__()

    __repr__ = __str__

    @property
    def _security_group_file(self):
        """ """
        tmp = os.path.join(self._ymir_service_root, 'security_groups.json')
        if os.path.exists(tmp):
            return tmp
    _sg_file = _security_group_file

    @property
    def _security_group_json(self):
        """ returns JSON for $service_root/security_groups.json
            if the file exists and is decodable, otherwise return
            None.  WARNING: this doesn't guarantee anything about the
            JSON schema
        """
        fname = self._security_group_file
        if fname is not None:
            with open(fname) as fhandle:
                try:
                    json = demjson.decode(fhandle.read())
                except demjson.JSONDecodeError:
                    self.report("error decoding: {0}".format(fname))
                else:
                    return json
    _sg_json = _security_group_json

    @util.declare_operation
    def system_service(self, command):
        """ run `sudo service <cmd>` on the remote host"""
        with self.ssh_ctx():
            api.run('sudo service {0}'.format(command))

    @util.declare_operation
    def supervisorctl(self, command):
        """ run `sudo supervisorctl <cmd>` on the remote host """
        with self.ssh_ctx():
            api.run('sudo supervisorctl {0}'.format(command))
    supervisor = supervisorctl

    @util.declare_operation
    def logs(self, *args):
        """ lists the known log files for this service"""
        if not args:
            self.list_log_files()

    @util.declare_operation
    def list_log_files(self):
        """ """
        with self.ssh_ctx():
            for file_or_dir in self.template_data()['logs']:
                if util.remote_path_exists(file_or_dir):
                    result = api.sudo(
                        'ls -l {0}'.format(file_or_dir), capture=True).strip()
                    self.report(" + {0}".format(str(result)))
                else:
                    self.report(" - {0}".format(file_or_dir))

    @property
    def _fabric_commands(self):
        """ """
        out = []
        for x in dir(self):
            if util.is_operation(self, x):
                out.append(x)
        return out

    @property
    @cached('service._ssh_config_string', 60 * 20)
    def _ssh_config_string(self):
        """ return a string suitable for use as ssh-config file """
        out = [
            "Host default",
            "  HostName {0}".format(self._host),
            "  User {0}".format(self._username),
            "  Port {0}".format(self._port),
            "  UserKnownHostsFile /dev/null",
            "  StrictHostKeyChecking no",
            "  PasswordAuthentication no",
            "  IdentityFile {0}".format(self._pem),
            "  IdentityOnly yes",
            "  LogLevel FATAL",
        ]
        return '\n'.join(out)

    def fabric_install(self):
        """ publish certain service-methods into the fabfile
            namespace. this method is responsible for
            dynamically creating fabric commands, and should
            only be called from inside fabfiles
        """
        import fabfile
        for x in self._fabric_commands:
            try:
                tmp = getattr(fabfile, x)
            except AttributeError:
                setattr(fabfile, x, api.task(getattr(self, x)))
            else:
                err = ('Service definition "{0}" attempted'
                       ' to publish method "{1}" as a fabric '
                       'command, but "{1}" is already present '
                       'in globals with value "{2}"').format(
                    self.__class__.__name__, x, str(tmp))
                self.report("ERROR:")
                raise SystemExit(err)

    def __init__(self, service_json_file=None, ):
        """ """
        self._ymir_service_root = os.path.dirname(service_json_file)
        self._ymir_service_json_file = service_json_file

    def report(self, msg, *args, **kargs):
        """ 'print' shortcut that includes some color and formatting """
        label = self._report_name()
        return util.report(label, msg, *args, **kargs)

    @util.declare_operation
    def setup(self):
        """ setup service (invoke after 'create', before 'provision')
        """
        self.report('setting up')
        # setup ansible first, because it updates local files and is
        # unusual in that it doesn't require a working  remote service
        self.setup_ansible()
        return self._setup(failures=0)

    def _setup(self, failures=0):
        """ """
        def retry(exc=None):
            """ """
            wait_period = 8
            if failures > 5:
                self.report("CRITICAL: encountered 5+ network failures")
                self.report("  Is the security group setup correctly?")
                self.report("  Is the internet turned on??")
                self.report("  Is the instance running?")
                raise SystemExit(1)
            if exc is not None:
                self.report(str(exc))
                self.report("network error? sleeping and retrying")
                time.sleep(wait_period)
            return self._setup(failures=failures + 1)
        cm_data = self._status()
        if cm_data['status'] == 'running':
            try:
                self.setup_ip()
            except fabric.exceptions.NetworkError:
                return retry()
        else:
            msg = 'no instance is running for this service yet!'
            self.report(ydata.FAIL + msg)
            return retry()

    @property
    @cached('service._instance', 60 * 20)
    def _instance(self):
        """ return the aws instance """
        return self._get_instance(strict=True)

    def ssh_ctx(self):
        """ """
        return util.ssh_ctx(
            ':'.join([self._host, self._port]),
            user=self._username,
            pem=self._pem,)

    def _restart_supervisor(self):
        self.report('  restarting everything')
        retries = 3
        cmd = "sudo /etc/init.d/supervisor restart"
        restart = lambda: api.run(cmd).return_code
        with api.settings(warn_only=True):
            result = restart()
            count = 0
            while result != 0 and count < retries:
                msg = ('failed to restart supervisor.'
                       '  trying again [{0}]').format(count)
                print msg
                result = restart()
                count += 1

    @util.declare_operation
    @util.require_running_instance
    def provision(self, instruction=None, **kargs):
        """ provision this service """
        self.report('preparing to provision: {0}'.format(
            yellow(instruction or '(everything)')))
        self._clean_puppet_tmp_dir()

        try:
            instruction_index = int(instruction)
        except:
            return self._provision_helper(instruction=instruction, **kargs)
        else:
            return self._provision_from_index(instruction_index, **kargs)

    def _provision_from_index(self, instruction_index, **kargs):
        """ given an integer, run the instruction at
            that index in the provision list
        """
        try:
            instruction = self.template_data()['provision_list'][
                instruction_index]
        except IndexError:
            msg = "bad instruction_index passed, not found in provision_list"
            raise SystemExit(msg)
        else:
            return self._provision_helper(instruction=instruction, **kargs)

    def _provision_helper(self, instruction=None, force=False, **kargs):
        """ `force` must be True to provision with arguments not
            mentioned in service's provision_list """
        provision_list = self.template_data()['provision_list']
        if instruction is not None:
            if not force and instruction not in provision_list:
                err = ('ERROR: Provisioning a single file requires that '
                       'the file should be mentioned in service.json, '
                       'but "{0}" was not found.').format(util.unexpand(instruction))
                raise SystemExit(err)
            provision_list = [instruction]
        with self.ssh_ctx():
            with api.lcd(self._ymir_service_root):
                msg = ('\n  ' + pprint.pformat(provision_list, indent=2)) if \
                    provision_list else "(empty)"
                self.report("Provision list for this service: " + msg)
                # NB: if clean==True, in the call below, the puppet deps
                # which were installed in the `setup` phase would be
                # destroyed.  not what is wanted for simple provisioning!
                self.copy_puppet(clean=False)
                for provision_item in provision_list:
                    protocol, instruction = util.split_instruction(
                        provision_item)
                    self.report('provision_list[{0}]:'.format(
                        provision_list.index(provision_item)))
                    self._run_provisioner(
                        protocol, instruction, **kargs)
        self.report(ydata.SUCCESS + "Finished with provision.")
        self.report("You might want to restart services now "
                    "using `fab service` or `fab supervisor`")

    def _run_provisioner(self, provisioner_name, provision_instruction, **kargs):
        self.report(' {0}'.format(
            blue(provisioner_name + "://") + provision_instruction))
        try:
            provision_fxn = getattr(
                self, '_provision_{0}'.format(provisioner_name))
        except AttributeError:
            self.report(
                "Fatal: no sucher provisioner `{0}`".format(provisioner_name))
            raise SystemExit()
        else:
            cmd = yapi.str_reflect(
                provision_instruction,
                ctx=self.template_data())
            if cmd != provision_instruction:
                self.report(yellow("≈") + "translated to: {0}".format(cmd))
            return provision_fxn(cmd, **kargs)

    def _provision_remote(self, cmd):
        """ handler for provision-list entries prefixed with `remote://` """
        return self.run(cmd)

    def _provision_local(self, cmd):
        """ handler for provision-list entries prefixed with `local://` """
        return api.local(cmd)

    @property
    def _debug_mode(self):
        """ use _service_json here, it's a simple bool and not templated  """
        if hasattr(self, '_debug_mode_cache'):
            return self._debug_mode_cache
        else:
            self._debug_mode_cache = self._service_json['ymir_debug']
            icon = ydata.SUCCESS if self._debug_mode_cache else ydata.FAIL
            self.report(icon + "ymir debug mode enabled?")
        return self._debug_mode_cache

    def setup_puppet(self):
        """ """
        # all NOOPs if puppet isn't supported
        self._clean_puppet_tmp_dir()
        self.copy_puppet(clean=True)
        self._setup_puppet_deps(force=True)

    def setup_ip(self):
        """ """
        with self.ssh_ctx():
            with api.lcd(self._ymir_service_root):
                self.setup_puppet()
                setup_list = self.template_data()['setup_list']
                for setup_item in setup_list:
                    self.report(' .. setup_list[{0}]: "{1}"'.format(
                        setup_list.index(setup_item),
                        setup_item
                    ))
                    puppet.run_puppet(
                        setup_item,
                        puppet_dir='puppet',
                        facts=self.facts,
                        debug=self._debug_mode,)
        self.report(ydata.SUCCESS + "Setup complete.  Now run `fab provision`")

    @property
    def facts(self):
        """ return a dictionary of facts, for use with
            either the puppet or ansible provisioners
        """
        json = self.template_data()
        service_defaults = json['service_defaults']
        # migrate a few other variables from the toplevel json,
        # this stuff might be used in filling out motds, etc
        service_defaults.update(
            # name=json['name'],
            # org_name=json['org_name'],
            # service_name=json['service_name'],
        )
        for fact in service_defaults:
            tmp = service_defaults[fact]
            if isinstance(tmp, basestring) and ('{' in tmp or '}' in tmp):
                self.report(
                    ydata.WARN + "facts containing mustaches is ignored: {0}".format(tmp))
        return service_defaults

    @util.declare_operation
    def sudo(self, *args, **kargs):
        with self.ssh_ctx():
            api.sudo(*args, **kargs)

    @util.declare_operation
    def run(self, command):
        """ run command on service host """
        with self.ssh_ctx():
            api.run(command)

    @property
    def _port(self):
        """ """
        return self._service_json['port']

    @property
    def _host(self):
        """ """
        return self._status().get('ip')

    def template_data(self):
        """ a last phase of reflection, for data that's potentially
            only available just-in-time.
        """
        tmp = self._service_json.copy()
        tmp.update(
            username=self._username,
            pem=self._pem,
            host=self._host,
            port=self._port,
        )
        # plist = [cmd.format(**tmp) for cmd in tmp['provision_list']]
        plist = [yapi.str_reflect(cmd, ctx=tmp)
                 for cmd in tmp['provision_list']]
        # slist = [cmd.format(**tmp) for cmd in tmp['setup_list']]
        slist = [yapi.str_reflect(cmd, ctx=tmp) for cmd in tmp['setup_list']]
        tmp['provision_list'] = plist
        tmp['setup_list'] = slist
        return tmp

    @util.declare_operation
    def show_facts(self):
        """ show facts (puppet key-values available to templates)"""
        self.report("facts available to puppet/ansible:")
        facts = sorted([[k, v] for k, v in self.facts.items()])
        for k, v in facts:
            print ' ', k, '=>', v
