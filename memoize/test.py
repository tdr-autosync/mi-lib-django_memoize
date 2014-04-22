import sys
import os
import time
import random
import string

from django.test import TestCase

from memoize import Memoizer, function_namespace


class MemoizeTestCase(TestCase):
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

        assert self.memoizer.get('hi') is None

    def test_06_memoize(self):
        @self.memoizer.memoize(5)
        def big_foo(a, b):
            return a+b+random.randrange(0, 100000)

        result = big_foo(5, 2)

        time.sleep(1)

        assert big_foo(5, 2) == result

        result2 = big_foo(5, 3)
        assert result2 != result

        time.sleep(6)

        assert big_foo(5, 2) != result

        time.sleep(1)

        assert big_foo(5, 3) != result2

    def test_07_delete_memoize(self):
        @self.memoizer.memoize(5)
        def big_foo(a, b):
            return a+b+random.randrange(0, 100000)

        result = big_foo(5, 2)
        result2 = big_foo(5, 3)

        time.sleep(1)

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
            return a+b+random.randrange(0, 100000)

        result = big_foo(5, 2)
        result2 = big_foo(5, 3)

        time.sleep(1)

        assert big_foo(5, 2) == result
        assert big_foo(5, 2) == result
        assert big_foo(5, 3) != result
        assert big_foo(5, 3) == result2

        self.memoizer.delete_memoized_verhash(big_foo)

        _fname = function_namespace(big_foo)
        version_key = self.memoizer._memvname(_fname)
        assert self.memoizer.get(version_key) is None

        assert big_foo(5, 2) != result
        assert big_foo(5, 3) != result2

        assert self.memoizer.get(version_key) is not None

    def test_08_delete_memoize(self):
        @self.memoizer.memoize()
        def big_foo(a, b):
            return a+b+random.randrange(0, 100000)

        result_a = big_foo(5, 1)
        result_b = big_foo(5, 2)

        assert big_foo(5, 1) == result_a
        assert big_foo(5, 2) == result_b
        self.memoizer.delete_memoized(big_foo, 5, 2)

        assert big_foo(5, 1) == result_a
        assert big_foo(5, 2) != result_b

        ## Cleanup bigfoo 5,1 5,2 or it might conflict with
        ## following run if it also uses memecache
        self.memoizer.delete_memoized(big_foo, 5, 2)
        self.memoizer.delete_memoized(big_foo, 5, 1)

    def test_09_args_memoize(self):
        @self.memoizer.memoize()
        def big_foo(a, b):
            return sum(a)+sum(b)+random.randrange(0, 100000)

        result_a = big_foo([5,3,2], [1])
        result_b = big_foo([3,3], [3,1])

        assert big_foo([5,3,2], [1]) == result_a
        assert big_foo([3,3], [3,1]) == result_b

        self.memoizer.delete_memoized(big_foo, [5,3,2], [1])

        assert big_foo([5,3,2], [1]) != result_a
        assert big_foo([3,3], [3,1]) == result_b

        ## Cleanup bigfoo 5,1 5,2 or it might conflict with
        ## following run if it also uses memecache
        self.memoizer.delete_memoized(big_foo, [5,3,2], [1])
        self.memoizer.delete_memoized(big_foo, [3,3], [1])

    def test_10_kwargs_memoize(self):
        @self.memoizer.memoize()
        def big_foo(a, b=None):
            return a+sum(b.values())+random.randrange(0, 100000)

        result_a = big_foo(1, dict(one=1,two=2))
        result_b = big_foo(5, dict(three=3,four=4))

        assert big_foo(1, dict(one=1,two=2)) == result_a
        assert big_foo(5, dict(three=3,four=4)) == result_b

        self.memoizer.delete_memoized(big_foo, 1, dict(one=1,two=2))

        assert big_foo(1, dict(one=1,two=2)) != result_a
        assert big_foo(5, dict(three=3,four=4)) == result_b

    def test_10a_kwargonly_memoize(self):
        @self.memoizer.memoize()
        def big_foo(a=None):
            if a is None:
                a = 0
            return a+random.random()

        result_a = big_foo()
        result_b = big_foo(5)

        assert big_foo() == result_a
        assert big_foo() < 1
        assert big_foo(5) == result_b
        assert big_foo(5) >= 5 and big_foo(5) < 6

    def test_10a_arg_kwarg_memoize(self):
        @self.memoizer.memoize()
        def f(a, b, c=1):
            return a+b+c+random.randrange(0, 100000)

        assert f(1,2) == f(1,2,c=1)
        assert f(1,2) == f(1,2,1)
        assert f(1,2) == f(1,2)
        assert f(1,2,3) != f(1,2)
        with self.assertRaises(TypeError):
            f(1)

    def test_10b_classarg_memoize(self):
        @self.memoizer.memoize()
        def bar(a):
            return a.value + random.random()

        class Adder(object):
            def __init__(self, value):
                self.value = value

        adder = Adder(15)
        adder2 = Adder(20)

        y = bar(adder)
        z = bar(adder2)

        assert y != z
        assert bar(adder) == y
        assert bar(adder) != z
        adder.value = 14
        assert bar(adder) == y
        assert bar(adder) != z

        assert bar(adder) != bar(adder2)
        assert bar(adder2) == z

    def test_10c_classfunc_memoize(self):
        class Adder(object):
            def __init__(self, initial):
                self.initial = initial

            @self.memoizer.memoize()
            def add(self, b):
                return self.initial + b

        adder1 = Adder(1)
        adder2 = Adder(2)

        x = adder1.add(3)
        assert adder1.add(3) == x
        assert adder1.add(4) != x
        assert adder1.add(3) != adder2.add(3)

    def test_14_memoized_multiple_arg_kwarg_calls(self):
        @self.memoizer.memoize()
        def big_foo(a, b,c=[1,1],d=[1,1]):
            return sum(a)+sum(b)+sum(c)+sum(d)+random.randrange(0, 100000)

        result_a = big_foo([5,3,2], [1], c=[3,3], d=[3,3])

        assert big_foo([5,3,2], [1], d=[3,3], c=[3,3]) == result_a
        assert big_foo(b=[1],a=[5,3,2],c=[3,3],d=[3,3]) == result_a
        assert big_foo([5,3,2], [1], [3,3], [3,3]) == result_a

    def test_15_memoize_multiple_arg_kwarg_delete(self):
        @self.memoizer.memoize()
        def big_foo(a, b,c=[1,1],d=[1,1]):
            return sum(a)+sum(b)+sum(c)+sum(d)+random.randrange(0, 100000)

        result_a = big_foo([5,3,2], [1], c=[3,3], d=[3,3])
        self.memoizer.delete_memoized(big_foo, [5,3,2],[1],[3,3],[3,3])
        result_b = big_foo([5,3,2], [1], c=[3,3], d=[3,3])
        assert result_a != result_b

        self.memoizer.delete_memoized(big_foo, [5,3,2],b=[1],c=[3,3],d=[3,3])
        result_b = big_foo([5,3,2], [1], c=[3,3], d=[3,3])
        assert result_a != result_b

        self.memoizer.delete_memoized(big_foo, [5,3,2],[1],c=[3,3],d=[3,3])
        result_a = big_foo([5,3,2], [1], c=[3,3], d=[3,3])
        assert result_a != result_b

        self.memoizer.delete_memoized(big_foo, [5,3,2],b=[1],c=[3,3],d=[3,3])
        result_a = big_foo([5,3,2], [1], c=[3,3], d=[3,3])
        assert result_a != result_b

        self.memoizer.delete_memoized(big_foo, [5,3,2],[1],c=[3,3],d=[3,3])
        result_b = big_foo([5,3,2], [1], c=[3,3], d=[3,3])
        assert result_a != result_b

        self.memoizer.delete_memoized(big_foo, [5,3,2],[1],[3,3],[3,3])
        result_a = big_foo([5,3,2], [1], c=[3,3], d=[3,3])
        assert result_a != result_b

    def test_16_memoize_kwargs_to_args(self):
        def big_foo(a, b, c=None, d=None):
            return sum(a)+sum(b)+random.randrange(0, 100000)

        expected = (1,2,'foo','bar')

        args, kwargs = self.memoizer.memoize_kwargs_to_args(big_foo, 1,2,'foo','bar')
        assert (args == expected)
        args, kwargs = self.memoizer.memoize_kwargs_to_args(big_foo, 2,'foo','bar',a=1)
        assert (args == expected)
        args, kwargs = self.memoizer.memoize_kwargs_to_args(big_foo, a=1,b=2,c='foo',d='bar')
        assert (args == expected)
        args, kwargs = self.memoizer.memoize_kwargs_to_args(big_foo, d='bar',b=2,a=1,c='foo')
        assert (args == expected)
        args, kwargs = self.memoizer.memoize_kwargs_to_args(big_foo, 1,2,d='bar',c='foo')
        assert (args == expected)
