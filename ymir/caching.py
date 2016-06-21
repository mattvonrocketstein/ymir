# -*- coding: utf-8 -*-
""" ymir.caching

    dumb lightweight caching decorators, etc.

    `cached` requires werkzeug, but at least avoids a
    memcache dependency.

"""
from functools import wraps
from werkzeug.contrib.cache import SimpleCache


def cached(key_or_fxn, timeout=5 * 60):
    """ dumb hack adapted from
        http://flask.pocoo.org/docs/patterns/viewdecorators/
    """
    from ymir import caching as c
    if not getattr(c, 'CACHE', None):
        c.CACHE = SimpleCache()
    cache = c.CACHE
    if isinstance(key_or_fxn, basestring):
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
