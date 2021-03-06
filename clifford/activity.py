import glob
import logging
import os
import StringIO
import sys
import time
from collections import namedtuple
from subprocess import call

import boto
import paramiko


Task = namedtuple('Task', ['build', 'image', 'instance_id', 'arg_list'])
LaunchResult = namedtuple('LaunchResult', ['build', 'image', 'instance_ids'])


def wait_for_ok(instance_ids, time_to_wait=360):
    waiting_time = 0
    conn = boto.connect_ec2()
    while True:
        sys.stdout.write('Sleeping 30 seconds...\n')
        time.sleep(30)
        waiting_time += 30
        all_instances = conn.get_all_instance_status()
        for instance in all_instances:
            if instance.id not in instance_ids:
                continue
            print instance.id, instance.system_status.status, instance.instance_status.status
            if instance.system_status.status == 'ok' and instance.instance_status.status == 'ok':
                instance_ids.remove(instance.id)
        if not instance_ids:
            break
        if waiting_time >= time_to_wait:
            raise RuntimeError('Servers not ok after %s' % time_to_wait)


def launcher(tag_name, aws_key_path, script_path, **kwargs):
    out = kwargs.get('out', StringIO.StringIO())

    if 'build' not in kwargs:
        out.write('Error: Build not found in kwargs to launcher')
        return
    build = kwargs['build']

    if 'image' not in kwargs:
        out.write('Error: Image not found in kwargs to launcher')
        return
    image = kwargs['image']

    conn = boto.connect_ec2()
    aws_image = conn.get_image(image_id=image['Id'])

    options = {
        'key_name': build['Key'],
        'instance_type': build['Size'],
        'security_group_ids': build['SecurityGroups'],
    }
    if 'UserData' in build:
        with open(os.path.join(script_path, build['UserData']), 'r') as fh:
            options['user_data'] = fh.read()
    if 'Zone' in build:
        options['placement'] = build['Zone']

    if kwargs.get('num', 1) > 1:
        options['min_count'] = kwargs['num']
        options['max_count'] = kwargs['num']

    out.write('Running instance(s)\n')
    reservation = aws_image.run(**options)
    time.sleep(15)

    instances = reservation.instances
    if 'q' in kwargs:
        l = LaunchResult(build, image, [inst.id for inst in instances])
        kwargs['q'].put(l)
    count = len(instances)

    out.write('Waiting for instance(s) to come up\n')
    for i in range(8):
        time.sleep(15)
        ready = True
        for inst in instances:
            status = inst.update()
            if status != 'running':
                out.write('%s\n' % status)
                ready = False
                break
        if ready:
            out.write('Instance(s) now running\n')
            break
    else:
        out.write('All instance(s) are not created equal!\n')
        if 'out' in kwargs:
            return
        return out

    out.write('Adding Tags to instance(s)\n')
    for idx, inst in enumerate(instances):
        if 'Suffix' in build:
            full_name = '%s-%s' % (tag_name, build['Suffix'])
        else:
            full_name = tag_name

        if count == 1 and 'counter' not in kwargs:
            inst.add_tag('Name', full_name)
        else:
            inst.add_tag('Name', '%s-%s' % (full_name, idx + 1 + kwargs.get('counter', 0)))

        if 'project_name' in kwargs and kwargs['project_name']:
            inst.add_tag('Project', kwargs['project_name'])

        if 'build_name' in kwargs and kwargs['build_name']:
            inst.add_tag('Build', kwargs['build_name'])

        inst.add_tag('Login', image['Login'])

    time.sleep(20)
    out.write('Instance(s) should now be running\n')
    for inst in instances:
        if aws_key_path:
            out.write('ssh -i %s/%s.pem %s@%s\n' % (aws_key_path,
                                                    inst.key_name,
                                                    image['Login'],
                                                    inst.public_dns_name))
        else:
            out.write('Public DNS: %s\n' % inst.public_dns_name)
    if 'out' in kwargs:
        return
    return out


