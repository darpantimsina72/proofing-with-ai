"""
Gemini access for the Proofing with AI app.

Self-contained on purpose: this folder imports nothing from
End_to_End_Pipeline.py or any other script outside it. The three auth paths
mirror the ones the main app offers, so the same key files work:

    geminiapi.txt    Gemini API key          -> mode "API"
    openaiapi.txt    OpenAI-compatible key   -> mode "OPENROUTER"  (gateway)
    vertex_key.json  service account         -> mode "JSON"        (Vertex AI)

Put whichever you use in this folder. All three return an object exposing
`client.models.generate_content(model=..., contents=...).text`, so callers
never need to know which one is in play.
"""

import json
import os
import ssl
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))

# Keys typed into the ACCESS KEYS panel (keystore.py, in the user's profile) win over the notepad files in this folder;
# with nothing stored, the files are read as before.
try:
    import keystore as _ks
except Exception:
    _ks = None


def _stored(section, field="api_key"):
    try:
        return _ks.get(section, field) if _ks else None
    except Exception:
        return None


def _stored_json_path(section):
    try:
        return _ks.json_path(section) if _ks else None
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
_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE

# Defaults per mode. Change here to move the whole app to another model.
GEMINI_API_MODEL = "gemini-3-pro-preview"
GEMINI_JSON_MODEL = "gemini-2.5-pro"

# Vertex location for JSON mode. "global" rather than a region: the Gemini 3
# models are only served from the global endpoint, and a regional one answers
# 404 NOT_FOUND for them. Measured on 2026-09-16 against projectforvertexai —
#   gemini-2.5-pro          us-central1 OK    global OK
#   gemini-3-flash-preview  us-central1 404   global OK
#   gemini-3.8-flash        us-central1 404   global OK
# so global costs nothing for the older models and is the only thing that
# reaches the newer ones. Set a region here if a model ever needs one.
VERTEX_LOCATION = "global"
OPENROUTER_MODEL = "vertex_ai/gemini-3.1-pro-preview"

# The in-house gateway. May be written with or without a trailing /v1.
OPENROUTER_BASE_URL = "https://offeringschat.isha.in/"

KEY_FILES = {
    "API": "geminiapi.txt",
    "OPENROUTER": "openaiapi.txt",
    "JSON": "vertex_key.json",
}

# Display order for the Gemini access panel, matching the main app's list.
MODE_ORDER = ["OPENROUTER", "API", "JSON"]

# What the app starts on when that key file is present: Open AI Api, the
# gateway. Falls back to whatever key files ARE present - see
# available_modes() and the launcher.
DEFAULT_MODE = "OPENROUTER"

# Pre-selected in the model dropdown, overriding whichever per-mode default
# MODE_DEFAULT_MODEL would otherwise supply. Picking "" in the panel puts the
# per-mode default back. The BARE id, not the "vertex_ai/" prefixed one in
# AVAILABLE_MODELS — that prefix is the gateway's naming, and JSON/Vertex is
# the default access mode.
DEFAULT_MODEL = "gemini-3.1-pro-preview"

# Switching the access mode switches the model with it. The same model needs
# a different id on each side — "gemini-3.7-flash" on Vertex is
# "vertex_ai/gemini-3.7-flash" on the gateway — so carrying a selection across
# a mode change is what produces the gateway's 401 ("user can only access
# models=[...]") and Vertex's 404. A mode with no entry here keeps whatever
# model is already selected.
MODE_PREFERRED_MODEL = {
    "OPENROUTER": "vertex_ai/gemini-3.7-flash",
    "JSON":       "gemini-3.1-pro-preview",
}

MODE_LABELS = {
    "OPENROUTER": "Open AI Api   (→ vertex_ai/gemini-3.1-pro-preview)",
    "API":        "Gemini API    (→ gemini-3-pro-preview)",
    "JSON":       "Gemini JSON   (→ gemini-2.5-pro)",
}

