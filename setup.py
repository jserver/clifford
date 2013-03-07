#!/usr/bin/env python

PROJECT = 'clifford'

# Change docs/sphinx/conf.py too!
VERSION = '0.1'

# Bootstrap installation of Distribute
import distribute_setup
distribute_setup.use_setuptools()

from setuptools import setup, find_packages

from distutils.util import convert_path
from fnmatch import fnmatchcase
import os
import sys

try:
    long_description = open('README.rst', 'rt').read()
except IOError:
    long_description = ''

setup(
    name=PROJECT,
    version=VERSION,

    description='Clifford, ec2 made easy.',
    long_description=long_description,

    author='Joe Server',
    author_email='servernyc@gmail.com',

    url='https://github.com/jserver/clifford',
    download_url='https://github.com/jserver/clifford/tarball/master',

    classifiers=['Development Status :: 3 - Alpha',
                 'License :: OSI Approved :: Apache Software License',
                 'Programming Language :: Python',
                 'Programming Language :: Python :: 2',
                 'Programming Language :: Python :: 2.7',
                 'Programming Language :: Python :: 3',
                 'Programming Language :: Python :: 3.2',
                 'Intended Audience :: Developers',
                 'Environment :: Console',
                 ],

    platforms=['Any'],

    scripts=[],

    provides=[],
    install_requires=['distribute', 'cliff', 'boto', 'paramiko'],

    namespace_packages=[],
    packages=find_packages(),
    include_package_data=True,

    entry_points={
        'console_scripts': [
            'clifford = clifford.main:main'
            ],
        'clifford': [
            # Lister tools
            'ls addresses = clifford.list:Addresses',
            'ls buckets = clifford.list:Buckets',
            'ls images = clifford.list:Images',
            'ls instances = clifford.list:Instances',
            'ls keys = clifford.list:Keys',
            'ls packages = clifford.list:Packages',
            'ls security groups = clifford.list:SecurityGroups',
            'ls snapshots = clifford.list:Snapshots',
            'ls volumes = clifford.list:Volumes',

            # EC2
            'set keydir = clifford.actions:SetKeyDir',
            'show keydir = clifford.show:KeyDir',
            'set owner = clifford.actions:SetOwner',
            'show owner = clifford.show:Owner',
            'set scriptdir = clifford.actions:SetScriptDir',
            'show scriptdir = clifford.show:ScriptDir',

            'add image = clifford.actions:AddImage',
            'create image = clifford.actions.CreateImage',
            'create snapshot = clifford.actions.CreateSnapshot',
            'rm image = clifford.actions:DeleteImage',
            'rm volume = clifford.actions:DeleteVolume',

            'show instance = clifford.show:Instance',
            'launch = clifford.launch:Launch',
            'terminate = clifford.actions:Terminate',
            'reboot = clifford.actions:Reboot',
            'stop = clifford.actions:Stop',
            'start = clifford.actions:Start',

            'remote install = clifford.remote:Install',
            'remote script = clifford.remote:Script',
            'remote upgrade = clifford.remote:Upgrade',

            'create package = clifford.package:CreatePackage',
            'package add = clifford.package:PackageAdd',
            'package rm = clifford.package:PackageRemove',
            'rm package = clifford.package:DeletePackage',
            'show package = clifford.show:Package',

            # Elastic IPs
            'associate = clifford.address:Associate',
            'disassociate = clifford.address:Disassociate',
            'allocate = clifford.address:Allocate',
            'release = clifford.address:Release',

            # S3
            'create bucket = clifford.storage:CreateBucket',
            'rm bucket = clifford.storage:DeleteBucket',
            'download = clifford.storage:Download',
            'upload = clifford.storage:Upload',
            ],
        },

    zip_safe=False,
    )
