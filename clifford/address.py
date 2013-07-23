import os
import time

import paramiko

from commands import BaseCommand
from main import config


class Associate(BaseCommand):
    "Associate an Elastic IP with an ec2 instance."

    def get_parser(self, prog_name):
        parser = super(Associate, self).get_parser(prog_name)
        parser.add_argument('--id', dest='arg_is_id', action='store_true')
        parser.add_argument('-e', '--etc-hosts', action='store_true')
        parser.add_argument('inst_name')
        return parser

    def take_action(self, parsed_args):
        instance = self.get_instance(parsed_args.inst_name, parsed_args.arg_is_id)

        addresses = [address for address in self.app.ec2_conn.get_all_addresses() if not address.instance_id]
        if not instance or not addresses:
            raise RuntimeError('Need both an instance and an address!')
        addresses = [{'text': address.public_ip, 'obj': address} for address in addresses]
        address = self.question_maker('Available IP Addresses', 'address', addresses)

        if self.sure_check():
            self.app.stdout.write('Attaching to Elastic IP...\n')
            address.associate(instance.id)

        if parsed_args.etc_hosts and 'Domain' in config:
            time.sleep(10)
            instance = self.get_instance(parsed_args.inst_name, parsed_args.arg_is_id)
            login = instance.tags.get('Login', '')
            if not login:
                raise RuntimeError('No Login tag found!')
            self.app.stdout.write('Updating Hostname on %s...\n' % parsed_args.inst_name)
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(instance.public_dns_name, username=login, key_filename=os.path.join(config.aws_key_path, instance.key_name + ".pem"))
            stdin, stdout, stderr = ssh.exec_command('sudo su -c "echo %s > /etc/hostname && hostname -F /etc/hostname"' % parsed_args.inst_name)
            fqdn = '%s.%s' % (parsed_args.inst_name, config['Domain'])
            stdin, stdout, stderr = ssh.exec_command('sudo su -c "echo \'\n### CLIFFORD\n%s\t%s\t%s\' >> /etc/hosts"' % (address.public_ip, fqdn, parsed_args.inst_name))
            ssh.close()


class Disassociate(BaseCommand):
    "Disassociate an Elastic IP with an ec2 instance."

    def get_parser(self, prog_name):
        parser = super(Disassociate, self).get_parser(prog_name)
        parser.add_argument('--id', dest='arg_is_id', action='store_true')
        parser.add_argument('inst_name')
        return parser

    def take_action(self, parsed_args):
        instance = self.get_instance(parsed_args.inst_name, parsed_args.arg_is_id)
        addresses = [address for address in self.app.ec2_conn.get_all_addresses() if address.instance_id == instance.id]
        if not addresses:
            raise RuntimeError('No attached addresses found!')
        address = addresses[0]

        if self.sure_check():
            self.app.stdout.write('Disassociating Elastic IP...\n')
            address.disassociate()


class Allocate(BaseCommand):
    "Allocate an Elastic IP."

    def take_action(self, parsed_args):
        if self.sure_check():
            self.app.stdout.write('Allocating Elastic IP...\n')
            address = self.app.ec2_conn.allocate_address()
            self.app.stdout.write('%s\n' % address)


class Release(BaseCommand):
    "Release an Elastic IP."

    def take_action(self, parsed_args):
        addresses = [address for address in self.app.ec2_conn.get_all_addresses() if not address.instance_id]
        if not addresses:
            raise RuntimeError('No unattached addresses found!')

        addresses = [{'text': address.public_ip, 'obj': address} for address in addresses]
        address = self.question_maker('Unattached IP Addresses', 'address', addresses)

        if self.sure_check():
            self.app.stdout.write('Releasing Elastic IP...\n')
            address.release()
