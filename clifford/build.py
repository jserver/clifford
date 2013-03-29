import time

from commands import BaseCommand
from mixins import SingleInstanceMixin


class Build(BaseCommand, SingleInstanceMixin):
    "Launch and bootstrap a new ec2 instance"

    def get_parser(self, prog_name):
        parser = super(Build, self).get_parser(prog_name)
        parser.add_argument('name')
        return parser

    def take_action(self, parsed_args):
        build = self.question_maker('Select Build', 'build',
                [{'text': build[6:]} for build in self.app.cparser.sections() if build.startswith('build:')])
        if not self.app.cparser.has_section('build:%s' % build):
            raise RuntimeError('No build with that name in config!\n')

        if not self.sure_check():
            return

        option_list = self.app.cparser.options('build:%s' % build)
        options = {}
        for option in option_list:
            options[option] = self.app.cparser.get('build:%s' % build, option)

        cmd = 'launch -y'
        cmd += ' --size %s' % options['size']
        cmd += ' --image %s' % options['image']
        cmd += ' --key %s' % options['key']
        cmd += ' --zone %s' % options['zone']
        cmd += ' --security_group %s' % options['security_group']
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

        if 'user_name' in options:
            cmd = 'remote create user -y'
            cmd += ' --id %s' % instance.id
            cmd += ' ' + options['user_name']
            if 'user_fullname' in options:
                cmd += ' --fullname %s' % options['user_fullname']
            else:
                cmd += ' --fullname %s' + options['user_name']
            self.app.run_subcommand(cmd.split(' '))

        # might need to wait until paramiko merges in the agent-forwarding
        #if 'user_script' in options:
        #    cmd = 'remote script -y'
        #    cmd += ' --id %s' % instance.id
        #    cmd += ' --script %s' % options['user_script']
        #    cmd += ' --user %s' % options['user_name']
        #    self.app.run_subcommand(cmd.split(' '))
