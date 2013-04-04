import time

from commands import BaseCommand
from mixins import SingleInstanceMixin


class Project(BaseCommand, SingleInstanceMixin):
    "Launch and bootstrap a new ec2 instance"

    def get_parser(self, prog_name):
        parser = super(Project, self).get_parser(prog_name)
        parser.add_argument('name')
        return parser

    def take_action(self, parsed_args):
        project = self.question_maker('Select Project', 'project',
                [{'text': section[8:]} for section in self.app.cparser.sections() if section.startswith('Project:')])
        if not self.app.cparser.has_section('Project:%s' % project):
            raise RuntimeError('No project with that name in config!\n')

        if not self.sure_check():
            return

        option_list = self.app.cparser.options('Project:%s' % project)
        options = {}
        for option in option_list:
            options[option] = self.app.cparser.get('Project:%s' % project, option)

        if 'build' not in options:
            raise RuntimeError('No build in project')

        cmd = 'build -y'
        cmd += ' --build %s' % options['build']
        cmd += ' ' + parsed_args.name
        self.app.run_subcommand(cmd.split(' '))
        time.sleep(15)

        instance = self.get_instance(parsed_args.name)
        if not instance:
            raise RuntimeError('Cannot find instance')

        if 'user_name' in options:
            cmd = 'remote create user -y'
            if 'user_fullname' in options:
                cmd += ' --fullname %s' % options['user_fullname']
            else:
                cmd += ' --fullname %s' + options['user_name']
            if 'user_password' in options:
                cmd += ' --password %s' % options['user_password']
            else:
                cmd += ' --password %s' % options['user_name']
            cmd += ' --id %s' % instance.id
            cmd += ' ' + options['user_name']
            self.app.run_subcommand(cmd.split(' '))

        if 'script' in options:
            cmd = 'remote script -y'
            cmd += ' --script %s' % options['script']
            cmd += ' --user %s' % options['user_name']
            cmd += ' --copy-only'
            cmd += ' --id %s' % instance.id
            self.app.run_subcommand(cmd.split(' '))
