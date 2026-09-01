import os
from supabase import create_client


def authenticate_user(email, password):
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")

    if not supabase_url or not supabase_key:
        raise RuntimeError("Supabase no está configurado")

    supabase = create_client(supabase_url, supabase_key)

    return supabase.auth.sign_in_with_password({
        "email": email,
        "password": password
    })