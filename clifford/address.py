import logging

from cliff.command import Command

from commands import InstanceCommand
from mixins import SingleBoxMixin


class Associate(InstanceCommand, SingleBoxMixin):
    "Associate an Elastic IP with an ec2 instance."

    log = logging.getLogger(__name__)

    def take_action(self, parsed_args):
        instance = self.get_box(parsed_args.name)
        addresses = [address for address in self.app.ec2_conn.get_all_addresses() if not address.instance_id]
        if instance and addresses:
            self.app.stdout.write('Available IP Addresses\n')
            self.app.stdout.write('----------------------\n')
            for index, item in enumerate(addresses):
                self.app.stdout.write('%s) %s\n' % (index, item.public_ip))
            address_choice = raw_input('Enter number of IP address: ')
            if not address_choice.isdigit() or int(address_choice) >= len(addresses):
                self.app.stdout.write('Not a valid IP address!\n')
                return
            address_choice = int(address_choice)
            ip_address = addresses[address_choice]
            self.app.stdout.write('Attaching to Elastic IP...\n')
            ip_address.associate(instance.id)


class Disassociate(Command):
    "Disassociate an Elastic IP with an ec2 instance."

    log = logging.getLogger(__name__)

    def take_action(self, parsed_args):
        addresses = [address for address in self.app.ec2_conn.get_all_addresses() if address.instance_id]
        if addresses:
            self.app.stdout.write('Attached IP Addresses\n')
            self.app.stdout.write('---------------------\n')
            for index, item in enumerate(addresses):
                self.app.stdout.write('%s) %s\n' % (index, item.public_ip))
            address_choice = raw_input('Enter number of IP address: ')
            if not address_choice.isdigit() or int(address_choice) >= len(addresses):
                self.app.stdout.write('Not a valid IP address!\n')
                return
            address_choice = int(address_choice)
            ip_address = addresses[address_choice]
            self.app.stdout.write('Disassociating Elastic IP...\n')
            ip_address.disassociate()


class Allocate(Command):
    "Allocate an Elastic IP."

    log = logging.getLogger(__name__)

    def take_action(self, parsed_args):
        self.app.stdout.write('Allocating Elastic IP...\n')
        self.app.ec2_conn.allocate_address()


class Release(Command):
    "Release an Elastic IP."

    log = logging.getLogger(__name__)

    def take_action(self, parsed_args):
        addresses = [address for address in self.app.ec2_conn.get_all_addresses() if not address.instance_id]
        if addresses:
            self.app.stdout.write('Unattached IP Addresses\n')
            self.app.stdout.write('-----------------------\n')
            for index, item in enumerate(addresses):
                self.app.stdout.write('%s) %s\n' % (index, item.public_ip))
            address_choice = raw_input('Enter number of IP address: ')
            if not address_choice.isdigit() or int(address_choice) >= len(addresses):
                self.app.stdout.write('Not a valid IP address!\n')
                return
            address_choice = int(address_choice)
            ip_address = addresses[address_choice]
            self.app.stdout.write('Releasing Elastic IP...\n')
            ip_address.release()
