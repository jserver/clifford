import logging

from cliff.command import Command
from cliff.show import ShowOne

from mixins import SingleBoxMixin


class Describe(ShowOne, SingleBoxMixin):
    "Show details about a single instance."

    log = logging.getLogger(__name__)

    def get_parser(self, prog_name):
        parser = super(Describe, self).get_parser(prog_name)
        parser.add_argument('name')
        return parser

    def take_action(self, parsed_args):
        instance = self.get_box(parsed_args.name)

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


class Owner(Command):
    "Show the owner saved to the config file."

    log = logging.getLogger(__name__)

    def take_action(self, parsed_args):
        if not self.app.cparser.has_option('Owner', 'owner'):
            raise RuntimeError('No owner set!')
        self.app.stdout.write(self.app.cparser.get('Owner', 'owner'))
