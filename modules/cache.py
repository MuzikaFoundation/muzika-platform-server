
import redis
from werkzeug.contrib.cache import RedisCache, SimpleCache
from config import CacheConfig

# connection pool is shared by all instances of MuzikaCache
_connection_pool = None

# cache instance. This is shared by all instances of MuzikaCache
_cache = None


class MuzikaCache:
    """
    The instances of this returns cache server interface.

    >>> cache = MuzikaCache()

    # set a key with value and timeout is 300 seconds
    >>> cache().set('key', 'value', timeout=300)

    # get a value from a key named 'key'
    >>> cache().get('key')
    """

    # when
    _cache = None

    def __call__(self):
        """
        Returns redis cache from redis config
        """
        if self._cache is None:
            cache_type = CacheConfig.cache_type
            if cache_type == 'redis':
                global _connection_pool
                if _connection_pool is None:
                    _connection_pool = redis.ConnectionPool(host=CacheConfig.host)

                self._cache = RedisCache(
                    key_prefix=CacheConfig.key_prefix,
                    host=CacheConfig.host,
                    port=CacheConfig.port,
                    connection_pool=_connection_pool
                )
            else:
                global _cache
                if _cache is None:
                    _cache = SimpleCache()
                    self._cache = _cache
                else:
                    self._cache = _cache

        return self._cache

    def reset(self):
        if self._cache is not None:
            self._cache = None
