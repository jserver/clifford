import json
import logging
import os
import sys
from collections import OrderedDict
from os.path import expanduser

import boto
from cliff.app import App
from cliff.commandmanager import CommandManager


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
        self.json_config_file = '%s/.clifford/config.json' % expanduser("~")
        self.config = self.read_config()

    def initialize_app(self, argv):
        self.log.debug('initialize_app')

        changes_made = False

        if 'AwsKeyPath' not in self.config:
            self.config['AwsKeyPath'] = self.input_valid_path('AwsKeyPath')
            changes_made = True

        if 'PubKeyPath' not in self.config:
            self.config['PubKeyPath']  = self.input_valid_path('PubKeyPath')
            changes_made = True

        if 'ScriptPath' not in self.config:
            self.config['ScriptPath']  = self.input_valid_path('ScriptPath')
            changes_made = True

        if changes_made:
            self.write_config()

    def prepare_to_run_command(self, cmd):
        self.log.debug('prepare_to_run_command %s', cmd.__class__.__name__)

    def clean_up(self, cmd, result, err):
        self.log.debug('clean_up %s', cmd.__class__.__name__)
        if err:
            self.log.debug('got an error: %s', err)

    def input_valid_path(self, name):
        while True:
            path = raw_input('Enter %s: ' % name)
            if not path:
                self.stdout.write('This field is required!\n')
                continue
            value = os.path.expanduser(path)
            value = os.path.expandvars(value)
            if not os.path.exists(value):
                self.stdout.write('Directory does not exist!\n')
                continue
            break
        return path

    def get_path(self, key):
        if key not in self.config:
            raise RuntimeError('%s not found!' % key)
        value = self.config[key]
        value = os.path.expanduser(value)
        value = os.path.expandvars(value)
        return value

    @property
    def aws_key_path(self):
        return self.get_path('AwsKeyPath')

    @property
    def pub_key_path(self):
        return self.get_path('PubKeyPath')

    @property
    def script_path(self):
        return self.get_path('ScriptPath')

    def read_config(self):
        if not os.path.exists(self.json_config_file):
            basedir = os.path.dirname(self.json_config_file)
            if not os.path.exists(basedir):
                os.makedirs(basedir)
            with open(self.json_config_file, 'a') as configfile:
                json.dump({}, configfile)
        with open(self.json_config_file, 'r') as configfile:
            return json.load(configfile, object_pairs_hook=OrderedDict)

    def write_config(self):
        with open(self.json_config_file, 'wb') as configfile:
            json.dump(self.config, configfile, indent=2, separators=(',', ': '))


def main(argv=sys.argv[1:]):
    myapp = CliffordApp()
    return myapp.run(argv)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