MODE_DEFAULT_MODEL = {
    "OPENROUTER": OPENROUTER_MODEL,
    "API": GEMINI_API_MODEL,
    "JSON": GEMINI_JSON_MODEL,
}

# Names come from the gateway's allowed-list. Picking one overrides the
# per-mode default for every call; "" means use the per-mode default.
# A group divider inside the model dropdown, not a model. The page turns
# it into two labelled <optgroup>s, so it is never selectable there.
MODEL_SEPARATOR = "────  for Open AI Api (gateway)  ────"

AVAILABLE_MODELS = [
    "vertex_ai/gemini-3.1-pro-preview",
    "gemini-2.5-pro",
    "gemini-3-flash-preview",
    "vertex_ai/gemini-3-pro-image-preview",
    "vertex_ai/gemini-2.5-flash-image",
    # Confirmed on 2026-09-16 by calling each one on Vertex at the global
    # endpoint — every id below answered a text prompt. Bare ids, no
    # "vertex_ai/" prefix: that prefix is the gateway's naming and is stripped
    # again for API / JSON modes.
    "gemini-3.1-pro-preview",
    "gemini-3.7-flash",
    "gemini-3.6-flash",
    "gemini-3.5-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
    "gemini-3.8-flash",

    MODEL_SEPARATOR,

# ── What the OpenRouter gateway will accept ─────────────────────────────────
# Its own allow-list, copied from the 401 it returns when you send anything
# else ("user can only access models=[...]"). It overlaps the Vertex list
# above, and the SAME model often needs a DIFFERENT id on each side —
# "gemini-3.7-flash" on Vertex is "vertex_ai/gemini-3.7-flash" here — which is
# why these are listed again rather than de-duplicated. Pick from the group
# that matches the access mode you are on.
    "vertex_ai/gemini-3.1-pro-preview",
    "gemini-2.5-pro",
    "gemini-3-flash-preview",
    "vertex_ai/gemini-3-pro-image-preview",
    "vertex_ai/gemini-2.5-flash-image",
    "vertex_ai/gemini-3.7-flash",
    "vertex_ai/gemini-3.5-flash",
    "gemini-3.6-flash",
    "gemini-3.1-flash",
]


def _openrouter_endpoint(base):
    base = (base or "").rstrip("/")
    if not base.endswith("/v1"):
        base += "/v1"
    return base + "/chat/completions"


OPENROUTER_URL = _openrouter_endpoint(OPENROUTER_BASE_URL)


def _openrouter_url_now():
    """The gateway's chat endpoint now: the base URL typed in the ACCESS KEYS panel when there is one (applies at once,
    no restart), else OPENROUTER_BASE_URL."""
    return _openrouter_endpoint(_stored("openai", "base_url") or OPENROUTER_BASE_URL)


def clean_api_key(raw):
    """Normalise a key pasted into a text file.

    Strips whitespace, a UTF-8 BOM and surrounding quotes, and uses only the
    first non-empty line. Notepad writes UTF-8 *with* a BOM on Windows and
    the BOM is not whitespace to str.strip(), so without this a key that
    looks perfectly correct is rejected as an invalid token."""
    text = (raw or "").lstrip("﻿")
    for line in text.splitlines():
        line = line.strip().strip("﻿").strip()
        if not line:
            continue
        if len(line) >= 2 and line[0] == line[-1] and line[0] in ("'", '"'):
            line = line[1:-1].strip()
        return line
    return ""


def _read_key(filename):
    section = {"openaiapi.txt": "openai", "geminiapi.txt": "gemini_api"}.get(filename)
    if section and _stored(section):
        return clean_api_key(_stored(section))
    path = os.path.join(HERE, filename)
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"{filename} not found in:\n  {HERE}\n\n"
            f"Create the file and paste your key into it.")
    with open(path, "r", encoding="utf-8") as fh:
        key = clean_api_key(fh.read())
    if not key:
        raise ValueError(f"{filename} is empty.")
    return key


