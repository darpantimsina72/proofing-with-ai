"""
Text to speech for the Proofing with AI app.

Self-contained: nothing here imports from outside this folder.

HOW PLAYBACK WORKS HERE
-----------------------
The desktop app streams PCM through sounddevice and time-stretches with
librosa. This app does neither. Python synthesizes MP3 and hands the bytes to
the browser, which plays them in an <audio> element. That buys play, pause,
resume and seeking for free, and speed becomes `audio.playbackRate`, which
modern browsers pitch-correct — better than resampling and with no numpy,
librosa or sounddevice to install.

Long scripts are split into chunks and synthesized in the background, so the
first chunk starts playing while the rest are still being made. The browser
plays them back to back.

KEY FILES (in this folder)
--------------------------
    elevenlabsttsapi.txt  ElevenLabs (the default; api.txt is still read
                          when that file is not here)
    CartesiaApi.txt   Cartesia
    vertex_key.json   Google Cloud TTS (also needs: pip install
                      google-cloud-texttospeech)
"""

import json
import os
import re
import ssl
import threading
import urllib.error
import urllib.request

from _voices_literal import TTS_LANGUAGES        # the voice tables, verbatim

HERE = os.path.dirname(os.path.abspath(__file__))

# Keys typed into the ACCESS KEYS panel (keystore.py) win over the files in this folder.
try:
    import keystore as _ks
except Exception:
    _ks = None


def _stored(section, field="api_key"):
    try:
        return _ks.get(section, field) if _ks else None
    except Exception:
        return None
# TLS verification is OFF, matching the main app (which sets the same
# check_hostname/verify_mode on its own context and passes verify=False to
# requests). The corporate proxy re-signs traffic with a certificate that
# OpenSSL 3 rejects outright — "Missing Authority Key Identifier" — so with
# verification on, every ElevenLabs, Cartesia and gateway call fails before
# it leaves the machine. This is inherited from the main app deliberately,
# not an oversight: on a network without that proxy, delete the two lines
# below and verification comes back.
_SSL = ssl.create_default_context()
_SSL.check_hostname = False
_SSL.verify_mode = ssl.CERT_NONE

PLATFORMS = ["ElevenLabs", "Google TTS", "Cartesia"]
# What the panel starts on — when its key file is here; otherwise the first
# platform that has one (see default_platform).
DEFAULT_PLATFORM = "ElevenLabs"
DEFAULT_LANGUAGE = "Telugu"
ENGINES = ["Standard", "WaveNet", "Chirp3"]
DEFAULT_ENGINE = "Standard"

LANGUAGE_NAMES = list(TTS_LANGUAGES)

# The ElevenLabs key: elevenlabsttsapi.txt, the file made for it, and
# api.txt — the name it had before — only when that one is not here.
ELEVENLABS_KEY_FILES = ("elevenlabsttsapi.txt", "api.txt")
ELEVENLABS_VOICE_ID = "gIchDAOLBvAVujg9tyCO"   # used when no voice named below
# The voice ElevenLabs reads in until another is picked. A NAME, because the
# id belongs to the account: it is looked up in the account's voice list
# (see elevenlabs_default_voice), and ELEVENLABS_VOICE_ID stands in when the
# account has no voice by this name.
ELEVENLABS_DEFAULT_VOICE_NAME = "Madhusmita"
ELEVENLABS_MODEL = "eleven_v4"                 # until another is picked
# The models the panel's Model dropdown offers, (model_id, label). Turbo
# v2.5 is left out: ElevenLabs have deprecated it in favour of Flash v2.5.
ELEVENLABS_MODELS = (
    ("eleven_v3", "v3"),
    ("eleven_v4", "v4"),
    ("eleven_v4_turbo", "v4 Turbo"),
    ("eleven_multilingual_v2", "Multilingual v2"),
    ("eleven_flash_v2_5", "Flash v2.5"),
)
ELEVENLABS_CHUNK_CHARS = 1000

