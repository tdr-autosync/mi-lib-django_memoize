django-memoize
================

.. module:: memoize

About
-----

**django-memoize** is an implementation
of `memoization <http://en.wikipedia.org/wiki/Memoization>`_ technique
for Django. You can think of it as a cache for function or method results.

Installation
------------

Install the extension with one of the following commands::

    $ easy_install django-memoize

or alternatively if you have pip installed::

    $ pip install django-memoize

Set Up
------

Add 'memoize' to your INSTALLED_APPS in settings.py::

    INSTALLED_APPS = [
        '...',
        'memoize',
    ]

Memoization is managed through a ``Memoizer`` instance::

    from memoize import Memoizer

    memoizer = Memoizer()

However, we recommend to use already defined instance of ``Memoizer`` and
use its methods::

    from memoize import memoize, delete_memoized, delete_memoized_verhash

    @memoize(timeout=60)
    def count_objects():
        pass

    delete_memoized(count_objects)

Memoization
-----------

See :meth:`~Memoizer.memoize`

In memoization, the functions arguments are also included into the cache_key.

Memoize is also designed for methods, since it will take into account
the `repr <https://docs.python.org/2/library/functions.html#func-repr>`_ of the
'self' or 'cls' argument as part of the cache key.

The theory behind memoization is that if you have a function you need
to call several times in one request, it would only be calculated the first
time that function is called with those arguments. For example, a model
object that determines if a user has a role. You might need to call this
function many times during a single request. To keep from hitting the database
every time this information is needed you might do something like the following::

    class Person(models.Model):
    	@memoize(timeout=50)
    	def has_membership(self, role_id):
    		return Group.objects.filter(user=self, role_id=role_id).count() >= 1


.. warning::

    Using mutable objects (classes, etc) as part of the cache key can become
    tricky. It is suggested to not pass in an object instance into a memoized
    function. However, the memoize does perform a repr() on the passed in arguments
    so that if the object has a __repr__ function that returns a uniquely
    identifying string for that object, that will be used as part of the
    cache key.

    For example, a model person object that returns the database id as
    part of the unique identifier.::

        class Person(models.Model):
            def __repr__(self):
                return "%s(%s)" % (self.__class__.__name__, self.id)

Deleting memoize cache
``````````````````````

You might need to delete the cache on a per-function bases. Using the above
example, lets say you change the users permissions and assign them to a role,
but now you need to re-calculate if they have certain memberships or not.
You can do this with the :meth:`~Memoizer.delete_memoized` function.::

	delete_memoized('user_has_membership')

.. note::

  If only the function name is given as parameter, all the memoized versions
  of it will be invalidated. However, you can delete specific cache by
  providing the same parameter values as when caching. In following
  example only the ``user``-role cache is deleted:

  .. code-block:: python

     user_has_membership('demo', 'admin')
     user_has_membership('demo', 'user')

     delete_memoized('user_has_membership', 'demo', 'user')

API
---

.. autoclass:: Memoizer
   :members: memoize, delete_memoized, delete_memoized_verhash

.. include:: ../CHANGES
