from collections import OrderedDict
from multiprocessing import Pool, Queue
import os
import time

from activity import Task
from activity import add_user, elastic_ip, group_installer, launcher, pip_installer, script_runner, static_host, upgrade
from commands import BaseCommand
from main import config
from mixins import LaunchOptionsMixin


class Build(BaseCommand, LaunchOptionsMixin):
    "Launch and bootstrap a new ec2 instance"

    def get_parser(self, prog_name):
        parser = super(Build, self).get_parser(prog_name)
        parser.add_argument('-a', '--add', action='store_true')
        parser.add_argument('-n', '--num', type=int, default=1)
        parser.add_argument('-r', '--remove', action='store_true')
        parser.add_argument('-u', '--update')
        parser.add_argument('build_name')
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

        if parsed_args.update:
            aws_images = self.app.ec2_conn.get_all_images(image_ids=[parsed_args.update])
            if aws_images:
                config.builds[parsed_args.build_name]['Image'] = parsed_args.update
                config.save()
                return
            else:
                raise RuntimeError('Image not found!')

        tag_name = raw_input('Enter Tag:Name Value (%s): ' % parsed_args.build_name)
        if not tag_name:
            tag_name = parsed_args.build_name
        if not tag_name.isalnum():
            raise RuntimeError('Keep names simple alpha-numeric!')

        if not self.sure_check():
            return

        build = config.builds[parsed_args.build_name]
        image = config.images[build['Image']]

        q = Queue()
        launcher(tag_name, config.aws_key_path, config.script_path,
                 build_name=parsed_args.build_name, build=build, image=image,
                 num=parsed_args.num, q=q, out=self.app.stdout)
        lr = q.get()

        self.app.stdout.write('Sleeping 1 minute to allow server to come up...\n')
        time.sleep(60)

        # begin the mutliprocessing
        pool = Pool(processes=len(lr.instance_ids))

        if 'ElasticIP' in build:
            tasks = [Task(build, image, inst_id, []) for inst_id in lr.instance_ids]
            self.run_activity(pool, elastic_ip, tasks)
            self.app.stdout.write('ElasticIP Finished\n')
            time.sleep(10)
        elif 'StaticHost' not in build or build['StaticHost'] != 'skip':
            tasks = [Task(build, image, inst_id, [tag_name]) for inst_id in lr.instance_ids]
            self.run_activity(pool, static_host, tasks)
            self.app.stdout.write('Static Host Finished\n')
            time.sleep(10)

        if build.get('Upgrade', '') in ['upgrade', 'dist-upgrade']:
            tasks = [Task(build, image, inst_id, []) for inst_id in lr.instance_ids]
            self.run_activity(pool, upgrade, tasks)
            self.app.stdout.write('Upgrade Finished\n')
            time.sleep(10)

        if build.get('Group', '') in config.groups:
            bundles = []
            self.get_bundles(build['Group'], bundles)
            if bundles:
                tasks = [Task(build, image, inst_id, [bundles]) for inst_id in lr.instance_ids]
                self.run_activity(pool, group_installer, tasks)
                self.app.stdout.write('Group Installer Finished\n')
                time.sleep(10)

        if build.get('Pip', '') in config.python_bundles:
            python_packages = config.python_bundles[build['Pip']]
            if python_packages:
                tasks = [Task(build, image, inst_id, [python_packages]) for inst_id in lr.instance_ids]
                self.run_activity(pool, pip_installer, tasks)
                self.app.stdout.write('Pip Installer Finished\n')
                time.sleep(10)

        if 'Script' in build:
            tasks = [Task(build, image, inst_id, [image['Login'], os.path.join(config.script_path, build['Script']), False]) for inst_id in lr.instance_ids]
            self.run_activity(pool, script_runner, tasks)

        if 'Adduser' in build:
            tasks = [Task(build, image, inst_id, [config.pub_key_path]) for inst_id in lr.instance_ids]
            self.run_activity(pool, add_user, tasks)

            if 'Script' in build['Adduser']:
                tasks = [Task(build, image, inst_id, [build['Adduser']['User'], os.path.join(config.script_path, build['Adduser']['Script']), False]) for inst_id in lr.instance_ids]
                self.run_activity(pool, script_runner, tasks)

        pool.close()
        pool.join()

    def get_bundles(self, group, bundles):
        for item in config.groups[group]:
            if item['Type'] == 'bundle':
                bundles.append((item['Value'], config.bundles[item['Value']]))
            elif item['Type'] == 'group':
                if item['Value'] in config.groups:
                    self.get_bundles(item['Value'], bundles)
            elif item['Type'] == 'packages':
                bundles.append(('packages', item['Value']))

    def run_activity(self, pool, func, tasks):
        results = []
        for task in tasks:
            self.app.stdout.write('==>%s starting: %s\n' % (func.func_name, task.instance_id))
            results.append(pool.apply_async(func, [config.aws_key_path, task]))

        completed = []
        while results:
            time.sleep(20)
            for result in results:
                if result.ready():
                    self.app.stdout.write('-------------------------\n')
                    self.app.stdout.write(result.get())
                    completed.append(result)
            results = [result for result in results if result not in completed]
            if not results:
                break
        self.app.stdout.write('-------------------------\n')

    def add(self, name):
        instance_type = self.get_instance_type()
        image = self.get_image(return_key=True)
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

        suffix = raw_input('Optional short suffix (i.e. www,db,lb,mq)? ')

        build = OrderedDict()
        build['Size'] = instance_type
        build['Image'] = image
        build['Key'] = key.name
        build['SecurityGroups'] = security_groups

        if hasattr(zone, 'name'):
            build['Zone'] = zone.name

        if user_data:
            build['UserData'] = user_data

        if suffix:
            build['Suffix'] = suffix

        if upgrade_option != 'Skip Step':
            build['Upgrade'] = upgrade_option

        if group_option != 'Skip Step':
            build['Group'] = group_option

        if bundle_option != 'Skip Step':
            build['Pip'] = bundle_option

        config.builds[name] = build
        config.save()