CARTESIA_KEY_FILE = "CartesiaApi.txt"
CARTESIA_API_BASE = "https://api.cartesia.ai"
CARTESIA_API_VERSION = "2024-11-13"
CARTESIA_MODEL = "sonic-3"
CARTESIA_CHUNK_CHARS = 2000
CARTESIA_PAGE_LIMIT = 100

GOOGLE_CHUNK_BYTES = 4800
# The main app reads this file for Google Cloud TTS — a service
# account, loaded explicitly rather than through the
# GOOGLE_APPLICATION_CREDENTIALS environment variable, so it cannot
# collide with the Vertex credentials Gemini may be using.
GOOGLE_TTS_KEY_FILE = "TTS_Key.json"

# Playback speeds offered in the panel. 1.25 is the default: reviewers listen
# to the same script many times over and settled on it.
SPEEDS = ["0.75", "1.0", "1.25", "1.5", "1.75", "2.0"]
DEFAULT_SPEED = "1.25"


def clean_key(raw):
    """Strip whitespace, a UTF-8 BOM and quotes; take the first real line.
    Notepad writes a BOM that str.strip() does not remove, which otherwise
    produces a key that looks right and is rejected."""
    text = (raw or "").lstrip("﻿")
    for line in text.splitlines():
        line = line.strip().strip("﻿").strip()
        if not line:
            continue
        if len(line) >= 2 and line[0] == line[-1] and line[0] in ("'", '"'):
            line = line[1:-1].strip()
        return line
    return ""


def _section_of(filename):
    return {"elevenlabsttsapi.txt": "elevenlabs", "api.txt": "elevenlabs",
            "CartesiaApi.txt": "cartesia", "TTS_Key.json": "tts_json"}.get(filename)


def read_key(filename):
    sec = _section_of(filename)
    if sec in ("elevenlabs", "cartesia") and _stored(sec):
        return clean_key(_stored(sec))
    path = os.path.join(HERE, filename)
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"{filename} not found in:\n  {HERE}\n\n"
            f"Create it and paste your key into it.")
    key = clean_key(open(path, "r", encoding="utf-8").read())
    if not key:
        raise ValueError(f"{filename} is empty.")
    return key


def have_key(filename):
    sec = _section_of(filename)
    if sec and _ks is not None and _ks.has(sec if sec != "tts_json" else "tts_json"):
        return True
    return os.path.exists(os.path.join(HERE, filename))


def elevenlabs_key_file():
    """The ElevenLabs key file in use: the first of ELEVENLABS_KEY_FILES
    that is here, or the preferred name when neither is — so the "not found"
    message names the file to create."""
    return next((f for f in ELEVENLABS_KEY_FILES if have_key(f)),
                ELEVENLABS_KEY_FILES[0])


def available_platforms():
    """Which platforms this folder is actually set up for."""
    out = []
    if have_key(elevenlabs_key_file()):
        out.append("ElevenLabs")
    if have_key(GOOGLE_TTS_KEY_FILE):
        out.append("Google TTS")
    if have_key(CARTESIA_KEY_FILE):
        out.append("Cartesia")
    return out


def default_platform():
    """DEFAULT_PLATFORM when its key is here; otherwise the first platform
    that is set up, so the panel never starts on one that cannot speak."""
    have = available_platforms()
    if DEFAULT_PLATFORM in have or not have:
        return DEFAULT_PLATFORM
    return have[0]


def language_code(language):
    return TTS_LANGUAGES.get(language, {}).get("code", "te-IN")


def voices_for(language, engine):
    return list(TTS_LANGUAGES.get(language, {}).get(engine, []))


def default_voice(language=None, engine=None):
    """First voice of the list, which is always the -A variant: the tables
    are ordered A, B, C, D. Used both at startup and whenever a change of
    language or engine leaves the previous pick invalid, so the selection
    lands on the same voice either way."""
    names = voices_for(language or DEFAULT_LANGUAGE,
                       engine or DEFAULT_ENGINE)
    return names[0] if names else ""


