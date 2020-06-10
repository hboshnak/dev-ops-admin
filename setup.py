import os
import re
from setuptools import setup

# Parse version


def parse_version():
    """Parse version number from __init__.py in top-level import package

    It is assumed that the version is defined as a string and the '=' sign
    is surrounded by at most one whitespace character to the left and to the
    right.

    Returns:
        version string
    Raises:
        ValueError if the parser could not match the version definition
    """
    init_fpath = os.path.join('devopstemplate', '__init__.py')
    with open(init_fpath, 'r') as fh:
        init_contents = fh.read()
        ver_re = r"^__version__ ?= ?['\"]([^'\"]*)['\"]"
        match = re.search(ver_re, init_contents, re.M)
        if match:
            version = match.group(1)
            return version
        else:
            raise ValueError('Could not parse version string')


with open('README.md', 'r') as fh:
    long_description = fh.read()

with open('devopstemplate/template.index', 'r') as fh:
    template_index = fh.read().splitlines()

version = parse_version()

# setup.py defines the Python package. The build process is triggered from
# Makefile. Adapt Makefile variable SETUPTOOLSFILES if build file dependencies
# change.
setup(name='devopstemplate',
      version=version,
      # Import package
      packages=['devopstemplate'],
      # Installation dependencies
      setup_requires=['setuptools >= 40.9.0',
                      'wheel'],
      # Package dependencies
      # install_requires=[],
      # Defines dev environment containing development dependencies
      # (for linting, testing, etc.)
      extras_require={'dev': ['pip >= 20.1.1',
                              'wheel',
                              'pytest',
                              'coverage',
                              'bandit',
                              'pylint',
                              'autopep8',
                              'flake8']
                      },
      entry_points={'console_scripts':
                    ['devopstemplate=devopstemplate.main:main']
                    },
      package_data={
          # Include data files in devopstemplate package
          # the file template.index specifies file paths relative to
          # devopstemplate/template directory
          'devopstemplate': (['template.index', 'template.json'] +
                             [f'template/{fpath}'
                              for fpath in template_index]),
      },
      # Generally do not assume that the package can safely be run as a zip
      # archive
      zip_safe=False,
      # Metadata to display on PyPI
      author='Leonard Rothacker',
      author_email='leonard.rothacker@googlemail.com',
      description=('This package provides a command-line interface for ' +
                   'setting up a Python project based on a DevOps template'),
      long_description=long_description,
      long_description_content_type='text/markdown',
      keywords='devops sonarqube docker',
      url='https://github.com/lrothack/dev-ops-admin',
      license='MIT',
      classifiers=['Intended Audience :: Developers',
                   'License :: OSI Approved :: MIT License',
                   'Programming Language :: Python :: 3.7'
                   'Programming Language :: Python :: 3.8'
                   'Environment :: Console',
                   ]
      )
