import logging

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
