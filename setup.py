#!/usr/bin/env python
"""
django-memoize
--------------

**django-memoize** is an implementation
of `memoization <http://en.wikipedia.org/wiki/Memoization>`_ technique
for Django. You can think of it as a cache for function or method results.

"""

from setuptools import setup, find_packages

setup(
    name='django-memoize',
    version='1.1.2',
    url='https://github.com/tvavrys/django-memoize',
    license='BSD',
    author='Thomas Vavrys',
    author_email='tvavrys@sleio.com',
    description='An implementation of memoization technique for Django.',
    long_description=__doc__,
    packages=find_packages(),
    zip_safe=False,
    install_requires=[
        'django'
    ],
    classifiers=[
        'Environment :: Web Environment',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ],
    test_suite='setuptest.setuptest.SetupTestSuite',
    tests_require=(
        'django-setuptest',
        'argparse',  # Required by django-setuptools on Python 2.6
    ),
)
