#!/usr/bin/env python
"""
django-memoize
--------------

**django-memoize** is an implementation
of `memoization <http://en.wikipedia.org/wiki/Memoization>`_ technique
for Django. You can think of it as a cache for function or method results.

"""

from setuptools import setup

setup(
    name='django-memoize',
    version='2.1.0',
    packages=['memoize'],
    include_package_data=True,
    license='BSD License',
    description='An implementation of memoization technique for Django.',
    url='https://github.com/tvavrys/django-memoize',
    author='Thomas Vavrys',
    author_email='tvavrys@sleio.com',
    long_description=__doc__,
    install_requires=[
        'django >= 1.7'
    ],
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Framework :: Django',
        'Framework :: Django :: 1.7',
        'Framework :: Django :: 1.8',
        'Framework :: Django :: 1.9',
        'Framework :: Django :: 1.10',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
    ],
)
