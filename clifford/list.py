import logging

from cliff.lister import Lister


class Images(Lister):
    "Show a list of images in ec2."

    log = logging.getLogger(__name__)

    def take_action(self, parsed_args):
        if not self.app.cparser.has_section('Images'):
            self.log.info('No Images available')
            return

        return (('Name', 'Description'),
                tuple(self.app.cparser.items('Images'))
               )


class Instances(Lister):
    "Show a list of instances in ec2."

    log = logging.getLogger(__name__)

    def take_action(self, parsed_args):
        reservations = self.app.ec2_conn.get_all_instances()
        boxes = []
        for res in reservations:
            for instance in res.instances:
                if instance.public_dns_name:
                    public_dns = instance.public_dns_name
                else:
                    public_dns = ''
                boxes.append((instance.tags.get('Name'),
                              instance.id,
                              instance.state,
                              instance.instance_type,
                              instance.root_device_type,
                              instance.architecture,
                              instance.placement,
                              public_dns))

        return (('Name', 'Id', 'State', 'Type', 'Root Device', 'Arch', 'Zone', 'Public DNS'),
                (box for box in boxes)
               )


class Keys(Lister):
    "Show a list of keys in ec2."

    log = logging.getLogger(__name__)

    def take_action(self, parsed_args):
        keys = self.app.ec2_conn.get_all_key_pairs()

        return (('Name', 'fingerprint'),
                ((key.name, key.fingerprint) for key in keys)
               )


class Owners(Lister):
    "Show a list of owners added to config."

    log = logging.getLogger(__name__)

    def take_action(self, parsed_args):
        if not self.app.cparser.has_section('Owners'):
            self.log.info('No Owners available')
            return

        return (('Name', 'ID'),
                tuple(self.app.cparser.items('Owners'))
               )


class SecurityGroups(Lister):
    "Show a list of security groups in ec2."

    log = logging.getLogger(__name__)

    def take_action(self, parsed_args):
        security_groups = self.app.ec2_conn.get_all_security_groups()

        return (('Name', 'Description'),
                ((group.name, group.description) for group in security_groups)
               )
