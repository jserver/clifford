from multiprocessing import Pool
import os
import time

from activity import group_installer, pip_installer, script_runner, upgrade
from commands import BaseCommand
from mixins import LaunchOptionsMixin, SingleInstanceMixin

class Build(BaseCommand, LaunchOptionsMixin, SingleInstanceMixin):
    "Launch and bootstrap a new ec2 instance"

    def get_parser(self, prog_name):
        parser = super(Build, self).get_parser(prog_name)
        parser.add_argument('-y', dest='assume_yes', action='store_true')
        parser.add_argument('--build')
        parser.add_argument('--count', type=int, default=1)
        parser.add_argument('--create', action='store_true')
        parser.add_argument('name')
        return parser

    def create(self, name):
        instance_type = self.get_instance_type()
        image_item = self.get_image(return_item=True)
        key = self.get_key()
        zone = self.get_zone()
        security_groups = self.get_security_groups(return_names=True)
        user_data = self.get_user_data(return_name=True)

        upgrade_options = [{'text': 'Skip Step'}, {'text': 'upgrade'}, {'text': 'dist-upgrade'}]
        upgrade_option = self.question_maker('Select upgrade option', 'upgrade', upgrade_options, start_at=0)

        if self.app.cparser.has_section('Groups'):
            groups = self.app.cparser.options('Groups')
            group_options = [{'text': 'Skip Step'}]
            group_options.extend([{'text': group} for group in groups])
            group_option = self.question_maker('Select group to install', 'group', group_options, start_at=0)
        else:
            group_option = 'Skip Step'

        if self.app.cparser.has_section('Python Bundles'):
            bundles = self.app.cparser.options('Python Bundles')
            bundle_options = [{'text': 'Skip Step'}]
            bundle_options.extend([{'text': bundle} for bundle in bundles])
            bundle_option = self.question_maker('Select python bundle to install', 'bundle', bundle_options, start_at=0)
        else:
            bundle_option = 'Skip Step'

        section = 'Build:' + name
        self.app.cparser.add_section(section)
        self.app.cparser.set(section, 'size', instance_type)
        self.app.cparser.set(section, 'login', image_item[1].split('@')[0])
        self.app.cparser.set(section, 'image', image_item[1].split('@')[1])
        self.app.cparser.set(section, 'key', key.name)

        if hasattr(zone, 'name'):
            self.app.cparser.set(section, 'zone', zone.name)

        self.app.cparser.set(section, 'security_groups', security_groups)

        if user_data:
            self.app.cparser.set(section, 'user_data', user_data)

        if upgrade_option != 'Skip Step':
            self.app.cparser.set(section, 'upgrade', upgrade_option)

        if group_option != 'Skip Step':
            self.app.cparser.set(section, 'group', group_option)

        if bundle_option != 'Skip Step':
            self.app.cparser.set(section, 'pip', bundle_option)

        self.app.write_config()

    def run_activity(self, reservation, pool, func, arg_list):
        results = []
        for inst in reservation.instances:
            self.app.stdout.write('%s Starting: %s\n' % (func.func_name, inst.id))
            results.append(pool.apply_async(func, [inst] + arg_list))

        completed = []
        while results:
            time.sleep(20)
            results = [result for result in results if result not in completed]
            for result in results:
                if result.ready():
                    self.app.stdout.write('-------------------------\n')
                    self.app.stdout.write('Result: %s\n' % result.get())
                    completed.append(result)

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

        count = parsed_args.count

        cmd = 'launch -y'
        cmd += ' --size %s' % options['size']
        cmd += ' --image %s' % self.app.cparser.get('Images', options['image'])
        cmd += ' --key %s' % options['key']
        cmd += ' --zone %s' % options['zone']
        cmd += ' --security-groups %s' % options['security_groups']
        if 'user_data' in options:
            cmd += ' --user-data %s' % options['user_data']
        cmd +=' --count %s' % count
        cmd += ' ' + parsed_args.name
        self.app.run_subcommand(cmd.split(' '))
        time.sleep(10)

        reservation = self.get_reservation(parsed_args.name)

        # begin the mutliprocessing
        pool = Pool(processes=len(reservation.instances))

        if 'upgrade' in options and options['upgrade'] in ['upgrade', 'dist-upgrade']:
            self.run_activity(reservation, pool, upgrade, [options['login'], options['upgrade'], self.app.aws_key_path])
            self.app.stdout.write('Upgrade Finished\n')
            time.sleep(10)

        if 'group' in options:
            group = self.app.get_option('Groups', options['group'])
            bundle_names = group.split(' ')
            bundles = []
            for bundle_name in bundle_names:
                bundle = self.app.get_option('Bundles', bundle_name, raise_error=False)
                if bundle:
                    bundles.append((bundle_name, bundle))

            for bundle in bundles:
                self.app.stdout.write('bundle: %s [%s]\n' % (bundle[0], bundle[1]))

            self.run_activity(reservation, pool, group_installer, [options['login'], bundles, self.app.aws_key_path])
            self.app.stdout.write('Group Installer Finished\n')
            time.sleep(10)

        if 'pip' in options:
            python_packages = self.app.get_option('Python Bundles', options['pip'])
            self.app.stdout.write('python: %s [%s]\n' % (options['pip'], python_packages))

            self.run_activity(reservation, pool, pip_installer, [options['login'], python_packages, self.app.aws_key_path])
            self.app.stdout.write('Pip Installer Finished\n')
            time.sleep(10)

        if 'script' in options:
            self.run_activity(reservation, pool, script_runner, [options['login'], os.path.join(self.app.script_path, options['script']), self.app.aws_key_path])

        pool.close()
        pool.join()