def voice_like(voice, language, engine):
    """The Standard voice in `language` for reading one sentence in another
    language. Always Standard, whatever engine the panel is on — the
    reviewers asked for it. The letter is kept where there is one
    (te-IN-Standard-B becomes en-US-Standard-B); otherwise it is the first
    Standard voice. `engine` is no longer used."""
    names = voices_for(language, "Standard")
    if not names:
        return voice
    parts = (voice or "").split("-", 2)
    tail = parts[2] if len(parts) == 3 else ""
    if tail:
        for n in names:
            if n.split("-", 2)[-1] == tail:
                return n
    return names[0]


def cartesia_language(lang_code):
    """Cartesia wants a bare ISO-639-1 code ("te"), not "te-IN"."""
    return (lang_code or "te-IN").split("-")[0]


# ── chunking ─────────────────────────────────────────────────────────────
def split_text(text, max_chars):
    """Split on sentence boundaries, never mid-sentence, and never longer
    than max_chars. Keeps the dubbing script's pause markers intact because
    it only ever breaks after . ! ? ; or a newline."""
    text = (text or "").strip()
    if not text:
        return []
    parts, buf = [], ""
    for piece in re.split(r'(?<=[.!?;])\s+|\n+', text):
        piece = piece.strip()
        if not piece:
            continue
        if buf and len(buf) + 1 + len(piece) > max_chars:
            parts.append(buf)
            buf = piece
        else:
            buf = (buf + " " + piece).strip() if buf else piece
    if buf:
        parts.append(buf)
    # A single sentence longer than the limit still has to be broken.
    out = []
    for p in parts:
        while len(p) > max_chars:
            out.append(p[:max_chars])
            p = p[max_chars:]
        if p:
            out.append(p)
    return out


def split_text_bytes(text, max_bytes=GOOGLE_CHUNK_BYTES):
    """Chunk for Google, whose limit is on UTF-8 BYTES.

    Telugu runs about three bytes a character, so a character count
    overshoots badly: 7,200 characters is 18,400 bytes. Sentences are packed
    by byte length, and a single sentence longer than the limit is cut at the
    largest character count that still fits — found by bisection, because
    where the byte budget lands inside a multi-byte string cannot be
    calculated directly."""
    pieces = []
    for p in re.split(r'(?<=[.!?;])\s+|\n+', (text or "").strip()):
        p = p.strip()
        if p:
            pieces.append(p)

    safe = []
    for p in pieces:
        while len(p.encode("utf-8")) > max_bytes:
            lo, hi = 1, len(p)
            while lo < hi:
                mid = (lo + hi + 1) // 2
                if len(p[:mid].encode("utf-8")) <= max_bytes:
                    lo = mid
                else:
                    hi = mid - 1
            safe.append(p[:lo])
            p = p[lo:]
        if p:
            safe.append(p)

    chunks, buf = [], ""
    for p in safe:
        cand = (buf + " " + p).strip() if buf else p
        if len(cand.encode("utf-8")) > max_bytes and buf:
            chunks.append(buf)
            buf = p
        else:
            buf = cand
    if buf:
        chunks.append(buf)
    return chunks


def chunks_for(platform, text):
    if platform == "ElevenLabs":
        return split_text(text, ELEVENLABS_CHUNK_CHARS)
    if platform == "Cartesia":
        return split_text(text, CARTESIA_CHUNK_CHARS)
    return split_text_bytes(text)


# ── per-platform synthesis: text in, MP3 bytes out ───────────────────────
def _post(url, payload, headers, timeout=300):
    req = urllib.request.Request(url, data=payload, method="POST",
                                 headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=_SSL) as r:
            return r.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {detail[:400]}") from exc


