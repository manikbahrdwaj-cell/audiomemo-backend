import io
import time
import base64
import asyncio
import soundfile as sf
import numpy as np
import pytest

from app.agent.vad import UtteranceDetector


def _wav_bytes_from_array(samples: np.ndarray, sample_rate: int = 16000) -> bytes:
    buf = io.BytesIO()
    sf.write(buf, samples, sample_rate, format="WAV")
    buf.seek(0)
    return buf.read()


def test_utterance_detector_completes_and_resets(monkeypatch):
    # Arrange: detector with low threshold and short silence window
    det = UtteranceDetector(silence_threshold_rms=0.01, silence_duration_ms=150)

    # Create a short speech chunk (sine) and a silence chunk
    speech = 0.1 * np.sin(2 * np.pi * 440 * np.linspace(0, 0.2, int(16000 * 0.2)))
    silence = np.zeros(int(16000 * 0.2), dtype=np.float32)

    speech_bytes = _wav_bytes_from_array(speech.astype(np.float32))
    silence_bytes = _wav_bytes_from_array(silence.astype(np.float32))

    # Control time.monotonic so we can simulate passage of time
    monotonic_values = [1000.0, 1000.3]

    def fake_monotonic():
        return monotonic_values.pop(0)

    monkeypatch.setattr(time, "monotonic", fake_monotonic)

    # Act: feed speech -> should not complete
    complete, _ = det.process_chunk(speech_bytes, 16000)
    assert complete is False

    # Act: feed silence after enough time -> should complete and return captured audio
    complete, captured = det.process_chunk(silence_bytes, 16000)
    assert complete is True
    assert isinstance(captured, (bytes, bytearray)) and len(captured) > 0

    # After completion, detector state should be reset: feeding speech again should start a new buffer
    monotonic_values.extend([2000.0, 2000.3])
    complete2, _ = det.process_chunk(speech_bytes, 16000)
    assert complete2 is False


def test_voice_agent_orchestrator_flow(monkeypatch):
    # Import here to avoid top-level side-effects
    from app.services.voice_agent import VoiceAgentOrchestrator, get_voice_agent, PROMPT_NOT_VERIFIED
    import app.agent.session_cache as session_cache

    orchestrator = VoiceAgentOrchestrator()

    # Prepare a verified session with a VAD stub that reports an immediate utterance
    client_id = "cid-1"
    captured_audio = b"fake-wav-bytes"

    class VADStub:
        def process_chunk(self, audio_bytes, sample_rate):
            return True, captured_audio

    session = {
        "verified": True,
        "phone_number": "+14155551001",
        "vad": VADStub(),
        "conversation_history": [],
    }

    monkeypatch.setattr(session_cache, "get", lambda cid: session if cid == client_id else None)
    updated = {}
    monkeypatch.setattr(session_cache, "update", lambda cid, **kw: updated.update(kw))

    # Mock transcribe_audio to return a plausible transcription
    async def fake_transcribe(data):
        return "what is my balance today"

    monkeypatch.setattr('app.services.voice_agent.transcribe_audio', fake_transcribe)

    # Mock graph invocation to return messages (we'll bypass AIMessage check by patching extractor)
    class GraphStub:
        async def ainvoke(self, state):
            return {"messages": []}

    monkeypatch.setattr('app.services.voice_agent.get_graph', lambda: GraphStub())
    monkeypatch.setattr('app.services.voice_agent._extract_last_ai_message', lambda msgs: "Your balance is $123.45")

    # Mock synthesise_speech to return bytes
    async def fake_tts(text, voice="alloy"):
        return b'mp3-bytes'

    monkeypatch.setattr('app.services.voice_agent.synthesise_speech', fake_tts)

    # Collect sent websocket payloads
    sent = []

    def send_ws_sync(payload):
        sent.append(payload)

    # Run the orchestrator
    asyncio.run(orchestrator.process_audio_chunk(client_id, b'data', 16000, send_ws_sync))

    # Assertions: should have sent a thinking or agent_audio payload at the end
    assert any(p.get('type') == 'agent_audio' for p in sent)
    # Conversation history updated in session_cache.update (updated dict contains conversation_history)
    assert 'conversation_history' in updated
    hist = updated['conversation_history']
    assert isinstance(hist, list)
    assert any(e['role'] == 'user' for e in hist)
    assert any(e['role'] == 'assistant' for e in hist)


