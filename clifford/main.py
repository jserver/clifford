import json
import logging
import os
import sys
from collections import OrderedDict

import boto
from cliff.app import App
from cliff.commandmanager import CommandManager


DEFAULT_CONFIG_FILE = os.path.expanduser('~/.clifford/config.json')


class CliffordApp(App):

    log = logging.getLogger(__name__)

    def __init__(self):
        super(CliffordApp, self).__init__(
            description='clifford ec2 app',
            version='0.1',
            command_manager=CommandManager('clifford', convert_underscores=False),
            )
        self.ec2_conn = boto.connect_ec2()
        self.s3_conn = boto.connect_s3()

    def initialize_app(self, argv):
        self.log.debug('initialize_app')

    def prepare_to_run_command(self, cmd):
        self.log.debug('prepare_to_run_command %s', cmd.__class__.__name__)

    def clean_up(self, cmd, result, err):
        self.log.debug('clean_up %s', cmd.__class__.__name__)
        if err:
            self.log.debug('got an error: %s', err)


class OrderedConfig(OrderedDict):
    def set_config_file_location(self, config_file):
        self.config_file = config_file

    @property
    def aws_key_path(self):
        return self.get_path('AwsKeyPath')

    @property
    def pub_key_path(self):
        return self.get_path('PubKeyPath')

    @property
    def script_path(self):
        return self.get_path('ScriptPath')

    @property
    def images(self):
        if 'Images' not in self:
            self['Images'] = OrderedDict()
        return self['Images']

    @property
    def bundles(self):
        if 'Bundles' not in self:
            self['Bundles'] = OrderedDict()
        return self['Bundles']

    @property
    def python_bundles(self):
        if 'PythonBundles' not in self:
            self['PythonBundles'] = OrderedDict()
        return self['PythonBundles']

    @property
    def groups(self):
        if 'Groups' not in self:
            self['Groups'] = OrderedDict()
        return self['Groups']

    @property
    def builds(self):
        if 'Builds' not in self:
            self['Builds'] = OrderedDict()
        return self['Builds']

    @property
    def projects(self):
        if 'Projects' not in self:
            self['Projects'] = OrderedDict()
        return self['Projects']

    def get_path(self, key):
        if key not in config:
            raise RuntimeError('%s not found!' % key)
        value = config[key]
        value = os.path.expanduser(value)
        value = os.path.expandvars(value)
        return value

    def save(self):
        with open(self.config_file, 'wb') as fp:
            json.dump(self, fp, indent=2, separators=(',', ': '))


def input_valid_dir(name):
    while True:
        path = raw_input('Enter %s: ' % name)
        if not path:
            print 'This field is required!\n'
            continue
        value = os.path.expanduser(path)
        value = os.path.expandvars(value)
        if not os.path.isdir(value):
            print 'Directory does not exist!\n'
            continue
        break
    return path


def default_config(config_file=DEFAULT_CONFIG_FILE):
    config = OrderedConfig()
    config.set_config_file_location(config_file)
    config['AwsKeyPath'] = input_valid_dir('AwsKeyPath')
    config['PubKeyPath'] = input_valid_dir('PubKeyPath')
    config['ScriptPath'] = input_valid_dir('ScriptPath')
    # config['Domain'] = raw_input('Enter domain: ')
    # config['Salt'] = raw_input('Enter Password Salt: ')
    config['Images'] = OrderedDict()
    config['Bundles'] = OrderedDict()
    config['PythonBundles'] = OrderedDict()
    config['Groups'] = OrderedDict()
    config['Builds'] = OrderedDict()
    config['Projects'] = OrderedDict()

    return config


def read_config(config_file=DEFAULT_CONFIG_FILE):
    if not os.path.exists(config_file):
        basedir = os.path.dirname(config_file)
        if not os.path.exists(basedir):
            os.makedirs(basedir)
        with open(config_file, 'a') as fp:
            json.dump(default_config(config_file), fp, indent=2, separators=(',', ': '))
    with open(config_file, 'r') as fp:
        raw_config = json.load(fp, object_pairs_hook=OrderedDict)
        config = OrderedConfig(raw_config)
        config.set_config_file_location(config_file)
        return config


config = None


def main(argv=sys.argv[1:]):
    global config
    if len(argv) == 2 and argv[0] == '--config':
        config = read_config(argv[1])
        argv = argv[2:]
    else:
        config = read_config()

    myapp = CliffordApp()
    return myapp.run(argv)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
