"""Access keys entered on the page (the ACCESS KEYS panel), kept in the app's OWN folder (the folder this file is in):
access_keys.json, and access_keys_json\\ for a dropped service-account file. Each app that has a copy of this module keeps
its own keys, and the keys travel with the folder. The folder's .gitignore keeps them out of Git; a zip or rar of the folder
DOES carry them, so leave access_keys.json out of anything you send.

  openai       base_url, api_key          the Open AI Api gateway
  gemini_api   api_key                    Gemini API
  vertex_json  content, filename          Gemini JSON (a Vertex AI service-account file)
  elevenlabs   api_key
  cartesia     api_key
  tts_json     content, filename          Google Cloud TTS (a service-account file)
  clickup      api_key                    ClickUp personal token

The engine (Performance_Script_App) asks this module first and falls back to the notepad files beside the script
when a section is empty here, so nothing that worked before stops working. A key is never sent back to the page:
`masked()` is what the page gets.

BLUE_DIAMOND_KEYS_DIR overrides the folder (tests). Nothing here touches the user's profile (AppData) any more.
"""
import json
import os
import threading

_LOCK = threading.Lock()

SECTIONS = {
    "openai":      ("base_url", "api_key"),
    "gemini_api":  ("api_key",),
    "vertex_json": ("content", "filename"),
    "elevenlabs":  ("api_key",),
    "cartesia":    ("api_key",),
    "tts_json":    ("content", "filename"),
    "clickup":     ("api_key",),
}
SECRET = {"api_key", "content"}          # what is never shown in full
JSON_SECTIONS = ("vertex_json", "tts_json")
# the notepad / json file each section used to come from (beside the script)
FILES = {"openai": "openaiapi.txt", "gemini_api": "geminiapi.txt", "vertex_json": "vertex_key.json",
         "elevenlabs": "api.txt", "cartesia": "CartesiaApi.txt", "tts_json": "TTS_Key.json",
         "clickup": "ClickupApi.txt"}
# what makes a section "set": its key (the base URL alone is not a key)
REQUIRED = {"openai": "api_key", "gemini_api": "api_key", "vertex_json": "content", "elevenlabs": "api_key",
            "cartesia": "api_key", "tts_json": "content", "clickup": "api_key"}


def store_dir():
    return os.environ.get("BLUE_DIAMOND_KEYS_DIR") or os.path.dirname(os.path.abspath(__file__))


def _file():
    return os.path.join(store_dir(), "access_keys.json")


def _read():
    try:
        with open(_file(), encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _write(data):
    os.makedirs(store_dir(), exist_ok=True)
    tmp = _file() + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=1)
    os.replace(tmp, _file())


def get(section, field="api_key"):
    """The stored value, or None."""
    v = (_read().get(section) or {}).get(field)
    return v if isinstance(v, str) and v.strip() else None


def has(section):
    return bool(get(section, REQUIRED[section]))


def put(section, **fields):
    """Keep `fields` of `section` (an empty value takes that field away)."""
    if section not in SECTIONS:
        raise KeyError(section)
    with _LOCK:
        data = _read()
        sec = dict(data.get(section) or {})
        for k, v in fields.items():
            if k not in SECTIONS[section]:
                raise KeyError(k)
            v = (v or "").strip() if isinstance(v, str) else v
            if v:
                sec[k] = v
            else:
                sec.pop(k, None)
        if sec:
            data[section] = sec
        else:
            data.pop(section, None)
        _write(data)


def clear(section):
    with _LOCK:
        data = _read()
        if data.pop(section, None) is not None:
            _write(data)
    try:                                     # the json copy made for libraries that want a file
        os.remove(os.path.join(store_dir(), "access_keys_json", section + ".json"))
    except OSError:
        pass


def json_path(section):
    """A file holding a stored service-account JSON (written when it is missing or differs), for the libraries that
    only take a path; None when the section has none."""
    text = get(section, "content")
    if not text:
        return None
    folder = os.path.join(store_dir(), "access_keys_json")
    path = os.path.join(folder, section + ".json")
    try:
        with open(path, encoding="utf-8") as fh:
            if fh.read() == text:
                return path
    except OSError:
        pass
    os.makedirs(folder, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    return path


def json_info(text):
    """(project_id, client_email) of a service-account JSON text, or raises ValueError saying what is wrong."""
    try:
        d = json.loads(text)
    except ValueError:
        raise ValueError("that is not a JSON file") from None
    if not isinstance(d, dict) or d.get("type") != "service_account" or not d.get("private_key") or not d.get("client_email"):
        raise ValueError("that JSON is not a service-account key (it needs type, client_email and private_key)")
    return d.get("project_id") or "", d.get("client_email") or ""


def masked():
    """What the page may see: whether each field is set, the last four characters of a key, the base URL in full,
    and for a JSON the project and account it names. Never a key."""
    data, out = _read(), {}
    for sec, fields in SECTIONS.items():
        s = data.get(sec) or {}
        info = {"set": has(sec), "fields": {}}
        for f in fields:
            v = s.get(f)
            if f in SECRET:
                info["fields"][f] = {"set": bool(v), "tail": (v[-4:] if v and f == "api_key" and len(v) > 8 else "")}
            else:
                info["fields"][f] = {"set": bool(v), "value": v or ""}
        if sec in JSON_SECTIONS and s.get("content"):
            try:
                info["project_id"], info["client_email"] = json_info(s["content"])
            except ValueError:
                pass
        out[sec] = info
    return out
