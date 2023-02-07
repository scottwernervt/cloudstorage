import io
import re
from glob import glob
from os.path import basename, dirname, join, splitext

from setuptools import find_packages, setup

INSTALL_REQUIRES = [
    "inflection>=0.3.1",
    "python-dateutil>=2.7.3",
    "python-magic>=0.4.15",
]
EXTRAS_REQUIRE = {
    "amazon": ["boto3>=1.8.00", "boto3-stubs[s3]>=1.12.41.0"],
    "digitalocean": ["boto3>=1.8.00", "boto3-stubs[s3]>=1.12.41.0"],
    "google": ["google-cloud-storage>=1.18.0", "requests>=2.19.1"],
    "local": [
        "filelock>=3.0.0",
        "itsdangerous>=1.1.0",
        "xattr>=0.9.6; sys_platform != 'win32'",
    ],
    "microsoft": ["azure==4.0.0"],
    "minio": ["minio==4.0.0"],
    "rackspace": ["openstacksdk<=0.17.2", "rackspacesdk==0.7.5", "requests>=2.19.1"],
    "tests": ["flake8==3.8.4", "prettyconf", "pytest==6.2.1", "requests>=2.19.1"],
    "lint": [
        "black==20.8b1",
        "flake8-bugbear==20.11.1",
        "flake8==3.8.4",
        "pre-commit==2.9.3",
    ],
    "check": [
        "check-manifest==0.46",
        "docutils==0.16",
        "pygments==2.7.4",
        "readme-renderer==28.0",
        "twine==3.3.0",
    ],
    "docs": [
        "pygments==2.7.4",
        "sphinx==3.4.3",
        "sphinx_autodoc_typehints==1.11.1",
        "sphinx_rtd_theme==0.5.1",
    ],
}
EXTRAS_REQUIRE["dev"] = EXTRAS_REQUIRE["tests"] + EXTRAS_REQUIRE["lint"] + ["tox"]


def read(*names, **kwargs):
    with io.open(
        join(dirname(__file__), *names), encoding=kwargs.get("encoding", "utf8")
    ) as fh:
        return fh.read()


def find_version(fname):
    """Attempts to find the version number in the file names fname.
    Raises RuntimeError if not found.
    """
    version = ""
    with open(fname, "r") as fp:
        reg = re.compile(r'__version__ = [\'"]([^\'"]*)[\'"]')
        for line in fp:
            m = reg.match(line)
            if m:
                version = m.group(1)
                break
    if not version:
        raise RuntimeError("Cannot find version information")
    return version


setup(
    name="cloudstorage",
    version=find_version("src/cloudstorage/__init__.py"),
    license="MIT",
    description="Unified cloud storage API for storage services.",
    long_description="%s\n%s"
    % (
        re.compile("^.. start-badges.*^.. end-badges", re.M | re.S).sub(
            "", read("README.rst")
        ),
        re.sub(":[a-z]+:`~?(.*?)`", r"``\1``", read("CHANGELOG.rst")),
    ),
    long_description_content_type="text/x-rst",
    author="Scott Werner",
    author_email="scott.werner.vt@gmail.com",
    url="https://github.com/scottwernervt/cloudstorage/",
    packages=find_packages("src", exclude=("test*", "docs*")),
    package_dir={"": "src"},
    py_modules=[splitext(basename(path))[0] for path in glob("src/*.py")],
    include_package_data=True,
    zip_safe=False,
    python_requires=">=3.5",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Environment :: Web Environment",
        "Intended Audience :: Developers",
        "Intended Audience :: Information Technology",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Topic :: Internet",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    keywords=" ".join(
        [
            "storage",
            "amazon",
            "aws",
            "s3",
            "azure",
            "rackspace",
            "cloudfiles",
            "google",
            "cloudstorage",
            "gcs",
            "minio",
        ]
    ),
    install_requires=INSTALL_REQUIRES,
    extras_require=EXTRAS_REQUIRE,
    test_suite="tests",
    project_urls={
        "Changelog": "https://cloudstorage.readthedocs.io/en/latest/changelog.html",
        "Issues": "https://github.com/scottwernervt/cloudstorage/issues",
    },
)
