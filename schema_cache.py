import time
import uuid
from datetime import datetime, timedelta

class SchemaCache:
    def __init__(self):
        self._cache = {}
        self._cleanup_interval = 3600  # Clean up every hour
        self._last_cleanup = time.time()
    
    def store_schema(self, connection_id, schema_data, schema_context, ttl_minutes=60):
        """Store schema data in server cache"""
        # Clean up expired entries periodically
        if time.time() - self._last_cleanup > self._cleanup_interval:
            self._cleanup_expired()
            self._last_cleanup = time.time()
        
        self._cache[connection_id] = {
            'schema_data': schema_data,
            'schema_context': schema_context,
            'created_at': datetime.now(),
            'expires_at': datetime.now() + timedelta(minutes=ttl_minutes)
        }
        return connection_id
    
    def get_schema(self, connection_id):
        """Retrieve schema data from cache"""
        if connection_id in self._cache:
            entry = self._cache[connection_id]
            if datetime.now() < entry['expires_at']:
                return entry['schema_data'], entry['schema_context']
            else:
                # Remove expired entry
                del self._cache[connection_id]
        return None, None
    
    def remove_schema(self, connection_id):
        """Remove schema from cache"""
        if connection_id in self._cache:
            del self._cache[connection_id]
    
    def _cleanup_expired(self):
        """Remove expired cache entries"""
        current_time = datetime.now()
        expired_keys = [
            key for key, entry in self._cache.items() 
            if current_time >= entry['expires_at']
        ]
        for key in expired_keys:
            del self._cache[key]

# Global cache instance
schema_cache = SchemaCache()