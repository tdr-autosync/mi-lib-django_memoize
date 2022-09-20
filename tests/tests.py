# -*- coding: utf-8 -*-
# vi:si:et:sw=4:sts=4:ts=4

import datetime
import random
import sys
import time
import logging

from django.test import SimpleTestCase
from django.conf import settings

from freezegun import freeze_time
from memoize import Memoizer, _get_argspec, function_namespace
from mock import MagicMock, patch


class MemoizeTestCase(SimpleTestCase):
    def setUp(self):
        self.memoizer = Memoizer()

    def test_00_set(self):
        self.memoizer.set('hi', 'hello')

        assert self.memoizer.get('hi') == 'hello'

    def test_01_add(self):
        self.memoizer.add('hi', 'hello')

        assert self.memoizer.get('hi') == 'hello'

        self.memoizer.add('hi', 'foobar')

        assert self.memoizer.get('hi') == 'hello'

    def test_02_delete(self):
        self.memoizer.set('hi', 'hello')

        self.memoizer.delete('hi')

        assert self.memoizer.get('hi') is self.memoizer.default_cache_value

    def test_03_delete_many(self):
        self.memoizer.set('hi', 'hello')
        self.memoizer.set('bye', 'goodbye')

        self.memoizer.delete_many('hi', 'bye')

        assert self.memoizer.get('hi') is self.memoizer.default_cache_value
        assert self.memoizer.get('bye') is self.memoizer.default_cache_value

    def test_04_clear(self):
        self.memoizer.set('hi', 'hello')
        self.memoizer.set('bye', 'goodbye')

        self.memoizer.clear()

        assert self.memoizer.get('hi') is self.memoizer.default_cache_value
        assert self.memoizer.get('bye') is self.memoizer.default_cache_value

    def test_06_memoize(self):
        @self.memoizer.memoize(5)
        def big_foo(a, b, func=lambda x: x):
            func(a)
            return a + b

        test_func = MagicMock()

        big_foo(5, 2, func=test_func)

        # Cached call
        big_foo(5, 2, func=test_func)

        # We are expecting only 1 call here as second one should be cached
        assert test_func.call_count == 1, "Count: {}".format(
            test_func.call_count)

        # different arguments so we should have additional call
        big_foo(5, 3, func=test_func)
        assert test_func.call_count == 2, "Count: {}".format(
            test_func.call_count)
        # Expired
        now = datetime.datetime.utcfromtimestamp(time.time())
        with freeze_time(now) as frozen_datetime:
            frozen_datetime.tick(delta=datetime.timedelta(seconds=6))
            # Cache should be expired so we have increasing amount of calls
            big_foo(5, 2, func=test_func)
            assert test_func.call_count == 3, "Count: {}".format(
                test_func.call_count)
            big_foo(5, 3, func=test_func)
            assert test_func.call_count == 4, "Count: {}".format(
                test_func.call_count)

    def test_06a_memoize(self):
        @self.memoizer.memoize(50)
        def big_foo(a, b):
            return a + b + random.randrange(0, 100000)

        result = big_foo(5, 2)

        assert big_foo(5, 2) == result

    def test_07_delete_memoize(self):
        @self.memoizer.memoize(5)
        def big_foo(a, b):
            return a + b + random.randrange(0, 100000)

        result = big_foo(5, 2)
        result2 = big_foo(5, 3)

        assert big_foo(5, 2) == result
        assert big_foo(5, 2) == result
        assert big_foo(5, 3) != result
        assert big_foo(5, 3) == result2

        self.memoizer.delete_memoized(big_foo)

        assert big_foo(5, 2) != result
        assert big_foo(5, 3) != result2

    def test_07b_delete_memoized_verhash(self):
        @self.memoizer.memoize(5)
        def big_foo(a, b):
            return a + b + random.randrange(0, 100000)

        result = big_foo(5, 2)
        result2 = big_foo(5, 3)

        assert big_foo(5, 2) == result
        assert big_foo(5, 2) == result
        assert big_foo(5, 3) != result
        assert big_foo(5, 3) == result2

        self.memoizer.delete_memoized_verhash(big_foo)

        _fname, _fname_instance = function_namespace(big_foo)
        version_key = self.memoizer._memvname(_fname)
        assert (
            self.memoizer.get(version_key) is self.memoizer.default_cache_value
        )

        assert big_foo(5, 2) != result
        assert big_foo(5, 3) != result2

        assert (
            self.memoizer.get(version_key) is not
            self.memoizer.default_cache_value
        )

    def test_08_delete_memoize(self):
        @self.memoizer.memoize()
        def big_foo(a, b):
            return a + b + random.randrange(0, 100000)

        result_a = big_foo(5, 1)
        result_b = big_foo(5, 2)

        assert big_foo(5, 1) == result_a
        assert big_foo(5, 2) == result_b
        self.memoizer.delete_memoized(big_foo, 5, 2)

        assert big_foo(5, 1) == result_a
        assert big_foo(5, 2) != result_b

        # Cleanup bigfoo 5,1 5,2 or it might conflict with
        # following run if it also uses memcache
        self.memoizer.delete_memoized(big_foo, 5, 2)
        self.memoizer.delete_memoized(big_foo, 5, 1)

    def test_09_args_memoize(self):
        @self.memoizer.memoize()
        def big_foo(a, b):
            return sum(a) + sum(b) + random.randrange(0, 100000)

        result_a = big_foo([5, 3, 2], [1])
        result_b = big_foo([3, 3], [3, 1])

        assert big_foo([5, 3, 2], [1]) == result_a
        assert big_foo([3, 3], [3, 1]) == result_b

        self.memoizer.delete_memoized(big_foo, [5, 3, 2], [1])

        assert big_foo([5, 3, 2], [1]) != result_a
        assert big_foo([3, 3], [3, 1]) == result_b

        # Cleanup bigfoo 5,1 5,2 or it might conflict with
        # following run if it also uses memcache
        self.memoizer.delete_memoized(big_foo, [5, 3, 2], [1])
        self.memoizer.delete_memoized(big_foo, [3, 3], [1])

    def test_10_kwargs_memoize(self):
        @self.memoizer.memoize()
        def big_foo(a, b=None):
            return a + sum(b.values()) + random.randrange(0, 100000)

        result_a = big_foo(1, dict(one=1, two=2))
        result_b = big_foo(5, dict(three=3, four=4))

        assert big_foo(1, dict(one=1, two=2)) == result_a
        assert big_foo(5, dict(three=3, four=4)) == result_b

        self.memoizer.delete_memoized(big_foo, 1, dict(one=1, two=2))

        assert big_foo(1, dict(one=1, two=2)) != result_a
        assert big_foo(5, dict(three=3, four=4)) == result_b

    def test_10a_kwargonly_memoize(self):
        @self.memoizer.memoize()
        def big_foo(a=None):
            if a is None:
                a = 0
            return a + random.random()

        result_a = big_foo()
        result_b = big_foo(5)

        assert big_foo() == result_a
        assert big_foo() < 1
        assert big_foo(5) == result_b
        assert big_foo(5) >= 5 and big_foo(5) < 6

    def test_10a_arg_kwarg_memoize(self):
        @self.memoizer.memoize()
        def f(a, b, c=1):
            return a + b + c + random.randrange(0, 100000)

        assert f(1, 2) == f(1, 2, c=1)
        assert f(1, 2) == f(1, 2, 1)
        assert f(1, 2) == f(1, 2)
        assert f(1, 2) != f(2, 1)
        assert f(1, 2, 3) != f(1, 2)
        with self.assertRaises(TypeError):
            f(1)

    def test_10ab_arg_kwarg_memoize(self):
        @self.memoizer.memoize()
        def f(a, **kwargs):
            return (a, kwargs, random.randrange(0, 100000000))

        f1 = f(1, b=2)
        assert f1 == f(1, b=2)
        assert f1 != f(1, b=4)

        f2 = f(5, c=6)
        assert f2 == f(5, c=6)
        assert f2 != f(7, c=6)

        self.memoizer.delete_memoized(f, 1, b=2)
        assert f1 != f(1, b=2)

        assert f2 == f(5, c=6)
        assert f2 != f(7, c=6)

    def test_10ac_arg_kwarg_memoize(self):
        @self.memoizer.memoize()
        def f(a, *args, **kwargs):
            return (a, args, kwargs, random.randrange(0, 100000000))

        f1 = f(1, 2, b=3)
        assert f1 == f(1, 2, b=3)
        assert f1 != f(1, 3, b=3)

        f2 = f(5, 6, c=7)
        assert f2 == f(5, 6, c=7)
        assert f2 != f(7, 6, c=7)

        self.memoizer.delete_memoized(f, 1, 2, b=3)
        assert f1 != f(1, 2, b=3)

        assert f2 == f(5, 6, c=7)
        assert f2 != f(7, 6, c=7)

        @self.memoizer.memoize()
        def f(a, b=1, *args, **kwargs):
            return (a, b, args, kwargs, random.randrange(0, 100000000))

        f3 = f(1, 3, 4)
        assert f3 == f(1, 3, 4)
        assert f3 == f(*(1, 3, 4))
        assert f3 != f(1, 3)

        self.memoizer.delete_memoized(f, 1, 3, 4)
        assert f3 != f(1, 3, 4)

    def test_10b_classarg_memoize(self):
        @self.memoizer.memoize()
        def bar(a, *args):
            return a.value + random.random() + sum(args)

        class Adder(object):
            def __init__(self, value, *args):
                self.value = (value + sum(args))

        adder = Adder(15)
        adder2 = Adder(20)
        adder3 = Adder(16, 5)
        adder4 = Adder(21, 6)

        w = bar(adder)
        x = bar(adder2)
        y = bar(adder3)
        z = bar(adder4)

        assert w != x
        assert y != z
        assert bar(adder) == w
        assert bar(adder) != x
        assert bar(adder3) == y
        assert bar(adder3) != z

        adder.value = 14
        adder3.value = 15

        assert bar(adder) == w
        assert bar(adder) != x
        assert bar(adder3) == y
        assert bar(adder3) != z

        assert bar(adder) != bar(adder2)
        assert bar(adder3) != bar(adder4)
        assert bar(adder2) == x
        assert bar(adder4) == z

    def test_10c_classfunc_memoize(self):
        class Adder(object):
            def __init__(self, initial):
                self.initial = initial

            @self.memoizer.memoize()
            def add(self, b, *args):
                return self.initial + b + sum(args)

        adder1 = Adder(1)
        adder2 = Adder(2)

        x = adder1.add(3)
        y = adder1.add(3, 4)
        assert adder1.add(3) == x
        assert adder1.add(4) != x
        assert adder1.add(3, 4) == y
        assert adder1.add(4, 4) != y
        assert adder1.add(3) != adder2.add(3)

    def test_10d_classfunc_memoize_delete(self):
        class Adder(object):
            def __init__(self, initial):
                self.initial = initial

            @self.memoizer.memoize()
            def add(self, b, *args):
                return self.initial + b + sum(args) + random.random()

        adder1 = Adder(1)
        adder2 = Adder(2)

        a1 = adder1.add(3)
        a2 = adder2.add(3)
        b1 = adder1.add(3, 1)
        b2 = adder2.add(3, 1)

        assert a1 != a2
        assert a1 != b1
        assert a2 != b2

        assert adder1.add(3) == a1
        assert adder2.add(3) == a2
        assert adder1.add(3, 1) == b1
        assert adder2.add(3, 1) == b2

        self.memoizer.delete_memoized(adder1.add)

        a3 = adder1.add(3)
        a4 = adder2.add(3)
        b3 = adder1.add(3, 1)
        b4 = adder2.add(3, 1)

        self.assertNotEqual(a1, a3)
        self.assertNotEqual(b1, b3)
        assert a1 != a3
        assert b1 != b3
        self.assertEqual(a2, a4)
        self.assertEqual(b2, b4)

        self.memoizer.delete_memoized(Adder.add)

        a5 = adder1.add(3)
        a6 = adder2.add(3)
        b5 = adder1.add(3, 1)
        b6 = adder2.add(3, 1)

        self.assertNotEqual(a5, a6)
        self.assertNotEqual(b5, b6)
        self.assertNotEqual(a3, a5)
        self.assertNotEqual(b3, b5)
        self.assertNotEqual(a4, a6)
        self.assertNotEqual(b4, b6)

    def test_10e_delete_memoize_classmethod(self):
        class Mock(object):
            @classmethod
            @self.memoizer.memoize(5)
            def big_foo(cls, a, b, *args):
                return a + b + sum(args) + random.randrange(0, 100000)

        result = Mock.big_foo(5, 2)
        result2 = Mock.big_foo(5, 3)
        result3 = Mock.big_foo(5, 2, 1)
        result4 = Mock.big_foo(5, 3, 1)

        assert Mock.big_foo(5, 2) == result
        assert Mock.big_foo(5, 2) == result
        assert Mock.big_foo(5, 3) != result
        assert Mock.big_foo(5, 3) == result2
        assert Mock.big_foo(5, 2, 1) == result3
        assert Mock.big_foo(5, 2, 1) == result3
        assert Mock.big_foo(5, 3, 1) != result3
        assert Mock.big_foo(5, 3, 1) == result4

        self.memoizer.delete_memoized(Mock.big_foo)

        assert Mock.big_foo(5, 2) != result
        assert Mock.big_foo(5, 3) != result2
        assert Mock.big_foo(5, 2, 1) != result3
        assert Mock.big_foo(5, 3, 1) != result4

    def test_14_memoized_multiple_arg_kwarg_calls(self):
        @self.memoizer.memoize()
        def big_foo(a, b, c=[1, 1], d=[1, 1]):
            return (sum(a) + sum(b) + sum(c) + sum(d) +
                    random.randrange(0, 100000))

        result_a = big_foo([5, 3, 2], [1], c=[3, 3], d=[3, 3])

        assert big_foo([5, 3, 2], [1], d=[3, 3], c=[3, 3]) == result_a
        assert big_foo(b=[1], a=[5, 3, 2], c=[3, 3], d=[3, 3]) == result_a
        assert big_foo([5, 3, 2], [1], [3, 3], [3, 3]) == result_a

    def test_15_memoize_multiple_arg_kwarg_delete(self):
        @self.memoizer.memoize()
        def big_foo(a, b, c=[1, 1], d=[1, 1]):
            return (sum(a) + sum(b) + sum(c) + sum(d) +
                    random.randrange(0, 100000))

        result_a = big_foo([5, 3, 2], [1], c=[3, 3], d=[3, 3])
        self.memoizer.delete_memoized(big_foo, [5, 3, 2], [1], [3, 3], [3, 3])
        result_b = big_foo([5, 3, 2], [1], c=[3, 3], d=[3, 3])
        assert result_a != result_b

        self.memoizer.delete_memoized(
            big_foo, [5, 3, 2], b=[1], c=[3, 3], d=[3, 3]
        )
        result_b = big_foo([5, 3, 2], [1], c=[3, 3], d=[3, 3])
        assert result_a != result_b

        self.memoizer.delete_memoized(
            big_foo, [5, 3, 2], [1], c=[3, 3], d=[3, 3]
        )
        result_a = big_foo([5, 3, 2], [1], c=[3, 3], d=[3, 3])
        assert result_a != result_b

        self.memoizer.delete_memoized(
            big_foo, [5, 3, 2], b=[1], c=[3, 3], d=[3, 3]
        )
        result_a = big_foo([5, 3, 2], [1], c=[3, 3], d=[3, 3])
        assert result_a != result_b

        self.memoizer.delete_memoized(
            big_foo, [5, 3, 2], [1], c=[3, 3], d=[3, 3]
        )
        result_b = big_foo([5, 3, 2], [1], c=[3, 3], d=[3, 3])
        assert result_a != result_b

        self.memoizer.delete_memoized(big_foo, [5, 3, 2], [1], [3, 3], [3, 3])
        result_a = big_foo([5, 3, 2], [1], c=[3, 3], d=[3, 3])
        assert result_a != result_b

    def test_16_memoize_kwargs_to_args(self):
        def big_foo(a, b, c=None, d=None):
            return sum(a) + sum(b) + random.randrange(0, 100000)

        expected = (1, 2, 'foo', 'bar')

        args, kwargs = self.memoizer._memoize_kwargs_to_args(
            big_foo, 1, 2, 'foo', 'bar')
        assert (args == expected)
        args, kwargs = self.memoizer._memoize_kwargs_to_args(
            big_foo, 2, 'foo', 'bar', a=1)
        assert (args == expected)
        args, kwargs = self.memoizer._memoize_kwargs_to_args(
            big_foo, a=1, b=2, c='foo', d='bar')
        assert (args == expected)
        args, kwargs = self.memoizer._memoize_kwargs_to_args(
            big_foo, d='bar', b=2, a=1, c='foo')
        assert (args == expected)
        args, kwargs = self.memoizer._memoize_kwargs_to_args(
            big_foo, 1, 2, d='bar', c='foo')
        assert (args == expected)

    def test_17_memoize_none_value(self):
        self.memoizer = Memoizer()

        @self.memoizer.memoize()
        def foo():
            return None

        cache_key = foo.make_cache_key(foo.uncached)
        assert (
            self.memoizer.get(cache_key) is self.memoizer.default_cache_value)
        result = foo()
        assert result is None
        assert self.memoizer.get(cache_key) is None

        self.memoizer.delete_memoized(foo)
        cache_key = foo.make_cache_key(foo.uncached)
        assert (
            self.memoizer.get(cache_key) is self.memoizer.default_cache_value)

    def test_17_delete_memoized_instancemethod_with_mutable_param(self):
        class Foo(object):
            def __init__(self, id):
                self.id = id

            @self.memoizer.memoize(5)
            def foo(self, bar_obj):
                return random.randrange(0, 100000) + bar_obj.id

            def __repr__(self):
                return ('{}({})'.format(self.__class__.__name__, self.id))

        class Bar(object):
            def __init__(self, id):
                self.id = id

            def __repr__(self):
                return ('{}({})'.format(self.__class__.__name__, self.id))

        a = Foo(1)
        b = Bar(1)
        c = Bar(2)

        result1 = a.foo(b)
        result2 = a.foo(c)

        assert(a.foo(b) == result1)
        assert(a.foo(c) == result2)

        self.memoizer.delete_memoized(a.foo, a, b)

        assert(a.foo(b) != result1)
        assert(a.foo(c) == result2)

    def test_18_python3_uses_getfullargspec(self):
        def foo():
            return None

        major_version = sys.version_info.major
        argspec = _get_argspec(foo)

        if major_version < 3:
            assert argspec.__class__.__name__ is 'ArgSpec'
        else:
            assert argspec.__class__.__name__ is 'FullArgSpec'

    def test_19_memoize_make_name(self):
        @self.memoizer.memoize()
        def f():
            return None

        without_make_name = f.make_cache_key(f.uncached)

        @self.memoizer.memoize(make_name=lambda fname: 'make_name' + fname)
        def f():
            return None

        with_make_name = f.make_cache_key(f.uncached)

        assert without_make_name != with_make_name

    def test_20_memoize_unless(self):
        @self.memoizer.memoize(unless=lambda: True)
        def f():
            return random.randrange(0, 100000)

        old_value = f()
        new_value = f()

        assert new_value != old_value

    @patch('memoize.Memoizer.get', side_effect=Exception)
    def test_21_memoize_get_backend_error(self, memoizer_get):
        logging.basicConfig()

        # disable logger (to avoid cluttering test output)
        logging.disable(logging.ERROR)

        memoizer = Memoizer()

        @memoizer.memoize()
        def f():
            return random.randrange(0, 100000)

        cache_key = f.make_cache_key(f.uncached)

        old_value = f()
        memoizer_get.assert_called_with(cache_key)

        memoizer_get.reset_mock()

        new_value = f()
        memoizer_get.assert_called_with(cache_key)

        assert new_value != old_value

        # re-enable logger
        logging.disable(logging.NOTSET)

    @patch('memoize.Memoizer.set', side_effect=Exception)
    def test_22_memoize_set_backend_error(self, memoizer_set):
        logging.basicConfig()

        # disable logger (to avoid cluttering test output)
        logging.disable(logging.ERROR)

        memoizer = Memoizer()

        @memoizer.memoize()
        def f():
            return random.randrange(0, 100000)

        cache_key = f.make_cache_key(f.uncached)

        old_value = f()
        memoizer_set.assert_called_with(
            cache_key,
            old_value,
            timeout=f.cache_timeout
        )

        memoizer_set.reset_mock()

        new_value = f()
        memoizer_set.assert_called_with(
            cache_key,
            new_value,
            timeout=f.cache_timeout
        )

        assert new_value != old_value

        # re-enable logger
        logging.disable(logging.NOTSET)

    def test_23_delete_memoized_not_callable(self):
        warning_raised = False

        try:
            self.memoizer.delete_memoized('function_name')
        except DeprecationWarning:
            warning_raised = True

        assert warning_raised

    @patch('memoize.Memoizer.delete', side_effect=Exception)
    def test_24_delete_memoized_backend_error(self, memoizer_delete):
        logging.basicConfig()

        # disable logger (to avoid cluttering test output)
        logging.disable(logging.ERROR)

        memoizer = Memoizer()

        @memoizer.memoize()
        def f(*args, **kwargs):
            return random.randrange(0, 100000)

        cache_key = f.make_cache_key(f.uncached, 'a', 'b', c='c', d='d')

        old_value = f('a', 'b', c='c', d='d')

        memoizer.delete_memoized(f, 'a', 'b', c='c', d='d')
        memoizer_delete.assert_called_with(cache_key)

        new_value = f('a', 'b', c='c', d='d')

        assert new_value == old_value

        # re-enable logger
        logging.disable(logging.NOTSET)

    def test_25_delete_memoized_verhash_not_callable(self):
        warning_raised = False

        try:
            self.memoizer.delete_memoized_verhash('function_name')
        except DeprecationWarning:
            warning_raised = True

        assert warning_raised

    @patch('memoize.Memoizer.delete', side_effect=Exception)
    def test_26_delete_memoized_verhash_backend_error(self, memoizer_delete):
        logging.basicConfig()

        # disable logger (to avoid cluttering test output)
        logging.disable(logging.ERROR)

        memoizer = Memoizer()

        @memoizer.memoize()
        def f():
            return random.randrange(0, 100000)

        _fname, _ = function_namespace(f)
        version_key = self.memoizer._memvname(_fname)

        result = f()

        assert f() == result
        assert memoizer.get(version_key) is not memoizer.default_cache_value

        memoizer.delete_memoized_verhash(f)

        memoizer_delete.assert_called_with(version_key)

        assert f() == result
        assert memoizer.get(version_key) is not memoizer.default_cache_value

        # re-enable logger
        logging.disable(logging.NOTSET)

    def test_27_update_memoized(self):
        @self.memoizer.memoize(0.05)
        def big_foo(a, b):
            return a + b + random.randrange(0, 100000)

        result = big_foo(5, 2)
        result2 = big_foo(5, 3)

        time.sleep(0.03)
        assert big_foo(5, 2) == result
        assert big_foo(5, 2) != result2
        assert big_foo(5, 3) != result
        assert big_foo(5, 3) == result2
        result3 = self.memoizer.update_memoized(big_foo, 5, 2)
        assert big_foo(5, 3) == result2

        # make sure the updated cached results also extended the timeout accordingly
        # big_foo(5, 2) timeout would have been extended by another 5 seconds
        # big_foo(5, 3) timeout would have stayed the same so it would have expired after 3 additional seconds
        time.sleep(0.03)
        assert big_foo(5, 2) != result
        assert big_foo(5, 2) == result3

    def test_28_update_memoized_not_callable(self):
        warning_raised = False

        try:
            self.memoizer.update_memoized('function_name')
        except DeprecationWarning:
            warning_raised = True

        assert warning_raised

    @patch('memoize.Memoizer.get', side_effect=Exception)
    def test_29_update_memoized_backend_error(self, memoizer_get):
        logging.basicConfig()

        # disable logger (to avoid cluttering test output)
        logging.disable(logging.ERROR)

        memoizer = Memoizer()

        @memoizer.memoize()
        def f():
            return random.randrange(0, 100000)

        cache_key = f.make_cache_key(f.uncached)

        old_value = self.memoizer.update_memoized(f)
        memoizer_get.assert_called_with(cache_key)

        memoizer_get.reset_mock()

        new_value = self.memoizer.update_memoized(f)
        memoizer_get.assert_called_with(cache_key)

        assert new_value != old_value

        # re-enable logger
        logging.disable(logging.NOTSET)

    @patch('memoize.Memoizer.get', side_effect=Exception)
    def test_30_update_memoized_backend_error(self, memoizer_get):
        settings.DEBUG = True
        logging.basicConfig()
        # disable logger (to avoid cluttering test output)
        logging.disable(logging.ERROR)

        memoizer = Memoizer()

        @memoizer.memoize()
        def f():
            return random.randrange(0, 100000)

        exception_raised = False
        try:
            self.memoizer.update_memoized(f)
        except Exception:
            exception_raised = True
        assert exception_raised

        settings.DEBUG = False
        memoizer_get.reset_mock()

        # re-enable logger
        logging.disable(logging.NOTSET)

    @patch('memoize.Memoizer.set', side_effect=Exception)
    def test_31_update_memoized_backend_error(self, memoizer_set):

        logging.basicConfig()

        # disable logger (to avoid cluttering test output)
        logging.disable(logging.ERROR)

        memoizer = Memoizer()

        @memoizer.memoize()
        def f():
            return random.randrange(0, 100000)

        old_value = self.memoizer.update_memoized(f)
        fname, instance_fname = function_namespace(f, args=[])
        version_key = self.memoizer._memvname(fname)
        version_val = self.memoizer.get(version_key)
        memoizer_set.assert_called_with(
            version_key,
            version_val,
            timeout=f.cache_timeout
        )

        memoizer_set.reset_mock()

        new_value = self.memoizer.update_memoized(f)
        memoizer_set.assert_called_with(
            version_key,
            version_val,
            timeout=f.cache_timeout
        )

        assert new_value != old_value

        # re-enable logger
        logging.disable(logging.NOTSET)

    @patch('memoize.Memoizer.set', side_effect=Exception)
    def test_32_update_memoized_backend_error(self, memoizer_set):
        settings.DEBUG = True
        logging.basicConfig()

        # disable logger (to avoid cluttering test output)
        logging.disable(logging.ERROR)

        memoizer = Memoizer()

        @memoizer.memoize()
        def f():
            return random.randrange(0, 100000)

        exception_raised = False
        try:
            self.memoizer.update_memoized(f)
        except Exception:
            exception_raised = True
        assert exception_raised

        settings.DEBUG = False
        memoizer_set.reset_mock()

        # re-enable logger
        logging.disable(logging.NOTSET)

