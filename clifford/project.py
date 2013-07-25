from collections import OrderedDict
from multiprocessing import Pool, Queue
import time

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
            raise RuntimeError('No Builds in project')
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
        q = Queue(total)

        results = []
        counter = 0
        for project_build in project['Builds']:
            build = config.builds[project_build['Build']]
            kwargs = {
                'build_name': project_build['Build'],
                'build': build,
                'project_name': parsed_args.project_name,
                'project': project,
                'num': project_build['Num'],
                'counter': counter,
                'q': q
            }
            results.append(pool.apply_async(launcher, [config.aws_key_path, tag_name], kwargs))
            counter += project_build['Num']
        launch_results = self.process_results(q, results)


        for lr in launch_results:
            if 'Upgrade' in lr.build and lr.build['Upgrade'] in ['upgrade', 'dist-upgrade']:
                self.run_activity(lr.reservation, pool, upgrade, [lr.build['Login'], lr.build['Upgrade'], config.aws_key_path])

        '''
        if 'Group' in build and build['Group'] in config.groups:
            bundles = []
            self.get_bundles(build['Group'], bundles)
            self.run_activity(reservation, pool, group_installer, [build['Login'], bundles, config.aws_key_path])
            self.app.stdout.write('Group Installer Finished\n')
            time.sleep(10)

        if 'Pip' in build and build['Pip'] in config.python_bundles:
            python_packages = config.python_bundles[build['Pip']]
            self.app.stdout.write('python: %s [%s]\n' % (build['Pip'], python_packages))

            self.run_activity(reservation, pool, pip_installer, [build['Login'], python_packages, config.aws_key_path])
            self.app.stdout.write('Pip Installer Finished\n')
            time.sleep(10)

        if 'Script' in build:
            self.run_activity(reservation, pool, script_runner, [build['Login'], os.path.join(config.script_path, build['Script']), config.aws_key_path])
        '''

        pool.close()
        pool.join()

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

    def process_results(self, q, results):
        launch_results = []
        completed = []
        while results:
            time.sleep(20)
            for result in results:
                if result.ready():
                    launch_results.append(q.get())
                    self.app.stdout.write('-------------------------\n')
                    self.app.stdout.write('Result: %s\n' % result.get())
                    completed.append(result)
            results = [result for result in results if result not in completed]
            if not results:
                break
        self.app.stdout.write('-------------------------\n')
        return launch_results

    def run_activity(self, reservation, pool, func, arg_list):
        results = []
        for inst in reservation.instances:
            self.app.stdout.write('===>%s starting: %s\n' % (func.func_name, inst.id))
            results.append(pool.apply_async(func, [inst] + arg_list))


            self.app.stdout.write('Upgrade Finished\n')
            time.sleep(10)

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
