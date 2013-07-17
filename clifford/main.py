import logging
import os
import sys
from ConfigParser import SafeConfigParser
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
        self.config_file = '%s/.clifford/config' % expanduser("~")
        self.ec2_conn = boto.connect_ec2()
        self.s3_conn = boto.connect_s3()
        self.cparser = SafeConfigParser()
        self.cparser.read(self.config_file)

    def initialize_app(self, argv):
        self.log.debug('initialize_app')

    def prepare_to_run_command(self, cmd):
        self.log.debug('prepare_to_run_command %s', cmd.__class__.__name__)

    def clean_up(self, cmd, result, err):
        self.log.debug('clean_up %s', cmd.__class__.__name__)
        if err:
            self.log.debug('got an error: %s', err)

    def get_option(self, section, option, raise_error=True):
        if not self.app.cparser.has_option(section, option):
            if raise_error:
                raise RuntimeError('No %s set!' % option)
            else:
                return None
        value = self.app.cparser.get(section, option)
        if option.endswith('_path'):
            value = os.path.expanduser(value)
            value = os.path.expandvars(value)
        return value

    def add_slash(self, key_path):
        if key_path[-1] != '/':
            key_path = key_path + '/'
        return key_path

    @property
    def aws_key_path(self):
        return self.get_option('General', 'aws_key_path')

    @property
    def pub_key_path(self):
        return self.get_option('General', 'pub_key_path')

    @property
    def script_path(self):
        return self.get_option('General', 'script_path')

    def write_config(self):
        with open(self.config_file, 'wb') as configfile:
            self.cparser.write(configfile)
        self.cparser.read(self.config_file)


def main(argv=sys.argv[1:]):
    myapp = CliffordApp()
    return myapp.run(argv)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
