import paramiko

from commands import BaseCommand, InstanceCommand


class Associate(InstanceCommand):
    "Associate an Elastic IP with an ec2 instance."

    def take_action(self, parsed_args):
        instance = self.get_instance(parsed_args.name, parsed_args.arg_is_id)

        addresses = [address for address in self.app.ec2_conn.get_all_addresses() if not address.instance_id]
        if not instance or not addresses:
            raise RuntimeError('Need both an instance and an address!')
        addresses = [{'text': address.public_ip, 'obj': address} for address in addresses]
        address = self.question_maker('Available IP Addresses', 'address', addresses)

        if self.sure_check():
            self.app.stdout.write('Attaching to Elastic IP...\n')
            address.associate(instance.id)

        if self.app.cparser.has_option('General', 'domain_name'):
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(instance.public_dns_name, username='ubuntu', key_filename='%s/%s.pem' % (self.key_path, instance.key_name))
            stdin, stdout, stderr = ssh.exec_command('sudo su -c "echo %s > /etc/hostname && hostname -F /etc/hostname"' % parsed_args.name)
            fqdn = '%s.%s' % (parsed_args.name, self.app.cparser.get('General', 'domain_name'))
            stdin, stdout, stderr = ssh.exec_command('sudo su -c "echo \'\n### CLIFFORD\n%s\t%s\t%s\' >> /etc/hosts"' % (address.public_ip, fqdn, parsed_args.name))
            ssh.close()


class Disassociate(BaseCommand):
    "Disassociate an Elastic IP with an ec2 instance."

    def take_action(self, parsed_args):
        addresses = [address for address in self.app.ec2_conn.get_all_addresses() if address.instance_id]
        if not addresses:
            raise RuntimeError('No attached addresses found!')
        addresses = [{'text': address.public_ip, 'obj': address} for address in addresses]
        address = self.question_maker('Attached IP Addresses', 'address', addresses)

        if self.sure_check():
            self.app.stdout.write('Disassociating Elastic IP...\n')
            address.disassociate()


class Allocate(BaseCommand):
    "Allocate an Elastic IP."

    def take_action(self, parsed_args):
        if self.sure_check():
            self.app.stdout.write('Allocating Elastic IP...\n')
            self.app.ec2_conn.allocate_address()


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