def synth_elevenlabs(text, voice_id=None, model_id=ELEVENLABS_MODEL):
    key = read_key(elevenlabs_key_file())
    vid = voice_id or ELEVENLABS_VOICE_ID
    payload = json.dumps({
        "text": text,
        "model_id": model_id,
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
    }).encode("utf-8")
    return _post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{vid}",
        payload,
        {"xi-api-key": key, "Content-Type": "application/json",
         "Accept": "audio/mpeg"})


def synth_cartesia(text, voice_id, language="te",
                   model_id=CARTESIA_MODEL):
    if not voice_id:
        raise ValueError("No Cartesia voice selected. Pick one in TTS "
                         "Settings.")
    key = read_key(CARTESIA_KEY_FILE)
    payload = json.dumps({
        "model_id": model_id,
        "transcript": text,
        "voice": {"mode": "id", "id": voice_id},
        "language": language,
        "output_format": {"container": "mp3", "bit_rate": 128000,
                          "sample_rate": 44100},
    }).encode("utf-8")
    return _post(
        f"{CARTESIA_API_BASE}/tts/bytes", payload,
        {"X-API-Key": key, "Cartesia-Version": CARTESIA_API_VERSION,
         "Content-Type": "application/json"})


_google_client = None


def _build_google_client():
    """Built exactly as the main app builds it: a service account read from
    TTS_Key.json with the cloud-platform scope, handed straight to the
    client. Loading it explicitly — rather than via the
    GOOGLE_APPLICATION_CREDENTIALS environment variable — keeps it separate
    from the Vertex credentials Gemini may be using in the same process."""
    try:
        from google.cloud import texttospeech
        from google.oauth2 import service_account
    except ImportError as exc:
        raise ImportError(
            "Google TTS needs extra packages:\n"
            "    pip install google-cloud-texttospeech google-auth\n"
            "Or choose ElevenLabs or Cartesia, which need none.") from exc

    try:
        cred = (_ks.json_path("tts_json") if _ks else None) or os.path.join(HERE, GOOGLE_TTS_KEY_FILE)
    except Exception:
        cred = os.path.join(HERE, GOOGLE_TTS_KEY_FILE)
    if not os.path.exists(cred):
        raise FileNotFoundError(
            GOOGLE_TTS_KEY_FILE + " not found in:\n  " + HERE)
    creds = service_account.Credentials.from_service_account_file(
        cred, scopes=["https://www.googleapis.com/auth/cloud-platform"])
    return texttospeech.TextToSpeechClient(credentials=creds)


def synth_google(text, lang_code, voice_name):
    """Google Cloud TTS via TTS_Key.json in this folder."""
    global _google_client
    from google.cloud import texttospeech
    if _google_client is None:
        _google_client = _build_google_client()

    resp = _google_client.synthesize_speech(
        input=texttospeech.SynthesisInput(text=text),
        voice=texttospeech.VoiceSelectionParams(
            language_code=lang_code or "te-IN", name=voice_name),
        audio_config=texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3))
    return resp.audio_content


def synth(platform, text, settings):
    """One chunk, whichever platform is selected."""
    if platform == "ElevenLabs":
        return synth_elevenlabs(
            text, settings.get("el_voice") or elevenlabs_default_voice(),
            settings.get("el_model") or ELEVENLABS_MODEL)
    if platform == "Cartesia":
        return synth_cartesia(
            text, settings.get("ct_voice"),
            cartesia_language(settings.get("lang_code")))
    return synth_google(text, settings.get("lang_code"),
                        settings.get("voice"))


# ── live voice lists ─────────────────────────────────────────────────────
def list_elevenlabs_voices():
    key = read_key(elevenlabs_key_file())
    req = urllib.request.Request("https://api.elevenlabs.io/v1/voices",
                                 headers={"xi-api-key": key})
    with urllib.request.urlopen(req, timeout=60, context=_SSL) as r:
        data = json.loads(r.read().decode("utf-8"))
    return [{"id": v.get("voice_id", ""), "name": v.get("name", "")}
            for v in data.get("voices", []) if v.get("voice_id")]


