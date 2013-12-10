import glob
import time
from subprocess import call

import paramiko

from commands import BaseCommand
from main import config
from mixins import PreseedMixin


class AddAptInstall(BaseCommand):
    "Add an apt repo and install a package from it."

    def get_parser(self, prog_name):
        parser = super(AddAptInstall, self).get_parser(prog_name)
        parser.add_argument('--id', dest='arg_is_id', action='store_true')
        parser.add_argument('name')
        parser.add_argument('option')
        return parser

    def take_action(self, parsed_args):
        instance = self.get_instance(parsed_args.name, parsed_args.arg_is_id)
        section = 'Apt:%s' % parsed_args.option

        if section not in config:
            raise RuntimeError('No apt repo named %s!' % parsed_args.option)
        options = config[section]

        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(instance.public_dns_name, username=self.get_user(instance), key_filename='%s/%s.pem' % (config.aws_key_path, instance.key_name))

        if 'keyserver' in options:
            stdin, stdout, stderr = ssh.exec_command('sudo apt-key adv --keyserver keyserver.ubuntu.com --recv %s 2>&1' % options['keyserver'])
            self.printOutError(stdout, stderr)
        elif 'publickey' in options:
            key = config[section]['publickey']
            stdin, stdout, stderr = ssh.exec_command('wget %s 2>&1' % key)
            self.printOutError(stdout, stderr)
            time.sleep(2)
            stdin, stdout, stderr = ssh.exec_command('sudo apt-key add %s 2>&1' % key.split('/').pop())
            self.printOutError(stdout, stderr)
        else:
            raise RuntimeError('Invalid apt section!')

        package = config[section]['package']
        time.sleep(5)
        stdin, stdout, stderr = ssh.exec_command('sudo su -c "echo \'deb %s\' > /etc/apt/sources.list.d/%s.list"' % (config[section]['deb'], package))

        stdin, stdout, stderr = ssh.exec_command('sudo apt-get -y update 2>&1')
        self.printOutError(stdout, stderr)
        time.sleep(5)
        self.app.stdout.write('UPDATED\n')

        cmd = 'apt-get -y install %s' % package
        stdin, stdout, stderr = ssh.exec_command('sudo su -c "env DEBIAN_FRONTEND=noninteractive %s 2>&1"' % cmd)
        self.printOutError(stdout, stderr)

        ssh.close()


class AptGetInstall(BaseCommand, PreseedMixin):
    "Install packages on a remote ec2 instance."

    def get_parser(self, prog_name):
        parser = super(AptGetInstall, self).get_parser(prog_name)
        parser.add_argument('--id', dest='arg_is_id', action='store_true')
        parser.add_argument('name')
        return parser

    def take_action(self, parsed_args):
        instance = self.get_instance(parsed_args.name, parsed_args.arg_is_id)

        packages = raw_input('Enter name of packages to install: ')
        if not packages:
            raise RuntimeError('No packages specified!')

        if self.sure_check():
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(instance.public_dns_name, username=self.get_user(instance), key_filename='%s/%s.pem' % (config.aws_key_path, instance.key_name))

            preseeds = self.get_preseeds(packages)
            cmd = 'apt-get -y install %s' % packages
            if preseeds:
                stdin, stdout, stderr = ssh.exec_command('cat << EOF | sudo debconf-set-selections\n%s\nEOF' % '\n'.join(preseeds))
                stdin, stdout, stderr = ssh.exec_command('sudo su -c "env DEBIAN_FRONTEND=noninteractive %s"' % cmd)
            else:
                stdin, stdout, stderr = ssh.exec_command('sudo %s' % cmd)
            for line in stdout.readlines():
                if any([item in line for item in ['Note, selecting', 'is already the newest version']]):
                    self.app.stdout.write(line)
            has_error = False
            for line in stderr.readlines():
                if line.startswith('E: '):
                    self.app.stdout.write(line)
                    has_error = True
            if not has_error:
                self.app.stdout.write('Installed %s\n' % packages)
            ssh.close()


