import time

from commands import BaseCommand
from mixins import LaunchOptionsMixin, SingleInstanceMixin


class Build(BaseCommand, LaunchOptionsMixin, SingleInstanceMixin):
    "Launch and bootstrap a new ec2 instance"

    def get_parser(self, prog_name):
        parser = super(Build, self).get_parser(prog_name)
        parser.add_argument('-y', dest='assume_yes', action='store_true')
        parser.add_argument('--build')
        parser.add_argument('--create', action='store_true')
        parser.add_argument('name')
        return parser

    def create(self, name):
        instance_type = self.get_instance_type()
        image = self.get_image(return_name=True)
        key = self.get_key()
        zone = self.get_zone()
        security_groups = self.get_security_groups(return_names=True)
        user_data = self.get_user_data(return_name=True)

        section = 'Build:' + name
        self.app.cparser.add_section(section)
        self.app.cparser.set(section, 'size', instance_type)
        self.app.cparser.set(section, 'image', image)
        self.app.cparser.set(section, 'key', key.name)

        if hasattr(zone, 'name'):
            self.app.cparser.set(section, 'zone', zone.name)

        self.app.cparser.set(section, 'security_groups', security_groups)

        if user_data:
            self.app.cparser.set(section, 'user_data', user_data)

        upgrade_options = [{'text': 'Skip Step'}, {'text': 'upgrade'}, {'text': 'dist-upgrade'}]
        upgrade_option = self.question_maker('Select upgrade option', 'upgrade', upgrade_options, start_at=0)
        if upgrade_option != 'Skip Step':
            self.app.cparser.set(section, 'upgrade', upgrade_option)

        groups = self.app.cparser.options('Groups')
        group_options = [{'text': 'Skip Step'}]
        group_options.extend([{'text': group} for group in groups])
        group_option = self.question_maker('Select group to install', 'group', group_options, start_at=0)
        if group_option != 'Skip Step':
            self.app.cparser.set(section, 'group', group_option)

        bundles = self.app.cparser.options('Python Bundles')
        bundle_options = [{'text': 'Skip Step'}]
        bundle_options.extend([{'text': bundle} for bundle in bundles])
        bundle_option = self.question_maker('Select python bundle to install', 'bundle', bundle_options, start_at=0)
        if bundle_option != 'Skip Step':
            self.app.cparser.set(section, 'pip', bundle_option)

        self.app.write_config()

    def take_action(self, parsed_args):
        if parsed_args.create:
            self.create(parsed_args.name)
            return

        if parsed_args.build:
            build = parsed_args.build
        else:
            build = self.question_maker('Select Build', 'build',
                    [{'text': section[6:]} for section in self.app.cparser.sections() if section.startswith('Build:')])
            if not self.app.cparser.has_section('Build:%s' % build):
                raise RuntimeError('No build with that name in config!\n')

        if not parsed_args.assume_yes and not self.sure_check():
            return

        option_list = self.app.cparser.options('Build:%s' % build)
        options = {}
        for option in option_list:
            options[option] = self.app.cparser.get('Build:%s' % build, option)

        cmd = 'launch -y'
        cmd += ' --size %s' % options['size']
        cmd += ' --image %s' % self.app.cparser.get('Images', options['image'])
        cmd += ' --key %s' % options['key']
        cmd += ' --zone %s' % options['zone']
        cmd += ' --security-groups %s' % options['security_groups']
        if 'user_data' in options:
            cmd += ' --user-data %s' % options['user_data']
        cmd += ' ' + parsed_args.name
        self.app.run_subcommand(cmd.split(' '))
        time.sleep(10)

        instance = self.get_instance(parsed_args.name)
        if not instance:
            raise RuntimeError('Cannot find instance')

        if 'upgrade' in options and options['upgrade'] in ['upgrade', 'dist-upgrade']:
            cmd = 'remote upgrade -y'
            cmd += ' --id %s' % instance.id
            if options['upgrade'] == 'upgrade':
                cmd += ' --upgrade'
            if options['upgrade'] == 'dist-upgrade':
                cmd += ' --dist-upgrade'
            self.app.run_subcommand(cmd.split(' '))
            time.sleep(35)

        if 'group' in options:
            cmd = 'remote group install -y'
            cmd += ' --id %s' % instance.id
            cmd += ' ' + options['group']
            self.app.run_subcommand(cmd.split(' '))
            time.sleep(5)

        if 'pip' in options:
            cmd = 'remote pip install -y'
            cmd += ' --id %s' % instance.id
            cmd += ' ' + options['pip']
            self.app.run_subcommand(cmd.split(' '))

        if 'script_name' in options:
            cmd = 'remote script -y'
            cmd += ' --script %s' % options['script_name']
            if 'script_action' in options and options['script_action'] == 'copy':
                cmd += ' --copy-only'
            cmd += ' --id %s' % instance.id
            self.app.run_subcommand(cmd.split(' '))
