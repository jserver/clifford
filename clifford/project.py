from collections import OrderedDict
import time

from commands import BaseCommand
from main import config, write_config
from mixins import SingleInstanceMixin


class Project(BaseCommand, SingleInstanceMixin):
    "Launch and bootstrap a new ec2 instance"

    def get_parser(self, prog_name):
        parser = super(Project, self).get_parser(prog_name)
        parser.add_argument('-c', '--create', action='store_true')
        parser.add_argument('name')
        return parser

    def take_action(self, parsed_args):
        if parsed_args.create:
            self.create(parsed_args.name)
            return

        if 'Projects' not in config:
            raise RuntimeError('No Projects found!')

        if parsed_args.name not in config['Projects']:
            raise RuntimeError('Project not found!')

        project = config['Projects'][parsed_args.name]
        if 'Build' not in project:
            raise RuntimeError('No build in project')

        self.app.stdout.write('This project will launch %s instance(s)' % project['Num'])
        if not self.sure_check():
            return

        cmd = 'build -y'
        cmd += ' --build %s' % project['Build']
        if 'Num' in project:
            cmd += ' --num %s' % project['Num']
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

    def create(self, name):
        build = self.question_maker('Select Build', 'build', [{'text': bld} for bld in config['Builds'].keys()])
        if not build:
            raise RuntimeError('No Build selected!\n')

        num = raw_input('How many instances? ')
        if not num.isdigit():
            raise RuntimeError('Invalid number!')

        project = OrderedDict()
        project['Build'] = build
        project['Num'] = int(num)
        config['Projects'][name] = project
        write_config()
