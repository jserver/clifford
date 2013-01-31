#Utilities go here
class SingleBoxMixin(object):
    def get_box(self, name):
        reservations = self.app.ec2_conn.get_all_instances(filters={'tag:Name': name})
        for res in reservations:
            if not res.instances:
                self.log.error('No instances wth name %s' % name)
            elif len(res.instances) > 1:
                self.log.error('More than one instance has name %s' % name)
            else:
                return res.instances[0]
            return None
