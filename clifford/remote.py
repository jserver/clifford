import logging
import os

import paramiko

from commands import InstanceCommand
from mixins import PreseedMixin


class AptGetInstall(InstanceCommand, PreseedMixin):
    "Install packages on a remote ec2 instance."

    def take_action(self, parsed_args):
        instance = self.get_instance(parsed_args.name, parsed_args.arg_is_id)
        key_path = self.get_option('Key Path', 'key_path')

        packages = raw_input('Enter name of packages to install: ')
        if not packages:
            raise RuntimeError('No packages specified!')

        if instance and self.sure_check():
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(instance.public_dns_name, username='ubuntu', key_filename='%s/%s.pem' % (key_path, instance.key_name))

            preseeds = self.get_preseeds(packages)
            cmd = 'apt-get -y install %s' % packages
            if preseeds:
                stdin, stdout, stderr = ssh.exec_command('cat << EOF | sudo debconf-set-selections\n%s\nEOF' % '\n'.join(preseeds))
                stdin, stdout, stderr = ssh.exec_command('sudo su -c "DEBIAN_FRONTEND=noninteractive; %s"' % cmd)
            else:
                stdin, stdout, stderr = ssh.exec_command('sudo %s' % cmd)
            for line in stdout.readlines():
                if any([x in line for x in ['Note, selecting', 'is already the newest version']]):
                    self.app.stdout.write(line)
            has_error = False
            for line in stderr.readlines():
                if line.startswith('E: '):
                    self.app.stdout.write(line)
                    has_error = True
            if not has_error:
                self.app.stdout.write('Installed %s\n' % packages)
            ssh.close()


class BundleInstall(InstanceCommand, PreseedMixin):
    "Install a bundle on a remote ec2 instance."

    def take_action(self, parsed_args):
        instance = self.get_instance(parsed_args.name, parsed_args.arg_is_id)
        key_path = self.get_option('Key Path', 'key_path')

        bundle_name = raw_input('Enter name of bundle to install: ')
        if not bundle_name or not self.app.cparser.has_option('Bundles', bundle_name):
            raise RuntimeError('Bundle not found!')
        bundle = self.app.cparser.get('Bundles', bundle_name)

        if instance and bundle and self.sure_check():
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(instance.public_dns_name, username='ubuntu', key_filename='%s/%s.pem' % (key_path, instance.key_name))

            preseeds = self.get_preseeds(bundle)
            cmd = 'apt-get -y install %s' % bundle
            if preseeds:
                stdin, stdout, stderr = ssh.exec_command('cat << EOF | sudo debconf-set-selections\n%s\nEOF' % '\n'.join(preseeds))
                stdin, stdout, stderr = ssh.exec_command('sudo su -c "DEBIAN_FRONTEND=noninteractive; %s"' % cmd)
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
                self.app.stdout.write('Installed bundle %s\n' % bundle_name)
            ssh.close()


class EasyInstall(InstanceCommand):
    "Python easy_install a bundle on a remote ec2 instance."

    def take_action(self, parsed_args):
        instance = self.get_instance(parsed_args.name, parsed_args.arg_is_id)
        key_path = self.get_option('Key Path', 'key_path')

        bundle = raw_input('Enter name of bundle to easy_install: ')
        if not bundle or not self.app.cparser.has_option('Python Bundles', bundle):
            raise RuntimeError('Bundle not found!')
        bundle = self.app.cparser.get('Python Bundles', bundle)

        if instance and bundle and self.sure_check():
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(instance.public_dns_name, username='ubuntu', key_filename='%s/%s.pem' % (key_path, instance.key_name))
            stdin, stdout, stderr = ssh.exec_command('sudo easy_install %s' % bundle)
            for line in stdout.readlines():
                self.app.stdout.write(line)
            ssh.close()


