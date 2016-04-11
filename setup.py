#!/usr/bin/env python

from setuptools import setup, find_packages

VERSION = '0.1.1'
DESCRIPTION = 'hassle free process restarting'

setup(
    name='rolld',
    version=VERSION,
    description=DESCRIPTION,
    author='ybrs',
    license='MIT',
    url="https://github.com/ybrs/project-switcher",
    author_email='aybars.badur@gmail.com',
    packages=['rolld'],
    install_requires = ['tornado', 'jinja2', 'psutil', 'requests'],
    entry_points={
          'console_scripts': [
              'rolld = rolld.manager:main'
          ]
    },
    classifiers = [
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Database',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ]
)