def add_user(aws_key_path, task):
    output = 'Running adduser on %s\n' % task.instance_id

    output += 'instance, '
    conn = boto.connect_ec2()
    reservations = conn.get_all_instances(instance_ids=[task.instance_id])
    instance = reservations[0].instances[0]
    pub_key_path = task.arg_list[0]
    adduser = task.build['Adduser']

    output += 'logger, '
    logname = 'add_user.%s' % instance.id
    logger = logging.getLogger(logname)
    logger.setLevel(logging.ERROR)
    fh = logging.FileHandler('/tmp/add_user_%s.log' % instance.id)
    logger.addHandler(fh)

    output += 'connecting'
    ssh = paramiko.SSHClient()
    ssh.set_log_channel(logname)
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    while True:
        try:
            ssh.connect(instance.public_dns_name,
                        username=task.image['Login'],
                        key_filename='%s/%s.pem' % (aws_key_path, instance.key_name))
            break
        except:
            output += ', sleep'
            time.sleep(60)

    output += '\n'

    output += 'Creating user, make sure to set password.\n'
    cmd = 'sudo adduser --disabled-password'
    #if 'Group' in adduser:
    #    cmd += ' --ingroup %s' % adduser['Group']
    cmd += ' --gecos "%s" %s' % (adduser['FullName'], adduser['User'])
    stdin, stdout, stderr = ssh.exec_command(cmd)
    for line in stderr.readlines():
        output += 'ERROR (adduser): %s\n' % line

    keys = glob.glob('%s/*.pub' % pub_key_path)

    if keys:
        user = adduser['User']
        stdin, stdout, stderr = ssh.exec_command(
                'sudo su -c "mkdir /home/%(user)s/.ssh && chown %(user)s:%(user)s /home/%(user)s/.ssh && chmod 700 /home/%(user)s/.ssh"' % {'user': user})
        for line in stderr.readlines():
            output += 'ERROR (mkdir): %s\n' % line

        contents = ''
        for key in keys:
            with open(key, 'r') as f:
                contents += f.read()

        stdin, stdout, stderr = ssh.exec_command('sudo su -c "cat << EOF > /home/%s/.ssh/authorized_keys\n%sEOF"' % (user, contents))
        for line in stderr.readlines():
            output += 'ERROR (cat): %s\n' % line

        stdin, stdout, stderr = ssh.exec_command(
                'sudo su -c "chown %(user)s:%(user)s /home/%(user)s/.ssh/authorized_keys; chmod 600 /home/%(user)s/.ssh/authorized_keys"' % {'user': user})
        for line in stderr.readlines():
            output += 'ERROR (authorized_keys): %s\n' % line

    if 'CopyFiles' in adduser:
        for item in adduser['CopyFiles']:
            with open(os.path.expanduser(item['From']), 'r') as f:
                contents = f.read()
                stdin, stdout, stderr = ssh.exec_command('sudo su -c "cat << EOF > %s\n%sEOF" %s' % (item['To'], contents, user))
                for line in stderr.readlines():
                    output += 'ERROR (copy): %s\n' % line

    #TODO: still need to be able to run a script as the new user

    ssh.close()
    return output


def copier(aws_key_path, task):
    output = 'Running Copier on %s\n' % task.instance_id

    output += 'instance, '
    conn = boto.connect_ec2()
    reservations = conn.get_all_instances(instance_ids=[task.instance_id])
    instance = reservations[0].instances[0]

    output += 'logger, '
    logname = 'copier.%s' % instance.id
    logger = logging.getLogger(logname)
    logger.setLevel(logging.ERROR)
    fh = logging.FileHandler('/tmp/copier_%s.log' % instance.id)
    logger.addHandler(fh)

    output += 'copying\n'

    file_name = task.arg_list[0]

    try:
        retcode = call('scp -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i %s/%s.pem %s %s@%s:~' % (aws_key_path, instance.key_name, file_name, task.image['Login'], instance.public_dns_name), shell=True)
        if retcode < 0:
            output += 'Child was terminated by signal %s\n' % -retcode
        else:
            output += 'Child returned %s\n' % retcode
    except OSError as e:
        output += 'Execution failed: %s\n' % e


