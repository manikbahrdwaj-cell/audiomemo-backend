import asyncio
import json
from fastapi.testclient import TestClient
from app.agent import session_cache


class DummyStreamingService:
    async def create_session(self, phone_number: str):
        # Lazy import to reuse the real dataclass
        from app.services.verification_streaming import StreamingVerificationSession
        return StreamingVerificationSession(phone_number=phone_number)


def test_agent_session_cache_set_verified():
    # Directly set a verified session and assert cache contents
    client_id = "test-client-1"
    phone = "+14155551001"

    # Ensure clean state
    session_cache.delete(client_id)

    session_cache.set_verified(client_id, phone)

    entry = session_cache.get(client_id)
    assert entry is not None
    assert entry.get("verified") is True
    assert entry.get("phone_number") == phone
    assert isinstance(entry.get("vad"), object)
    assert entry.get("conversation_history") == []
