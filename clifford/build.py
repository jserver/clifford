import time

from commands import BaseCommand
from mixins import SingleInstanceMixin


class Build(BaseCommand, SingleInstanceMixin):
    "Launch and bootstrap a new ec2 instance"

    def get_parser(self, prog_name):
        parser = super(Build, self).get_parser(prog_name)
        parser.add_argument('-y', dest='assume_yes', action='store_true')
        parser.add_argument('--build')
        parser.add_argument('name')
        return parser

    def take_action(self, parsed_args):
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
        cmd += ' --image %s' % options['image']
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

        if 'easy_install' in options:
            cmd = 'remote easy_install -y'
            cmd += ' --id %s' % instance.id
            cmd += ' ' + options['easy_install']
            self.app.run_subcommand(cmd.split(' '))

        if 'script_name' in options:
            cmd = 'remote script -y'
            cmd += ' --script %s' % options['script_name']
            if 'script_action' in options and options['script_action'] == 'copy':
                cmd += ' --copy-only'
            cmd += ' --id %s' % instance.id
            self.app.run_subcommand(cmd.split(' '))
