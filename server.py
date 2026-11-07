"""
The local web server behind the Proofing with AI page.

Self-contained: imports only the standard library and its two neighbours in
this folder.

SECURITY
--------
Bound to 127.0.0.1 only, on a random free port, and every request must carry
the session token minted at startup. Without it the server answers 403, so
nothing else on the machine can drive it or read the script.
"""

import collections
import json
import os
import re
import time
import sys
import subprocess
import urllib.request
import urllib.error
import secrets
import socket
import threading
import webbrowser
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

import gemini_client
import keystore
import review_core as core
import sync_helper
import tts

HERE = os.path.dirname(os.path.abspath(__file__))
PAGE_FILE = "index.html"
DETECT_PROMPT = "Detection_Prompt.txt"
SUGGEST_PROMPT = "Get_Suggestions_Prompt.txt"
ONESHOT_PROMPT = "Detection_and_Suggestions_Prompt.txt"
# The batch's own version: written for a book that another AI has already
# translated and proofed, so detection checks the Telugu against the English
# too, and the three versions are degrees of change rather than audio gaps.
BATCH_ONESHOT_PROMPT = "Detection_and_Suggestions_Prompt_Batch.txt"
# ...and its Get suggestions, for the sentences marked by hand on a batch
# page: the book's version of SUGGEST_PROMPT, written the same way.
BATCH_SUGG_PROMPT = "Get_Suggestions_Prompt_Batch.txt"
# Corrections to sync with new version: the approved Telugu brought in line
# with the book's revised (final) English. Its terms list is filled in from
# BATCH_ONESHOT_PROMPT at {{BOOK_TERMS}}.
SYNC_PROMPT = "Sync_With_Final_English_Prompt_Batch.txt"
TRANSLATE_PROMPT = "Custom_Text_Translation_Prompt.txt"
# One folder of prompts per language: Prompts/Telugu, Prompts/Hindi … A
# language whose folder is missing a prompt gets it made from the
# language-neutral master in Prompts/_template (see load_prompt).
PROMPTS_DIR = "Prompts"
PROMPT_TEMPLATE_DIR = "_template"
APP_SETTINGS_FILE = "App_Settings.json"    # {"language": "Hindi"} — the panel's choice, kept across launches
BATCH_FILE = "Batch_Progress.json"         # where progress went before Load pages
BATCH_LAST_FILE = "Batch_Last_Opened.txt"  # which progress file was open last
PROGRESS_SUFFIX = ".progress.json"         # beside a file chosen with Load pages
LEGACY_SUFFIX = ".batch.json"              # the main app's earlier name for it
CLIP_CACHE_MAX = 400       # sentence clips kept for the read-aloud, newest last


def fill_language(text, language):
    """{{LANGUAGE}} / {{LANGUAGE_UPPER}} in a prompt or contract, filled."""
    return (text.replace("{{LANGUAGE_UPPER}}", language.upper())
                .replace("{{LANGUAGE}}", language))


def prompt_path(name, language):
    return os.path.join(HERE, PROMPTS_DIR, language, name)


def load_prompt(name, language):
    """The prompt `name` for `language`: Prompts/<language>/<name>.

    A language whose folder does not have the file yet gets a copy made
    from Prompts/_template/<name> — the language-neutral master, with the
    language's name filled in — and that copy is what the team edits from
    then on (its terms list, its examples). The master is never read for a
    language that has its own file, so an edit there never reaches a
    language already set up."""
    path = prompt_path(name, language)
    if not os.path.exists(path):
        tpl = os.path.join(HERE, PROMPTS_DIR, PROMPT_TEMPLATE_DIR, name)
        if not os.path.exists(tpl):
            raise FileNotFoundError(
                f"{name} not found for {language}:\n  {path}\n"
                f"and there is no template to make it from:\n  {tpl}")
        with open(tpl, "r", encoding="utf-8") as fh:
            body = fill_language(fh.read(), language)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(body)
        return body
    with open(path, "r", encoding="utf-8") as fh:
        return fill_language(fh.read(), language)


def load_app_language():
    """The language chosen last time, or the default."""
    try:
        with open(os.path.join(HERE, APP_SETTINGS_FILE), "r",
                  encoding="utf-8") as fh:
            lang = json.load(fh).get("language", "")
    except Exception:
        lang = ""
    return lang if lang in tts.APP_LANGUAGES else tts.DEFAULT_LANGUAGE


def save_app_language(language):
    with open(os.path.join(HERE, APP_SETTINGS_FILE), "w",
              encoding="utf-8") as fh:
        json.dump({"language": language}, fh, ensure_ascii=False, indent=2)