class BundleInstall(BaseCommand):
    "Install a bundle on a remote ec2 instance."

    def get_parser(self, prog_name):
        parser = super(BundleInstall, self).get_parser(prog_name)
        parser.add_argument('--id', dest='arg_is_id', action='store_true')
        parser.add_argument('name')
        parser.add_argument('option')
        return parser

    def take_action(self, parsed_args):
        instance = self.get_instance(parsed_args.name, parsed_args.arg_is_id)
        bundle = config.bundles[parsed_args.option]

        if self.sure_check():
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(instance.public_dns_name, username=self.get_user(instance), key_filename='%s/%s.pem' % (config.aws_key_path, instance.key_name))

            preseeds = self.get_preseeds(bundle)
            cmd = 'apt-get -y install %s' % bundle
            if preseeds:
                stdin, stdout, stderr = ssh.exec_command('cat << EOF | sudo debconf-set-selections\n%s\nEOF' % '\n'.join(preseeds))
                stdin, stdout, stderr = ssh.exec_command('sudo su -c "env DEBIAN_FRONTEND=noninteractive %s"' % cmd)
            else:
                stdin, stdout, stderr = ssh.exec_command('sudo %s' % cmd)
            for line in stdout.readlines():
                if 'is already the newest version' in line:
                    self.app.stdout.write(line)
            has_error = False
            for line in stderr.readlines():
                if line.startswith('E: '):
                    self.app.stdout.write(line)
                    has_error = True
            if not has_error:
                self.app.stdout.write('Installed bundle %s\n' % parsed_args.option)
            ssh.close()


class AddUser(BaseCommand):
    "Run useradd and scp all public (*.pub) keys to the ec2 instance."

    def get_parser(self, prog_name):
        parser = super(AddUser, self).get_parser(prog_name)
        parser.add_argument('-y', dest='assume_yes', action='store_true')
        parser.add_argument('--no-keys', action='store_true')
        parser.add_argument('--fullname', nargs='+')
        parser.add_argument('--group')
        parser.add_argument('--id', dest='arg_is_id', action='store_true')
        parser.add_argument('name')
        parser.add_argument('user')
        return parser

    def take_action(self, parsed_args):
        instance = self.get_instance(parsed_args.name, parsed_args.arg_is_id)
        user = parsed_args.user

        keys = glob.glob('%s/*.pub' % config.pub_key_path)
        if not keys:
            raise RuntimeError('No public keys found in key_path!')

        if parsed_args.fullname:
            fullname = ' '.join(parsed_args.fullname)
        else:
            fullname = raw_input('Enter full name of user: ')
        if not fullname:
            raise RuntimeError('fullname not specified!')

        if not parsed_args.no_keys:
            self.app.stdout.write('The following keys will be copied:\n')
            for key in keys:
                key = key[len(config.pub_key_path) + 1:]
                self.app.stdout.write(key + '\n')

        if parsed_args.assume_yes or self.sure_check():
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(instance.public_dns_name, username=self.get_user(instance), key_filename='%s/%s.pem' % (config.aws_key_path, instance.key_name))

            contents = ''
            for key in keys:
                with open(key, 'r') as f:
                    contents += f.read()

            self.app.stdout.write('Creating user, make sure to set password on first login.\n')
            cmd = 'sudo adduser --disabled-password'
            if parsed_args.group:
                cmd += ' --ingroup %s' % parsed_args.group
            cmd += ' --gecos "%s" %s' % (fullname, user)
            stdin, stdout, stderr = ssh.exec_command(cmd)
            self.printOutError(stdout, stderr)

            if not parsed_args.no_keys:
                stdin, stdout, stderr = ssh.exec_command('sudo su -c "mkdir /home/%s/.ssh && chown %s:users /home/%s/.ssh && chmod 700 /home/%s/.ssh"' % (user, user, user, user))
                self.printOutError(stdout, stderr)

                stdin, stdout, stderr = ssh.exec_command('sudo su -c "cat << EOF > /home/%s/.ssh/authorized_keys\n%sEOF"' % (user, contents))
                self.printOutError(stdout, stderr)

                stdin, stdout, stderr = ssh.exec_command('sudo su -c "chown %s:users /home/%s/.ssh/authorized_keys; chmod 600 /home/%s/.ssh/authorized_keys"' % (user, user, user))
                self.printOutError(stdout, stderr)

            ssh.close()


