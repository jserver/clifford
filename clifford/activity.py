import logging
import os
import time

import boto
import paramiko


def launcher(aws_key_path, tag_name, **kwargs):
    output = ''

    if 'build' not in kwargs:
        output += 'Error: Build not found in kwargs to launcher'
        return
    build = kwargs['build']

    conn = boto.connect_ec2()
    image = conn.get_image(image_id=build['Image'])

    options = {
        'key_name': build['Key'],
        'instance_type': build['Size'],
        'security_group_ids': build['SecurityGroups'],
    }
    if 'UserData' in build:
        options['user_data'] = build['UserData']
    if 'Zone' in build:
        options['placement'] = build['Zone']

    if 'num' in kwargs and kwargs['num'] > 1:
        options['min_count'] = kwargs['num']
        options['max_count'] = kwargs['num']

    reservation = image.run(**options)
    time.sleep(10)

    instances = reservation.instances
    count = len(instances)
    time.sleep(10)
    output += 'Adding Tags to instance(s)\n'
    for idx, inst in enumerate(instances):
        if count == 1:
            inst.add_tag('Name', tag_name)
        else:
            inst.add_tag('Name', '%s [%s]' % (tag_name, idx + 1))
        if 'project_name' in kwargs and kwargs['project_name']:
            inst.add_tag('Project', kwargs['project_name'])
        if 'build_name' in kwargs and kwargs['build_name']:
            inst.add_tag('Build', kwargs['build_name'])
        inst.add_tag('Login', build['Login'])

    cnt = 0
    while cnt < 6:
        cnt += 1
        time.sleep(20)
        ready = True
        for inst in instances:
            status = inst.update()
            if status != 'running':
                output += '%s\n' % status
                ready = False
                break
        if ready:
            break
    if cnt == 6:
        output += 'All instance(s) are not created equal!\n'
        return output

    time.sleep(20)
    output += 'Instance(s) should now be running\n'
    for inst in instances:
        if aws_key_path:
            output += 'ssh -i %s.pem %s@%s\n' % (os.path.join(aws_key_path, inst.key_name), build['Login'], inst.public_dns_name)
        else:
            output += 'Public DNS: %s\n' % inst.public_dns_name
    return output


def group_installer(instance, username, bundles, aws_key_path):
    logname = 'group_installer.%s' % instance.id
    logger = logging.getLogger(logname)
    logger.setLevel(logging.ERROR)
    fh = logging.FileHandler('/tmp/group_installer_%s.log' % instance.id)
    logger.addHandler(fh)

    output = 'Running Group Installer on %s\n' % instance.id

    ssh = paramiko.SSHClient()
    ssh.set_log_channel(logname)
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(instance.public_dns_name, username=username, key_filename='%s.pem' % os.path.join(aws_key_path, instance.key_name))

    has_error = False
    for bundle in bundles:
        name = bundle[0]
        packages = bundle[1]

        stdin, stdout, stderr = ssh.exec_command('sudo apt-get -y install %s' % packages)
        for line in stdout.readlines():
            if any([item in line for item in ['Note, selecting', 'is already the newest version']]):
                output += line + '\n'
        for line in stderr.readlines():
            if line.startswith('E: '):
                output += line + '\n'
                has_error = True
        if has_error:
            output += 'Unable to Continue...\n'
            ssh.close()
            return output
        time.sleep(5)
        if name == 'packages':
            output += 'Installed packages: %s\n' % packages
        else:
            output += 'Installed bundle: %s\n' % name

    ssh.close()
    return output


