import logging

from cliff.command import Command
from cliff.show import ShowOne

from mixins import SingleInstanceMixin


class Instance(ShowOne, SingleInstanceMixin):
    "Show details about a single instance."

    log = logging.getLogger(__name__)

    def get_parser(self, prog_name):
        parser = super(Instance, self).get_parser(prog_name)
        parser.add_argument('name')
        return parser

    def take_action(self, parsed_args):
        instance = self.get_instance(parsed_args.name)

        columns = ('Name',
                   'Id',
                   'State',
                   'Type',
                   'Root Device',
                   'Arch',
                   'Zone',
                   'Public DNS'
                   )
        data = (instance.tags.get('Name'),
                instance.id,
                instance.state,
                instance.instance_type,
                instance.root_device_type,
                instance.architecture,
                instance.placement,
                instance.public_dns_name or '',
                )

        return (columns, data)


class KeyDir(Command):
    "Show the key dir saved to the config file."

    log = logging.getLogger(__name__)

    def take_action(self, parsed_args):
        if not self.app.cparser.has_option('Key Dir', 'keydir'):
            raise RuntimeError('No keydir set!')
        self.app.stdout.write('%s\n' % self.app.cparser.get('Key Dir', 'keydir'))


class Owner(Command):
    "Show the owner saved to the config file."

    log = logging.getLogger(__name__)

    def take_action(self, parsed_args):
        if not self.app.cparser.has_option('Owner', 'owner'):
            raise RuntimeError('No owner set!')
        self.app.stdout.write('%s\n' % self.app.cparser.get('Owner', 'owner'))


class Package(Command):
    "Display the items in the package."

    log = logging.getLogger(__name__)

    def get_parser(self, prog_name):
        parser = super(Package, self).get_parser(prog_name)
        parser.add_argument('name')
        return parser

    def take_action(self, parsed_args):
        if not self.app.cparser.has_option('Packages', parsed_args.name):
            raise RuntimeError('No package named %s!' % parsed_args.name)
        self.app.stdout.write('%s\n' % self.app.cparser.get('Packages', parsed_args.name))


class ScriptDir(Command):
    "Show the script dir saved to the config file."

    log = logging.getLogger(__name__)

    def take_action(self, parsed_args):
        if not self.app.cparser.has_option('Script Dir', 'scriptdir'):
            raise RuntimeError('No scriptdir set!')
        self.app.stdout.write('%s\n' % self.app.cparser.get('Script Dir', 'scriptdir'))