def test_utterance_detector_undecodable_input(monkeypatch):
    det = UtteranceDetector(silence_threshold_rms=0.01, silence_duration_ms=150)
    # Undecodable bytes should be treated as silence and not raise
    complete, captured = det.process_chunk(b'not-a-wav', 16000)
    assert complete is False
    assert captured == b""


def test_orchestrator_short_transcription(monkeypatch):
    from app.services.voice_agent import VoiceAgentOrchestrator
    import app.agent.session_cache as session_cache

    orchestrator = VoiceAgentOrchestrator()
    client_id = "cid-short"

    class VADStub:
        def process_chunk(self, audio_bytes, sample_rate):
            return True, b'captured'

    session = {"verified": True, "phone_number": "+14155551001", "vad": VADStub(), "conversation_history": []}
    monkeypatch.setattr(session_cache, "get", lambda cid: session if cid == client_id else None)

    # Track updates to ensure history is NOT updated for short transcription
    called_update = {"count": 0}
    def fake_update(cid, **kw):
        called_update["count"] += 1
    monkeypatch.setattr(session_cache, "update", fake_update)

    async def short_transcribe(data):
        return "hi"
    monkeypatch.setattr('app.services.voice_agent.transcribe_audio', short_transcribe)

    async def fake_tts(text, voice="alloy"):
        return b'ask-again-bytes'
    monkeypatch.setattr('app.services.voice_agent.synthesise_speech', fake_tts)

    sent = []
    def send_ws(payload):
        sent.append(payload)

    asyncio.run(orchestrator.process_audio_chunk(client_id, b'data', 16000, send_ws))

    # Should have sent an agent_audio with TTS prompt and not updated history
    assert any(p.get('type') == 'agent_audio' for p in sent)
    assert called_update['count'] == 0


def test_orchestrator_langgraph_failure_updates_history(monkeypatch):
    from app.services.voice_agent import VoiceAgentOrchestrator
    import app.agent.session_cache as session_cache

    orchestrator = VoiceAgentOrchestrator()
    client_id = "cid-fail"

    class VADStub:
        def process_chunk(self, audio_bytes, sample_rate):
            return True, b'captured'

    session = {"verified": True, "phone_number": "+14155551002", "vad": VADStub(), "conversation_history": []}
    monkeypatch.setattr(session_cache, "get", lambda cid: session if cid == client_id else None)

    updated = {}
    monkeypatch.setattr(session_cache, "update", lambda cid, **kw: updated.update(kw))

    async def transcribe(data):
        return "what is my balance today"
    monkeypatch.setattr('app.services.voice_agent.transcribe_audio', transcribe)

    class GraphFail:
        async def ainvoke(self, state):
            raise ValueError('SECURITY_MAX_RETRIES')
    monkeypatch.setattr('app.services.voice_agent.get_graph', lambda: GraphFail())

    async def fake_tts(text, voice="alloy"):
        return b'apology-bytes'
    monkeypatch.setattr('app.services.voice_agent.synthesise_speech', fake_tts)

    sent = []
    def send_ws(payload):
        sent.append(payload)

    asyncio.run(orchestrator.process_audio_chunk(client_id, b'data', 16000, send_ws))

    # Check that conversation_history was updated with user + assistant apology
    assert 'conversation_history' in updated
    hist = updated['conversation_history']
    assert any(e['role'] == 'user' for e in hist)
    assert any('Sorry' in e['text'] or "could not process" in e['text'] for e in hist if e['role'] == 'assistant')
    # And an agent_audio response should have been sent
    assert any(p.get('type') == 'agent_audio' for p in sent)