def pip_installer(instance, username, packages, aws_key_path):
    logname = 'pip_installer.%s' % instance.id
    logger = logging.getLogger(logname)
    logger.setLevel(logging.ERROR)
    fh = logging.FileHandler('/tmp/pip_installer_%s.log' % instance.id)
    logger.addHandler(fh)

    output = 'Running Pip Installer on %s\n' % instance.id

    ssh = paramiko.SSHClient()
    ssh.set_log_channel(logname)
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(instance.public_dns_name, username=username, key_filename='%s.pem' % os.path.join(aws_key_path, instance.key_name))

    stdin, stdout, stderr = ssh.exec_command('sudo pip install %s' % packages)
    for line in stdout.readlines():
        if line.startswith('Installed') or line.startswith('Finished') or line.startswith('Successfully'):
            output += line + '\n'

    ssh.close()
    return output


def script_runner(instance, username, script, aws_key_path, copy_only=False):
    logname = 'script_runner.%s' % instance.id
    logger = logging.getLogger(logname)
    logger.setLevel(logging.ERROR)
    fh = logging.FileHandler('/tmp/script_runner_%s.log' % instance.id)
    logger.addHandler(fh)

    output = 'Running Pip Installer on %s\n' % instance.id

    ssh = paramiko.SSHClient()
    ssh.set_log_channel(logname)
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    # quite fragile, what if an ubuntu machine has a user named admin
    if username in ['admin', 'ubuntu']:
        ssh.connect(instance.public_dns_name, username=username, key_filename='%s.pem' % os.path.join(aws_key_path, instance.key_name))
    else:
        ssh.connect(instance.public_dns_name, username=username)

    script_name = os.path.basename(script)

    with open(script, 'r') as f:
        contents = f.read()
        ssh.exec_command('cat << EOF > %s\n%s\nEOF' % (script_name, contents))
        ssh.exec_command('chmod 744 %s' % script_name)

    if not copy_only:
        channel = ssh.get_transport().open_session()
        channel.settimeout(0.1)
        channel.input_enabled = True
        forward = paramiko.agent.AgentRequestHandler(channel)

        channel.exec_command('/home/%s/%s' % (username, script_name))

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


def upgrade(instance, username, action, aws_key_path):
    output = 'Running %s on %s\n' % (action, instance.id)

    logname = 'upgrade.%s' % instance.id
    logger = logging.getLogger(logname)
    logger.setLevel(logging.ERROR)
    fh = logging.FileHandler('/tmp/upgrade_%s.log' % instance.id)
    logger.addHandler(fh)

    ssh = paramiko.SSHClient()
    ssh.set_log_channel(logname)
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(instance.public_dns_name, username=username, key_filename='%s.pem' % os.path.join(aws_key_path, instance.key_name))

    stdin, stdout, stderr = ssh.exec_command('sudo su -c "echo \'\n### CLIFFORD\n127.0.1.1\t%s\' >> /etc/hosts"' % instance.tags.get('Name'))

    has_error = False
    stdin, stdout, stderr = ssh.exec_command('sudo apt-get -y update')
    for line in stderr.readlines():
        if line.startswith('E: '):
            output += line + '\n'
            has_error = True
    if has_error:
        output += 'Unable to Continue...\n'
        ssh.close()
        return output
    time.sleep(5)
    output += 'UPDATED\n'

    stdin, stdout, stderr = ssh.exec_command('sudo apt-get -s upgrade')
    string_list = ['The following packages have been kept back:', 'The following packages will be upgraded:']
    for line in stdout.readlines():
        if line.rstrip() in string_list or line.startswith('  '):
            output += line + '\n'
    time.sleep(5)

    if action in ['upgrade', 'dist-upgrade']:
        stdin, stdout, stderr = ssh.exec_command('sudo su -c "env DEBIAN_FRONTEND=noninteractive apt-get -y -o DPkg::Options::=--force-confnew %s"' % action)
        for line in stderr.readlines():
            if line.startswith('E: '):
                output += line + '\n'
                has_error = True
        if has_error:
            output += 'Unable to Continue...\n'
            ssh.close()
            return output
        time.sleep(5)
        output += '%sD\n' % action.upper()

    ssh.close()

    if action == 'dist-upgrade':
        time.sleep(5)
        output += 'Rebooting...\n'
        instance.reboot()
        time.sleep(20)

    return output
