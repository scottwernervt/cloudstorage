.. :changelog:

Changelog
---------

1.0.0 (Unreleased)
+++++++++++++++++++

Features

* Start following (`Semantic Versioning <https://semver.org/>`_).


0.11.0 (2021-01-15)
+++++++++++++++++++

Features

* Atomic local file write (`#68 <https://github.com/scottwernervt/cloudstorage/pull/68>`_). Thanks @habibutsu.
* New DigitalOcean Spaces Driver (`#67 <https://github.com/scottwernervt/cloudstorage/pull/67>`_). Thanks @RangelReale.

Bugs

* Convert ``bytes`` to ``str`` before saving the json file for Windows Xattr simulator (`#66 <https://github.com/scottwernervt/cloudstorage/pull/66>`_). Thanks @RangelReale!
* Handle ``pathlib.Path`` properly for ``Blob.download`` download and ``Container.upload_blob`` (`#65 <https://github.com/scottwernervt/cloudstorage/pull/65>`_). Thanks @sibowsb!
* Fix Bob ``NotFoundError`` message for AWS driver (`#64 <https://github.com/scottwernervt/cloudstorage/pull/64>`_). Thanks @sibowsb!

Other

0.10.1 (2020-04-20)
+++++++++++++++++++

Features

* Add support to mimic ``xattr`` in Windows by storing data in ``.<filename>.xattr`` (`#56 <https://github.com/scottwernervt/cloudstorage/pull/56>`_). Thanks @RangelReale.
* Add support for ``python 3.8``.

Bugs

* Freeze package ``azure`` to version `4.0.0` (`#58 <https://github.com/scottwernervt/cloudstorage/issues/58>`_).
* Drop support for ``python 3.4`` due to ``PyYAML`` requirement ``!=3.4.*``.

0.10.0 (2019-08-10)
+++++++++++++++++++

Bugs

* Azure ``get_blob`` raises ``TypeError`` when Content MD5 missing in remote (`#47 <https://github.com/scottwernervt/cloudstorage/issues/47>`_). Thanks @matt-carr.
* ``AzureStorageDriver`` reads stream twice without rewinding (`#44 <https://github.com/scottwernervt/cloudstorage/issues/44>`_). Thanks @matt-carr.
* Update package dependencies to fix tests (`#43 <https://github.com/scottwernervt/cloudstorage/issues/43>`_).

Changes from 0.9.0:

* Azure driver will issue a warning if Content MD5 is not populated.
* Google driver tests will not run if credentials file is not present.

0.9.0 (2018-11-29)
++++++++++++++++++

Features

* Driver authentication can be verified using ``DriverName.validate_credentials()`` (`#34 <https://github.com/scottwernervt/cloudstorage/issues/34>`_).

Changes from 0.8.0:

* Initializing ``GoogleStorageDriver`` with an invalid credentials file will
  raise ``CredentialsError`` exception instead of ``CloudStorageError``.

0.8.0 (2018-11-06)
++++++++++++++++++

Features

* ``Blob`` and ``Container``'s ``meta_data`` is now a case insensitive dictionary.
* Add new driver for Minio Cloud Storage (`#25 <https://github.com/scottwernervt/cloudstorage/issues/25>`_).
  Install driver requirements with: ``pip install cloudstorage[minio]``.

Other

* Move to ``src`` folder structure for package.

0.7.0 (2018-10-03)
++++++++++++++++++

Features

* ``Cache-Control`` supported for Amazon, Google, Local, and Microsoft (`#11 <https://github.com/scottwernervt/cloudstorage/issues/11>`_).
* Each driver's package dependencies are now optional (`#4 <https://github.com/scottwernervt/cloudstorage/issues/4>`_).

Other

* Remove rackspace package dependency ``rfc6266_parser``.
* Add ``flake8`` linting and ``sphinx`` doc building to tox and travis.

0.6 (2018-07-24)
++++++++++++++++

* Copy metadata from ``setup.py`` to ``setup.cfg``
* Add rate limit timeout when calling google cloud storage backend during tests.
* Catch ``UnicodeDecodeError`` when decoding local file attribute values.
* Upgrade dependencies and include ``requirements.txt`` and ``dev-requirements.txt``.

0.5 (2018-02-26)
++++++++++++++++

* Update rackspacesdk to 0.7.5 and fix broken API calls (`#14 <https://github.com/scottwernervt/cloudstorage/issues/14>`_).

0.4 (2017-08-29)
++++++++++++++++

* Implement Microsoft Azure Storage driver (`#1 <https://github.com/scottwernervt/cloudstorage/issues/1>`_).
* Google upload_blob is failing for binary stream (`#7 <https://github.com/scottwernervt/cloudstorage/issues/7>`_ and `#8 <https://github.com/scottwernervt/cloudstorage/issues/8>`_).
* Fixed type annotations using mypy.
* Formatted code using flake8 recommendations.

0.3 (2017-05-24)
++++++++++++++++

* Fixes `#6 <https://github.com/scottwernervt/cloudstorage/issues/6>`_: Add kwargs to each driver's init method.

0.2 (2017-04-21)
++++++++++++++++

* Add pip cache to travis yml file to speed up tests.
* Set wheel python-tag to py3 only
* Set tox to pass all env variables to py.test
* Add travis repo encrypted env variables for running tests.

0.1 (2017-04-20)
++++++++++++++++

* First release.