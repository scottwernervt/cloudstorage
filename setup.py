import os
import re

from setuptools import find_packages, setup

ROOT = os.path.abspath(os.path.dirname(__file__))
VERSION_RE = re.compile(r'''__version__ = ['"]([0-9.]+)['"]''')

install_requires = [
    'inflection>=0.3.1',  # MIT
    'python-dateutil>=2.7.3',  # Simplified BSD
    'python-magic>=0.4.15',  # MIT
    'requests>=2.19.1',  # Apache 2.0
    # Python 3.4 needs backports
    'typing;python_version<"3.5"',  # PSF
    'httpstatus35;python_version<"3.5"',  # PSF
]


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
    project_urls={
        'Bug Tracker': 'https://github.com/scottwernervt/cloudstorage/issues',
        'Documentation': 'https://cloudstorage.readthedocs.io',
        'Source Code': 'https://github.com/scottwernervt/cloudstorage',
    },
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
        'Programming Language :: Python :: 3.7',
        'Topic :: Internet',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
    packages=find_packages(exclude=['contrib', 'docs', 'tests']),
    install_requires=install_requires,
    extras_require={
        'amazon': [
            'boto3>=1.7.60',  # Apache 2.0
        ],
        'google': [
            'google-cloud-storage>=1.10.0',  # Apache 2.0
        ],
        'local': [
            'filelock>=3.0.0',  # Public Domain
            'itsdangerous>=0.24',  # BSD License
            'xattr>=0.9.3',  # MIT
        ],
        'microsoft': [
            'azure>=3.0.0',  # MIT
        ],
        'rackspace': [
            'rackspacesdk>=0.7.5',  # Apache 2.0
        ],
        'docs': [
            'sphinx',  # BSD
            'sphinx_rtd_theme',  # MIT
            'sphinx_autodoc_typehints',  # MIT
            'Pygments',  # BSD
        ],
    },
    setup_requires=[
        'pytest-runner',  # MIT
    ],
    tests_require=[
        'flake8',  # MIT
        'pytest',  # MIT
        'prettyconf',  # MIT
        'tox',  # MIT
    ],
    test_suite='tests',
    include_package_data=True,
    zip_safe=False,
)
