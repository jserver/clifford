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


class Buckets(Lister):
    "Show a list of Buckets in S3."

    log = logging.getLogger(__name__)

    def take_action(self, parsed_args):
        buckets = self.app.s3_conn.get_all_buckets()

        return (('Name', 'Website'),
                ((bucket.name, bucket.get_website_endpoint()) for bucket in buckets)
               )


class Images(Lister):
    "Show a list of images in ec2."

    log = logging.getLogger(__name__)

    def take_action(self, parsed_args):
        if not self.app.cparser.has_option('Images', 'images'):
            raise RuntimeError('No images added!')

        images_str = self.app.cparser.get('Images', 'images')
        image_ids = images_str.split(',')
        if image_ids:
            images = [(image.id, image.name, image.description) for image in self.app.ec2_conn.get_all_images(image_ids=image_ids)]

        return (('Image ID', 'Name', 'Description'),
                tuple(images)
               )


class Instances(Lister):
    "Show a list of instances in ec2."

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

        return (('Name', 'Id', 'State', 'Type', 'Root Device', 'Arch', 'Zone', 'Public DNS'),
                (instance for instance in instances)
               )


class Keys(Lister):
    "Show a list of keys in ec2."

    log = logging.getLogger(__name__)

    def take_action(self, parsed_args):
        keys = self.app.ec2_conn.get_all_key_pairs()

        return (('Name', 'fingerprint'),
                ((key.name, key.fingerprint) for key in keys)
               )


class Packages(Lister):
    "Show a list of packages in config."

    log = logging.getLogger(__name__)

    def take_action(self, parsed_args):
        packages = self.app.cparser.items('Packages')

        return (('Name', 'Packages'),
                ((package[0], package[1]) for package in packages)
               )


class SecurityGroups(Lister):
    "Show a list of security groups in ec2."

    log = logging.getLogger(__name__)

    def take_action(self, parsed_args):
        security_groups = self.app.ec2_conn.get_all_security_groups()

        return (('Name', 'Description'),
                ((group.name, group.description) for group in security_groups)
               )


class Snapshots(Lister):
    "Show a list of snapshots in ec2."

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
    "Show a list of Volumes in ec2."

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
