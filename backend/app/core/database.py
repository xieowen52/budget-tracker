from functools import lru_cache

from supabase import Client, create_client

from app.core.config import settings


@lru_cache(maxsize=1)
def get_supabase() -> Client:
    """Return a singleton Supabase client using the service-role key.

    The service-role key bypasses Row Level Security, so we enforce
    authorization ourselves in the route handlers.
    """
    return create_client(settings.supabase_url, settings.supabase_service_role_key)
