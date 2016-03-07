# -*- coding: utf-8 -*-
""" ymir.caching

    dumb lightweight caching decorators, etc.

    `cached` requires werkzeug, but at least avoids a
    memcache dependency.

"""
import time
from functools import wraps


def cached(key_or_fxn, timeout=5 * 60, use_request_vars=False):
    """ dumb hack adapted from
        http://flask.pocoo.org/docs/patterns/viewdecorators/ """
    from werkzeug.contrib.cache import SimpleCache
    from ymir import caching as c
    if not getattr(c, 'CACHE', None):
        c.CACHE = SimpleCache()
    cache = c.CACHE
    if use_request_vars:
        tmp1 = key_or_fxn
        assert isinstance(key_or_fxn, basestring)

        def cache_key_fxn():
            from flask import request
            req = request
            z = sorted(req.values.items())
            import json
            key = tmp1 + json.dumps(z)
            return key
    elif isinstance(key_or_fxn, basestring):
        cache_key_fxn = lambda: key_or_fxn

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            tmp2 = cache_key_fxn()
            rv = cache.get(tmp2)
            if rv is not None:
                return rv
            rv = f(*args, **kwargs)
            cache.set(tmp2, rv, timeout=timeout)
            return rv
        return decorated_function
    return decorator

# Adapted from:
#  http://code.activestate.com/recipes/325905-memoize-decorator-with-timeout/


class MWT(object):

    """Memoize With Timeout"""
    _caches = {}
    _timeouts = {}

    def __init__(self, timeout=2):
        self.timeout = timeout

    def collect(self):
        """Clear cache of results which have timed out"""
        for func in self._caches:
            cache = {}
            for key in self._caches[func]:
                tmp = self._caches[func][key][1]
                if (time.time() - tmp) < self._timeouts[func]:
                    cache[key] = self._caches[func][key]
            self._caches[func] = cache

    def __call__(self, f):
        self.cache = self._caches[f] = {}
        self._timeouts[f] = self.timeout

        def func(*args, **kwargs):
            kw = sorted(kwargs.items())
            key = (args, tuple(kw))
            try:
                v = self.cache[key]
                # print("cache") # dbg
                if (time.time() - v[1]) > self.timeout:
                    raise KeyError
            except KeyError:
                # print("new") # dbg
                v = self.cache[key] = [
                    f(*args, **kwargs),
                    time.time()]
            return v[0]
        func.func_name = f.__name__

        return func
