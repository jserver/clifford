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
        section = 'Bundles' if not parsed_args.is_py_bundle else 'Python Bundles'
        self.app.stdout.write('%s\n' % self.get_option(section, parsed_args.name))


class DomainName(BaseCommand):
    "Show the domain_name saved to the config file."

    def take_action(self, parsed_args):
        self.app.stdout.write('%s\n' % self.get_option('General', 'domain_name'))


class Group(BaseCommand):
    "Display the items in a group."

    def get_parser(self, prog_name):
        parser = super(Group, self).get_parser(prog_name)
        parser.add_argument('name')
        return parser

    def take_action(self, parsed_args):
        self.app.stdout.write('%s\n' % self.get_option('Groups', parsed_args.name))


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
        self.app.stdout.write('%s\n' % self.key_path)


class PasswordSalt(BaseCommand):
    "Show the password_salt saved to the config file."

    def take_action(self, parsed_args):
        self.app.stdout.write('%s\n' % self.get_option('General', 'password_salt'))


class ScriptPath(BaseCommand):
    "Show the script_path saved to the config file."

    def take_action(self, parsed_args):
        self.app.stdout.write('%s\n' % self.script_path)