class ProofingServer:
    def __init__(self, mode, model=None):
        # model=None at construction means "nothing asked for", which lands
        # on the app's DEFAULT_MODEL. Choosing "(this access mode's default)"
        # in the panel later sends "" and act_set_config turns that back into
        # None, which run_prompt reads as "use this mode's own default".
        # Nothing asked for starts on the access mode's own model — what
        # picking that mode in the panel would select.
        self.mode = mode
        self.model = (gemini_client.MODE_PREFERRED_MODEL.get(
                          mode, gemini_client.DEFAULT_MODEL)
                      if model is None else model)
        self.session = core.Session()
        self.token = secrets.token_urlsafe(24)
        # The language the whole app works in: the prompts, the page's
        # labels, the file formats, and what the two TTS panels start on.
        self.language = load_app_language()
        # TTS settings, mirroring the desktop app's panel.
        self.tts = {
            "platform": tts.default_platform(),
            "language": self.language,
            "engine": tts.DEFAULT_ENGINE,
            "voice": tts.default_voice(self.language),
            "el_voice": "",
            "el_model": tts.ELEVENLABS_MODEL,
            "ct_voice": "",
            "speed": tts.DEFAULT_SPEED,
        }
        # The Suggestions TTS Settings panel's own settings, for the play
        # buttons in the book's Suggestions box. Independent of the panel
        # above: Google's Standard Telugu voice until changed.
        self.tts_sugg = {
            "platform": "Google TTS",
            "language": self.language,
            "engine": "Standard",
            "voice": tts.default_voice(self.language, "Standard"),
            "el_voice": "",
            "el_model": tts.ELEVENLABS_MODEL,
            "ct_voice": "",
            "speed": tts.DEFAULT_SPEED,
        }
        self.jobs = {}
        self._job_seq = 0
        self.httpd = None
        self.port = None
        self._lock = threading.Lock()
        # The batch's progress file, when it came through Load pages (None:
        # BATCH_FILE here), and every progress path Load pages has handed
        # out — the only ones act_batch_use will accept.
        self.batch_path = None
        self._picked = set()
        self._dialog_lock = threading.Lock()
        # Sync helper files read so far, by path: (stamp, Helper).
        self._helpers = {}
        # Sentence clips for the read-aloud (see act_tts_sentence).
        self._clips = collections.OrderedDict()
        self._clip_busy = {}
        self._clip_lock = threading.Lock()

    # ── lifecycle ────────────────────────────────────────────────────────
    def start(self):
        if self.httpd is None:
            s = socket.socket()
            s.bind(("127.0.0.1", 0))
            self.port = s.getsockname()[1]
            s.close()
            self.httpd = ThreadingHTTPServer(("127.0.0.1", self.port),
                                             _make_handler(self))
            self.httpd.daemon_threads = True
            threading.Thread(target=self.httpd.serve_forever,
                             daemon=True).start()
        return self.url()

    def url(self):
        return f"http://127.0.0.1:{self.port}/?t={self.token}"

    def stop(self):
        if self.httpd is not None:
            try:
                self.httpd.shutdown()
                self.httpd.server_close()
            except Exception:
                pass
            self.httpd = None

    def open_browser(self):
        webbrowser.open(self.url())

    def _run(self, text, prompt_name, contract):
        body = (load_prompt(prompt_name, self.language)
                + fill_language(contract, self.language))
        return gemini_client.run_prompt(text, body, self.mode, self.model)

    # ── actions ──────────────────────────────────────────────────────────
    def act_set_config(self, patch):
        """Gemini access and model, and the app's language, set from the
        panels at the top of the page. Only the keys sent change. An empty
        model means "use this mode's default", which is what the main app's
        None override does."""
        with self._lock:
            if "mode" in patch and patch["mode"] in gemini_client.MODE_ORDER:
                self.mode = patch["mode"]
            if "model" in patch:
                self.model = (patch["model"] or None)
            lang = patch.get("language")
            if lang in tts.APP_LANGUAGES and lang != self.language:
                self.language = lang
                save_app_language(lang)
                # Both TTS panels read in the app's language until the
                # reviewer picks another there; a Google voice that belonged
                # to the old language's list is swapped for the new list's.
                for cfg in (self.tts, self.tts_sugg):
                    cfg["language"] = lang
                    allowed = tts.voices_for(lang, cfg["engine"])
                    if allowed and cfg["voice"] not in allowed:
                        cfg["voice"] = allowed[0]
        return self.config()

    def config(self):
        have = gemini_client.available_modes()
        return {
            "language": self.language,
            "languages": tts.APP_LANGUAGES,
            "prompts_dir": os.path.join(PROMPTS_DIR, self.language),
            "mode": self.mode,
            "model": self.model or "",
            "modes": [{"value": m,
                       "label": gemini_client.MODE_LABELS[m],
                       "available": m in have,
                       "keyfile": gemini_client.KEY_FILES[m],
                       "default_model": gemini_client.MODE_DEFAULT_MODEL[m],
                       "preferred_model":
                           gemini_client.MODE_PREFERRED_MODEL.get(m, "")}
                      for m in gemini_client.MODE_ORDER],
            "models": list(gemini_client.AVAILABLE_MODELS),
            "model_separator": gemini_client.MODEL_SEPARATOR,
        }

    # ── ACCESS KEYS panel: the keys typed on the page (keystore.py), tested and imported here ──
    KEY_MODE = {"openai": "OPENROUTER", "gemini_api": "API", "vertex_json": "JSON"}

    def _keys_reply(self):
        """What the page gets after a change: the masked keys, and the config the keys decide (which Gemini modes and
        TTS platforms have a key now)."""
        return {"keys": self._keys_state(), "config": self.config(), "tts": self.tts_config(),
                "tts_sugg": self.tts_config("sugg")}

    def _keys_state(self):
        return {"sections": keystore.masked(), "dir": keystore.store_dir(),
                "files": {s: os.path.isfile(os.path.join(HERE, f)) for s, f in keystore.FILES.items()},
                "default_base_url": gemini_client.OPENROUTER_BASE_URL}

    def act_keys_set(self, p):
        sec = p.get("section")
        if sec not in keystore.SECTIONS:
            return {"error": "No such key."}
        try:
            if sec in keystore.JSON_SECTIONS:
                text = p.get("json") or ""
                pid, _mail = keystore.json_info(text)
                if sec == "vertex_json" and not pid:
                    raise ValueError("that service-account file has no project_id, which Gemini JSON needs")
                keystore.put(sec, content=text, filename=os.path.basename(p.get("filename") or ""))
            else:
                upd = {}
                for f, v in (p.get("fields") or {}).items():
                    if f not in keystore.SECTIONS[sec]:
                        continue
                    v = (v or "").strip()
                    if f == "api_key":
                        v = gemini_client.clean_api_key(v)
                        if not v:
                            continue                     # an empty key box means "keep the one saved"
                    elif f == "base_url" and v and not re.match(r"^https?://\S+$", v):
                        raise ValueError("the base URL must start with http:// or https://")
                    upd[f] = v                           # an empty base URL takes it away: the default is used
                if not upd:
                    raise ValueError("there is nothing to save — paste a key first")
                keystore.put(sec, **upd)
        except ValueError as exc:
            return {"error": str(exc)}
        except OSError as exc:
            return {"error": f"the keys could not be saved: {exc}"}
        return self._keys_reply()

    def act_keys_clear(self, section):
        if section not in keystore.SECTIONS:
            return {"error": "No such key."}
        keystore.clear(section)
        return self._keys_reply()

    def act_keys_import(self):
        """Fill the panel from the notepad / json files in this folder — only the keys not already saved."""
        done = []
        files = dict(keystore.FILES)
        files["elevenlabs"] = tts.elevenlabs_key_file()
        for sec, fname in files.items():
            path = os.path.join(HERE, fname)
            if sec == "clickup" or keystore.has(sec) or not os.path.isfile(path):
                continue
            try:
                with open(path, encoding="utf-8-sig") as fh:
                    raw = fh.read()
                if sec in keystore.JSON_SECTIONS:
                    keystore.json_info(raw)
                    keystore.put(sec, content=raw, filename=fname)
                else:
                    key = gemini_client.clean_api_key(raw)
                    if not key:
                        continue
                    keystore.put(sec, api_key=key)
                done.append(fname)
            except (OSError, ValueError):
                continue
        r = self._keys_reply()
        r["imported"] = done
        return r

    def act_keys_test(self, section):
        """A tiny real request with the key as it is now (stored, else the file): one Gemini answer for the three Gemini
        modes, a voices call for ElevenLabs and Cartesia; a Google JSON is only read. Gives up after 60 s."""
        if section not in keystore.SECTIONS or section == "clickup":
            return {"error": "No such key."}
        box = {}

        def run():
            try:
                t0 = time.time()
                if section in self.KEY_MODE:
                    client, model = gemini_client.make_client(self.KEY_MODE[section], None)
                    text = (client.models.generate_content(model=model, contents="Reply with the single word OK.").text or "").strip()
                    box["message"] = f"✔ {model} answered “{text[:40]}” in {time.time() - t0:.1f}s"
                elif section == "elevenlabs":
                    self._key_get("https://api.elevenlabs.io/v1/voices?page_size=1", {"xi-api-key": tts.read_key(tts.elevenlabs_key_file())})
                    box["message"] = "✔ ElevenLabs accepted the key"
                elif section == "cartesia":
                    self._key_get(f"{tts.CARTESIA_API_BASE}/voices?limit=1", {"X-API-Key": tts.read_key(tts.CARTESIA_KEY_FILE),
                                                                           "Cartesia-Version": tts.CARTESIA_API_VERSION})
                    box["message"] = "✔ Cartesia accepted the key"
                else:
                    text = keystore.get(section, "content")          # tts_json: only read, nothing to ask
                    if not text:
                        raise RuntimeError("no JSON saved here — drop the file first")
                    pid, mail = keystore.json_info(text)
                    box["message"] = f"✔ a service-account file for {mail}" + (f" · project {pid}" if pid else "")
            except Exception as exc:
                box["error"] = str(exc)
        th = threading.Thread(target=run, daemon=True)
        th.start()
        th.join(60)
        if th.is_alive():
            return {"error": "no answer within 60 seconds"}
        return {"error": box["error"]} if "error" in box else {"message": box.get("message", "✔")}

    @staticmethod
    def _key_get(url, headers):
        req = urllib.request.Request(url, headers=dict(headers, **{"User-Agent": "Proofing-With-AI/1.0", "Accept": "application/json"}))
        try:
            with urllib.request.urlopen(req, timeout=30, context=gemini_client._SSL_CTX) as resp:
                return resp.read()
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:200].replace("\n", " ")
            raise RuntimeError(f"HTTP {exc.code}: {detail}") from None
        except urllib.error.URLError as exc:
            raise RuntimeError(f"could not reach it: {exc.reason}") from None

    # ── text to speech ───────────────────────────────────────────────────
    def _tts_for(self, profile):
        """The settings a request means: "sugg" for the Suggestions TTS
        Settings panel, anything else for the main one."""
        return self.tts_sugg if profile == "sugg" else self.tts

    def tts_config(self, profile=None):
        have = tts.available_platforms()
        cfg = self._tts_for(profile)
        lang = cfg["language"]
        return {
            "platforms": [{"value": p, "available": p in have}
                          for p in tts.PLATFORMS],
            "languages": tts.LANGUAGE_NAMES,
            "engines": tts.ENGINES,
            "voices": tts.voices_for(lang, cfg["engine"]),
            "speeds": tts.SPEEDS,
            "el_models": [{"value": m, "label": label}
                          for m, label in tts.ELEVENLABS_MODELS],
            "current": dict(cfg),
            "lang_code": tts.language_code(lang),
        }

    def act_set_tts(self, patch):
        profile = patch.get("profile")
        with self._lock:
            cfg = self._tts_for(profile)
            for k in ("platform", "language", "engine", "voice",
                      "el_voice", "el_model", "ct_voice", "speed"):
                if k in patch:
                    cfg[k] = str(patch[k] or "")
            # Changing language or engine invalidates a Google voice that
            # belonged to the old list, so fall back to the first of the new
            # one rather than leaving a name the API will reject.
            allowed = tts.voices_for(cfg["language"], cfg["engine"])
            if allowed and cfg["voice"] not in allowed:
                cfg["voice"] = allowed[0]
        return self.tts_config(profile)

    def act_tts_voices(self, platform):
        """The ElevenLabs and Cartesia voice lists come from their APIs."""
        try:
            if platform == "ElevenLabs":
                # `default` is the voice the panel preselects — the one named
                # tts.ELEVENLABS_DEFAULT_VOICE_NAME, when the account has it.
                voices = tts.list_elevenlabs_voices()
                return {"voices": voices, "default": tts.find_voice(voices)}
            if platform == "Cartesia":
                return {"voices": tts.list_cartesia_voices()}
        except Exception as exc:
            return {"error": f"{type(exc).__name__}: {exc}"}
        return {"voices": []}

    # ── the batch's saved progress ───────────────────────────────────────
    # A file, not the browser's storage: the server takes a new random port
    # every launch, and browser storage belongs to one origin — port
    # included — so a batch kept there would be gone on the next start.
    #
    # Load pages opens a Windows file dialog HERE, in Python, because only
    # this side can know where a file lives — a browser is handed a file's
    # contents and never its path. Knowing the path is what lets progress be
    # saved beside the file it came from ("Chapter 1_1-50 pages.json" gets
    # "Chapter 1_1-50 pages.progress.json"), the same as the main app does,
    # so a folder of chapter files keeps each chapter's work next to it.
    # BATCH_FILE in this folder is where progress went before Load pages —
    # still reopened on start, so a batch in progress then is not lost.
    def _batch_target(self):
        return self.batch_path or os.path.join(HERE, BATCH_FILE)

    def _remember_batch(self, path):
        try:
            with open(os.path.join(HERE, BATCH_LAST_FILE), "w",
                      encoding="utf-8") as fh:
                fh.write(path)
        except Exception:
            pass                # only a convenience; the work itself is saved

    @staticmethod
    def _is_progress(data):
        """A progress file, rather than a list of pages: an object holding
        pages that each carry a status."""
        pages = data.get("pages") if isinstance(data, dict) else None
        return (isinstance(pages, list) and bool(pages)
                and all(isinstance(p, dict) and "status" in p and "telugu" in p
                        for p in pages))

    def _ask_open_path(self, title="Load pages — a batch JSON, or its progress file",
                       initialdir=None):
        """A file dialog, on top of the browser; one at a time.

        On a Mac it is the system's own Choose File dialog, through
        osascript: Tk cannot be used here, because macOS lets only a
        program's main thread open a window, and this runs in a request's
        thread — Tk there kills the whole app (abort, "Python quit
        unexpectedly"). On Windows, its own hidden Tk root, made and
        destroyed in this request's thread, so nothing Tk outlives the
        call."""
        start = initialdir or (os.path.dirname(self.batch_path)
                               if self.batch_path else None)
        if sys.platform == "darwin":
            return self._ask_open_path_mac(title, start)
        import tkinter as tk
        from tkinter import filedialog
        with self._dialog_lock:
            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True)
            try:
                return filedialog.askopenfilename(
                    parent=root,
                    title=title,
                    initialdir=initialdir or (os.path.dirname(self.batch_path)
                                              if self.batch_path else None),
                    filetypes=[("JSON", "*.json"), ("All files", "*.*")]) or ""
            finally:
                root.destroy()

    def _ask_open_path_mac(self, title, initialdir=None):
        """The macOS Choose File dialog; "" when cancelled."""
        def q(text):                      # an AppleScript string literal
            return '"' + str(text).replace("\\", "\\\\").replace('"', '\\"') + '"'
        script = "POSIX path of (choose file with prompt " + q(title)
        if initialdir and os.path.isdir(initialdir):
            script += " default location (POSIX file " + q(initialdir) + ")"
        script += ")"
        # "activate" brings the dialog in front of the browser.
        script = "activate\nreturn " + script
        with self._dialog_lock:
            r = subprocess.run(["osascript", "-e", script],
                               capture_output=True, text=True)
        if r.returncode != 0:            # cancelled (-128), or no dialog
            if "-128" in (r.stderr or ""):
                return ""
            raise RuntimeError("the file dialog did not open: "
                               + (r.stderr or "").strip())
        return r.stdout.strip()

    def act_batch_pick(self):
        """Load pages: choose a file, and report what it is.

        A progress file comes back as the batch to carry on with. A batch
        JSON comes back as its text — the page parses it — with the
        progress already saved beside it, if any, so
        the page can offer to carry on from that instead."""
        path = self._ask_open_path()
        if not path:
            return {"cancelled": True}
        path = os.path.normpath(path)
        name = os.path.basename(path)
        try:
            with open(path, "r", encoding="utf-8") as fh:
                raw = fh.read()
            data = json.loads(raw.lstrip("﻿"))
        except Exception as exc:
            return {"error": f"Could not read {name} — {exc}"}

        if self._is_progress(data):
            # A progress file under the main app's old name carries on under
            # the new one.
            prog = (path[:-len(LEGACY_SUFFIX)] + PROGRESS_SUFFIX
                    if path.lower().endswith(LEGACY_SUFFIX) else path)
            self._picked.add(prog)
            return {"kind": "progress", "name": name, "batch": data,
                    "progress_path": prog,
                    "marks": self._restore_end_marks(data)}

        base = os.path.splitext(path)[0]
        prog = base + PROGRESS_SUFFIX
        prev_path = next((p for p in (prog, base + LEGACY_SUFFIX)
                          if os.path.exists(p)), None)
        prev = None
        if prev_path:
            # A file already under the progress name is never written over —
            # not even one that cannot be read as progress.
            try:
                with open(prev_path, "r", encoding="utf-8") as fh:
                    prev = json.load(fh)
            except Exception:
                prev = None
            if not self._is_progress(prev):
                pname = os.path.basename(prev_path)
                return {"error": f"{pname} is beside {name} but cannot be read "
                                 f"as its progress, so nothing was loaded — it "
                                 f"is never written over. Move it to another "
                                 f"folder or rename it, then Load pages again."}
        self._picked.add(prog)
        return {"kind": "pages", "name": name, "text": raw,
                "progress_path": prog, "saved": prev,
                "marks": self._restore_end_marks(prev) if prev else {},
                "saved_name": os.path.basename(prev_path) if prev else ""}

    def act_batch_use(self, path):
        """From now on, save to `path`: a progress path Load pages handed
        out — or the one act_batch_load reopened. Any other path is
        refused, so the page cannot be made to write wherever it likes."""
        if not path or path not in self._picked:
            return {"error": "that file was not chosen with Load pages"}
        with self._lock:
            self.batch_path = path or None
            target = self._batch_target()
        self._remember_batch(target)
        return {"ok": True, "path": target, "name": os.path.basename(target)}

    def act_batch_save(self, batch):
        with self._lock:
            path = self._batch_target()
            tmp = path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(batch, fh, ensure_ascii=False)
            os.replace(tmp, path)       # never a half-written save
        return {"ok": True}

    @staticmethod
    def _restore_end_marks(batch):
        """{page: marks put back} — core.restore_end_marks on every page of a
        saved batch as it is opened, for the punctuation Version 1 dropped
        before keep_end_mark existed. The page says so and saves the result."""
        put = {}
        for p in (batch or {}).get("pages") or []:
            if isinstance(p, dict):
                n = core.restore_end_marks(p)
                if n:
                    put[str(p.get("page", ""))] = n
        return put

    def act_batch_load(self):
        """The batch that was open last — wherever its progress file is —
        or, before anything was ever loaded that way, BATCH_FILE here."""
        path = ""
        try:
            with open(os.path.join(HERE, BATCH_LAST_FILE), "r",
                      encoding="utf-8") as fh:
                path = fh.read().strip()
        except Exception:
            pass
        if not (path and os.path.exists(path)):
            path = os.path.join(HERE, BATCH_FILE)
        if not os.path.exists(path):
            return {"batch": None}
        try:
            with open(path, "r", encoding="utf-8") as fh:
                batch = json.load(fh)
        except Exception as exc:
            return {"batch": None,
                    "error": f"{os.path.basename(path)}: {exc}"}
        with self._lock:
            self.batch_path = (None if path == os.path.join(HERE, BATCH_FILE)
                               else path)
        self._picked.add(path)
        return {"batch": batch, "path": path, "name": os.path.basename(path),
                "marks": self._restore_end_marks(batch)}

    def act_tts_start(self, text, language=""):
        """`language` overrides the panel's for this one read — the batch's
        Play reads the English sentence before the Telugu, with the rest of
        the panel (platform, engine, speed) left as it is."""
        text = (text or "").strip()
        if not text:
            return {"error": "There is nothing to read."}
        with self._lock:
            settings = dict(self.tts)
            if language and language in tts.LANGUAGE_NAMES \
                    and language != settings["language"]:
                settings["language"] = language
                settings["voice"] = tts.voice_like(
                    settings["voice"], language, settings["engine"])
            settings["lang_code"] = tts.language_code(settings["language"])
            self._job_seq += 1
            jid = self._job_seq
            for old in self.jobs.values():       # only one player at a time
                old.cancelled = True
            job = tts.Job(jid, settings["platform"], text, settings)
            self.jobs = {jid: job}
        job.start()
        st = job.status()
        st["speed"] = settings["speed"]
        return st

    def act_tts_sentence(self, text, fresh=False, profile=None):
        """(mp3 bytes, error) for ONE sentence — what the batch's read-aloud
        plays, a sentence at a time.

        Kept, keyed by the voice settings and the text, so Repeat and
        Previous cost nothing, and a sentence that did not change is never
        made twice. Two requests for the same sentence at once (the page
        reading ahead while the user jumps) share one synthesis.

        `fresh` (the read-aloud's Regenerate) throws the kept clip away
        first, so the sentence is made again. `profile` "sugg" reads with
        the Suggestions TTS Settings panel's voice instead."""
        text = (text or "").strip()
        if not text:
            return None, "There is nothing to read."
        with self._lock:
            settings = dict(self._tts_for(profile))
        settings["lang_code"] = tts.language_code(settings["language"])
        key = (settings["platform"], settings["voice"], settings["el_voice"],
               settings["el_model"], settings["ct_voice"],
               settings["lang_code"], text)
        with self._clip_lock:
            if fresh:
                self._clips.pop(key, None)
            hit = self._clips.get(key)
            if hit is not None:
                self._clips.move_to_end(key)
                return hit, None
            ev = self._clip_busy.get(key)
            mine = ev is None
            if mine:
                ev = self._clip_busy[key] = threading.Event()
        if not mine:
            ev.wait(180)
            with self._clip_lock:
                hit = self._clips.get(key)
            return (hit, None) if hit is not None else (
                None, "the sentence could not be made")
        try:
            # A sentence is short, but one past a platform's limit is still
            # split; MP3 frames simply follow one another.
            data = b"".join(tts.synth(settings["platform"], c, settings)
                            for c in tts.chunks_for(settings["platform"], text))
            with self._clip_lock:
                self._clips[key] = data
                while len(self._clips) > CLIP_CACHE_MAX:
                    self._clips.popitem(last=False)
            return data, None
        except Exception as exc:
            return None, f"{type(exc).__name__}: {exc}"
        finally:
            with self._clip_lock:
                self._clip_busy.pop(key, None)
            ev.set()

    def act_tts_status(self, jid):
        job = self.jobs.get(int(jid))
        return job.status() if job else {"error": "no such job"}

    def act_tts_stop(self):
        with self._lock:
            for job in self.jobs.values():
                job.cancelled = True
            self.jobs = {}
        return {"ok": True}

    def act_sync(self, telugu, spans):
        """The page edits the script in place, so it reports the new text and
        where each highlight ended up.

        The DOM is authoritative for span positions after an edit: the
        highlight elements move with the text as it is typed, so their
        offsets are read back rather than guessed. A highlight the user
        deleted outright simply does not come back, and its finding goes."""
        with self._lock:
            self.session.telugu = telugu or ""
            # The script as first pasted, if nothing has claimed that yet:
            # this runs on the paste's own sync, before any edit can have
            # happened to it.
            if not self.session.baseline and self.session.telugu.strip():
                self.session.baseline = self.session.telugu
            total = len(self.session.telugu)
            reported = {}
            for sp in (spans or []):
                try:
                    reported[int(sp["id"])] = sp
                except (KeyError, TypeError, ValueError):
                    continue
            kept = []
            for f in self.session.findings:
                sp = reported.get(f["id"])
                if sp is None:
                    continue
                start = max(0, min(int(sp.get("start", 0)), total))
                end = max(start, min(int(sp.get("end", start)), total))
                f["start"], f["end"] = start, end
                f["current"] = self.session.telugu[start:end]
                kept.append(f)
            self.session.findings = kept
            return self.session.as_json()

    def act_set_scripts(self, english, telugu):
        """The page owns the text and pushes its copy before any run.

        If the Telugu changed, every finding is dropped: they were located
        against the old string, and a stale offset would splice a version
        into the wrong place."""
        with self._lock:
            if telugu != self.session.telugu:
                self.session.reset_findings()
                self.session.baseline = telugu or ""
            self.session.english = english or ""
            self.session.telugu = telugu or ""
            if not self.session.baseline:
                self.session.baseline = self.session.telugu
            return self.session.as_json()

    def act_detect(self):
        with self._lock:
            telugu = self.session.telugu
        if not telugu.strip():
            return {"error": f"The {self.language} script is empty."}
        raw = self._run(telugu, DETECT_PROMPT, core.JSON_CONTRACT)
        found, note = core.parse_findings(raw)
        if note:
            return {"error": note, "raw": (raw or "")[:4000]}

        with self._lock:
            self.session.reset_findings("ai")
            used = [(f["start"], f["end"]) for f in self.session.findings]
            missed = []
            for item in found:
                span = core.locate(self.session.telugu, item["text"], used)
                if span is None:
                    missed.append(item)
                    continue
                used.append(span)
                self.session.new_finding(span[0], span[1], item["issue"], "ai")
            state = self.session.as_json()
        state["missed"] = [{"text": m["text"], "issue": m["issue"]}
                           for m in missed]
        return state

    def act_translate(self):
        """Translate the English box into the Telugu box.

        One Gemini call with Custom_Text_Translation_Prompt.txt. The reply is
        the script itself, not JSON, so it goes in as-is once any code fence
        the model wrapped it in has been peeled off.

        Every finding is dropped: a finding is a character range into the old
        Telugu, and there is no old Telugu any more. Keeping them would leave
        highlights sitting over unrelated words.
        """
        with self._lock:
            english = self.session.english
        if not english.strip():
            return {"error": "The English box is empty — paste the "
                             "transcript first."}

        raw = gemini_client.run_prompt(
            english, load_prompt(TRANSLATE_PROMPT, self.language),
            self.mode, self.model)
        text = core._strip_fence(raw or "").strip()
        if not text:
            return {"error": "the model returned an empty translation"}

        with self._lock:
            self.session.telugu = text
            self.session.baseline = text     # a new script, so a new start
            self.session.reset_findings()
            state = self.session.as_json()
        return state

    def act_oneshot(self):
        """Detect AND write the three versions in a single Gemini call.

        The two-step path sends a numbered list in its second call and matches
        the reply back by that number, so a dropped, reordered or renumbered
        item silently attaches its versions to the wrong sentence — nothing
        checks that the returned original is the sentence that was asked
        about. Here every object carries the sentence it belongs to and is
        located in the script directly, so there is no number to slip.

        Version 1 is applied to everything, as Do AI Proofing does; every
        version stays on the finding, so any of them (including the original)
        can be clicked afterwards."""
        with self._lock:
            english, telugu = self.session.english, self.session.telugu
        if not telugu.strip():
            return {"error": f"The {self.language} script is empty."}

        items, note, raw = self._oneshot_items(english, telugu)
        if not items:
            return {"error": note or "the model found nothing to improve",
                    "raw": (raw or "")[:4000]}

        with self._lock:
            self.session.reset_findings("ai")
            missed, applied = self._place_oneshot(self.session, items)
            state = self.session.as_json()
        state["missed"] = [{"text": m["text"], "issue": m["issue"]}
                           for m in missed]
        state["applied"] = applied
        state["note"] = note
        return state

    def _oneshot_items(self, english, telugu, prompt_name=ONESHOT_PROMPT):
        """(items, note, raw) — the one-step call itself, shared by the
        single-script button and the batch (which passes its own prompt)."""
        payload = (f"=== English transcript ===\n{english}"
                   f"\n\n=== {self.language} dubbing script ===\n{telugu}")
        raw = self._run(payload, prompt_name, core.ONESHOT_CONTRACT)
        items, note = core.parse_oneshot(raw)
        return items, note, raw

    @staticmethod
    def _place_oneshot(session, items):
        """Locate every item in `session`, hang its versions on it, then put
        Version 1 in place. Returns (missed, applied)."""
        used = [(f["start"], f["end"]) for f in session.findings]
        missed = []
        for it in items:
            span = core.locate(session.telugu, it["text"], used)
            if span is None:
                missed.append(it)
                continue
            used.append(span)
            f = session.new_finding(span[0], span[1], it["issue"], "ai")
            f["english"] = it["english"]
            f["options"] = core.keep_end_mark(session.telugu[span[0]:span[1]],
                                              it["suggestions"][:3])
        # Applied after every span is placed: apply_version shifts the
        # spans that follow it, and locating against a script that was
        # already being rewritten would put later findings in the wrong
        # place.
        applied = 0
        for f in list(session.spans()):
            if f["options"]:
                session.apply_version(f["id"], f["options"][0])
                applied += 1
        return missed, applied

    def act_batch_oneshot(self, english, telugu):
        """One page of the batch: the same one-step proofing, run on a
        throwaway Session so the review in the boxes above is never touched.

        The page keeps the batch itself (saving it through act_batch_save),
        so everything it needs comes back here — the script with Version 1
        applied and every finding with its span into THAT script.

        An empty reply with no note is a clean page, not a failure: the model
        was asked and found nothing to improve."""
        english, telugu = english or "", telugu or ""
        if not telugu.strip():
            return {"error": f"this page has no {self.language}"}
        items, note, raw = self._oneshot_items(english, telugu,
                                               BATCH_ONESHOT_PROMPT)
        if not items and note:
            return {"error": note, "raw": (raw or "")[:4000]}

        sess = core.Session()
        sess.english, sess.telugu = english, telugu
        missed, applied = self._place_oneshot(sess, items)
        state = sess.as_json()
        state["missed"] = [{"text": m["text"], "issue": m["issue"]}
                           for m in missed]
        state["applied"] = applied
        state["note"] = note
        return state

    def act_suggestions(self, scope="all"):
        with self._lock:
            targets = [f for f in self.session.spans()
                       if scope == "all" or f["kind"] == scope]
            english, telugu = self.session.english, self.session.telugu
        if not targets:
            return {"error": "Nothing is flagged yet."}
        # Loud rather than silent: with no transcript the model has nothing
        # to quote and writes its own English, which is worse than an error
        # because it looks like an answer.
        if not english.strip():
            return {"error": "The English script has not reached the server "
                             "\u2014 put it in the English box and try again."}

        en_sents = core.split_sentences(english)
        listed, send_map = [], {}
        for i, f in enumerate(targets, 1):
            send_map[i] = f["id"]
            issue = f["issue"] or "(no description given — judge from context)"
            listed.append(f"{i}. {f['current']}\n   issue: {issue}")
        payload = (
            f"=== English transcript (meaning reference; quote it by "
            f"number) ===\n{core.number_sentences(en_sents)}"
            f"\n\n=== {self.language} dubbing script ===\n{telugu}"
            f"\n\n=== Identified sentences to improve ===\n"
            + "\n\n".join(listed))

        raw = self._run(payload, SUGGEST_PROMPT, core.SUGG_CONTRACT)
        items, note = core.parse_suggestions(raw)
        if note:
            return {"error": note, "raw": (raw or "")[:4000]}

        by_n = {it["n"]: it for it in items if it["n"] is not None}
        with self._lock:
            filled = 0
            for n, fid in send_map.items():
                f = self.session.get(fid)
                item = by_n.get(n)
                if f is None or item is None:
                    continue
                f["options"] = core.keep_end_mark(f["current"],
                                                  item["suggestions"][:3])
                f["english"] = core.english_from(en_sents, item)
                f["gesture_en"] = item.get("gesture_en", "")
                filled += 1
            state = self.session.as_json()
        state["filled"] = filled
        return state

    def act_batch_suggestions(self, english, telugu, items):
        """Versions for the sentences a reviewer marked by hand on one batch
        page — what Get suggestions does above, with the book's own prompt
        (BATCH_SUGG_PROMPT) and no session: the page sends its English, its
        Telugu as it stands, and the marked items, [{"text", "issue"}].

        Returns {"results": [...]}, one per item in the order sent, each
        {"suggestions": [...], "english": "..."} — or {} where the model
        gave nothing back for that one."""
        english, telugu = english or "", telugu or ""
        items = [it for it in (items or []) if (it.get("text") or "").strip()]
        if not items:
            return {"error": "Nothing is marked on this page."}
        # Loud rather than silent, as above: with no English the model has
        # nothing to quote and writes its own, which looks like an answer.
        if not english.strip():
            return {"error": "This page has no English to work from."}
        en_sents = core.split_sentences(english)
        listed = []
        for i, it in enumerate(items, 1):
            issue = (it.get("issue") or "").strip() or \
                "(no description given — judge from context)"
            listed.append(f"{i}. {it['text'].strip()}\n   issue: {issue}")
        payload = (
            f"=== English transcript (meaning reference; quote it by "
            f"number) ===\n{core.number_sentences(en_sents)}"
            f"\n\n=== {self.language} dubbing script ===\n{telugu}"
            f"\n\n=== Identified sentences to improve ===\n"
            + "\n\n".join(listed))
        raw = self._run(payload, BATCH_SUGG_PROMPT, core.SUGG_CONTRACT)
        got, note = core.parse_suggestions(raw)
        if note:
            return {"error": note, "raw": (raw or "")[:4000]}
        by_n = {g["n"]: g for g in got if g["n"] is not None}
        results = []
        for i in range(1, len(items) + 1):
            g = by_n.get(i)
            results.append({} if g is None else {
                "suggestions": core.keep_end_mark(items[i - 1]["text"],
                                                  g["suggestions"][:3]),
                "english": core.english_from(en_sents, g)})
        return {"results": results}

    # ── Corrections to sync with new version ────────────────────────────
    # The book's English was revised after the Telugu was translated and
    # proofed. The chapter's helper file (sync_helper.py) knows every
    # sentence the editors touched; each one on the page goes to the model
    # with an id, and every id must come back with the Telugu for the final
    # English. Version 1 is applied; the reviewer ticks each one to check it.
    SYNC_NEW = "[NEW SENTENCE]"

    def _sync_prompt(self):
        """The sync prompt, with THIS BOOK'S TERMS taken from the batch
        proofing prompt — so the terms list stays in one file here."""
        body = load_prompt(SYNC_PROMPT, self.language)
        terms = ""
        try:
            src = load_prompt(BATCH_ONESHOT_PROMPT, self.language)
            m = re.search(r"THIS BOOK'S TERMS.*?(?=\n\s*Detection:)", src, re.S)
            terms = m.group(0).strip() if m else ""
        except FileNotFoundError:
            pass
        return body.replace("{{BOOK_TERMS}}", terms)

    def _helper(self, path):
        """The helper file at `path`, read once and kept until it changes."""
        path = os.path.normpath(path or "")
        if not path or not os.path.isfile(path):
            raise FileNotFoundError(f"the helper file is not there any more: {path}")
        st = os.stat(path)
        stamp = (st.st_mtime, st.st_size)
        got = self._helpers.get(path)
        if got is None or got[0] != stamp:
            got = (stamp, sync_helper.load(path))
            self._helpers[path] = got
        return got[1]

    def act_batch_helper_info(self, path):
        """What the Book tab shows about a helper file."""
        try:
            h = self._helper(path)
        except Exception as exc:
            return {"error": f"Could not open the helper file — {exc}"}
        d = h.data
        return {"path": os.path.normpath(path), "name": os.path.basename(path),
                "chapter": d.get("chapter"), "title": d.get("title", ""),
                "counts": d.get("counts", {}), "source": d.get("source", "")}

    def act_batch_helper_pick(self):
        path = self._ask_open_path(
            "Open helper file — the chapter's sync helper (.json)")
        if not path:
            return {"cancelled": True}
        return self.act_batch_helper_info(path)

    @staticmethod
    def _sync_label(c):
        mv = c.get("moved") or {}
        if c["kind"] == "del":
            t = "This sentence is removed in English"
            if "to" in mv:
                t += " (moved elsewhere in the chapter)"
            return f"{c['id']} · {t}: “{c['old']}”"
        if c["kind"] == "add":
            t = "New sentence in English"
            if "from" in mv:
                t += " (moved here from elsewhere in the chapter)"
            return f"{c['id']} · {t}"
        return f"{c['id']} · Changed in English — earlier draft: “{c['old']}”"

    def _sync_payload(self, english, telugu, pc, te_paras, paired):
        tagged = [q.get("tagged", english[q["en"][0]:q["en"][1]])
                  for q in pc["paras"]]
        if paired:
            body = "\n\n".join(
                f"¶{k}\nEN: {en}\nTE: {telugu[s:e]}"
                for k, (en, (s, e)) in enumerate(zip(tagged, te_paras), 1))
            head = "=== The page, as paragraph pairs ==="
        else:
            body = ("EN (final English):\n" + "\n\n".join(tagged)
                    + f"\n\nTE (approved {self.language}):\n" + telugu)
            head = (f"=== The page (its English and {self.language} paragraphs do not "
                    f"pair one to one — find the {self.language} by meaning) ===")
        kinds = {"chg": "changed", "add": "added", "del": "deleted"}
        ids = ", ".join(f"{c['id']} (¶{c['para']}, {kinds[c['kind']]})"
                        if paired else f"{c['id']} ({kinds[c['kind']]})"
                        for c in pc["changes"])
        return f"{head}\n\n{body}\n\n=== Ids to answer ===\n{ids}"

    def _sync_ask(self, payload, ids):
        # Low effort: a page has a dozen or more ids, and the model's long
        # think on them ran past the gateway's 100 s limit (HTTP 524).
        # The gateway now and then gives up on a call it would answer in
        # seconds the next time (HTTP 524) — so one more try before the page
        # is marked Failed.
        for attempt in (1, 2):
            try:
                raw = gemini_client.run_prompt(
                    payload, self._sync_prompt() + core.SYNC_CONTRACT,
                    self.mode, self.model, effort="low")
                break
            except Exception as exc:
                if attempt == 2 or not re.search(r"\b(524|502|503|504)\b|timed? ?out",
                                                 str(exc), re.I):
                    raise
        items, note = core.parse_sync(raw)
        want = set(ids)
        for it in items:
            it["ids"] = [i for i in it["ids"] if i in want]
        return [it for it in items if it["ids"]], note, raw

    def act_batch_sync(self, english, telugu, helper="", before=None):
        """One page: every sentence of it that the editors touched, answered
        by the model with the Telugu for the final English. Version 1 is
        applied straight away; each correction stays "not checked" until the
        reviewer ticks a row, and ORIGINAL puts the approved Telugu back.

        A deleted sentence's version is "" (so it comes out); an added one is
        placed as [NEW SENTENCE] and at once replaced by its translation, so
        ORIGINAL ("") takes it out again.

        `before`: the English of the batch's pages before this one, so the
        page is looked for after them in the chapter."""
        english, telugu = english or "", telugu or ""
        if not helper:
            return {"error": "Open the chapter's helper file first "
                             "(\U0001F4CE Open helper file)."}
        if not telugu.strip():
            return {"error": f"this page has no {self.language}"}
        if not english.strip():
            return {"error": "this page has no English"}
        try:
            h = self._helper(helper)
        except Exception as exc:
            return {"error": f"Could not open the helper file — {exc}"}

        cursor = None
        for e in before or []:
            cursor = sync_helper.page_changes(h, e or "", cursor)["cursor"]
        pc = sync_helper.page_changes(h, english, cursor)
        changes = pc["changes"]
        te_paras = sync_helper._paras(telugu)
        paired = len(te_paras) == len(pc["paras"])
        report = {"changes": len(changes), "answered": 0, "placed": 0,
                  "not_in_telugu": [], "unplaced": [],
                  "unfound_en": [u[:300] for u in pc["unfound"]],
                  "paired": paired}
        if not changes:
            return {"telugu": telugu, "findings": [], "missed": [],
                    "sync": report, "note": ""}

        ids = [c["id"] for c in changes]
        payload = self._sync_payload(english, telugu, pc, te_paras, paired)
        answers, note, raw = self._sync_ask(payload, ids)
        if not answers and note:
            return {"error": note, "raw": (raw or "")[:4000]}
        got = {i for a in answers for i in a["ids"]}
        missing = [i for i in ids if i not in got]
        if missing:
            # One more ask, for exactly the ids that did not come back.
            more, note2, _ = self._sync_ask(
                payload + "\n\nThese ids are still unanswered. Answer ONLY "
                          "these: " + ", ".join(missing), missing)
            answers += more
            note = note or note2

        by_id = {c["id"]: c for c in changes}
        seen, placed, unplaced, gone = set(), [], [], []

        def para_range(n):
            return te_paras[n - 1] if paired and 1 <= n <= len(te_paras) else None

        QM = "\"“”‘’'"

        def whole(sp, text):
            """`sp` widened over the quote marks (and closing marks) the
            model's quote had at either end: locate() leaves them out, and
            a version that has them would then double them."""
            s0, e0 = sp
            t = text.strip()
            lead = len(t) - len(t.lstrip(QM))
            while lead and s0 > 0 and telugu[s0 - 1] in QM:
                s0 -= 1
                lead -= 1
            for ch in t[len(t.rstrip(QM + ".,;!?…")):]:
                if e0 < len(telugu) and telugu[e0] == ch:
                    e0 += 1
            return s0, e0

        def find(text, n, free=False):
            sp = find_(text, n, free)
            return whole(sp, text) if sp else None

        def find_(text, n, free=False):
            # `free`: a place to put a new sentence after may sit inside
            # another correction's sentence; it is not a span of its own.
            used = [] if free else \
                [(x["start"], x["end"]) for x in placed if not x["ins"]]
            # Its own paragraph first, then the one above (a paragraph that
            # "continues above"), then anywhere on the page.
            for k in (n, n - 1):
                rng = para_range(k)
                if rng:
                    sp = core.locate(telugu[rng[0]:rng[1]], text,
                                     [(a - rng[0], b - rng[0]) for a, b in used])
                    if sp:
                        return sp[0] + rng[0], sp[1] + rng[0]
            return core.locate(telugu, text, used)

        # Answers that quote no Telugu last: they may belong to a correction
        # another answer places (new footnotes sharing one placeholder).
        answers.sort(key=lambda a: 0 if (a["telugu"] or a["after"] or a["status"] in
                                         ("add", "not_in_telugu", "elsewhere")) else 1)
        for a in answers:
            aid = [i for i in a["ids"] if i in by_id and i not in seen]
            if not aid:
                continue
            seen.update(aid)
            cs = [by_id[i] for i in aid]
            issue = "\n".join(self._sync_label(c) for c in cs)
            if a["note"]:
                issue += "\n→ " + a["note"]
            eng = " ".join(c["new"] for c in cs if c["new"]) or \
                "(removed in the final English) " + " ".join(c["old"] for c in cs)
            row = {"ids": aid, "english": eng, "issue": issue,
                   "suggestion": a["suggestion"], "telugu": a["telugu"]}
            st = a["status"]
            if st == "not_in_telugu" and all(c["kind"] == "del" for c in cs):
                gone.append(row)
                continue
            if st == "elsewhere":
                unplaced.append(dict(row, why=f"the model says its {self.language} is not on this page"))
                continue
            adding = st == "add" or (not a["telugu"] and a["suggestion"]
                                     and any(c["kind"] == "add" for c in cs))
            if adding:
                if not a["suggestion"]:
                    unplaced.append(dict(row, why="no translation came back"))
                    continue
                if a["after"]:
                    sp = find(a["after"], a["para"], free=True)
                    if not sp:
                        unplaced.append(dict(row, why=f"could not find the {self.language} it goes after: “" + a["after"] + "”"))
                        continue
                    pos, first = sp[1], False
                    # Past a closing quote or bracket: never inside a quotation.
                    while pos < len(telugu) and telugu[pos] in "\"”’»)]":
                        pos += 1
                else:
                    rng = para_range(a["para"])
                    if not rng:
                        unplaced.append(dict(row, why="no place given for it"))
                        continue
                    pos, first = rng[0], True
                placed.append({"ins": True, "start": pos, "end": pos,
                               "first": first, "row": row, "kinds": cs})
                continue
            if not a["telugu"]:
                # New footnotes that share one placeholder paragraph, answered
                # in the correction that took the placeholder: one correction.
                rng = para_range(a["para"])
                host = rng and next((x for x in placed if not x["ins"]
                                     and rng[0] <= x["start"] < rng[1]
                                     and telugu[x["start"]:x["end"]].lstrip().startswith("[[")),
                                    None)
                if host:
                    host["row"]["ids"] += aid
                    host["row"]["issue"] += "\n" + issue
                    continue
                unplaced.append(dict(row, why=f"no {self.language} was quoted for it"))
                continue
            sp = find(a["telugu"], a["para"])
            if not sp:
                # The same Telugu as an answer already placed: one correction.
                key = " ".join(a["telugu"].split())
                twin = next((x for x in placed if not x["ins"] and
                             " ".join(telugu[x["start"]:x["end"]].split())
                             .strip(".,;!?") == key.strip(".,;!?")), None)
                if twin:
                    twin["row"]["ids"] += aid
                    twin["row"]["issue"] += "\n" + issue
                    continue
                unplaced.append(dict(row, why=f"could not find the {self.language} it quoted"))
                continue
            deleting = st == "delete" or (not a["suggestion"] and
                                          all(c["kind"] == "del" for c in cs))
            if deleting and all(c.get("dup") for c in cs):
                # A line the earlier draft had twice: if the Telugu has it
                # only once, that once is the line that stays.
                q = " ".join(telugu[sp[0]:sp[1]].split()).strip(".,;!?")
                if " ".join(telugu.split()).count(q) < 2:
                    gone.append(dict(row, issue=row["issue"] + f"\n→ The {self.language} has "
                                     "this line once — it belongs to the line that stays."))
                    continue
            s0, e0 = sp
            if deleting:
                while e0 < len(telugu) and telugu[e0] in " \t":
                    e0 += 1
                sugg = ""
            else:
                sugg = a["suggestion"] or telugu[s0:e0]
                sugg = core.keep_end_mark(telugu[s0:e0], [sugg])[0]
            placed.append({"ins": False, "start": s0, "end": e0, "row": row,
                           "sugg": sugg, "del": deleting,
                           "same": not deleting and sugg.strip() == telugu[s0:e0].strip(),
                           "kinds": cs})

        for i in ids:
            if i not in seen:
                c = by_id[i]
                unplaced.append({"ids": [i], "english": c["new"] or c["old"],
                                 "issue": self._sync_label(c), "suggestion": "",
                                 "telugu": "", "why": "no answer came back for it"})

        # The text with every [NEW SENTENCE] in it, and every span moved along
        # by the placeholders put in before it.
        # A placeholder never goes inside another correction's sentence.
        for x in placed:
            if x["ins"]:
                for y in placed:
                    if not y["ins"] and y["start"] < x["start"] < y["end"]:
                        x["start"] = y["end"]
        ins = sorted((x for x in placed if x["ins"]), key=lambda x: x["start"])
        text, add_at = telugu, []
        shift = 0
        for x in ins:
            t = (self.SYNC_NEW + " ") if x["first"] else (" " + self.SYNC_NEW)
            p0 = x["start"] + shift
            text = text[:p0] + t + text[p0:]
            x["new_start"], x["new_end"] = p0, p0 + len(t)
            x["sugg"] = (x["row"]["suggestion"] + " ") if x["first"] else \
                (" " + x["row"]["suggestion"])
            add_at.append((x["start"], len(t)))
            shift += len(t)
        findings = []
        for x in placed:
            if x["ins"]:
                s0, e0, orig = x["new_start"], x["new_end"], ""
                cur = text[s0:e0]
                kind = "add"
            else:
                d = sum(n for p, n in add_at if p <= x["start"])
                s0, e0 = x["start"] + d, x["end"] + d
                orig = cur = text[s0:e0]
                kind = "del" if x["del"] else "chg"
            r = x["row"]
            findings.append({
                "start": s0, "end": e0, "orig": orig, "current": cur,
                "english": r["english"], "issue": r["issue"],
                "options": [x["sugg"]], "kind": "ai",
                # By what the editors did, not by where it was placed: a
                # moved-in sentence whose Telugu is already there is "Added".
                "category": ("Added" if any(c["kind"] == "add" for c in x["kinds"])
                             else "Removed" if any(c["kind"] == "del" for c in x["kinds"])
                             else "Changed"),
                "sync": {"ids": r["ids"], "kind": kind,
                         "same": bool(x.get("same")), "decided": False}})
        findings.sort(key=lambda f: f["start"])
        # Version 1 goes in straight away, every span moved along by the
        # ones before it. Still "not checked" until the reviewer ticks a row;
        # ORIGINAL puts the approved Telugu back (or takes an added one out).
        delta = 0
        for f in findings:
            s0, e0 = f["start"] + delta, f["end"] + delta
            v = f["options"][0]
            text = text[:s0] + v + text[e0:]
            f["start"], f["end"], f["current"] = s0, s0 + len(v), v
            delta += len(v) - (e0 - s0)
        report.update({"answered": len(seen), "placed": len(findings),
                       "not_in_telugu": gone, "unplaced": unplaced})
        return {"telugu": text, "findings": findings, "missed": unplaced,
                "sync": report, "note": note}

    def act_apply(self, fid, index, text=None):
        """index 0 is the untouched original; 1..3 are the model's versions.

        `text`, for a version edited in the Suggestions box, is stored AS
        that version first — so the box, the export and the next render all
        show the edit — and then applied. The original is never edited."""
        with self._lock:
            f = self.session.get(fid)
            if f is None:
                return {"error": "No such finding."}
            options = [f["orig"]] + list(f["options"])
            if not (0 <= index < len(options)):
                return {"error": "No such version."}
            text = " ".join((text or "").split("\n")).strip()
            if text and index >= 1:
                f["options"][index - 1] = text
                options[index] = text
            self.session.apply_version(fid, options[index])
            return self.session.as_json()

    def act_apply_text(self, fid, text):
        """Put an arbitrary string into a finding's span.

        What the "selected part" button sends: a fragment of a version rather
        than a whole one. Session.apply_version already takes the text, so
        act_apply's index lookup is the only thing being skipped.
        """
        text = (text or "").strip()
        if not text:
            return {"error": "Nothing was selected in that version."}
        with self._lock:
            if self.session.get(fid) is None:
                return {"error": "No such finding."}
            self.session.apply_version(fid, text)
            return self.session.as_json()

    def act_autoapply(self):
        with self._lock:
            applied = 0
            for f in list(self.session.spans()):
                if f["options"]:
                    self.session.apply_version(f["id"], f["options"][0])
                    applied += 1
            state = self.session.as_json()
        state["applied"] = applied
        return state

    def act_add_issue(self, start, end, issue, mark=None):
        """Mark a hand-picked span. Anything it overlaps is superseded —
        two findings over the same characters would fight when a version is
        applied. Only the older highlight goes; the text is untouched."""
        with self._lock:
            t = self.session.telugu
            start = max(0, min(int(start), len(t)))
            end = max(0, min(int(end), len(t)))
            while start < end and t[start].isspace():
                start += 1
            while end > start and t[end - 1].isspace():
                end -= 1
            if end <= start:
                return {"error": "Select some text first."}

            superseded = []
            for f in list(self.session.findings):
                if start < f["end"] and end > f["start"]:
                    superseded.append(f["id"])
                    self.session.findings.remove(f)
            # Clamped against the span it belongs to, so a stale or
            # malformed pair cannot reach the page.
            span = end - start
            if mark is not None:
                try:
                    m0 = max(0, min(int(mark[0]), span))
                    m1 = max(0, min(int(mark[1]), span))
                    mark = [m0, m1] if m1 > m0 else None
                except (TypeError, ValueError, IndexError):
                    mark = None
            f = self.session.new_finding(start, end, issue or "", "man",
                                         mark)
            state = self.session.as_json()
        state["selected"] = f["id"]
        state["superseded"] = superseded
        return state

    def act_clear(self, fid=None, kind=None):
        """Drop highlights. The script text is never changed by this."""
        with self._lock:
            if fid is not None:
                f = self.session.get(int(fid))
                if f is None:
                    return {"error": "No such finding."}
                self.session.findings.remove(f)
            else:
                self.session.reset_findings(kind)
            return self.session.as_json()

    def act_export(self):
        """The change log: one block per selection.

        Built here rather than in the page because the sentence widening
        and the word diff are the same code the Review tab in the main app
        runs — see EXPORT_SENT_ENDS in review_core.py. The page only puts
        what comes back on the clipboard."""
        with self._lock:
            telugu = self.session.telugu
            baseline = self.session.baseline
            findings = [dict(f) for f in self.session.spans()]
        text = core.export_changes_text(telugu, findings, baseline=baseline,
                                        language=self.language)
        # Selections are no longer the only thing worth copying: a script
        # the reviewer only retyped has a change log of its own.
        if not findings and (not baseline.strip()
                             or baseline.strip() == (telugu or "").strip()):
            return {"error": "Nothing has changed yet."}
        return {"text": text, "count": len(findings)}

    def act_load_proofed(self, text):
        """Load a proofed script file: both boxes and every flagged
        sentence, in one drop.

        The file is the Proofing stage's own deliverable, so everything the
        tab needs is in it — the original of each flagged sentence, the note
        behind it and the three versions — and the spans are found by
        looking for the text that is actually in the script. See
        PROOFED_ENGLISH_HEAD in review_core.py.

        Everything already in the session goes: this is a different script,
        and a finding is an offset into the old one. The page asks first."""
        english, telugu, entries, note = core.parse_proofed_script(text or "")
        if not telugu:
            return {"error": note or f"there is no {self.language} in that file"}
        rows, baseline, missed = core.proofed_to_findings(
            telugu, entries, core.locate)
        with self._lock:
            self.session.english = english
            self.session.telugu = telugu
            # Before the stage applied Version 1 — so the change log shows
            # what it changed, rather than reading as though the script
            # arrived that way.
            self.session.baseline = baseline
            self.session.reset_findings()
            for r in rows:
                f = self.session.new_finding(r["start"], r["end"],
                                             r["issue"], "ai")
                f["orig"] = r["orig"]
                f["current"] = r["current"]
                f["english"] = r["english"]
                f["options"] = r["options"]
            state = self.session.as_json()
        state["loaded"] = len(rows)
        state["missed"] = [{"text": m.get("orig", ""),
                            "issue": m.get("issue", "")} for m in missed]
        state["note"] = note
        return state

    def act_load_state(self, page):
        """Load the page of a JSON saved with Export JSON into the session:
        both boxes and every correction, with its versions, note and kind,
        at the offsets it was saved with.

        `current` is the script now and `telugu` the script as it came in,
        which becomes the baseline the change log compares against. A
        correction whose saved text is no longer at its offsets is left out
        and counted. Everything already in the session goes."""
        page = page if isinstance(page, dict) else {}
        current = str(page.get("current") or page.get("telugu") or "")
        if not current.strip():
            return {"error": f"there is no {self.language} in that file"}
        rows = sorted((f for f in (page.get("findings") or [])
                       if isinstance(f, dict)),
                      key=lambda f: int(f.get("start", 0) or 0))
        loaded, missed = 0, []
        with self._lock:
            self.session.english = str(page.get("english") or "")
            self.session.telugu = current
            self.session.baseline = str(page.get("telugu") or current)
            self.session.reset_findings()
            at = 0
            for r in rows:
                try:
                    a, b = int(r.get("start")), int(r.get("end"))
                except (TypeError, ValueError):
                    missed.append(r); continue
                cur = str(r.get("current") or "")
                if not (at <= a < b <= len(current)) or current[a:b] != cur:
                    missed.append(r); continue
                kind = "man" if r.get("kind") == "man" else "ai"
                f = self.session.new_finding(a, b, str(r.get("issue") or ""), kind)
                f["orig"] = str(r.get("orig") or cur)
                f["current"] = cur
                f["english"] = str(r.get("english") or "")
                f["options"] = [str(o) for o in (r.get("options") or [])][:3]
                at = b
                loaded += 1
            state = self.session.as_json()
        state["loaded"] = loaded
        state["missed"] = [{"text": str(m.get("current") or m.get("orig") or ""),
                            "issue": str(m.get("issue") or "")} for m in missed]
        return state

    def act_set_issue(self, fid, issue):
        with self._lock:
            f = self.session.get(int(fid))
            if f is None:
                return {"error": "No such finding."}
            f["issue"] = issue
            return self.session.as_json()


