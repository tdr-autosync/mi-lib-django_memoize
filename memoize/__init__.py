# -*- coding: utf-8 -*-
__version__ = '2.1.0'
__versionfull__ = __version__

import functools
import hashlib
import inspect
import logging
import uuid

from django.conf import settings
from django.core.cache import cache as default_cache
from django.core.cache.backends.base import DEFAULT_TIMEOUT
from django.utils.encoding import force_bytes

logger = logging.getLogger(__name__)


class DefaultCacheObject(object):
    pass


DEFAULT_CACHE_OBJECT = DefaultCacheObject()


def _get_argspec(f):
    try:
        argspec = inspect.getargspec(f)
    except ValueError:
        # this can happen in python 3.5 when
        # function has keyword-only arguments or annotations
        argspec = inspect.getfullargspec(f)
    return argspec


def function_namespace(f, args=None):
    """
    Attempts to returns unique namespace for function
    """
    m_args = _get_argspec(f).args
    instance_token = None

    instance_self = getattr(f, '__self__', None)

    if instance_self and not inspect.isclass(instance_self):
        instance_token = repr(f.__self__)
    elif m_args and m_args[0] == 'self' and args:
        instance_token = repr(args[0])

    module = f.__module__ or __name__

    if hasattr(f, '__qualname__'):
        name = f.__qualname__
    else:
        klass = getattr(f, '__self__', None)

        if klass and not inspect.isclass(klass):
            klass = klass.__class__

        if not klass:
            klass = getattr(f, 'im_class', None)

        if not klass:
            if m_args and args:
                if m_args[0] == 'self':
                    klass = args[0].__class__
                elif m_args[0] == 'cls':
                    klass = args[0]

        if klass:
            name = klass.__name__ + '.' + f.__name__
        else:
            name = f.__name__

    ns = '.'.join((module, name))

    if instance_token:
        ins = '.'.join((module, name, instance_token))
    else:
        ins = None

    return ns, ins


