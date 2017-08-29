.. :changelog:

Changelog
---------

0.4 (2017-08-29)
++++++++++++++++

* Implement Microsoft Azure Storage driver (#1).
* Google upload_blob is failing for binary stream (#7 and #8).
* Fixed type annotations using mypy.
* Formatted code using flake8 recommendations.

0.3 (2017-05-24)
++++++++++++++++

* Fixes #6: Add kwargs to each driver's init method.

0.2 (2017-04-21)
++++++++++++++++

* Add pip cache to travis yml file to speed up tests.
* Set wheel python-tag to py3 only
* Set tox to pass all env variables to py.test
* Add travis repo encrypted env variables for running tests.

0.1 (2017-04-20)
++++++++++++++++

* First release.