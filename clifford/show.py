import logging

from cliff.show import ShowOne

from commands import BaseCommand
from mixins import SingleInstanceMixin


class Bundle(BaseCommand):
    "Display the packages in a bundle."

    def get_parser(self, prog_name):
        parser = super(Bundle, self).get_parser(prog_name)
        parser.add_argument('--py', dest='is_py_bundle', action='store_true')
        parser.add_argument('name')
        return parser

    def take_action(self, parsed_args):
        section = 'Bundles' if not is_py_bundle else 'Python Bundles'
        if not self.app.cparser.has_option(section, parsed_args.name):
            raise RuntimeError('No bundle named %s!' % parsed_args.name)
        self.app.stdout.write('%s\n' % self.app.cparser.get(section, parsed_args.name))


class Group(BaseCommand):
    "Display the items in a group."

    def get_parser(self, prog_name):
        parser = super(Group, self).get_parser(prog_name)
        parser.add_argument('name')
        return parser

    def take_action(self, parsed_args):
        if not self.app.cparser.has_option('Groups', parsed_args.name):
            raise RuntimeError('No group named %s!' % parsed_args.name)
        self.app.stdout.write('%s\n' % self.app.cparser.get('Groups', parsed_args.name))


class Instance(ShowOne, SingleInstanceMixin):
    "Show details about a single instance."

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


class KeyPath(BaseCommand):
    "Show the key_path saved to the config file."

    def take_action(self, parsed_args):
        if not self.app.cparser.has_option('Key Path', 'key_path'):
            raise RuntimeError('No key_path set!')
        self.app.stdout.write('%s\n' % self.app.cparser.get('Key Path', 'key_path'))


class Owner(BaseCommand):
    "Show the owner saved to the config file."

    def take_action(self, parsed_args):
        if not self.app.cparser.has_option('Owner', 'owner'):
            raise RuntimeError('No owner set!')
        self.app.stdout.write('%s\n' % self.app.cparser.get('Owner', 'owner'))


class ScriptPath(BaseCommand):
    "Show the script_path saved to the config file."

    def take_action(self, parsed_args):
        if not self.app.cparser.has_option('Script Path', 'script_path'):
            raise RuntimeError('No script_path set!')
        self.app.stdout.write('%s\n' % self.app.cparser.get('Script Path', 'script_path'))