class GroupInstall(InstanceCommand, PreseedMixin):
    "Install a group of bundles on a remote ec2 instance."

    def take_action(self, parsed_args):
        instance = self.get_instance(parsed_args.name, parsed_args.arg_is_id)
        key_path = self.get_option('Key Path', 'key_path')

        group_name = raw_input('Enter name of group to install: ')
        if not group_name or not self.app.cparser.has_option('Groups', group_name):
            raise RuntimeError('Group not found!')
        group = self.app.cparser.get('Groups', group_name)
        bundle_names = group.split(' ')

        if instance and bundle_names and self.sure_check():
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(instance.public_dns_name, username='ubuntu', key_filename='%s/%s.pem' % (key_path, instance.key_name))

            has_error = False
            for bundle_name in bundle_names:
                if not self.app.cparser.has_option('Bundles', bundle_name):
                    continue
                bundle = self.app.cparser.get('Bundles', bundle_name)
                preseeds = self.get_preseeds(bundle)
                cmd = 'apt-get -y install %s' % bundle
                if preseeds:
                    stdin, stdout, stderr = ssh.exec_command('cat << EOF | sudo debconf-set-selections\n%s\nEOF' % '\n'.join(preseeds))
                    stdin, stdout, stderr = ssh.exec_command('sudo su -c "DEBIAN_FRONTEND=noninteractive; %s"' % cmd)
                else:
                    stdin, stdout, stderr = ssh.exec_command('sudo %s' % cmd)
                for line in stdout.readlines():
                    if any([x in line for x in ['Note, selecting', 'is already the newest version']]):
                        self.app.stdout.write(line)
                for line in stderr.readlines():
                    if line.startswith('E: '):
                        self.app.stdout.write(line)
                        has_error = True
                if has_error:
                    ssh.close()
                    raise RuntimeError("Unable to continue...")
                self.app.stdout.write('Installed bundle %s\n' % bundle_name)

            ssh.close()


class Script(InstanceCommand):
    "Run a bash script on a remote ec2 instance."

    def take_action(self, parsed_args):
        instance = self.get_instance(parsed_args.name, parsed_args.arg_is_id)
        key_path = self.get_option('Key Path', 'key_path')
        script_path = self.get_option('Script Path', 'script_path')

        if instance:
            script_name = raw_input('Enter name of script: ')
            script = os.path.join(script_path, script_name)
            if not os.path.isfile(script):
                raise RuntimeError('Could not locate Script!')

            if self.sure_check():
                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                ssh.connect(instance.public_dns_name, username='ubuntu', key_filename='%s/%s.pem' % (key_path, instance.key_name))
                with open(script, 'r') as f:
                    contents = f.read()
                    if contents[-1:] == '\n':
                        eof = 'EOF'
                    else:
                        eof = '\nEOF'
                    stdin, stdout, stderr = ssh.exec_command('cat << EOF > clifford_script.sh\n%s%s' % (contents, eof))
                stdin, stdout, stderr = ssh.exec_command('chmod 744 clifford_script.sh; ./clifford_script.sh')
                for line in stdout.readlines():
                    self.app.stdout.write(line)
                for line in stderr.readlines():
                    self.app.stdout.write('ERROR: %s' % line)
                ssh.close()


class Upgrade(InstanceCommand):
    "Update and Upgrade an ec2 instance."

    def take_action(self, parsed_args):
        instance = self.get_instance(parsed_args.name, parsed_args.arg_is_id)
        if not self.app.cparser.has_option('Key Path', 'key_path'):
            raise RuntimeError('No key_path set!')
        key_path = self.app.cparser.get('Key Path', 'key_path')
        if key_path[-1:] == '/':
            key_path = key_path[:-1]

        if instance and self.sure_check():
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(instance.public_dns_name, username='ubuntu', key_filename='%s/%s.pem' % (key_path, instance.key_name))

            has_error = False
            stdin, stdout, stderr = ssh.exec_command('sudo su -c "apt-get -y update"')
            for line in stderr.readlines():
                if line.startswith('E: '):
                    self.app.stdout.write(line)
                    has_error = True
            if has_error:
                raise RuntimeError("Unable to continue...")
            self.app.stdout.write('UPDATED\n')

            upgrade = raw_input('Do you want to upgrade? ')
            if upgrade.lower() in ['y', 'yes']:
                stdin, stdout, stderr = ssh.exec_command('sudo su -c "env DEBIAN_FRONTEND=noninteractive apt-get -y -o DPkg::Options::=--force-confnew upgrade"')
                for line in stderr.readlines():
                    if line.startswith('E: '):
                        self.app.stdout.write(line)
                        has_error = True
                if has_error:
                    raise RuntimeError("Unable to continue...")
                self.app.stdout.write('UPGRADED\n')

            dist_upgrade = raw_input('Do you want to dist-upgrade? ')
            if dist_upgrade.lower() in ['y', 'yes']:
                stdin, stdout, stderr = ssh.exec_command('sudo su -c "env DEBIAN_FRONTEND=noninteractive apt-get -y -o DPkg::Options::=--force-confnew dist-upgrade"')
                for line in stderr.readlines():
                    if line.startswith('E: '):
                        self.app.stdout.write(line)
                        has_error = True
                if has_error:
                    raise RuntimeError("Unable to continue...")
                self.app.stdout.write('DIST-UPGRADED\n')

            ssh.close()

            reboot = raw_input('Do you want to reboot? ')
            if reboot.lower() in ['y', 'yes']:
                self.app.stdout.write('Rebooting...\n')
                instance.reboot()
