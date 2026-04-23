import os
from supabase import create_client, Client

_url: str = os.environ["SUPABASE_URL"]
_key: str = os.environ["SUPABASE_SERVICE_ROLE_KEY"]

supabase: Client = create_client(_url, _key)


def test_connection() -> bool:
    """Query system_config to verify Supabase connectivity."""
    try:
        supabase.table("system_config").select("key").limit(1).execute()
        return True
    except Exception:
        return False
