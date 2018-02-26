import os
import re
import sys

from setuptools import find_packages, setup

ROOT = os.path.abspath(os.path.dirname(__file__))
VERSION_RE = re.compile(r'''__version__ = ['"]([0-9.]+)['"]''')

install_requires = [
    'azure>=2.0.0',  # MIT
    'boto3>=1.4.5',  # Apache 2.0
    'filelock>=2.0.0',  # Public Domain
    'google-cloud-storage>=1.4',  # Apache 2.0
    'inflection',  # MIT
    'itsdangerous>=0.24',  # BSD License
    'python-dateutil',  # Simplified BSD
    'python-magic',  # MIT
    'rackspacesdk>=0.7.5',  # Apache 2.0
    'requests',  # Apache 2.0
    'rfc6266-parser',  # GNU LGPL
    'xattr',  # MIT
]

# Python 3.4 needs backports
if sys.version_info < (3, 5):
    install_requires.extend([
        'typing',  # PSF
        'httpstatus35',  # MIT
    ])


def get_version():
    init = open(os.path.join(ROOT, 'cloudstorage', '__init__.py')).read()
    return VERSION_RE.search(init).group(1)


download_url = 'https://github.com/scottwernervt/cloudstorage/' \
               'archive/%s.tar.gz' % get_version()

setup(
    name='cloudstorage',
    version=get_version(),
    author='Scott Werner',
    author_email='scott.werner.vt@gmail.com',
    description='Unified cloud storage API for storage services.',
    long_description=open('README.rst').read(),
    license='MIT',
    platforms='Posix; MacOS X; Windows',
    keywords=' '.join([
        'storage',
        'amazon',
        'aws',
        's3',
        'azure',
        'rackspace',
        'cloudfiles',
        'google',
        'cloudstorage',
        'gcs',
    ]),
    url='https://github.com/scottwernervt/cloudstorage',
    download_url=download_url,
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'Intended Audience :: Information Technology',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Topic :: Internet',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
    packages=find_packages(exclude=['contrib', 'docs', 'tests*']),
    install_requires=install_requires,
    extras_require={
        'tests': 'pytest',  # MIT
        'docs': [
            'sphinx',  # BSD
            'sphinx_rtd_theme',  # MIT
        ]
    },
    setup_requires=[
        'pytest-runner',  # MIT
        # 'flake8',   # MIT
    ],
    tests_require=[
        'pytest',  # MIT
        'prettyconf',  # MIT
        'tox',  # MIT
    ],
    test_suite='tests',
    include_package_data=True,
    zip_safe=False,
)
