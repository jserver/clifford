from collections import OrderedDict
from multiprocessing import Pool
import os
import time

from activity import group_installer, pip_installer, script_runner, upgrade
from commands import BaseCommand
from main import config
from mixins import LaunchOptionsMixin

class Build(BaseCommand, LaunchOptionsMixin):
    "Launch and bootstrap a new ec2 instance"

    def get_parser(self, prog_name):
        parser = super(Build, self).get_parser(prog_name)
        parser.add_argument('-y', dest='assume_yes', action='store_true')
        parser.add_argument('-b', '--build')
        parser.add_argument('-c', '--create', action='store_true')
        parser.add_argument('-n', '--num', type=int, default=1)
        parser.add_argument('name')
        return parser

    def take_action(self, parsed_args):
        if parsed_args.create:
            self.create(parsed_args.name)
            return

        if not config.builds:
            raise RuntimeError('No Builds found!')

        if parsed_args.build and parsed_args.build in config.builds.keys():
            build = parsed_args.build
        else:
            build = self.question_maker('Select Build', 'build', [{'text': bld} for bld in config.builds.keys()])
            if not build:
                raise RuntimeError('No Build selected!\n')

        if not parsed_args.assume_yes and not self.sure_check():
            return

        options = config.builds[build]

        cmd = 'launch -y'
        cmd += ' --size %s' % options['Size']
        cmd += ' --image %s' % options['Login']
        cmd += ' --image %s' % options['Image']
        cmd += ' --key %s' % options['Key']
        cmd += ' --zone %s' % options['Zone']
        cmd += ' --security-groups %s' % ','.join(options['SecurityGroups'])
        if 'UserData' in options:
            cmd += ' --user-data %s' % options['UserData']
        cmd +=' --num %s' % parsed_args.num
        cmd += ' ' + parsed_args.name
        self.app.run_subcommand(cmd.split(' '))
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

    def create(self, name):
        if not config.images:
            raise RuntimeError('No Images Found')

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
