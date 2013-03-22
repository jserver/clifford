class PreseedMixin(object):
    def get_preseeds(self, bundle):
        preseeds = []
        packages = bundle.split(' ')
        for package in packages:
            if not self.app.cparser.has_section('%s.debconf' % package):
                continue
            options = self.app.cparser.options('%s.debconf' % package)
            if options:
                for option in options:
                    preseeds.append(self.app.cparser.get('%s.debconf' % package, option))
        return preseeds


class SingleInstanceMixin(object):
    def get_instance(self, name, arg_is_id):
        if arg_is_id:
            reservations = self.app.ec2_conn.get_all_instances(instance_ids=[name])
        else:
            reservations = self.app.ec2_conn.get_all_instances(filters={'tag:Name': name})
            possible_reservations = []
            for res in reservations:
                for instance in res.instances:
                    if instance.state == 'terminated':
                        pass
                    else:
                        possible_reservations.append(res)
            if len(possible_reservations) > 1:
                raise RuntimeError('More than one reservation returned, use --id')
            reservations = possible_reservations
        if not reservations:
            raise RuntimeError('No instances found')
        res = reservations[0]
        if not res.instances:
            raise RuntimeError('No instances wth name %s' % name)
        elif len(res.instances) > 1:
            raise RuntimeError('More than one instance in reservation!' % name)
        return res.instances[0]
