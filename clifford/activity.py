import logging
import os
import time

import paramiko


def group_installer(username, instance, bundles, aws_key_path):
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
        output += 'Installed bundle %s\n' % name

    ssh.close()
    return output


def pip_installer(username, instance, packages, aws_key_path):
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


def script_runner(username, instance, script, aws_key_path, copy_only=False):
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


def upgrade(username, instance, action, aws_key_path):
    logname = 'upgrade.%s' % instance.id
    logger = logging.getLogger(logname)
    logger.setLevel(logging.ERROR)
    fh = logging.FileHandler('/tmp/upgrade_%s.log' % instance.id)
    logger.addHandler(fh)

    output = 'Running %s on %s\n' % (action, instance.id)

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

    if action != 'dist-upgrade':
        if action == 'upgrade':
            upgrade = 'y'
        else:
            upgrade = raw_input('Do you want to upgrade? ')
        if upgrade.lower() in ['y', 'yes']:
            stdin, stdout, stderr = ssh.exec_command('sudo su -c "env DEBIAN_FRONTEND=noninteractive apt-get -y -o DPkg::Options::=--force-confnew upgrade"')
            for line in stderr.readlines():
                if line.startswith('E: '):
                    output += line + '\n'
                    has_error = True
            if has_error:
                output += 'Unable to Continue...\n'
                ssh.close()
                return output
            time.sleep(5)
            output += 'UPGRADED\n'

    if action == 'upgrade':
        dist_upgrade = 'n'
    elif action == 'dist_upgrade':
        dist_upgrade = 'y'
    else:
        dist_upgrade = raw_input('Do you want to dist-upgrade? ')

    if dist_upgrade.lower() in ['y', 'yes']:
        stdin, stdout, stderr = ssh.exec_command('sudo su -c "env DEBIAN_FRONTEND=noninteractive apt-get -y -o DPkg::Options::=--force-confnew dist-upgrade"')
        for line in stderr.readlines():
            if line.startswith('E: '):
                output += line + '\n'
                has_error = True
        if has_error:
            output += 'Unable to Continue...\n'
            ssh.close()
            return output
        time.sleep(5)
        output += 'DIST-UPGRADED\n'

    ssh.close()

    if action == 'dist-upgrade':
        reboot = 'y'
    elif action == 'upgrade':
        reboot = 'n'
    else:
        reboot = raw_input('Do you want to reboot? ')

    if reboot.lower() in ['y', 'yes']:
        time.sleep(5)
        output += 'Rebooting...\n'
        instance.reboot()
        time.sleep(20)

    return output