class GroupInstall(BaseCommand):
    "Install a group of bundles on a remote ec2 instance."

    def get_parser(self, prog_name):
        parser = super(GroupInstall, self).get_parser(prog_name)
        parser.add_argument('-y', dest='assume_yes', action='store_true')
        parser.add_argument('--id', dest='arg_is_id', action='store_true')
        parser.add_argument('name')
        parser.add_argument('option')
        return parser

    def take_action(self, parsed_args):
        instance = self.get_instance(parsed_args.name, parsed_args.arg_is_id)

        group = config.groups[parsed_args.option]
        bundle_names = group.split(' ')

        if bundle_names and (parsed_args.assume_yes or self.sure_check()):
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(instance.public_dns_name, username=self.get_user(instance), key_filename='%s/%s.pem' % (config.aws_key_path, instance.key_name))

            has_error = False
            for bundle_name in bundle_names:
                if bundle_name in config.bundles:
                    bundle = config.bundles[bundle_name]
                else:
                    if bundle_name.startswith('&'):
                        cmd = 'remote group install -y'
                        cmd += ' --id %s' % instance.id
                        cmd += ' ' + bundle_name[1:]
                        self.app.run_subcommand(cmd.split(' '))
                        time.sleep(5)
                        continue
                    elif bundle_name.startswith('+'):
                        cmd = 'remote add-apt install'
                        cmd += ' --id %s' % instance.id
                        cmd += ' ' + bundle_name[1:]
                        self.app.run_subcommand(cmd.split(' '))
                        time.sleep(5)
                        continue
                    elif bundle_name.startswith('@'):
                        cmd = 'remote ppa install -y'
                        cmd += ' --id %s' % instance.id
                        cmd += ' ' + bundle_name[1:]
                        self.app.run_subcommand(cmd.split(' '))
                        time.sleep(5)
                        continue

                    if bundle_name.startswith('$'):
                        bundle = bundle_name[1:]
                    else:
                        self.app.stdout.write('No bundle named %s\n' % bundle_name)
                        continue

                preseeds = self.get_preseeds(bundle)
                cmd = 'apt-get -y install %s' % bundle
                if preseeds:
                    stdin, stdout, stderr = ssh.exec_command('cat << EOF | sudo debconf-set-selections\n%s\nEOF' % '\n'.join(preseeds))
                    stdin, stdout, stderr = ssh.exec_command('sudo su -c "env DEBIAN_FRONTEND=noninteractive %s"' % cmd)
                else:
                    stdin, stdout, stderr = ssh.exec_command('sudo %s' % cmd)
                for line in stdout.readlines():
                    if any([item in line for item in ['Note, selecting', 'is already the newest version']]):
                        self.app.stdout.write(line)
                for line in stderr.readlines():
                    if line.startswith('E: '):
                        self.app.stdout.write(line)
                        has_error = True
                if has_error:
                    ssh.close()
                    raise RuntimeError('Unable to continue!')
                time.sleep(5)
                self.app.stdout.write('Installed bundle %s\n' % bundle_name)
            ssh.close()


class PipInstall(BaseCommand):
    "Python pip install a bundle on a remote ec2 instance."

    def get_parser(self, prog_name):
        parser = super(PipInstall, self).get_parser(prog_name)
        parser.add_argument('-y', dest='assume_yes', action='store_true')
        parser.add_argument('--id', dest='arg_is_id', action='store_true')
        parser.add_argument('name')
        parser.add_argument('option')
        return parser

    def take_action(self, parsed_args):
        instance = self.get_instance(parsed_args.name, parsed_args.arg_is_id)
        bundle = config.python_bundles[parsed_args.option]

        if parsed_args.assume_yes or self.sure_check():
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(instance.public_dns_name, username=self.get_user(instance), key_filename='%s/%s.pem' % (config.aws_key_path, instance.key_name))
            stdin, stdout, stderr = ssh.exec_command('sudo pip install %s' % bundle)
            for line in stdout.readlines():
                if line.startswith('Installed') or line.startswith('Finished'):
                    self.app.stdout.write(line)
            ssh.close()