def find_voice(voices, name=None):
    """The id of the voice called `name` (ELEVENLABS_DEFAULT_VOICE_NAME by
    default) in a list from list_elevenlabs_voices, or "". An exact name
    first, then one that starts with it ("Madhusmita - Expressive Narrator"), then one that
    contains it; case never matters."""
    want = (name or ELEVENLABS_DEFAULT_VOICE_NAME).strip().lower()
    names = [((v.get("name") or "").strip().lower(), v.get("id", ""))
             for v in voices]
    for test in (lambda n: n == want, lambda n: n.startswith(want),
                 lambda n: want in n):
        hit = next((vid for n, vid in names if vid and test(n)), "")
        if hit:
            return hit
    return ""


_el_default = None          # the default voice's id, once it has been looked up


def elevenlabs_default_voice():
    """The id of ELEVENLABS_DEFAULT_VOICE_NAME on this account, looked up
    by name the first time a voice is needed and remembered after that —
    the account's voice list is what knows the id, not this file.

    With no voice of that name the built-in ELEVENLABS_VOICE_ID speaks
    instead; that answer is remembered too. A lookup that FAILS (no network,
    say) is not remembered, so the next read tries again — and the built-in
    voice speaks in the meantime."""
    global _el_default
    if _el_default is not None:
        return _el_default
    try:
        voices = list_elevenlabs_voices()
    except Exception:
        return ELEVENLABS_VOICE_ID
    _el_default = find_voice(voices) or ELEVENLABS_VOICE_ID
    return _el_default


def list_cartesia_voices():
    key = read_key(CARTESIA_KEY_FILE)
    out, page = [], None
    for _ in range(10):                      # bounded: pages of 100
        url = f"{CARTESIA_API_BASE}/voices/?limit={CARTESIA_PAGE_LIMIT}"
        if page:
            url += f"&starting_after={page}"
        req = urllib.request.Request(
            url, headers={"X-API-Key": key,
                          "Cartesia-Version": CARTESIA_API_VERSION})
        with urllib.request.urlopen(req, timeout=60, context=_SSL) as r:
            data = json.loads(r.read().decode("utf-8"))
        rows = data.get("data", data if isinstance(data, list) else [])
        for v in rows:
            if v.get("id"):
                out.append({"id": v["id"],
                            "name": v.get("name", ""),
                            "language": v.get("language", "")})
        if not data.get("has_more") or not rows:
            break
        page = rows[-1].get("id")
    return out


# ── a playback job: chunks synthesized in the background ─────────────────
class Job:
    """One Start / Start-from-cursor press.

    Chunks are synthesized in order on a worker thread and handed to the
    browser as each becomes ready, so playback begins on chunk 0 while the
    rest are still being made — the same streaming behaviour as the desktop
    player, without any audio library here."""

    def __init__(self, job_id, platform, text, settings):
        self.id = job_id
        self.platform = platform
        self.settings = settings
        self.chunks = chunks_for(platform, text)
        self.audio = [None] * len(self.chunks)
        self.errors = [None] * len(self.chunks)
        self.done = 0
        self.cancelled = False
        self._lock = threading.Lock()

    def start(self):
        threading.Thread(target=self._work, daemon=True).start()
        return self

    def _work(self):
        for i, chunk in enumerate(self.chunks):
            if self.cancelled:
                return
            try:
                data = synth(self.platform, chunk, self.settings)
            except Exception as exc:
                with self._lock:
                    self.errors[i] = f"{type(exc).__name__}: {exc}"
                return
            with self._lock:
                self.audio[i] = data
                self.done += 1

    def status(self):
        with self._lock:
            err = next((e for e in self.errors if e), None)
            return {"id": self.id, "total": len(self.chunks),
                    "ready": self.done, "error": err}

    def chunk(self, i):
        with self._lock:
            if not (0 <= i < len(self.chunks)):
                return None, "no such chunk"
            if self.errors[i]:
                return None, self.errors[i]
            return self.audio[i], None
