import logging
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

    def write_config(self):
        with open(self.config_file, 'wb') as configfile:
            self.cparser.write(configfile)
        self.cparser.read(self.config_file)


def main(argv=sys.argv[1:]):
    myapp = CliffordApp()
    return myapp.run(argv)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
