import getpass
import glob
import time

import paramiko

from commands import InstanceCommand, RemoteCommand, RemoteUserCommand
from mixins import PreseedMixin


class AptGetInstall(InstanceCommand, PreseedMixin):
    "Install packages on a remote ec2 instance."

    def take_action(self, parsed_args):
        instance = self.get_instance(parsed_args.name, parsed_args.arg_is_id)

        packages = raw_input('Enter name of packages to install: ')
        if not packages:
            raise RuntimeError('No packages specified!')

        if self.sure_check():
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(instance.public_dns_name, username='ubuntu', key_filename='%s/%s.pem' % (self.key_path, instance.key_name))

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


class BundleInstall(RemoteCommand):
    "Install a bundle on a remote ec2 instance."

    def take_action(self, parsed_args):
        instance = self.get_instance(parsed_args.name, parsed_args.arg_is_id)
        bundle = self.get_option('Bundles', parsed_args.option)

        if self.sure_check():
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(instance.public_dns_name, username='ubuntu', key_filename='%s/%s.pem' % (self.key_path, instance.key_name))

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


class CreateUser(RemoteUserCommand):
    "Run useradd and scp all public (*.pub) keys to the ec2 instance."

    def get_parser(self, prog_name):
        parser = super(CreateUser, self).get_parser(prog_name)
        parser.add_argument('--fullname', nargs='+')
        parser.add_argument('--password', nargs='+')
        return parser

    def take_action(self, parsed_args):
        instance = self.get_instance(parsed_args.name, parsed_args.arg_is_id)
        user = parsed_args.user

        keys = glob.glob('%s/*.pub' % self.key_path)
        if not keys:
            raise RuntimeError('No public keys found in key_path')

        password_salt = self.get_option('General', 'password_salt')

        if parsed_args.fullname:
            fullname = ' '.join(parsed_args.fullname)
        else:
            fullname = raw_input('Enter full name of user: ')
        if not fullname:
            raise RuntimeError('fullname not specified!')

        if parsed_args.password:
            password = ' '.join(parsed_args.password)
        else:
            password = getpass.getpass('Enter password: ')
        if not password:
            raise RuntimeError('password not specified')

        self.app.stdout.write('The following keys will be copied:\n')
        for key in keys:
            key = key[len(self.key_path) + 1:]
            self.app.stdout.write(key + '\n')

        if parsed_args.assume_yes or self.sure_check():
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(instance.public_dns_name, username='ubuntu', key_filename='%s/%s.pem' % (self.key_path, instance.key_name))

            contents = ''
            for key in keys:
                with open(key, 'r') as f:
                    contents += f.read()

            cmd = 'sudo useradd -m -g users -G sudo -c \'%s\' -s /bin/bash' % fullname
            if parsed_args.password:
                cmd += ' -p $(perl -e \'print crypt("%s", "%s")\')' % (password, password_salt)
            cmd += ' ' + user
            stdin, stdout, stderr = ssh.exec_command(cmd)
            self.printOutError(stdout, stderr)

            stdin, stdout, stderr = ssh.exec_command('sudo su -c "mkdir /home/%s/.ssh && chown %s:users /home/%s/.ssh && chmod 700 /home/%s/.ssh"' % (user, user, user, user))
            self.printOutError(stdout, stderr)

            stdin, stdout, stderr = ssh.exec_command('sudo su -c "cat << EOF > /home/%s/.ssh/authorized_keys\n%sEOF"' % (user, contents))
            self.printOutError(stdout, stderr)

            stdin, stdout, stderr = ssh.exec_command('sudo su -c "chown %s:users /home/%s/.ssh/authorized_keys; chmod 600 /home/%s/.ssh/authorized_keys"' % (user, user, user))
            self.printOutError(stdout, stderr)

            ssh.close()


class EasyInstall(RemoteCommand):
    "Python easy_install a bundle on a remote ec2 instance."

    def take_action(self, parsed_args):
        instance = self.get_instance(parsed_args.name, parsed_args.arg_is_id)
        bundle = self.get_option('Python Bundles', parsed_args.option)

        if parsed_args.assume_yes or self.sure_check():
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(instance.public_dns_name, username='ubuntu', key_filename='%s/%s.pem' % (self.key_path, instance.key_name))
            stdin, stdout, stderr = ssh.exec_command('sudo easy_install %s' % bundle)
            for line in stdout.readlines():
                if line.startswith('Installed') or line.startswith('Finished'):
                    self.app.stdout.write(line)
            ssh.close()


class GroupInstall(RemoteCommand):
    "Install a group of bundles on a remote ec2 instance."

    def take_action(self, parsed_args):
        instance = self.get_instance(parsed_args.name, parsed_args.arg_is_id)

        group = self.get_option('Groups', parsed_args.option)
        bundle_names = group.split(' ')

        if bundle_names and (parsed_args.assume_yes or self.sure_check()):
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(instance.public_dns_name, username='ubuntu', key_filename='%s/%s.pem' % (self.key_path, instance.key_name))

            has_error = False
            for bundle_name in bundle_names:
                if self.app.cparser.has_option('Bundles', bundle_name):
                    bundle = self.app.cparser.get('Bundles', bundle_name)
                else:
                    if bundle_name.startswith('&'):
                        cmd = 'remote group install -y'
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

                    if bundle_name.startswith('+'):
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
                    raise RuntimeError('Unable to continue...')
                time.sleep(5)
                self.app.stdout.write('Installed bundle %s\n' % bundle_name)
            ssh.close()