class PPAInstall(BaseCommand):
    "Add a ppa and install the package."

    def get_parser(self, prog_name):
        parser = super(PPAInstall, self).get_parser(prog_name)
        parser.add_argument('--id', dest='arg_is_id', action='store_true')
        parser.add_argument('name')
        parser.add_argument('option')
        return parser

    def take_action(self, parsed_args):
        instance = self.get_instance(parsed_args.name, parsed_args.arg_is_id)

        if 'PPAs' not in config:
            raise RuntimeError('No PPAs available!')

        if parsed_args.option:
            package_name = parsed_args.option
        else:
            options = config['PPAs']
            package_name = self.question_maker('Select PPA', 'ppa', [{'text': item} for item in options])

        ppa_name = config['PPAs'][package_name]
        if not ppa_name:
            raise RuntimeError('PPA Name not found!')

        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(instance.public_dns_name, username=self.get_user(instance), key_filename='%s/%s.pem' % (config.aws_key_path, instance.key_name))

        stdin, stdout, stderr = ssh.exec_command('sudo add-apt-repository -y ppa:%s 2>&1' % ppa_name)
        self.printOutError(stdout, stderr)
        time.sleep(5)

        stdin, stdout, stderr = ssh.exec_command('sudo apt-get -y update 2>&1')
        self.printOutError(stdout, stderr)
        time.sleep(5)
        self.app.stdout.write('UPDATED\n')

        cmd = 'apt-get -y install %s' % package_name
        stdin, stdout, stderr = ssh.exec_command('sudo su -c "env DEBIAN_FRONTEND=noninteractive %s 2>&1"' % cmd)
        self.printOutError(stdout, stderr)

        ssh.close()


class CopyFile(BaseCommand):
    "Copy a file to a remote ec2 instance."

    def get_parser(self, prog_name):
        parser = super(CopyFile, self).get_parser(prog_name)
        parser.add_argument('-y', dest='assume_yes', action='store_true')
        parser.add_argument('--user')
        parser.add_argument('--id', dest='arg_is_id', action='store_true')
        parser.add_argument('name')
        parser.add_argument('file_name', nargs='+')
        return parser

    def take_action(self, parsed_args):
        instance = self.get_instance(parsed_args.name, parsed_args.arg_is_id)

        try:
            if parsed_args.user:
                retcode = call('scp %s %s@%s:~' % (' '.join(parsed_args.file_name), parsed_args.user, instance.public_dns_name), shell=True)
            else:
                retcode = call('scp -i %s/%s.pem %s %s@%s:~' % (config.aws_key_path, instance.key_name, ' '.join(parsed_args.file_name), self.get_user(instance), instance.public_dns_name), shell=True)

            if retcode < 0:
                self.app.stdout.write("Child was terminated by signal %s\n" % -retcode)
            else:
                self.app.stderr.write("Child returned %s\n" % retcode)

        except OSError as e:
            self.app.stderr.write("Execution failed: %s\n" % e)