def _make_handler(srv):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass                                  # this is a UI, not a service

        def _authorised(self, qs):
            token = (qs.get("t", [""])[0]
                     or self.headers.get("X-Proofing-Token", ""))
            return secrets.compare_digest(token, srv.token)

        def _send(self, code, body, ctype="application/json; charset=utf-8"):
            data = body if isinstance(body, bytes) else body.encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            try:
                self.wfile.write(data)
            except Exception:
                pass

        def _json(self, obj, code=200):
            self._send(code, json.dumps(obj, ensure_ascii=False))

        def do_GET(self):
            parsed = urlparse(self.path)
            qs = parse_qs(parsed.query)
            if not self._authorised(qs):
                return self._send(403, "Forbidden", "text/plain")
            if parsed.path in ("/", "/index.html"):
                page = os.path.join(HERE, PAGE_FILE)
                if not os.path.exists(page):
                    return self._send(500, f"{PAGE_FILE} missing", "text/plain")
                with open(page, "r", encoding="utf-8") as fh:
                    # The page is written with {{LANGUAGE}} wherever the
                    # language is named, and lang="{{LANG_TAG}}" on the
                    # boxes that hold it; both are filled here, so a change
                    # of language is a reload.
                    html = (fh.read().replace("__TOKEN__", srv.token)
                            .replace("{{LANG_TAG}}", tts.lang_tag(srv.language))
                            .replace("{{LANGUAGE}}", srv.language))
                return self._send(200, html, "text/html; charset=utf-8")
            if parsed.path == "/api/tts/chunk":
                try:
                    jid = int(qs.get("job", ["0"])[0])
                    idx = int(qs.get("i", ["0"])[0])
                except ValueError:
                    return self._send(400, "bad chunk request", "text/plain")
                job = srv.jobs.get(jid)
                if job is None:
                    return self._send(404, "no such job", "text/plain")
                data, err = job.chunk(idx)
                if err:
                    return self._send(500, err, "text/plain")
                if data is None:
                    # not synthesized yet - the page retries
                    return self._send(202, "not ready", "text/plain")
                return self._send(200, data, "audio/mpeg")
            if parsed.path == "/api/tts/status":
                return self._json(srv.act_tts_status(
                    qs.get("job", ["0"])[0]))
            if parsed.path == "/api/batch/load":
                return self._json(srv.act_batch_load())
            if parsed.path == "/api/state":
                st = srv.session.as_json()
                st["presets"] = [list(p) for p in core.ALL_PRESETS]
                st["config"] = srv.config()
                st["keys"] = srv._keys_state()
                st["tts"] = srv.tts_config()
                st["tts_sugg"] = srv.tts_config("sugg")
                return self._json(st)
            return self._send(404, "Not found", "text/plain")

        def do_POST(self):
            parsed = urlparse(self.path)
            qs = parse_qs(parsed.query)
            if not self._authorised(qs):
                return self._send(403, "Forbidden", "text/plain")
            try:
                n = int(self.headers.get("Content-Length") or 0)
                p = json.loads(self.rfile.read(n) or b"{}")
            except Exception as exc:
                return self._json({"error": f"bad request: {exc}"}, 400)

            r = parsed.path
            try:
                if r == "/api/tts/config":
                    return self._json(srv.act_set_tts(p))
                if r == "/api/tts/voices":
                    return self._json(srv.act_tts_voices(
                        p.get("platform", "")))
                if r == "/api/tts/start":
                    return self._json(srv.act_tts_start(
                        p.get("text", ""), p.get("language", "")))
                if r == "/api/tts/sentence":
                    data, err = srv.act_tts_sentence(
                        p.get("text", ""), bool(p.get("fresh")),
                        p.get("profile"))
                    if err:
                        return self._json({"error": err}, 500)
                    return self._send(200, data, "audio/mpeg")
                if r == "/api/tts/stop":
                    return self._json(srv.act_tts_stop())
                if r == "/api/keys/set":
                    return self._json(srv.act_keys_set(p))
                if r == "/api/keys/clear":
                    return self._json(srv.act_keys_clear(p.get("section")))
                if r == "/api/keys/import":
                    return self._json(srv.act_keys_import())
                if r == "/api/keys/test":
                    return self._json(srv.act_keys_test(p.get("section")))
                if r == "/api/config":
                    return self._json(srv.act_set_config(p))
                if r == "/api/sync":
                    return self._json(srv.act_sync(
                        p.get("telugu", ""), p.get("spans", [])))
                if r == "/api/setscripts":
                    return self._json(srv.act_set_scripts(
                        p.get("english", ""), p.get("telugu", "")))
                if r == "/api/detect":
                    return self._json(srv.act_detect())
                if r == "/api/translate":
                    return self._json(srv.act_translate())
                if r == "/api/oneshot":
                    return self._json(srv.act_oneshot())
                if r == "/api/batch/save":
                    return self._json(srv.act_batch_save(p.get("batch")))
                if r == "/api/batch/pick":
                    return self._json(srv.act_batch_pick())
                if r == "/api/batch/use":
                    return self._json(srv.act_batch_use(
                        str(p.get("path") or "")))
                if r == "/api/batch/suggestions":
                    return self._json(srv.act_batch_suggestions(
                        p.get("english", ""), p.get("telugu", ""),
                        p.get("items") or []))
                if r == "/api/batch/oneshot":
                    return self._json(srv.act_batch_oneshot(
                        p.get("english", ""), p.get("telugu", "")))
                if r == "/api/batch/sync":
                    return self._json(srv.act_batch_sync(
                        p.get("english", ""), p.get("telugu", ""),
                        p.get("helper", ""), p.get("before") or []))
                if r == "/api/batch/helper/pick":
                    return self._json(srv.act_batch_helper_pick())
                if r == "/api/batch/helper/info":
                    return self._json(srv.act_batch_helper_info(
                        p.get("path", "")))
                if r == "/api/suggestions":
                    return self._json(srv.act_suggestions(
                        p.get("scope", "all")))
                if r == "/api/apply":
                    return self._json(srv.act_apply(int(p["id"]),
                                                    int(p["index"]),
                                                    p.get("text")))
                if r == "/api/applytext":
                    return self._json(srv.act_apply_text(
                        int(p["id"]), str(p.get("text", ""))))
                if r == "/api/autoapply":
                    return self._json(srv.act_autoapply())
                if r == "/api/addissue":
                    return self._json(srv.act_add_issue(
                        p.get("start"), p.get("end"), p.get("issue", ""),
                        p.get("mark")))
                if r == "/api/clear":
                    return self._json(srv.act_clear(p.get("id"),
                                                    p.get("kind")))
                if r == "/api/loadstate":
                    return self._json(srv.act_load_state(p.get("page")))
                if r == "/api/loadproofed":
                    return self._json(srv.act_load_proofed(
                        p.get("text", "")))
                if r == "/api/export":
                    return self._json(srv.act_export())
                if r == "/api/issue":
                    return self._json(srv.act_set_issue(
                        int(p["id"]), str(p.get("issue", ""))))
            except Exception as exc:
                return self._json({"error": f"{type(exc).__name__}: {exc}"},
                                  500)
            return self._send(404, "Not found", "text/plain")

    return Handler
