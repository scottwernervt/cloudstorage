============
Contributing
============

Contributions are welcome, and they are greatly appreciated! Every little bit 
helps, and credit will always be given.

Types of Contributions
----------------------

You can contribute in many ways:

Report Bugs
~~~~~~~~~~~

Report bugs at https://github.com/scottwernervt/cloudstorage/issues.

If you are reporting a bug, please include:

* Any details about your local setup that might be helpful in troubleshooting.
* If you can, provide detailed steps to reproduce the bug.
* If you don't have steps to reproduce the bug, just note your observations in
  as much detail as you can. Questions to start a discussion about the issue
  are welcome.

Fix Bugs
~~~~~~~~

Look through the GitHub issues for bugs. Anything tagged with "bug"
is open to whoever wants to implement it.

Implement Features
~~~~~~~~~~~~~~~~~~

Look through the GitHub issues for features. Anything tagged with "enhancement"
and "help wanted" is open to whoever wants to implement it.

Please do not combine multiple feature enhancements into a single pull request.

Write Documentation
~~~~~~~~~~~~~~~~~~~

cloudstorage could always use more documentation, whether as part of the
official cloudstorage docs or in docstrings. Documentation is written in
`reStructured Text`_ (rST). A quick rST reference can be found
`here <http://docutils.sourceforge.net/docs/user/rst/quickref.html>`_.
Builds are powered by Sphinx_.

If you want to review your changes on the documentation locally, you can do::

    pip install -r docs/requirements.txt
    sphinx-build docs/ docs/_build/

This will compile the documentation.

Submit Feedback
~~~~~~~~~~~~~~~

The best way to send feedback is to file an issue at
https://github.com/scottwernervt/cloudstorage/issues.

If you are proposing a feature:

* Explain in detail how it would work.
* Keep the scope as narrow as possible, to make it easier to implement.

Setting Up the Code for Local Development
-----------------------------------------

Here's how to set up `cloudstorage` for local development.

1. Fork the `cloudstorage` repo on GitHub.

2. Clone your fork locally::

    $ git clone git@github.com:your_name_here/cloudstorage.git

3. Install your local copy into a virtualenv. Assuming you have virtualenvwrapper installed, this is how you set up your fork for local development::

    $ mkvirtualenv cloudstorage
    $ cd cloudstorage/
    $ pip install -r dev-requirements.txt

4. Create a branch for local development::

    $ git checkout -b name-of-your-bugfix-or-feature

Now you can make your changes locally.

5. When you're done making changes, check that your changes pass the tests::

    $ tox

6. Please run flake8 and fix any glaring issues: ::

    $ flake8 .

7. Add yourself to ``AUTHORS.rst``.

8. Commit your changes and push your branch to GitHub::

    $ git add .
    $ git commit -m "Your detailed description of your changes."
    $ git push origin name-of-your-bugfix-or-feature

9. Submit a pull request through the GitHub website.


Contributor Guidelines
----------------------

Pull Request Guidelines
~~~~~~~~~~~~~~~~~~~~~~~

Before you submit a pull request, check that it meets these guidelines:

1. The pull request should include tests.
2. If the pull request adds functionality, the docs should be updated. Put
   your new functionality into a function with a docstring.
3. The pull request should work for Python 3.4, 3.5, 3.6, and 3.7 on Travis CI.
4. Check https://travis-ci.org/scottwernervt/cloudstorage/pull_requests to
   ensure the tests pass for all supported Python versions and platforms.

Coding Standards
~~~~~~~~~~~~~~~~

* PEP8 when sensible.
* Test ruthlessly.
* Write docs for new features.

Testing with tox
----------------

Tox uses py.test under the hood, hence it supports the same syntax for selecting tests.

To run all tests: ::

    $ python setup.py test

To run all tests using various versions of python in virtualenvs defined in tox.ini, just run tox.::

    $ tox

.. _Sphinx: http://sphinx.pocoo.org/
.. _`reStructured Text`: http://docutils.sourceforge.net/rst.html