class PPAInstall(RemoteCommand):
    "Add a ppa and install the package."

    def take_action(self, parsed_args):
        instance = self.get_instance(parsed_args.name, parsed_args.arg_is_id)

        if not self.app.cparser.has_section('PPAs'):
            raise RuntimeError('No PPAs available')

        if parsed_args.option:
            package_name = parsed_args.option
        else:
            options = self.app.cparser.options('PPAs')
            package_name = self.question_maker('Select PPA', 'ppa', [{'text': item} for item in options])

        ppa_name = self.get_option('PPAs', package_name)
        if not ppa_name:
            raise RuntimeError('PPA Name not found')

        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(instance.public_dns_name, username='ubuntu', key_filename='%s/%s.pem' % (self.key_path, instance.key_name))

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


class Script(InstanceCommand):
    "Run a bash script on a remote ec2 instance."

    def get_parser(self, prog_name):
        parser = super(Script, self).get_parser(prog_name)
        parser.add_argument('--script')
        parser.add_argument('--user', default='ubuntu')
        parser.add_argument('--copy-only', action='store_true')
        return parser

    def take_action(self, parsed_args):
        instance = self.get_instance(parsed_args.name, parsed_args.arg_is_id)

        if parsed_args.script:
            script_name = parsed_args.script
            script = '%s/%s' % (self.script_path, parsed_args.script)
        else:
            scripts = glob.glob('%s/*.sh' % self.script_path)
            script_name = self.question_maker('Select script', 'script', [{'text': item[len(self.script_path) + 1:]} for item in scripts])
            script = '%s/%s' % (self.script_path, script_name)

        if parsed_args.assume_yes or self.sure_check():
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            if parsed_args.user == 'ubuntu':
                ssh.connect(instance.public_dns_name, username=parsed_args.user, key_filename='%s/%s.pem' % (self.key_path, instance.key_name))
            else:
                ssh.connect(instance.public_dns_name, username=parsed_args.user)

            with open(script, 'r') as f:
                contents = f.read()
                ssh.exec_command('cat << EOF > %s\n%s\nEOF' % (script_name, contents))

            if not parsed_args.copy_only:
                channel = ssh.get_transport().open_session()
                channel.settimeout(0.1)
                channel.input_enabled = True
                forward = paramiko.agent.AgentRequestHandler(channel)

                channel.exec_command('sh %s' % script_name)
                while True:
                    if channel.exit_status_ready():
                        break
                status = channel.recv_exit_status()
                self.app.stdout.write('Script status: %s\n' % status)

                channel.close()
                forward.close()

            ssh.close()


class Upgrade(InstanceCommand):
    "Update and upgrade an ec2 instance."

    def get_parser(self, prog_name):
        parser = super(Upgrade, self).get_parser(prog_name)
        parser.add_argument('--upgrade', action='store_true')
        parser.add_argument('--dist-upgrade', action='store_true')
        return parser

    def take_action(self, parsed_args):
        instance = self.get_instance(parsed_args.name, parsed_args.arg_is_id)

        if parsed_args.assume_yes or self.sure_check():
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(instance.public_dns_name, username='ubuntu', key_filename='%s/%s.pem' % (self.key_path, instance.key_name))

            has_error = False
            stdin, stdout, stderr = ssh.exec_command('sudo apt-get -y update')
            for line in stderr.readlines():
                if line.startswith('E: '):
                    self.app.stdout.write(line)
                    has_error = True
            if has_error:
                raise RuntimeError("Unable to continue...")
            time.sleep(5)
            self.app.stdout.write('UPDATED\n')

            stdin, stdout, stderr = ssh.exec_command('sudo apt-get -s upgrade')
            string_list = ['The following packages have been kept back:', 'The following packages will be upgraded:']
            for line in stdout.readlines():
                if line.rstrip() in string_list or line.startswith('  '):
                    self.app.stdout.write(line)
            time.sleep(5)

            if not parsed_args.dist_upgrade:
                if parsed_args.upgrade:
                    upgrade = 'y'
                else:
                    upgrade = raw_input('Do you want to upgrade? ')
                if upgrade.lower() in ['y', 'yes']:
                    stdin, stdout, stderr = ssh.exec_command('sudo su -c "env DEBIAN_FRONTEND=noninteractive apt-get -y -o DPkg::Options::=--force-confnew upgrade"')
                    for line in stderr.readlines():
                        if line.startswith('E: '):
                            self.app.stdout.write(line)
                            has_error = True
                    if has_error:
                        raise RuntimeError("Unable to continue...")
                    time.sleep(5)
                    self.app.stdout.write('UPGRADED\n')

            if parsed_args.upgrade:
                dist_upgrade = 'n'
            elif parsed_args.dist_upgrade:
                dist_upgrade = 'y'
            else:
                dist_upgrade = raw_input('Do you want to dist-upgrade? ')

            if dist_upgrade.lower() in ['y', 'yes']:
                stdin, stdout, stderr = ssh.exec_command('sudo su -c "env DEBIAN_FRONTEND=noninteractive apt-get -y -o DPkg::Options::=--force-confnew dist-upgrade"')
                for line in stderr.readlines():
                    if line.startswith('E: '):
                        self.app.stdout.write(line)
                        has_error = True
                if has_error:
                    raise RuntimeError("Unable to continue...")
                time.sleep(5)
                self.app.stdout.write('DIST-UPGRADED\n')

            ssh.close()

            if parsed_args.upgrade or parsed_args.dist_upgrade:
                reboot = 'y'
            else:
                reboot = raw_input('Do you want to reboot? ')

            if reboot.lower() in ['y', 'yes']:
                time.sleep(5)
                self.app.stdout.write('Rebooting...\n')
                instance.reboot()
                time.sleep(20)
