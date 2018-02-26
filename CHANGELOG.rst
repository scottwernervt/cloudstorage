.. :changelog:

Changelog
---------

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