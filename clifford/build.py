from collections import OrderedDict
from multiprocessing import Pool
import os
import time

from activity import group_installer, launcher, pip_installer, script_runner, upgrade
from commands import BaseCommand
from main import config
from mixins import LaunchOptionsMixin

class Build(BaseCommand, LaunchOptionsMixin):
    "Launch and bootstrap a new ec2 instance"

    def get_parser(self, prog_name):
        parser = super(Build, self).get_parser(prog_name)
        parser.add_argument('-a', '--add', action='store_true')
        parser.add_argument('-n', '--num', type=int, default=1)
        parser.add_argument('--project')
        parser.add_argument('-r', '--remove', action='store_true')
        parser.add_argument('build_name')
        parser.add_argument('tag_name')
        return parser

    def take_action(self, parsed_args):
        if parsed_args.add:
            if parsed_args.build_name in config.builds:
                raise RuntimeError('A build already exists by that name!')
            self.add(parsed_args.build_name)
            return

        if parsed_args.build_name not in config.builds:
            raise RuntimeError('Build not found!')

        if parsed_args.remove:
            del(config.builds[parsed_args.build_name])
            config.save()
            return

        if parsed_args.project:
            self.app.stdout.write('Project: %s; Build: %s\n' % (parsed_args.project, parsed_args.build_name))
        tag_name = raw_input('Enter Tag:Name Value (%s): ' % parsed_args.build_name)
        if not tag_name:
            tag_name = parsed_args.build_name

        if not self.sure_check():
            return

        options = config.builds[parsed_args.build_name]

        kwargs = {
            'key_name': options['Key'],
            'instance_type': options['Size'],
            'security_group_ids': options['SecurityGroups'],
        }
        if 'UserData' in options:
            kwargs['user_data'] = options['UserData']
        if 'Zone' in options:
            kwargs['placement'] = options['Zone']

        if parsed_args.num > 1:
            kwargs['min_count'] = parsed_args.num
            kwargs['max_count'] = parsed_args.num

        project = parsed_args.project or ''
        build = parsed_args.build_name or ''
        launcher(options['Image'], project, build, tag_name, config.aws_key_path, options['Login'], **kwargs)
        time.sleep(10)

        reservation = self.get_reservation(parsed_args.name)

        # begin the mutliprocessing
        pool = Pool(processes=len(reservation.instances))

        if 'Upgrade' in options and options['Upgrade'] in ['upgrade', 'dist-upgrade']:
            self.run_activity(reservation, pool, upgrade, [options['Login'], options['Upgrade'], config.aws_key_path])
            self.app.stdout.write('Upgrade Finished\n')
            time.sleep(10)

        if 'Group' in options and options['Group'] in config.groups:
            group = config.groups[options['Group']]
            bundles = []
            self.get_bundles(group, bundles)
            self.run_activity(reservation, pool, group_installer, [options['Login'], bundles, config.aws_key_path])
            self.app.stdout.write('Pip Installer Finished\n')
            time.sleep(10)

        if 'Pip' in options:
            python_packages = config.python_bundles[options['Pip']]
            self.app.stdout.write('python: %s [%s]\n' % (options['Pip'], python_packages))

            self.run_activity(reservation, pool, pip_installer, [options['Login'], python_packages, config.aws_key_path])
            self.app.stdout.write('Pip Installer Finished\n')
            time.sleep(10)

        if 'Script' in options:
            self.run_activity(reservation, pool, script_runner, [options['Login'], os.path.join(config.script_path, options['Script']), config.aws_key_path])

        pool.close()
        pool.join()

    def get_bundles(self, group, bundles):
        for item in config.groups[group]:
            if item['Type'] == 'bundle':
                bundles.append(config.bundles[item['Value']])
            elif item['Type'] == 'group':
                self.get_bundles(item['Value'], bundles)
            elif item['Type'] == 'packages':
                bundles.append(item['Value'])

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

    def add(self, name):
        instance_type = self.get_instance_type()
        image_item = self.get_image(return_item=True)
        key = self.get_key()
        zone = self.get_zone()
        security_groups = self.get_security_groups(return_names=True)
        user_data = self.get_user_data(return_name=True)

        upgrade_options = [{'text': 'Skip Step'}, {'text': 'upgrade'}, {'text': 'dist-upgrade'}]
        upgrade_option = self.question_maker('Select upgrade option', 'upgrade', upgrade_options, start_at=0)

        if config.groups:
            groups = config.groups
            group_options = [{'text': 'Skip Step'}]
            group_options.extend([{'text': item} for item in groups.keys()])
            group_option = self.question_maker('Select group to install', 'group', group_options, start_at=0)
        else:
            group_option = 'Skip Step'

        if config.python_bundles:
            bundles = config.python_bundles
            bundle_options = [{'text': 'Skip Step'}]
            bundle_options.extend([{'text': item} for item in bundles.keys()])
            bundle_option = self.question_maker('Select python bundle to install', 'bundle', bundle_options, start_at=0)
        else:
            bundle_option = 'Skip Step'

        build = OrderedDict()
        build['Size'] = instance_type
        build['Login'] = image_item['Login']
        build['Image'] = image_item['Id']
        build['Key'] = key.name
        build['SecurityGroups'] = security_groups

        if hasattr(zone, 'name'):
            build['Zone'] = zone.name

        if user_data:
            build['UserData'] = user_data

        if upgrade_option != 'Skip Step':
            build['Upgrade'] = upgrade_option

        if group_option != 'Skip Step':
            build['Group'] = group_option

        if bundle_option != 'Skip Step':
            build['Pip'] = bundle_option

        config.builds[name] = build
        config.save()
