import logging
import os

from cliff.lister import Lister


ROWS, COLUMNS = [int(i) for i in os.popen('stty size', 'r').read().split()]


class Addresses(Lister):
    "List of IP addresses in ec2."

    log = logging.getLogger(__name__)

    def take_action(self, parsed_args):
        addresses = self.app.ec2_conn.get_all_addresses()

        return (('Public IP', 'Instance ID'),
                ((address.public_ip, address.instance_id) for address in addresses)
               )


class Buckets(Lister):
    "List of Buckets in S3."

    log = logging.getLogger(__name__)

    def take_action(self, parsed_args):
        buckets = self.app.s3_conn.get_all_buckets()

        return (('Name', 'Website'),
                ((bucket.name, bucket.get_website_endpoint()) for bucket in buckets)
               )


class Images(Lister):
    "List of images stored in the config."

    log = logging.getLogger(__name__)

    def take_action(self, parsed_args):
        if not self.app.cparser.has_option('Images', 'images'):
            raise RuntimeError('No images added!')

        images_str = self.app.cparser.get('Images', 'images')
        image_ids = images_str.split(',')
        if image_ids:
            images = [(image.id, image.name) for image in self.app.ec2_conn.get_all_images(image_ids=image_ids)]

        return (('Image ID', 'Name'),
                tuple(images)
               )


class Instances(Lister):
    "List of instances in ec2."

    log = logging.getLogger(__name__)

    def take_action(self, parsed_args):
        reservations = self.app.ec2_conn.get_all_instances()
        instances = []
        for res in reservations:
            for instance in res.instances:
                if instance.public_dns_name:
                    public_dns = instance.public_dns_name
                else:
                    public_dns = ''
                instances.append((instance.tags.get('Name'),
                                  instance.id,
                                  instance.state,
                                  instance.instance_type,
                                  instance.root_device_type,
                                  instance.architecture,
                                  instance.placement,
                                  public_dns))

        return (('Name', 'Id', 'State', 'Type', 'RootDevice', 'Arch', 'Zone', 'PublicDNS'),
                (instance for instance in instances)
               )


class Keys(Lister):
    "List of keys in ec2."

    log = logging.getLogger(__name__)

    def take_action(self, parsed_args):
        keys = self.app.ec2_conn.get_all_key_pairs()

        return (('Name', 'fingerprint'),
                ((key.name, key.fingerprint) for key in keys)
               )


class Packages(Lister):
    "List of packages in config."

    log = logging.getLogger(__name__)

    def take_action(self, parsed_args):
        if not self.app.cparser.has_section('Packages'):
            raise RuntimeError('No packages found!')

        packages = self.app.cparser.items('Packages')
        max_name_len = max(4, max([len(package[0]) for package in packages]))
        max_packages_len = COLUMNS - max_name_len - 7

        package_tuples = []
        for package in packages:
            if len(package[1]) > max_packages_len:
                package_tuples.append((package[0], package[1][:max_packages_len - 3] + '...'))
            else:
                package_tuples.append((package[0], package[1]))


        return (('Name', 'Packages'),
                package_tuples
                )


class SecurityGroups(Lister):
    "List of security groups in ec2."

    log = logging.getLogger(__name__)

    def take_action(self, parsed_args):
        security_groups = self.app.ec2_conn.get_all_security_groups()

        return (('Name', 'Description'),
                ((group.name, group.description) for group in security_groups)
               )


class Snapshots(Lister):
    "List of snapshots in ec2."

    log = logging.getLogger(__name__)

    def take_action(self, parsed_args):
        if not self.app.cparser.has_option('Owner', 'owner'):
            raise RuntimeError('No owner set!')

        owner = self.app.cparser.get('Owner', 'owner')
        snapshots = self.app.ec2_conn.get_all_snapshots(owner=owner)

        return (('Name', 'ID', 'Size', 'Status', 'Progress' ),
                ((snapshot.tags.get('name', ''),
                  snapshot.id,
                  '%s GiB' % snapshot.volume_size,
                  snapshot.status,
                  snapshot.progress) for snapshot in snapshots)
               )


class Volumes(Lister):
    "List of Volumes in ec2."

    log = logging.getLogger(__name__)

    def take_action(self, parsed_args):
        volumes = self.app.ec2_conn.get_all_volumes()

        return (('Name', 'ID', 'Size', 'Type', 'Snapshot ID', 'Zone', 'Status', 'Instance ID'),
                ((volume.tags.get('name', ''),
                  volume.id,
                  '%s GiB' % volume.size,
                  volume.type,
                  volume.snapshot_id,
                  volume.zone,
                  volume.status,
                  hasattr(volume, 'attach_data') and volume.attach_data.instance_id or '') for volume in volumes)
               )