def test_orchestrator_undecodable_graph_messages(monkeypatch):
    from app.services.voice_agent import VoiceAgentOrchestrator
    import app.agent.session_cache as session_cache

    orchestrator = VoiceAgentOrchestrator()
    client_id = "cid-udec"

    class VADStub:
        def process_chunk(self, audio_bytes, sample_rate):
            return True, b'captured'

    session = {"verified": True, "phone_number": "+14155551003", "vad": VADStub(), "conversation_history": []}
    monkeypatch.setattr(session_cache, "get", lambda cid: session if cid == client_id else None)

    updated = {}
    monkeypatch.setattr(session_cache, "update", lambda cid, **kw: updated.update(kw))

    async def transcribe(data):
        return "please list my recent transactions"
    monkeypatch.setattr('app.services.voice_agent.transcribe_audio', transcribe)

    # Graph returns messages that are not AIMessage instances (undecodable)
    class GraphUndecodable:
        async def ainvoke(self, state):
            return {"messages": ["raw-string-output", {"tool": "mcp_exec", "error": "malformed"}]}

    monkeypatch.setattr('app.services.voice_agent.get_graph', lambda: GraphUndecodable())

    async def fake_tts(text, voice="alloy"):
        return b'fallback-bytes'
    monkeypatch.setattr('app.services.voice_agent.synthesise_speech', fake_tts)

    sent = []
    def send_ws(payload):
        sent.append(payload)

    asyncio.run(orchestrator.process_audio_chunk(client_id, b'data', 16000, send_ws))

    # Conversation history should include the user turn and a fallback assistant response
    assert 'conversation_history' in updated
    hist = updated['conversation_history']
    assert any(e['role'] == 'user' for e in hist)
    assert any(e['role'] == 'assistant' for e in hist)
    # Fallback assistant text used when messages are undecodable
    assert any("I'm sorry" in e.get('text', '') or "could not process" in e.get('text', '') for e in hist if e['role'] == 'assistant')
    assert any(p.get('type') == 'agent_audio' for p in sent)


def test_orchestrator_graph_mcp_tool_error_outputs(monkeypatch):
    from app.services.voice_agent import VoiceAgentOrchestrator
    import app.agent.session_cache as session_cache

    orchestrator = VoiceAgentOrchestrator()
    client_id = "cid-mcp-error"

    class VADStub:
        def process_chunk(self, audio_bytes, sample_rate):
            return True, b'captured'

    session = {"verified": True, "phone_number": "+14155551004", "vad": VADStub(), "conversation_history": []}
    monkeypatch.setattr(session_cache, "get", lambda cid: session if cid == client_id else None)

    updated = {}
    monkeypatch.setattr(session_cache, "update", lambda cid, **kw: updated.update(kw))

    async def transcribe(data):
        return "what happened to my last payment"
    monkeypatch.setattr('app.services.voice_agent.transcribe_audio', transcribe)

    # Simulate LangGraph returning a tool-error shaped message (MCP-related error payload)
    class GraphToolError:
        async def ainvoke(self, state):
            return {"messages": [{"type": "tool_error", "detail": "MCP execution failed: timeout"}]}

    monkeypatch.setattr('app.services.voice_agent.get_graph', lambda: GraphToolError())

    async def fake_tts(text, voice="alloy"):
        return b'error-bytes'
    monkeypatch.setattr('app.services.voice_agent.synthesise_speech', fake_tts)

    sent = []
    def send_ws(payload):
        sent.append(payload)

    asyncio.run(orchestrator.process_audio_chunk(client_id, b'data', 16000, send_ws))

    assert 'conversation_history' in updated
    hist = updated['conversation_history']
    assert any(e['role'] == 'user' for e in hist)
    # Assistant should contain a safe fallback when tool outputs are present but not AIMessage
    assert any("Sorry" in e.get('text', '') or "could not process" in e.get('text', '') or "I'm sorry" in e.get('text', '') for e in hist if e['role'] == 'assistant')
    assert any(p.get('type') == 'agent_audio' for p in sent)