def elastic_ip(aws_key_path, task):
    output = 'Running elastic_ip on %s\n' % task.instance_id

    output += 'instance, '
    conn = boto.connect_ec2()
    reservations = conn.get_all_instances(instance_ids=[task.instance_id])
    instance = reservations[0].instances[0]
    elasticip = task.build['ElasticIP']

    output += 'logger, '
    logname = 'elastic_ip.%s' % instance.id
    logger = logging.getLogger(logname)
    logger.setLevel(logging.ERROR)
    fh = logging.FileHandler('/tmp/elastic_ip_%s.log' % instance.id)
    logger.addHandler(fh)

    output += 'connecting'
    ssh = paramiko.SSHClient()
    ssh.set_log_channel(logname)
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    while True:
        try:
            ssh.connect(instance.public_dns_name, username=task.image['Login'], key_filename='%s/%s.pem' % (aws_key_path, instance.key_name))
            break
        except:
            output += ', sleep'
            time.sleep(60)

    output += '\nUpdating /etc/hosts and setting Hostname.\n'

    addresses = [address for address in conn.get_all_addresses() if not address.instance_id]
    #addresses = [address.public_ip for address in addresses]
    for address in addresses:
        if elasticip['IP'] == address.public_ip:
            address.associate(instance.id)
            break
    else:
        output += 'Address not available\n'
        return output

    stdin, stdout, stderr = ssh.exec_command('sudo su -c "echo \'\n### CLIFFORD\n127.0.0.1\t%s\n%s\t%s\t%s\' >> /etc/hosts"' % (elasticip['Hostname'], elasticip['IP'], elasticip['FQDN'], elasticip['Hostname']))
    for line in stderr.readlines():
        output += 'ERROR (elasticip): %s\n' % line

    stdin, stdout, stderr = ssh.exec_command('sudo su -c "echo \'%s\' > /etc/hostname"' % elasticip['Hostname'])
    for line in stderr.readlines():
        output += 'ERROR (elasticip): %s\n' % line

    stdin, stdout, stderr = ssh.exec_command('sudo hostname -F /etc/hostname')
    for line in stderr.readlines():
        output += 'ERROR (elasticip): %s\n' % line

    time.sleep(5)
    #output += 'Rebooting...\n'
    #instance.reboot()
    #time.sleep(60)

    ssh.close()
    return output


def group_installer(aws_key_path, task):
    output = 'Running Group Installer on %s\n' % task.instance_id

    output += 'instance, '
    conn = boto.connect_ec2()
    reservations = conn.get_all_instances(instance_ids=[task.instance_id])
    instance = reservations[0].instances[0]

    output += 'logger, '
    logname = 'group_installer.%s' % instance.id
    logger = logging.getLogger(logname)
    logger.setLevel(logging.ERROR)
    fh = logging.FileHandler('/tmp/group_installer_%s.log' % instance.id)
    logger.addHandler(fh)

    output += 'connecting, '
    ssh = paramiko.SSHClient()
    ssh.set_log_channel(logname)
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    while True:
        try:
            ssh.connect(instance.public_dns_name, username=task.image['Login'], key_filename='%s/%s.pem' % (aws_key_path, instance.key_name))
            break
        except:
            output += 'sleep, '
            time.sleep(60)

    output += 'installing\n'
    has_error = False
    for bundle in task.arg_list[0]:
        name = bundle[0]
        packages = bundle[1]

        stdin, stdout, stderr = ssh.exec_command('sudo apt-get -y install %s' % packages)
        for line in stdout.readlines():
            if any([item in line for item in ['Note, selecting', 'is already the newest version']]):
                output += line
        for line in stderr.readlines():
            if line.startswith('E: '):
                output += line
                has_error = True
        if has_error:
            output += 'Unable to Continue!\n'
            ssh.close()
            return output
        time.sleep(5)
        if name == 'packages':
            output += 'Installed packages: %s\n' % packages
        else:
            output += 'Installed bundle: %s\n' % name

    ssh.close()
    return output


