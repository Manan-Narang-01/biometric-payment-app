"""WebAuthn/FIDO2 registration and authentication service."""
import base64
import json
from datetime import datetime, timezone
from typing import Optional

from webauthn import (
    generate_registration_options,
    verify_registration_response,
    generate_authentication_options,
    verify_authentication_response,
    options_to_json,
)
from webauthn.helpers.structs import (
    AuthenticatorSelectionCriteria,
    UserVerificationRequirement,
    ResidentKeyRequirement,
    AuthenticatorAttachment,
    AuthenticatorTransport,
    PublicKeyCredentialDescriptor,
)
from webauthn.helpers.cose import COSEAlgorithmIdentifier
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import structlog

from app.core.config import settings
from app.core.redis_client import get_redis
from app.models import User, WebAuthnCredential

logger = structlog.get_logger()


class WebAuthnService:

    @staticmethod
    def _rp_id() -> str:
        return settings.WEBAUTHN_RP_ID

    @staticmethod
    def _origin() -> str:
        return settings.WEBAUTHN_ORIGIN

    # ── Registration ───────────────────────────────────────

    async def begin_registration(self, user: User, db: AsyncSession) -> dict:
        """Generate registration challenge and store in Redis."""
        # Get existing credentials to exclude
        result = await db.execute(
            select(WebAuthnCredential).where(
                WebAuthnCredential.user_id == user.id,
                WebAuthnCredential.is_active == True,
            )
        )
        existing = result.scalars().all()
        exclude_credentials = [
            PublicKeyCredentialDescriptor(id=base64.urlsafe_b64decode(c.credential_id + "=="))
            for c in existing
        ]

        options = generate_registration_options(
            rp_id=self._rp_id(),
            rp_name=settings.WEBAUTHN_RP_NAME,
            user_id=user.id.encode(),
            user_name=user.username,
            user_display_name=user.display_name,
            authenticator_selection=AuthenticatorSelectionCriteria(
                resident_key=ResidentKeyRequirement.PREFERRED,
                user_verification=UserVerificationRequirement.REQUIRED,
            ),
            supported_pub_key_algs=[
                COSEAlgorithmIdentifier.ECDSA_SHA_256,
                COSEAlgorithmIdentifier.RSASSA_PKCS1_v1_5_SHA_256,
            ],
            exclude_credentials=exclude_credentials,
        )

        # Store challenge in Redis (5 min TTL)
        redis = get_redis()
        challenge_b64 = base64.urlsafe_b64encode(options.challenge).decode()
        await redis.setex(
            f"webauthn:reg:{user.id}",
            300,
            challenge_b64,
        )

        return json.loads(options_to_json(options))

    async def complete_registration(
        self,
        user: User,
        credential_data: dict,
        device_name: str,
        db: AsyncSession,
    ) -> WebAuthnCredential:
        """Verify registration response and store credential."""
        redis = get_redis()
        challenge_b64 = await redis.get(f"webauthn:reg:{user.id}")
        if not challenge_b64:
            raise ValueError("Registration challenge expired or not found")

        challenge = base64.urlsafe_b64decode(challenge_b64 + "==")

        try:
            verification = verify_registration_response(
                credential=credential_data,
                expected_challenge=challenge,
                expected_rp_id=self._rp_id(),
                expected_origin=self._origin(),
                require_user_verification=True,
            )
        except Exception as e:
            logger.warning("WebAuthn registration verification failed", error=str(e))
            raise ValueError(f"Biometric verification failed: {e}")

        # Delete challenge
        await redis.delete(f"webauthn:reg:{user.id}")

        # Store credential (public key only — never store biometric data)
        credential_id_b64 = base64.urlsafe_b64encode(
            verification.credential_id
        ).decode().rstrip("=")

        pub_key_b64 = base64.b64encode(
            verification.credential_public_key
        ).decode()

        credential = WebAuthnCredential(
            user_id=user.id,
            credential_id=credential_id_b64,
            public_key=pub_key_b64,
            sign_count=verification.sign_count,
            device_name=device_name,
            aaguid=str(verification.aaguid) if verification.aaguid else None,
            transports=credential_data.get("response", {}).get("transports"),
        )
        db.add(credential)
        await db.flush()
        return credential

    # ── Authentication ─────────────────────────────────────

    async def begin_authentication(self, user: User, db: AsyncSession) -> dict:
        """Generate authentication challenge."""
        result = await db.execute(
            select(WebAuthnCredential).where(
                WebAuthnCredential.user_id == user.id,
                WebAuthnCredential.is_active == True,
            )
        )
        credentials = result.scalars().all()
        if not credentials:
            raise ValueError("No biometric credentials registered for this account")

        allow_credentials = [
            PublicKeyCredentialDescriptor(
                id=base64.urlsafe_b64decode(c.credential_id + "=="),
                transports=[AuthenticatorTransport(t) for t in (c.transports or [])],
            )
            for c in credentials
        ]

        options = generate_authentication_options(
            rp_id=self._rp_id(),
            allow_credentials=allow_credentials,
            user_verification=UserVerificationRequirement.REQUIRED,
        )

        redis = get_redis()
        challenge_b64 = base64.urlsafe_b64encode(options.challenge).decode()
        await redis.setex(f"webauthn:auth:{user.id}", 300, challenge_b64)

        return json.loads(options_to_json(options))

    async def complete_authentication(
        self,
        user: User,
        credential_data: dict,
        db: AsyncSession,
    ) -> WebAuthnCredential:
        """Verify authentication response."""
        redis = get_redis()
        challenge_b64 = await redis.get(f"webauthn:auth:{user.id}")
        if not challenge_b64:
            raise ValueError("Authentication challenge expired")

        challenge = base64.urlsafe_b64decode(challenge_b64 + "==")

        # Find the matching credential
        raw_id = credential_data.get("rawId") or credential_data.get("id", "")
        result = await db.execute(
            select(WebAuthnCredential).where(
                WebAuthnCredential.user_id == user.id,
                WebAuthnCredential.is_active == True,
            )
        )
        credentials = result.scalars().all()

        matched = None
        for cred in credentials:
            cred_id_padded = cred.credential_id + "=="
            decoded = base64.urlsafe_b64decode(cred_id_padded)
            if base64.urlsafe_b64encode(decoded).decode().rstrip("=") == raw_id.rstrip("="):
                matched = cred
                break

        if not matched:
            raise ValueError("Credential not found")

        pub_key_bytes = base64.b64decode(matched.public_key)

        try:
            verification = verify_authentication_response(
                credential=credential_data,
                expected_challenge=challenge,
                expected_rp_id=self._rp_id(),
                expected_origin=self._origin(),
                credential_public_key=pub_key_bytes,
                credential_current_sign_count=matched.sign_count,
                require_user_verification=True,
            )
        except Exception as e:
            logger.warning("WebAuthn authentication failed", error=str(e))
            raise ValueError(f"Biometric verification failed: {e}")

        # Update sign count and last_used
        matched.sign_count = verification.new_sign_count
        matched.last_used = datetime.now(timezone.utc)
        await redis.delete(f"webauthn:auth:{user.id}")
        return matched


webauthn_service = WebAuthnService()