class Script(BaseCommand):
    "Run a bash script on a remote ec2 instance."

    def get_parser(self, prog_name):
        parser = super(Script, self).get_parser(prog_name)
        parser.add_argument('-y', dest='assume_yes', action='store_true')
        parser.add_argument('--script')
        parser.add_argument('--user')
        parser.add_argument('--format')
        parser.add_argument('--copy-only', action='store_true')
        parser.add_argument('--id', dest='arg_is_id', action='store_true')
        parser.add_argument('name')
        return parser

    def take_action(self, parsed_args):
        instance = self.get_instance(parsed_args.name, parsed_args.arg_is_id)
        script_path = config.script_path

        if parsed_args.script:
            script_name = parsed_args.script
            script = '%s/%s' % (script_path, parsed_args.script)
        else:
            scripts = glob.glob('%s/*.sh' % script_path)
            script_name = self.question_maker('Select script', 'script', [{'text': item[len(script_path) + 1:]} for item in scripts])
            script = '%s/%s' % (script_path, script_name)

        if parsed_args.assume_yes or self.sure_check():
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            if parsed_args.user:
                ssh.connect(instance.public_dns_name, username=parsed_args.user)
            else:
                ssh.connect(instance.public_dns_name, username=self.get_user(instance), key_filename='%s/%s.pem' % (config.aws_key_path, instance.key_name))

            with open(script, 'r') as f:
                contents = f.read()
                if parsed_args.format:
                    format_args = parsed_args.format.split(',')
                    contents = contents % tuple(format_args)
                ssh.exec_command('cat << EOF > %s\n%s\nEOF' % (script_name, contents))
                ssh.exec_command('chmod 744 %s' % script_name)

            if not parsed_args.copy_only:
                channel = ssh.get_transport().open_session()
                channel.settimeout(0.1)
                channel.input_enabled = True
                forward = paramiko.agent.AgentRequestHandler(channel)

                if parsed_args.user:
                    channel.exec_command('/home/%s/%s' % (parsed_args.user, script_name))
                else:
                    channel.exec_command('/home/%s/%s' % (self.get_user(instance), script_name))

                while True:
                    if channel.exit_status_ready():
                        break
                    time.sleep(10)
                status = channel.recv_exit_status()
                self.app.stdout.write('Script status: %s\n' % status)

                channel.close()
                forward.close()

            ssh.close()


class Update(BaseCommand):
    "Update an ec2 instance."

    def get_parser(self, prog_name):
        parser = super(Update, self).get_parser(prog_name)
        parser.add_argument('-y', dest='assume_yes', action='store_true')
        parser.add_argument('--id', dest='arg_is_id', action='store_true')
        parser.add_argument('name')
        return parser

    def take_action(self, parsed_args):
        instance = self.get_instance(parsed_args.name, parsed_args.arg_is_id)

        if parsed_args.assume_yes or self.sure_check():
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(instance.public_dns_name, username=self.get_user(instance), key_filename='%s/%s.pem' % (config.aws_key_path, instance.key_name))

            has_error = False
            stdin, stdout, stderr = ssh.exec_command('sudo apt-get -y update')
            for line in stderr.readlines():
                if line.startswith('E: '):
                    self.app.stdout.write(line)
                    has_error = True
            if has_error:
                raise RuntimeError("Unable to continue!")
            time.sleep(5)
            self.app.stdout.write('UPDATED\n')


class Upgrade(BaseCommand):
    "Update and upgrade an ec2 instance."

    def get_parser(self, prog_name):
        parser = super(Upgrade, self).get_parser(prog_name)
        parser.add_argument('-y', dest='assume_yes', action='store_true')
        parser.add_argument('--dry-run', action='store_true')
        parser.add_argument('--dist-upgrade', action='store_true')
        parser.add_argument('--reboot', action='store_true')
        parser.add_argument('--id', dest='arg_is_id', action='store_true')
        parser.add_argument('name')
        return parser

    def take_action(self, parsed_args):
        instance = self.get_instance(parsed_args.name, parsed_args.arg_is_id)

        if parsed_args.assume_yes or self.sure_check():
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(instance.public_dns_name, username=self.get_user(instance), key_filename='%s/%s.pem' % (config.aws_key_path, instance.key_name))

            if parsed_args.dry_run:
                cmd = 'sudo apt-get --dry-run %s'
            else:
                cmd = 'sudo su -c "env DEBIAN_FRONTEND=noninteractive apt-get -y -o DPkg::Options::=--force-confnew %s"'
            if parsed_args.dist_upgrade:
                cmd = cmd % 'dist-upgrade'
            else:
                cmd = cmd % 'upgrade'

            stdin, stdout, stderr = ssh.exec_command(cmd)
            string_list = ['The following packages have been kept back:', 'The following packages will be upgraded:']
            for line in stdout.readlines():
                if line.rstrip() in string_list or line.startswith('  '):
                    self.app.stdout.write(line)
                for line in stderr.readlines():
                    if line.startswith('E: '):
                        self.app.stdout.write(line)

            ssh.close()

            if parsed_args.reboot:
                time.sleep(5)
                self.app.stdout.write('Rebooting...\n')
                instance.reboot()
                time.sleep(30)
