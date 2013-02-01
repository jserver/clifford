import logging

from cliff.lister import Lister


class Addresses(Lister):
    "Show a list of IP addresses in ec2."

    log = logging.getLogger(__name__)

    def take_action(self, parsed_args):
        addresses = self.app.ec2_conn.get_all_addresses()

        return (('Public IP', 'Instance ID'),
                ((address.public_ip, address.instance_id) for address in addresses)
               )


class Images(Lister):
    "Show a list of images in ec2."

    log = logging.getLogger(__name__)

    def take_action(self, parsed_args):
        images = []
        if not self.app.cparser.has_section('Images') or not self.app.cparser.has_option('Images', 'images'):
            self.log.info('No Images available')
        else:
            images_str = self.app.cparser.get('Images', 'images')
            image_ids = images_str.split(',')
            if image_ids:
                images = [(image.id, image.name, image.description) for image in self.app.ec2_conn.get_all_images(image_ids=image_ids)]

        return (('Name', 'Description', 'Image ID'),
                tuple(images)
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
        owners = tuple()
        if self.app.cparser.has_section('Owners'):
            owners = self.app.cparser.items('Owners')
        else:
            self.log.info('No Owners available')

        return (('Name', 'ID'),
                tuple(owners)
               )


class SecurityGroups(Lister):
    "Show a list of security groups in ec2."

    log = logging.getLogger(__name__)

    def take_action(self, parsed_args):
        security_groups = self.app.ec2_conn.get_all_security_groups()

        return (('Name', 'Description'),
                ((group.name, group.description) for group in security_groups)
               )
