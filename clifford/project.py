from collections import OrderedDict
from multiprocessing import Manager, Pool, Queue
import time

from activity import Task
from activity import launcher, upgrade
from commands import BaseCommand
from main import config


class Project(BaseCommand):
    "Launch and bootstrap a new ec2 instance"

    def get_parser(self, prog_name):
        parser = super(Project, self).get_parser(prog_name)
        parser.add_argument('-a', '--add', action='store_true')
        parser.add_argument('-r', '--remove', action='store_true')
        parser.add_argument('project_name')
        return parser

    def take_action(self, parsed_args):
        if parsed_args.add:
            if parsed_args.project_name in config.projects:
                raise RuntimeError('A project already exists by that name!')
            self.add(parsed_args.project_name)
            return

        if parsed_args.project_name not in config.projects:
            raise RuntimeError('Project not found!')

        if parsed_args.remove:
            del(config.projects[parsed_args.project_name])
            config.save()
            return

        project = config.projects[parsed_args.project_name]
        if 'Builds' not in project or not project['Builds']:
            raise RuntimeError('No Builds in project!')
        tag_name = raw_input('Enter Tag:Name Value (%s): ' % parsed_args.project_name)
        if not tag_name:
            tag_name = parsed_args.project_name
        if '[' in tag_name or ']' in tag_name:
            self.app.stdout.write('Clifford Tag Names may not include brackets')
            return

        if not self.sure_check():
            return

        total = sum(b['Num'] for b in project['Builds'])
        pool = Pool(processes=total)
        m = Manager()
        q = m.Queue(total)

        results = []
        counter = 0
        for project_build in project['Builds']:
            build = config.builds[project_build['Build']]
            image = config.images[build['Image']]
            kwargs = {
                'build_name': project_build['Build'],
                'build': build,
                'image': image,
                'project_name': parsed_args.project_name,
                'project': project,
                'num': project_build['Num'],
                'counter': counter,
                'q': q
            }
            results.append(pool.apply_async(launcher, [tag_name, config.aws_key_path, config.script_path], kwargs))
            counter += project_build['Num']
        launch_results = self.process_results(q, results)

        tasks = []
        for lr in launch_results:
            if lr.build.get('Upgrade', '') in ['upgrade', 'dist-upgrade']:
                for inst_id in lr.instance_ids:
                    tasks.append(Task(lr.build, lr.image, inst_id, []))
        self.run_activity(pool, upgrade, tasks)
        self.app.stdout.write('Upgrade Finished\n')

        '''
        instances = []
        for lr in launch_results:
            if lr.build.get('Upgrade', '') in ['upgrade', 'dist-upgrade']:
                reservations = self.app.ec2_conn.get_all_instances(instance_ids=lr.instance_ids)
                for res in reservations:
                    for inst in res.instances:
                        instances.append(inst)



        for lr in launch_results:
            reservations = self.app.ec2_conn.get_all_instances(instance_ids=lr.instance_ids)

            if 'Upgrade' in lr.build and lr.build['Upgrade'] in ['upgrade', 'dist-upgrade']:
                self.run_activity(lr.reservation, pool, upgrade, [lr.image['Login'], lr.build['Upgrade'], config.aws_key_path])

            if 'Group' in lr.build and lr.build['Group'] in config.groups:
                bundles = []
                self.get_bundles(lr.build['Group'], bundles)
                self.run_activity(reservation, pool, group_installer, [lr.image['Login'], bundles, config.aws_key_path])
                self.app.stdout.write('Group Installer Finished\n')
                time.sleep(10)

            if 'PyGroup' in lr.build and lr.build['PyGroup'] in config.python_bundles:
                python_packages = config.python_bundles[lr.build['PyGroup']]
                self.app.stdout.write('python: %s [%s]\n' % (lr.build['PyGroup'], python_packages))

                self.run_activity(reservation, pool, py_installer, [lr.image['Login'], python_packages, config.aws_key_path])
                self.app.stdout.write('Python Installer Finished\n')
                time.sleep(10)

            if 'Script' in lr.build:
                self.run_activity(reservation, pool, script_runner, [lr.image['Login'], os.path.join(config.script_path, lr.build['Script']), config.aws_key_path])
        '''

        pool.close()
        pool.join()

        '''
        instance = self.get_instance(parsed_args.name)
        if not instance:
            raise RuntimeError('Cannot find instance!')

        if 'user_name' in options:
            cmd = 'remote create user -y'
            if 'user_fullname' in options:
                cmd += ' --fullname %s' % options['user_fullname']
            else:
                cmd += ' --fullname %s' + options['user_name']
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

    def process_results(self, q, results):
        launch_results = []
        completed = []
        while results:
            time.sleep(20)
            for result in results:
                if result.ready():
                    launch_results.append(q.get())
                    self.app.stdout.write('-------------------------\n')
                    self.app.stdout.write(result.get().getvalue())
                    completed.append(result)
            results = [result for result in results if result not in completed]
            if not results:
                break
        self.app.stdout.write('-------------------------\n')
        return launch_results

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
        project = OrderedDict()
        project['Builds'] = []
        build_items = [{'text': 'Skip Step'}] + [{'text': bld} for bld in config.builds.keys()]
        while True:
            build = self.question_maker('Select Build', 'build', build_items, start_at=0)
            if not build:
                continue
            if build == 'Skip Step':
                break

            num = raw_input('How many instances? ')
            if not num.isdigit():
                raise RuntimeError('Invalid number!')

            _dict = OrderedDict()
            _dict['Build'] = build
            _dict['Num'] = int(num)
            project['Builds'].append(_dict)

        if project['Builds']:
            config.projects[name] = project
            config.save()
