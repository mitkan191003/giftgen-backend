from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import httpx
import jwt
from jwt import InvalidTokenError, PyJWKClient

from app.core.config import get_settings


class CognitoConfigurationError(RuntimeError):
    pass


class CognitoAuthenticationError(RuntimeError):
    pass


@dataclass(slots=True, frozen=True)
class CognitoIdentity:
    subject: str
    email: str
    display_name: str | None
    token_use: str


class CognitoJWTVerifier:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.region = self.settings.cognito_region or self.settings.aws_region
        self.user_pool_id = self.settings.cognito_user_pool_id
        self.client_id = self.settings.cognito_client_id
        if not self.user_pool_id or not self.client_id:
            raise CognitoConfigurationError(
                "COGNITO_USER_POOL_ID and COGNITO_CLIENT_ID must be configured when AUTH_MODE=cognito"
            )

        self.issuer = (
            self.settings.cognito_issuer
            or f"https://cognito-idp.{self.region}.amazonaws.com/{self.user_pool_id}"
        )
        self.jwks_client = PyJWKClient(f"{self.issuer}/.well-known/jwks.json")

    def verify(self, token: str) -> CognitoIdentity:
        try:
            unverified = jwt.decode(
                token,
                options={
                    "verify_signature": False,
                    "verify_exp": False,
                    "verify_aud": False,
                },
                algorithms=["RS256"],
            )
        except InvalidTokenError as exc:
            raise CognitoAuthenticationError("Malformed Cognito token") from exc

        token_use = unverified.get("token_use")
        if token_use not in {"id", "access"}:
            raise CognitoAuthenticationError("Unsupported Cognito token_use")

        try:
            signing_key = self.jwks_client.get_signing_key_from_jwt(token)
        except Exception as exc:  # pragma: no cover - network/runtime path
            raise CognitoAuthenticationError("Unable to resolve Cognito signing key") from exc

        decode_kwargs = {
            "key": signing_key.key,
            "algorithms": ["RS256"],
            "issuer": self.issuer,
            "options": {"require": ["sub", "iss", "exp", "iat", "token_use"]},
        }
        if token_use == "id":
            decode_kwargs["audience"] = self.client_id
        else:
            decode_kwargs["options"]["verify_aud"] = False

        try:
            claims = jwt.decode(token, **decode_kwargs)
        except InvalidTokenError as exc:
            raise CognitoAuthenticationError("Cognito token verification failed") from exc

        if token_use == "access":
            if claims.get("client_id") != self.client_id:
                raise CognitoAuthenticationError("Cognito access token client_id did not match")
        else:
            if claims.get("aud") != self.client_id:
                raise CognitoAuthenticationError("Cognito ID token audience did not match")

        subject = str(claims.get("sub") or "").strip()
        if not subject:
            raise CognitoAuthenticationError("Cognito token did not include sub")

        email = self._extract_email(claims, token if token_use == "access" else None)
        display_name = self._extract_display_name(claims, email)
        return CognitoIdentity(
            subject=subject,
            email=email,
            display_name=display_name,
            token_use=token_use,
        )

    def _extract_email(self, claims: dict[str, object], access_token: str | None) -> str:
        email = claims.get("email")
        if isinstance(email, str) and email.strip():
            return email.strip().lower()

        username = claims.get("username") or claims.get("cognito:username")
        if isinstance(username, str) and "@" in username:
            return username.strip().lower()

        if access_token and self.settings.cognito_domain:
            userinfo = self._fetch_userinfo(access_token)
            userinfo_email = userinfo.get("email")
            if isinstance(userinfo_email, str) and userinfo_email.strip():
                return userinfo_email.strip().lower()

        raise CognitoAuthenticationError("Cognito token did not provide a usable email identity")

    def _extract_display_name(self, claims: dict[str, object], email: str) -> str | None:
        for key in ("name", "preferred_username", "username", "cognito:username"):
            value = claims.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return email.split("@")[0]

    def _fetch_userinfo(self, access_token: str) -> dict[str, object]:
        domain = self.settings.cognito_domain.rstrip("/")
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(
                    f"{domain}/oauth2/userInfo",
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                response.raise_for_status()
                payload = response.json()
        except Exception as exc:  # pragma: no cover - network/runtime path
            raise CognitoAuthenticationError("Unable to fetch Cognito userinfo") from exc

        if not isinstance(payload, dict):
            raise CognitoAuthenticationError("Cognito userinfo response was invalid")
        return payload


@lru_cache
def get_cognito_verifier() -> CognitoJWTVerifier:
    return CognitoJWTVerifier()