def py_installer(aws_key_path, task):
    output = 'Running Python Installer on %s\n' % task.instance_id

    output += 'instance, '
    conn = boto.connect_ec2()
    reservations = conn.get_all_instances(instance_ids=[task.instance_id])
    instance = reservations[0].instances[0]

    output += 'logger, '
    logname = 'py_installer.%s' % instance.id
    logger = logging.getLogger(logname)
    logger.setLevel(logging.ERROR)
    fh = logging.FileHandler('/tmp/py_installer_%s.log' % instance.id)
    logger.addHandler(fh)

    output += 'connecting'
    ssh = paramiko.SSHClient()
    ssh.set_log_channel(logname)
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    while True:
        try:
            ssh.connect(instance.public_dns_name, username=task.image['Login'], key_filename='%s/%s.pem' % (aws_key_path, instance.key_name))
            break
        except:
            output += ', sleep'
            time.sleep(60)
    output += '\n'

    py_installer = task.arg_list[0]
    packages = task.arg_list[1]
    stdin, stdout, stderr = ssh.exec_command('sudo %s %s' % (py_installer, packages))
    for line in stdout.readlines():
        if line.startswith('Installed') or line.startswith('Finished') or line.startswith('Successfully'):
            output += line

    ssh.close()
    return output


def script_runner(aws_key_path, task):
    output = 'Running Script on %s\n' % task.instance_id

    user = task.arg_list[0]

    output += 'instance, '
    conn = boto.connect_ec2()
    reservations = conn.get_all_instances(instance_ids=[task.instance_id])
    instance = reservations[0].instances[0]
    name_tag = instance.tags.get('Name')

    output += 'logger, '
    logname = 'script_runner.%s' % instance.id
    logger = logging.getLogger(logname)
    logger.setLevel(logging.ERROR)
    fh = logging.FileHandler('/tmp/script_runner_%s.log' % instance.id)
    logger.addHandler(fh)

    output += 'connecting'
    ssh = paramiko.SSHClient()
    ssh.set_log_channel(logname)
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    while True:
        try:
            ssh.connect(instance.public_dns_name, username=task.image['Login'], key_filename='%s/%s.pem' % (aws_key_path, instance.key_name))
            break
        except:
            output += ', sleep'
            time.sleep(60)
    output += '\n'

    script = task.arg_list[1]
    copy_only = task.arg_list[2]
    script_name = os.path.basename(script)

    with open(script, 'r') as f:
        contents = f.read()
        if user in ['admin', 'ec2-user', 'ubuntu'] and 'ScriptFormatArgs' in task.build:
            format_args = task.build['ScriptFormatArgs'].split(',')
            format_args = [name_tag for arg in format_args if arg == '@name']
            contents = contents % tuple(format_args)
        if user == task.image['Login']:
            ssh.exec_command('cat << EOF > /home/%s/%s\n%s\nEOF' % (user, script_name, contents))
        else:
            ssh.exec_command('sudo su -c "cat << EOF > /home/%s/%s\n%s\nEOF" %s' % (user, script_name, contents, user))
        time.sleep(5)
        ssh.exec_command('sudo chown %(user)s:%(user)s /home/%(user)s/%(script)s' % {'user': user, 'script': script_name})
        time.sleep(5)
        ssh.exec_command('sudo chmod 744 /home/%(user)s/%(script)s' % {'user': user, 'script': script_name})

    if not copy_only:
        channel = ssh.get_transport().open_session()
        channel.settimeout(0.1)
        channel.input_enabled = True
        forward = paramiko.agent.AgentRequestHandler(channel)

        channel.exec_command('sudo su -c "/home/%s/%s" %s' % (user, script_name, user))

        while True:
            time.sleep(5)
            if channel.exit_status_ready():
                break
        status = channel.recv_exit_status()
        output += 'Script status: %s\n' % status

        channel.close()
        forward.close()

    ssh.close()
    return output


