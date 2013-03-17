import logging
import os

import paramiko

from commands import InstanceCommand
from mixins import SureCheckMixin


class EasyInstall(InstanceCommand, SureCheckMixin):
    "Python easy_install a package group on a remote ec2 instance."

    log = logging.getLogger(__name__)

    def take_action(self, parsed_args):
        instance = self.get_instance(parsed_args.name, parsed_args.arg_is_id)
        if not self.app.cparser.has_option('Key Dir', 'keydir'):
            raise RuntimeError('No keydir set!')
        keydir = self.app.cparser.get('Key Dir', 'keydir')
        if keydir[-1:] == '/':
            keydir = keydir[:-1]
        package = raw_input('Enter name of package to easy_install: ')
        if not package or not self.app.cparser.has_option('Packages', package):
            raise RuntimeError('Package not found!')
        packages = self.app.cparser.get('Packages', package)

        if instance and packages and self.sure_check():
            cmd = 'sudo easy_install %s' % packages
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(instance.public_dns_name, username='ubuntu', key_filename='%s/%s.pem' % (keydir, instance.key_name))
            stdin, stdout, stderr = ssh.exec_command(cmd)
            for line in stdout.readlines():
                self.app.stdout.write(line)
            ssh.close()


class GroupInstall(InstanceCommand, SureCheckMixin):
    "Install a group of packages on a remote ec2 instance."

    log = logging.getLogger(__name__)

    def get_preseeds(self, packages):
        preseeds = []
        package_list = packages.split(' ')
        for package in package_list:
            if not self.app.cparser.has_section('%s.debconf' % package):
                continue
            options = self.app.cparser.options('%s.debconf' % package)
            if options:
                for option in options:
                    preseeds.append(self.app.cparser.get('%s.debconf' % package, option))
        return preseeds


    def take_action(self, parsed_args):
        instance = self.get_instance(parsed_args.name, parsed_args.arg_is_id)
        if not self.app.cparser.has_option('Key Dir', 'keydir'):
            raise RuntimeError('No keydir set!')
        keydir = self.app.cparser.get('Key Dir', 'keydir')
        if keydir[-1:] == '/':
            keydir = keydir[:-1]
        group = raw_input('Enter name of group to install: ')
        if not group or not self.app.cparser.has_option('Groups', group):
            raise RuntimeError('Group not found!')
        packages = self.app.cparser.get('Groups', group)
        packages = packages.split(' ')

        if instance and packages and self.sure_check():
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(instance.public_dns_name, username='ubuntu', key_filename='%s/%s.pem' % (keydir, instance.key_name))

            for package in packages:
                if not self.app.cparser.has_option('Packages', package):
                    continue
                package_names = self.app.cparser.get('Packages', package)
                cmd = 'apt-get -y install %s' % package_names
                preseeds = self.get_preseeds(package_names)
                if preseeds:
                    stdin, stdout, stderr = ssh.exec_command('cat << EOF | sudo debconf-set-selections\n%s\nEOF' % '\n'.join(preseeds))
                    stdin, stdout, stderr = ssh.exec_command('sudo su -c "DEBIAN_FRONTEND=noninteractive; %s"' % cmd)
                else:
                    stdin, stdout, stderr = ssh.exec_command('sudo %s' % cmd)
                for line in stdout.readlines():
                    self.app.stdout.write(line)
            ssh.close()


class PackageInstall(InstanceCommand, SureCheckMixin):
    "Install a package on a remote ec2 instance."

    log = logging.getLogger(__name__)

    def get_preseeds(self, packages):
        preseeds = []
        package_list = packages.split(' ')
        for package in package_list:
            if not self.app.cparser.has_section('%s.debconf' % package):
                continue
            options = self.app.cparser.options('%s.debconf' % package)
            if options:
                for option in options:
                    preseeds.append(self.app.cparser.get('%s.debconf' % package, option))
        return preseeds


    def take_action(self, parsed_args):
        instance = self.get_instance(parsed_args.name, parsed_args.arg_is_id)
        if not self.app.cparser.has_option('Key Dir', 'keydir'):
            raise RuntimeError('No keydir set!')
        keydir = self.app.cparser.get('Key Dir', 'keydir')
        if keydir[-1:] == '/':
            keydir = keydir[:-1]
        package = raw_input('Enter name of package to install: ')
        if not package or not self.app.cparser.has_option('Packages', package):
            raise RuntimeError('Package not found!')
        package_names = self.app.cparser.get('Packages', package)

        if instance and package_names and self.sure_check():
            cmd = 'apt-get -y install %s' % package_names
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(instance.public_dns_name, username='ubuntu', key_filename='%s/%s.pem' % (keydir, instance.key_name))

            preseeds = self.get_preseeds(package_names)
            if preseeds:
                stdin, stdout, stderr = ssh.exec_command('cat << EOF | sudo debconf-set-selections\n%s\nEOF' % '\n'.join(preseeds))
                stdin, stdout, stderr = ssh.exec_command('sudo su -c "DEBIAN_FRONTEND=noninteractive; %s"' % cmd)
            else:
                stdin, stdout, stderr = ssh.exec_command('sudo %s' % cmd)
            for line in stdout.readlines():
                self.app.stdout.write(line)
            ssh.close()


class Script(InstanceCommand, SureCheckMixin):
    "Run a bash script on a remote ec2 instance."

    log = logging.getLogger(__name__)

    def get_dir(self, section, option):
        if not self.app.cparser.has_option(section, option):
            raise RuntimeError('No %s set!' % option)
        dir = self.app.cparser.get(section, option)
        if dir[-1:] == '/':
            dir = dir[:-1]
        return dir


    def take_action(self, parsed_args):
        instance = self.get_instance(parsed_args.name, parsed_args.arg_is_id)
        keydir = self.get_dir('Key Dir', 'keydir')
        scriptdir = self.get_dir('Script Dir', 'scriptdir')

        if instance:
            script_name = raw_input('Enter name of script: ')
            script = os.path.join(scriptdir, script_name)
            if not os.path.isfile(script):
                raise RuntimeError('Could not locate Script!')

            if self.sure_check():
                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                ssh.connect(instance.public_dns_name, username='ubuntu', key_filename='%s/%s.pem' % (keydir, instance.key_name))
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
                ssh.close()


class Upgrade(InstanceCommand, SureCheckMixin):
    "Update and Upgrade an ec2 instance."

    log = logging.getLogger(__name__)

    def take_action(self, parsed_args):
        instance = self.get_instance(parsed_args.name, parsed_args.arg_is_id)
        if not self.app.cparser.has_option('Key Dir', 'keydir'):
            raise RuntimeError('No keydir set!')
        keydir = self.app.cparser.get('Key Dir', 'keydir')
        if keydir[-1:] == '/':
            keydir = keydir[:-1]

        if instance and self.sure_check():
            cmd = 'sudo apt-get -y update; sudo apt-get -y upgrade'
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(instance.public_dns_name, username='ubuntu', key_filename='%s/%s.pem' % (keydir, instance.key_name))
            stdin, stdout, stderr = ssh.exec_command(cmd)
            for line in stdout.readlines():
                self.app.stdout.write(line)
            ssh.close()
