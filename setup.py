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
    install_requires=['distribute', 'cliff', 'boto'],

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
            'ls images = clifford.list:Images',
            'ls instances = clifford.list:Instances',
            'ls keys = clifford.list:Keys',
            'ls owners = clifford.list:Owners',
            'ls security groups = clifford.list:SecurityGroups',

            # EC2
            'add image = clifford.actions:AddImage',
            'add owner = clifford.actions:AddOwner',
            'desc = clifford.show:Describe',
            'launch = clifford.launch:Launch',
            'terminate = clifford.actions:Terminate',
            'reboot = clifford.actions:Reboot',
            'stop = clifford.actions:Stop',
            'start = clifford.actions:Start',

            # Elastic IPs
            'associate = clifford.address:Associate',
            'disassociate = clifford.address:Disassociate',
            'allocate = clifford.address:Allocate',
            'release = clifford.address:Release',
            ],
        },

    zip_safe=False,
    )
