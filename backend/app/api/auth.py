import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials

from app.core.config import Settings, get_settings
from app.core.security import auth_scheme
from app.models.schemas import AuthCredentials, AuthResponse, LogoutResponse


router = APIRouter(prefix="/auth", tags=["auth"])


def _auth_url(settings: Settings, path: str) -> str:
    return f"{settings.supabase_url.rstrip('/')}/auth/v1{path}"


def _anon_headers(settings: Settings, token: str | None = None) -> dict[str, str]:
    headers = {
        "apikey": settings.supabase_anon_key,
        "Content-Type": "application/json",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _service_headers(settings: Settings) -> dict[str, str]:
    return {
        "apikey": settings.supabase_service_role_key,
        "Authorization": f"Bearer {settings.supabase_service_role_key}",
        "Content-Type": "application/json",
    }


def _error_detail(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return response.text or "Supabase auth request failed"

    if isinstance(payload, dict):
        error_code = payload.get("error_code") or payload.get("code")
        message = (
            payload.get("msg")
            or payload.get("message")
            or payload.get("error_description")
            or payload.get("error")
        )
        if error_code == "over_email_send_rate_limit":
            return (
                "Supabase email rate limit reached. Sign-up uses auto-confirm on the backend; "
                "try again in a few minutes or disable email confirmations in Supabase Auth settings."
            )
        if error_code == "email_address_invalid":
            return "Supabase rejected this email address. Use a valid email format."
        if error_code == "user_already_exists":
            return "An account with this email already exists. Try signing in instead."
        if error_code == "invalid_credentials":
            return "Invalid email or password."
        if message:
            return str(message)

    return "Supabase auth request failed"


def _to_auth_response(payload: dict, fallback_message: str | None = None) -> AuthResponse:
    session = payload.get("session") or payload
    user = payload.get("user") or session.get("user")
    return AuthResponse(
        access_token=session.get("access_token"),
        refresh_token=session.get("refresh_token"),
        token_type=session.get("token_type", "bearer"),
        expires_in=session.get("expires_in"),
        user=user,
        message=fallback_message,
    )


async def _password_sign_in(
    client: httpx.AsyncClient,
    settings: Settings,
    email: str,
    password: str,
) -> httpx.Response:
    return await client.post(
        _auth_url(settings, "/token?grant_type=password"),
        headers=_anon_headers(settings),
        json={"email": email, "password": password},
    )


@router.post("/sign-up", response_model=AuthResponse)
async def sign_up(
    credentials: AuthCredentials,
    settings: Settings = Depends(get_settings),
) -> AuthResponse:
    settings.require_supabase()
    email = credentials.email.strip().lower()

    async with httpx.AsyncClient(timeout=20) as client:
        admin_response = await client.post(
            _auth_url(settings, "/admin/users"),
            headers=_service_headers(settings),
            json={
                "email": email,
                "password": credentials.password,
                "email_confirm": True,
            },
        )

        if admin_response.status_code == 422:
            detail = _error_detail(admin_response)
            if "already" not in detail.lower():
                raise HTTPException(status_code=admin_response.status_code, detail=detail)
            user_created = False
        elif admin_response.status_code >= 400:
            raise HTTPException(
                status_code=admin_response.status_code,
                detail=_error_detail(admin_response),
            )
        else:
            user_created = True

        sign_in_response = await _password_sign_in(client, settings, email, credentials.password)

    if sign_in_response.status_code >= 400:
        raise HTTPException(
            status_code=sign_in_response.status_code,
            detail=_error_detail(sign_in_response),
        )

    return _to_auth_response(
        sign_in_response.json(),
        fallback_message="Account created and signed in." if user_created else "Signed in.",
    )


@router.post("/sign-in", response_model=AuthResponse)
async def sign_in(
    credentials: AuthCredentials,
    settings: Settings = Depends(get_settings),
) -> AuthResponse:
    settings.require_supabase()
    email = credentials.email.strip().lower()

    async with httpx.AsyncClient(timeout=20) as client:
        response = await _password_sign_in(client, settings, email, credentials.password)

    if response.status_code >= 400:
        raise HTTPException(status_code=response.status_code, detail=_error_detail(response))
    return _to_auth_response(response.json())


@router.post("/logout", response_model=LogoutResponse)
async def logout(
    credentials: HTTPAuthorizationCredentials | None = Depends(auth_scheme),
    settings: Settings = Depends(get_settings),
) -> LogoutResponse:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
        )

    settings.require_supabase()
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(
            _auth_url(settings, "/logout"),
            headers=_anon_headers(settings, credentials.credentials),
        )
    if response.status_code >= 400:
        raise HTTPException(status_code=response.status_code, detail=_error_detail(response))
    return LogoutResponse(ok=True, message="Logged out")
