"""SSO authentication API endpoints."""
import secrets
from typing import Optional
from fastapi import APIRouter, Query, HTTPException, Request
from fastapi.responses import RedirectResponse, JSONResponse

from gateway.auth.sso import sso_manager
from gateway.auth.jwt_handler import jwt_handler
from gateway.monitoring.logger import logger
from shared.exceptions import AuthenticationError


router = APIRouter(prefix="/api/auth/sso", tags=["sso"])


# In-memory state storage (use Redis in production)
_sso_states = {}


@router.get("/providers")
async def list_sso_providers():
    """
    List available SSO providers.

    Returns:
        List of provider names
    """
    providers = sso_manager.list_providers()
    return {"providers": providers}


@router.get("/{provider}/login")
async def sso_login(
    provider: str,
    redirect_uri: str = Query(..., description="Callback URL after authentication"),
):
    """
    Initiate SSO login flow.

    Args:
        provider: SSO provider name (google, github, azure)
        redirect_uri: URL to redirect to after authentication

    Returns:
        Redirect to provider's authorization page
    """
    sso_provider = sso_manager.get_provider(provider)

    if not sso_provider:
        raise HTTPException(
            status_code=404,
            detail=f"SSO provider '{provider}' not found or not configured",
        )

    # Generate state for CSRF protection
    state = secrets.token_urlsafe(32)

    # Store state temporarily (use Redis in production)
    _sso_states[state] = {
        "provider": provider,
        "redirect_uri": redirect_uri,
    }

    # Get authorization URL
    try:
        auth_url = await sso_provider.get_authorization_url(redirect_uri, state)
        logger.info("sso_login_initiated", provider=provider)
        return RedirectResponse(url=auth_url)
    except Exception as e:
        logger.error("sso_login_failed", provider=provider, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to initiate SSO login")


@router.get("/{provider}/callback")
async def sso_callback(
    request: Request,
    provider: str,
    code: str = Query(..., description="Authorization code"),
    state: str = Query(..., description="State parameter"),
):
    """
    Handle SSO callback after user authentication.

    Args:
        provider: SSO provider name
        code: Authorization code from provider
        state: State parameter for CSRF protection

    Returns:
        JWT token for authenticated user
    """
    # Verify state
    state_data = _sso_states.pop(state, None)

    if not state_data:
        raise HTTPException(status_code=400, detail="Invalid or expired state")

    if state_data["provider"] != provider:
        raise HTTPException(status_code=400, detail="Provider mismatch")

    # Get provider
    sso_provider = sso_manager.get_provider(provider)

    if not sso_provider:
        raise HTTPException(status_code=404, detail=f"Provider '{provider}' not found")

    try:
        # Exchange code for tokens
        tokens = await sso_provider.exchange_code(code, state_data["redirect_uri"])

        # Get user information
        access_token = tokens.get("access_token")
        if not access_token:
            raise AuthenticationError("No access token received")

        user_info = await sso_provider.get_user_info(access_token)

        # Create user session (you would typically create/update user in database here)
        username = user_info.get("email") or user_info.get("login") or user_info.get("id")

        # Generate JWT token
        jwt_token = jwt_handler.create_token(
            username=username,
            user_id=0,  # Would get from database
            scopes=["read", "write"],
            expiration_minutes=60 * 24,  # 24 hours
        )

        logger.info(
            "sso_authentication_successful",
            provider=provider,
            username=username,
        )

        # Return token
        return JSONResponse(
            content={
                "access_token": jwt_token.access_token,
                "token_type": "bearer",
                "expires_in": 60 * 60 * 24,
                "user": {
                    "username": username,
                    "email": user_info.get("email"),
                    "name": user_info.get("name"),
                    "provider": provider,
                },
            }
        )

    except AuthenticationError as e:
        logger.error("sso_callback_auth_error", provider=provider, error=str(e))
        raise HTTPException(status_code=401, detail=str(e))

    except Exception as e:
        logger.error("sso_callback_failed", provider=provider, error=str(e))
        raise HTTPException(status_code=500, detail="SSO authentication failed")


@router.get("/{provider}/logout")
async def sso_logout(provider: str):
    """
    Handle SSO logout.

    Args:
        provider: SSO provider name

    Returns:
        Success message
    """
    # In a real implementation, you would:
    # 1. Revoke the refresh token if available
    # 2. Clear session/JWT token
    # 3. Optionally redirect to provider's logout URL

    logger.info("sso_logout", provider=provider)

    return {"message": "Logged out successfully", "provider": provider}
