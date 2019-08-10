import io
import re
from glob import glob
from os.path import basename, dirname, join, splitext

from setuptools import find_packages, setup


def read(*names, **kwargs):
    with io.open(
            join(dirname(__file__), *names),
            encoding=kwargs.get('encoding', 'utf8')
    ) as fh:
        return fh.read()


setup(
    name='cloudstorage',
    version='0.10.0',
    license='MIT',
    description='Unified cloud storage API for storage services.',
    long_description='%s\n%s' % (
        re.compile('^.. start-badges.*^.. end-badges', re.M | re.S).sub(
            '', read('README.rst')),
        re.sub(':[a-z]+:`~?(.*?)`', r'``\1``', read('CHANGELOG.rst'))
    ),
    author='Scott Werner',
    author_email='scott.werner.vt@gmail.com',
    url='https://github.com/scottwernervt/cloudstorage/',
    packages=find_packages('src'),
    package_dir={'': 'src'},
    py_modules=[splitext(basename(path))[0] for path in glob('src/*.py')],
    include_package_data=True,
    zip_safe=False,
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
        'minio',
    ]),
    install_requires=[
        'inflection>=0.3.1',  # MIT
        'python-dateutil>=2.7.3',  # Simplified BSD
        'python-magic>=0.4.15',  # MIT
        # Python 3.4 needs backports
        'typing;python_version<"3.5"',  # PSF
        'httpstatus35;python_version<"3.5"',  # PSF
    ],
    extras_require={
        'amazon': [
            'boto3>=1.8.00',  # Apache 2.0
        ],
        'google': [
            'google-cloud-storage>=1.18.0',  # Apache 2.0
            'requests>=2.19.1',  # Apache 2.0
        ],
        'local': [
            'filelock>=3.0.0',  # Public Domain
            'itsdangerous>=1.1.0',  # BSD License
            'xattr>=0.9.6',  # MIT
        ],
        'microsoft': [
            'azure>=4.0.0',  # MIT
        ],
        'minio': [
            'minio>=4.0.0',  # Apache 2.0
        ],
        'rackspace': [
            'openstacksdk<=0.17.2',  # Apache 2.0
            'rackspacesdk>=0.7.5',  # Apache 2.0
            'requests>=2.19.1',  # Apache 2.0
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
        'requests>=2.19.1',
        'tox',  # MIT
    ],
    test_suite='tests',
)
