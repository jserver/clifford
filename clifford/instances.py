import logging

from cliff.lister import Lister


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
