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

def get_user_profile(user_id, access_token, refresh_token):
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")

    if not supabase_url or not supabase_key:
        raise RuntimeError("Supabase no está configurado")

    supabase = create_client(supabase_url, supabase_key)

    supabase.auth.set_session(access_token, refresh_token)

    response = (
        supabase
        .table("profiles")
        .select("nombre, rol")
        .eq("id", user_id)
        .single()
        .execute()
    )

    return response.data

def get_admin_client():
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_secret_key = os.getenv("SUPABASE_SECRET_KEY")

    if not supabase_url or not supabase_secret_key:
        raise RuntimeError("Supabase admin no está configurado")

    return create_client(supabase_url, supabase_secret_key)

def list_auth_users():
    supabase = get_admin_client()

    auth_users = supabase.auth.admin.list_users()

    profiles_response = (
        supabase
        .table("profiles")
        .select("id, nombre, rol")
        .execute()
    )

    profiles = profiles_response.data or []

    profiles_by_id = {
        profile["id"]: profile
        for profile in profiles
    }

    usuarios = []

    for user in auth_users:
        profile = profiles_by_id.get(user.id, {})

        usuarios.append({
            "id": user.id,
            "email": user.email,
            "nombre": profile.get("nombre", ""),
            "rol": profile.get("rol", "")
        })

    return usuarios

def create_auth_user(email, password):
    supabase = get_admin_client()

    response = supabase.auth.admin.create_user({
        "email": email,
        "password": password,
        "email_confirm": True
    })

    return response.user

def create_user_profile(user_id, nombre, rol):
    supabase = get_admin_client()

    response = (
        supabase
        .table("profiles")
        .insert({
            "id": user_id,
            "nombre": nombre,
            "rol": rol
        })
        .execute()
    )

    return response.data

def delete_auth_user(user_id):
    supabase = get_admin_client()

    response = supabase.auth.admin.delete_user(user_id)

    return response

def update_auth_user(user_id, email=None, password=None):
    supabase = get_admin_client()

    datos = {}

    if email:
        datos["email"] = email

    if password:
        datos["password"] = password

    if datos:
        supabase.auth.admin.update_user_by_id(
            user_id,
            datos
        )
def update_user_profile(user_id, nombre, rol):
    supabase = get_admin_client()

    response = (
        supabase
        .table("profiles")
        .update({
            "nombre": nombre,
            "rol": rol
        })
        .eq("id", user_id)
        .execute()
    )

    return response.data