def available_modes():
    """Which auth paths have a key — typed in the ACCESS KEYS panel, or a file in this folder — in panel order."""
    section = {"OPENROUTER": "openai", "API": "gemini_api", "JSON": "vertex_json"}
    return [m for m in MODE_ORDER
            if (_ks is not None and _ks.has(section[m])) or os.path.exists(os.path.join(HERE, KEY_FILES[m]))]


class _OpenRouterClient:
    """Duck-typed stand-in for google-genai's Client, over the gateway's
    OpenAI-compatible chat-completions endpoint."""

    class _Response:
        __slots__ = ("text",)

        def __init__(self, text):
            self.text = text

    class _Models:
        def __init__(self, api_key):
            self._api_key = api_key

        def generate_content(self, *, model, contents):
            payload = json.dumps({
                "model": model,
                "messages": [{"role": "user", "content": contents}],
            }).encode("utf-8")
            req = urllib.request.Request(
                _openrouter_url_now(), data=payload, method="POST",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                    # A real User-Agent is required: the gateway sits behind
                    # Cloudflare, which blocks urllib's default and answers
                    # with a 1010 that looks nothing like an auth failure.
                    "User-Agent": "Proofing-With-AI/1.0",
                    "HTTP-Referer": "https://local-app/proofing-with-ai",
                    "X-Title": "Proofing with AI",
                })
            try:
                with urllib.request.urlopen(req, timeout=600,
                                            context=_SSL_CTX) as resp:
                    body = resp.read().decode("utf-8", errors="replace")
            except urllib.error.HTTPError as exc:
                detail = exc.read().decode("utf-8", errors="replace")
                raise RuntimeError(
                    f"Gateway HTTP {exc.code}: {detail[:500]}") from exc
            try:
                data = json.loads(body)
                return _OpenRouterClient._Response(
                    data["choices"][0]["message"]["content"] or "")
            except (KeyError, IndexError, ValueError) as exc:
                raise RuntimeError(
                    f"Unexpected gateway response: {body[:500]}") from exc

    def __init__(self, api_key):
        self.models = _OpenRouterClient._Models(api_key)


def _vertex_project():
    path = _stored_json_path("vertex_json") or os.path.join(HERE, KEY_FILES["JSON"])
    if not os.path.exists(path):
        raise FileNotFoundError(f"vertex_key.json not found in:\n  {HERE}")
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = path
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    project = data.get("project_id")
    if not project:
        raise ValueError("vertex_key.json has no 'project_id'.")
    return project


def _strip_vertex_prefix(model):
    """The gateway names models "vertex_ai/x"; the google-genai SDK wants
    plain "x"."""
    return model.split("/", 1)[1] if model.startswith("vertex_ai/") else model


def make_client(mode, model=None):
    """(client, model_name) for the requested auth path."""
    if mode == "OPENROUTER":
        return (_OpenRouterClient(_read_key(KEY_FILES["OPENROUTER"])),
                model or OPENROUTER_MODEL)

    try:
        from google import genai
    except ImportError as exc:
        raise ImportError(
            "google-genai is not installed. Either run:\n"
            "    pip install google-genai\n"
            "or put openaiapi.txt in this folder to use the gateway "
            "instead, which needs no extra package.") from exc

    if mode == "API":
        return (genai.Client(api_key=_read_key(KEY_FILES["API"])),
                _strip_vertex_prefix(model or GEMINI_API_MODEL))
    return (genai.Client(vertexai=True, project=_vertex_project(),
                         location=VERTEX_LOCATION),
            _strip_vertex_prefix(model or GEMINI_JSON_MODEL))


def run_prompt(text, prompt_body, mode, model=None):
    """One call: prompt body, then the user's text, and give back the reply."""
    client, model_name = make_client(mode, model)
    full = f"{prompt_body}\n\n=== Input Text ===\n{text}"
    return client.models.generate_content(
        model=model_name, contents=full).text