class Memoizer(object):
    """
    This class is used to control the memoizer objects.
    """
    def __init__(self, cache=default_cache, cache_prefix='memoize',
                 default_cache_value=DEFAULT_CACHE_OBJECT):
        self.cache = cache
        self.cache_prefix = cache_prefix
        self.default_cache_value = default_cache_value

    def get(self, key):
        "Proxy function for internal cache object."
        return self.cache.get(key=key, default=self.default_cache_value)

    def set(self, key, value, timeout=DEFAULT_TIMEOUT):
        "Proxy function for internal cache object."
        self.cache.set(key=key, value=value, timeout=timeout)

    def add(self, key, value, timeout=DEFAULT_TIMEOUT):
        "Proxy function for internal cache object."
        self.cache.add(key=key, value=value, timeout=timeout)

    def delete(self, key):
        "Proxy function for internal cache object."
        self.cache.delete(key=key)

    def delete_many(self, *keys):
        "Proxy function for internal cache object."
        self.cache.delete_many(keys=keys)

    def clear(self):
        "Proxy function for internal cache object."
        self.cache.clear()

    def get_many(self, *keys):
        "Proxy function for internal cache object."
        d = self.cache.get_many(keys=keys)

        values = []
        for key in keys:
            values.append(
                d.get(key)
            )

        return values

    def set_many(self, mapping, timeout=DEFAULT_TIMEOUT):
        "Proxy function for internal cache object."
        self.cache.set_many(data=mapping, timeout=timeout)

    def _memvname(self, funcname):
        return funcname + '_memver'

    def _memoize_make_version_hash(self):
        return uuid.uuid4().hex

    def _memoize_version(self, f, args=None,
                         reset=False, delete=False, timeout=DEFAULT_TIMEOUT):
        """
        Updates the hash version associated with a memoized function or method.
        """
        fname, instance_fname = function_namespace(f, args=args)
        version_key = self._memvname(fname)
        fetch_keys = [version_key]

        if instance_fname:
            instance_version_key = self._memvname(instance_fname)
            fetch_keys.append(instance_version_key)

        # Only delete the per-instance version key or per-function version
        # key but not both.
        if delete:
            self.delete(fetch_keys[-1])
            return fname, None

        version_data_list = self.get_many(*fetch_keys)
        dirty = False

        if version_data_list[0] is None:
            version_data_list[0] = self._memoize_make_version_hash()
            dirty = True

        if instance_fname and version_data_list[1] is None:
            version_data_list[1] = self._memoize_make_version_hash()
            dirty = True

        # Only reset the per-instance version or the per-function version
        # but not both.
        if reset:
            fetch_keys = fetch_keys[-1:]
            version_data_list = [self._memoize_make_version_hash()]
            dirty = True

        if dirty:
            self.set_many(
                dict(zip(fetch_keys, version_data_list)), timeout=timeout
            )

        return fname, ''.join(version_data_list)

    def _memoize_make_cache_key(self, make_name=None, timeout=DEFAULT_TIMEOUT):
        """
        Function used to create the cache_key for memoized functions.
        """
        def make_cache_key(f, *args, **kwargs):
            _timeout = getattr(timeout, 'cache_timeout', timeout)
            fname, version_data = self._memoize_version(f, args=args,
                                                        timeout=_timeout)

            #: this should have to be after version_data, so that it
            #: does not break the delete_memoized functionality.
            if callable(make_name):
                altfname = make_name(fname)
            else:
                altfname = fname

            if callable(f):
                keyargs, keykwargs = self._memoize_kwargs_to_args(
                    f, *args, **kwargs
                )
            else:
                keyargs, keykwargs = args, kwargs

            cache_key = hashlib.md5(
                force_bytes((altfname, keyargs, keykwargs))
            ).hexdigest()
            cache_key += version_data

            if self.cache_prefix:
                cache_key = '%s:%s' % (self.cache_prefix, cache_key)

            return cache_key
        return make_cache_key

    def _memoize_kwargs_to_args(self, f, *args, **kwargs):
        #: Inspect the arguments to the function
        #: This allows the memoization to be the same
        #: whether the function was called with
        #: 1, b=2 is equivilant to a=1, b=2, etc.
        new_args = []
        arg_num = 0
        argspec = _get_argspec(f)

        args_len = len(argspec.args)
        for i in range(args_len):
            if i == 0 and argspec.args[i] in ('self', 'cls'):
                #: use the repr of the class instance
                #: this supports instance methods for
                #: the memoized functions, giving more
                #: flexibility to developers
                arg = repr(args[0])
                arg_num += 1
            elif argspec.args[i] in kwargs:
                arg = kwargs.pop(argspec.args[i])
            elif arg_num < len(args):
                arg = args[arg_num]
                arg_num += 1
            elif abs(i - args_len) <= len(argspec.defaults):
                arg = argspec.defaults[i - args_len]
                arg_num += 1
            else:
                arg = None
                arg_num += 1

            #: Attempt to convert all arguments to a
            #: hash/id or a representation?
            #: Not sure if this is necessary, since
            #: using objects as keys gets tricky quickly.
            # if hasattr(arg, '__class__'):
            #     try:
            #         arg = hash(arg)
            #     except:
            #         arg = repr(arg)

            #: Or what about a special __cacherepr__ function
            #: on an object, this allows objects to act normal
            #: upon inspection, yet they can define a representation
            #: that can be used to make the object unique in the
            #: cache key. Given that a case comes across that
            #: an object "must" be used as a cache key
            # if hasattr(arg, '__cacherepr__'):
            #     arg = arg.__cacherepr__

            new_args.append(arg)

        # If there are any missing varargs then
        # just append them since consistency of the key trumps order.
        if argspec.varargs and args_len < len(args):
            new_args.extend(args[args_len:])

        return tuple(new_args), kwargs

    def memoize(self, timeout=DEFAULT_TIMEOUT, make_name=None, unless=None):
        """
        Use this to cache the result of a function, taking its arguments into
        account in the cache key.

        Information on
        `Memoization <http://en.wikipedia.org/wiki/Memoization>`_.

        Example::

            @memoize(timeout=50)
            def big_foo(a, b):
                return a + b + random.randrange(0, 1000)

        .. code-block:: pycon

            >>> big_foo(5, 2)
            753
            >>> big_foo(5, 3)
            234
            >>> big_foo(5, 2)
            753

        .. note::

            The returned decorated function now has three function attributes
            assigned to it.

                **uncached**
                    The original undecorated function. readable only

                **cache_timeout**
                    The cache timeout value for this function. For a custom
                    value to take affect, this must be set before the function
                    is called.

                    readable and writable

                **make_cache_key**
                    A function used in generating the cache_key used.

                    readable and writable


        :param timeout: Default: 300. If set to an integer, will cache
                        for that amount of time. Unit of time is in seconds.
        :param make_name: Default None. If set this is a function that accepts
                          a single argument, the function name, and returns a
                          new string to be used as the function name.
                          If not set then the function name is used.
        :param unless: Default None. Cache will *always* execute the caching
                       facilities unelss this callable is true.
                       This will bypass the caching entirely.

        """

        def memoize(f):
            @functools.wraps(f)
            def decorated_function(*args, **kwargs):
                #: bypass cache
                if callable(unless) and unless() is True:
                    return f(*args, **kwargs)

                try:
                    cache_key = decorated_function.make_cache_key(
                        f, *args, **kwargs
                    )
                    rv = self.get(cache_key)
                except Exception:
                    if settings.DEBUG:
                        raise
                    logger.exception(
                        "Exception possibly due to cache backend."
                    )
                    return f(*args, **kwargs)

                if rv == self.default_cache_value:
                    rv = f(*args, **kwargs)
                    try:
                        self.set(
                            cache_key, rv,
                            timeout=decorated_function.cache_timeout
                        )
                    except Exception:
                        if settings.DEBUG:
                            raise
                        logger.exception(
                            "Exception possibly due to cache backend."
                        )
                return rv

            decorated_function.uncached = f
            decorated_function.cache_timeout = timeout
            decorated_function.make_cache_key = self._memoize_make_cache_key(
                make_name, decorated_function
            )
            decorated_function.delete_memoized = (
                lambda: self.delete_memoized(f)
            )

            return decorated_function
        return memoize

    def delete_memoized(self, f, *args, **kwargs):
        """
        Deletes the specified functions caches, based by given parameters.
        If parameters are given, only the functions that were memoized with
        them will be erased. Otherwise all versions of the caches will be
        forgotten.

        Example::

            @memoize(50)
            def random_func():
                return random.randrange(1, 50)

            @memoize()
            def param_func(a, b):
                return a+b+random.randrange(1, 50)

        .. code-block:: pycon

            >>> random_func()
            43
            >>> random_func()
            43
            >>> delete_memoized('random_func')
            >>> random_func()
            16
            >>> param_func(1, 2)
            32
            >>> param_func(1, 2)
            32
            >>> param_func(2, 2)
            47
            >>> delete_memoized('param_func', 1, 2)
            >>> param_func(1, 2)
            13
            >>> param_func(2, 2)
            47

        Delete memoized is also smart about instance methods vs class methods.

        When passing a instancemethod, it will only clear the cache related
        to that instance of that object. (object uniqueness can be overridden
        by defining the __repr__ method, such as user id).

        When passing a classmethod, it will clear all caches related across
        all instances of that class.

        Example::

            class Adder(object):
                @memoize()
                def add(self, b):
                    return b + random.random()

        .. code-block:: pycon

            >>> adder1 = Adder()
            >>> adder2 = Adder()
            >>> adder1.add(3)
            3.23214234
            >>> adder2.add(3)
            3.60898509
            >>> delete_memoized(adder.add)
            >>> adder1.add(3)
            3.01348673
            >>> adder2.add(3)
            3.60898509
            >>> delete_memoized(Adder.add)
            >>> adder1.add(3)
            3.53235667
            >>> adder2.add(3)
            3.72341788

        :param fname: Name of the memoized function, or a reference to the
                      function.
        :param \*args: A list of positional parameters used with memoized
                       function.
        :param \**kwargs: A dict of named parameters used with memoized
                          function.

        .. note::

            django-memoize uses inspect to order kwargs into positional args
            when the function is memoized. If you pass a function reference
            into ``fname`` instead of the function name, django-memoize will
            be able to place the args/kwargs in the proper order, and delete
            the positional cache.

            However, if ``delete_memoized`` is just called with the name of the
            function, be sure to pass in potential arguments in the same order
            as defined in your function as args only, otherwise django-memoize
            will not be able to compute the same cache key.

        .. note::

            django-memoize maintains an internal random version hash for the
            function. Using delete_memoized will only swap out the version
            hash, causing the memoize function to recompute results and put
            them into another key.

            This leaves any computed caches for this memoized function within
            the caching backend.

            It is recommended to use a very high timeout with memoize if using
            this function, so that when the version has is swapped, the old
            cached results would eventually be reclaimed by the caching
            backend.
        """
        if not callable(f):
            raise DeprecationWarning(
                "Deleting messages by relative name is no longer"
                " reliable, please switch to a function reference"
            )

        try:
            if not args and not kwargs:
                self._memoize_version(f, reset=True)
            else:
                cache_key = f.make_cache_key(f.uncached, *args, **kwargs)
                self.delete(cache_key)
        except Exception:
            if settings.DEBUG:
                raise
            logger.exception("Exception possibly due to cache backend.")

    def delete_memoized_verhash(self, f, *args):
        """
        Delete the version hash associated with the function.

        .. warning::

            Performing this operation could leave keys behind that have
            been created with this version hash. It is up to the application
            to make sure that all keys that may have been created with this
            version hash at least have timeouts so they will not sit orphaned
            in the cache backend.
        """
        if not callable(f):
            raise DeprecationWarning(
                "Deleting messages by relative name is no longer"
                " reliable, please use a function reference"
            )

        try:
            self._memoize_version(f, delete=True)
        except Exception:
            if settings.DEBUG:
                raise
            logger.exception("Exception possibly due to cache backend.")


# Memoizer instance
_memoizer = Memoizer()

# Public objects
memoize = _memoizer.memoize
delete_memoized = _memoizer.delete_memoized
delete_memoized_verhash = _memoizer.delete_memoized_verhash
