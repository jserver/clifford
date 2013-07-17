import time

from commands import BaseCommand
from mixins import SingleInstanceMixin


class Project(BaseCommand, SingleInstanceMixin):
    "Launch and bootstrap a new ec2 instance"

    def get_parser(self, prog_name):
        parser = super(Project, self).get_parser(prog_name)
        parser.add_argument('-n', '--name')
        parser.add_argument('-p', '--project')
        return parser

    def take_action(self, parsed_args):
        name = raw_input('Enter name to tag instances with: ')
        if not name or not self.is_ok(name):
            raise RuntimeError('Inavlid Name!\n')

        if not parsed_args.project:
            project = self.question_maker('Select Project', 'project',
                    [{'text': section[8:]} for section in self.app.cparser.sections() if section.startswith('Project:')])
        else:
            project = parsed_args.project
        if not self.app.cparser.has_section('Project:%s' % project):
            raise RuntimeError('No project with that name in config!\n')

        if not self.sure_check():
            return

        items = self.app.cparser.items('Project:%s' % project)
        options = {}
        for item in items:
            options[item[0]] = item[1]

        if 'build' not in options:
            raise RuntimeError('No build in project')

        cmd = 'build -y'
        cmd += ' --build %s' % options['build']
        if 'count' in options:
            cmd += ' --count %s' % options['count']
        cmd += ' ' + parsed_args.name
        self.app.run_subcommand(cmd.split(' '))
        time.sleep(15)

        '''
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

        if 'script_name' in options:
            cmd = 'remote script -y'
            cmd += ' --script %s' % options['script_name']
            cmd += ' --user %s' % options['user_name']
            if 'script_action' in options and options['script_action'] == 'copy':
                cmd += ' --copy-only'
            cmd += ' --id %s' % instance.id
            self.app.run_subcommand(cmd.split(' '))
        '''