def static_host(aws_key_path, task):
    output = 'Running static_host on %s\n' % task.instance_id

    output += 'instance, '
    conn = boto.connect_ec2()
    reservations = conn.get_all_instances(instance_ids=[task.instance_id])
    instance = reservations[0].instances[0]
    tag_name = task.arg_list[0]

    output += 'logger, '
    logname = 'static_host.%s' % instance.id
    logger = logging.getLogger(logname)
    logger.setLevel(logging.ERROR)
    fh = logging.FileHandler('/tmp/static_host_%s.log' % instance.id)
    logger.addHandler(fh)

    output += 'connecting'
    ssh = paramiko.SSHClient()
    ssh.set_log_channel(logname)
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    while True:
        try:
            ssh.connect(instance.public_dns_name, username=task.image['Login'], key_filename='%s/%s.pem' % (aws_key_path, instance.key_name))
            break
        except:
            output += ', sleep'
            time.sleep(60)

    output += '\nUpdating /etc/hosts and setting Hostname.\n'

    stdin, stdout, stderr = ssh.exec_command('sudo su -c "echo \'\n### CLIFFORD\n127.0.0.1\t%s\' >> /etc/hosts"' % tag_name)
    for line in stderr.readlines():
        output += 'ERROR (static_host hosts): %s\n' % line

    stdin, stdout, stderr = ssh.exec_command('sudo su -c "echo \'%s\' > /etc/hostname"' % tag_name)
    for line in stderr.readlines():
        output += 'ERROR (static_host hostname): %s\n' % line

    stdin, stdout, stderr = ssh.exec_command('sudo hostname -F /etc/hostname')
    for line in stderr.readlines():
        output += 'ERROR (static_host reload): %s\n' % line

    time.sleep(5)
    #output += 'Rebooting...\n'
    #instance.reboot()
    #time.sleep(60)

    ssh.close()
    return output



def upgrade(aws_key_path, task):
    output = 'Running %s on %s\n' % (task.build['Upgrade'], task.instance_id)

    output += 'instance, '
    conn = boto.connect_ec2()
    reservations = conn.get_all_instances(instance_ids=[task.instance_id])
    instance = reservations[0].instances[0]

    output += 'logger, '
    logname = 'upgrade.%s' % instance.id
    logger = logging.getLogger(logname)
    logger.setLevel(logging.ERROR)
    fh = logging.FileHandler('/tmp/upgrade_%s.log' % instance.id)
    logger.addHandler(fh)

    output += 'connecting'
    ssh = paramiko.SSHClient()
    ssh.set_log_channel(logname)
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    while True:
        try:
            ssh.connect(instance.public_dns_name, username=task.image['Login'], key_filename='%s/%s.pem' % (aws_key_path, instance.key_name))
            break
        except:
            output += ', sleep'
            time.sleep(60)

    output += '\n'
    #output += 'hosts\n'
    #stdin, stdout, stderr = ssh.exec_command('grep -Fq CLIFFORD /etc/hosts || sudo su -c "echo \'\n### CLIFFORD\n127.0.1.1\t%s\' >> /etc/hosts"' % instance.tags.get('Name'))

    has_error = False
    stdin, stdout, stderr = ssh.exec_command('sudo apt-get -y update')
    for line in stderr.readlines():
        if line.startswith('E: '):
            output += line
            has_error = True
    if has_error:
        output += 'Unable to Continue!\n'
        ssh.close()
        return output
    time.sleep(5)
    output += 'UPDATED\n'

    stdin, stdout, stderr = ssh.exec_command('sudo apt-get -s upgrade')
    string_list = ['The following packages have been kept back:', 'The following packages will be upgraded:']
    for line in stdout.readlines():
        if line.rstrip() in string_list or line.startswith('  '):
            output += line
    time.sleep(5)

    if task.build['Upgrade'] in ['upgrade', 'dist-upgrade']:
        stdin, stdout, stderr = ssh.exec_command('sudo su -c "env DEBIAN_FRONTEND=noninteractive apt-get -y -o DPkg::Options::=--force-confnew %s"' % task.build['Upgrade'])
        for line in stderr.readlines():
            if line.startswith('E: '):
                output += line
                has_error = True
        if has_error:
            output += 'Unable to Continue!\n'
            ssh.close()
            return output
        time.sleep(5)
        output += '%sD\n' % task.build['Upgrade'].upper()

    ssh.close()

    if task.build['Upgrade'] == 'dist-upgrade':
        time.sleep(5)
        output += 'Rebooting...\n'
        instance.reboot()
        time.sleep(60)

    return output
