"""ElevenLabs text-to-speech. Returns an honest result when no key is set or the call fails."""
import json
import os
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

DEFAULT_VOICE_ID = "21m00Tcm4TlvDq8ikWAM"


def synthesize(text: str, out_dir: str = "out") -> dict:
    key = os.environ.get("ELEVENLABS_API_KEY")
    if not key:
        return {"audio_path": None, "note": "ElevenLabs is not configured (set ELEVENLABS_API_KEY). The text is still returned."}
    voice_id = os.environ.get("ELEVENLABS_VOICE_ID", DEFAULT_VOICE_ID)
    req = urllib.request.Request(
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
        data=json.dumps({"text": text, "model_id": "eleven_multilingual_v2"}).encode(),
        headers={"xi-api-key": key, "Content-Type": "application/json", "Accept": "audio/mpeg"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=40) as resp:
            audio = resp.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "ignore")[:300]
        return {"audio_path": None, "note": f"ElevenLabs refused the request (HTTP {exc.code}): {detail}"}
    except Exception as exc:
        return {"audio_path": None, "note": f"ElevenLabs request failed ({type(exc).__name__}). The text is still returned."}
    folder = Path(out_dir)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"briefing_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3"
    path.write_bytes(audio)
    return {"audio_path": str(path.resolve()), "note": "Audio saved."}