"""Update the app from its GitHub repository — the same files a fresh
download of the repository would give, without downloading a zip by hand.

    check()   -> {"current", "latest", "available", "changes": [...]}
    apply()   -> {"ok", "version", "written", "backup", "kept_yours": [...]}

What is replaced: only files that are in the repository — the app's code,
its page, its prompts. What is never touched: everything else in the folder
— the key files, App_Settings.json, the chapters list, logs, progress files
(those live beside the chapter files anyway). Every file that is replaced
is first copied to Backup/before-update-<date>/, so nothing is lost; a
prompt the team had edited here is listed in "kept_yours" so they know
where their version is.

A folder that is a git checkout (a developer's) is never updated this way:
git does that there.

VERSION_FILE holds the commit the folder was last updated to, and
MANIFEST_FILE what each file looked like then — how a file edited here
since is told apart from one that is simply old.
"""
import datetime
import hashlib
import io
import json
import os
import shutil
import ssl
import urllib.error
import urllib.request
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = "darpantimsina72/proofing-with-ai"
BRANCH = "main"
VERSION_FILE = "VERSION.txt"
MANIFEST_FILE = "update_manifest.json"
TIMEOUT = 20


def _ctx_list():
    """A verified connection first. A network that inspects HTTPS (an
    office proxy) breaks verification; the app's AI calls already go
    through such a network unverified, so the update does the same rather
    than never working there."""
    first = ssl.create_default_context()
    try:
        import certifi
        first = ssl.create_default_context(cafile=certifi.where())
    except Exception:
        pass
    loose = ssl.create_default_context()
    loose.check_hostname = False
    loose.verify_mode = ssl.CERT_NONE
    return [first, loose]


def _get(url, accept="application/vnd.github+json"):
    last = None
    for ctx in _ctx_list():
        try:
            req = urllib.request.Request(url, headers={
                "Accept": accept, "User-Agent": "proofing-with-ai-updater"})
            with urllib.request.urlopen(req, timeout=TIMEOUT, context=ctx) as r:
                return r.read()
        except ssl.SSLError as exc:
            last = exc
        except urllib.error.URLError as exc:
            if isinstance(getattr(exc, "reason", None), ssl.SSLError):
                last = exc
                continue
            raise
    raise last


def is_git_checkout():
    return os.path.isdir(os.path.join(HERE, ".git"))


def current_version():
    try:
        with open(os.path.join(HERE, VERSION_FILE), "r", encoding="utf-8") as fh:
            return fh.read().strip()
    except Exception:
        return ""


def check():
    """What GitHub has, against what this folder has."""
    if is_git_checkout():
        return {"available": False, "git": True,
                "note": "This folder is a git checkout; update it with git."}
    commits = json.loads(_get(
        f"https://api.github.com/repos/{REPO}/commits?sha={BRANCH}&per_page=30"))
    latest = commits[0]["sha"] if commits else ""
    cur = current_version()
    changes = []
    for c in commits:
        if c["sha"] == cur:
            break
        changes.append(c["commit"]["message"].split("\n")[0])
    return {"current": cur, "latest": latest,
            "available": bool(latest) and latest != cur,
            "changes": changes}


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def apply():
    """Download the latest commit and put its files in place."""
    if is_git_checkout():
        return {"ok": False, "error": "This folder is a git checkout; update it with git."}
    info = check()
    sha = info["latest"]
    if not sha:
        return {"ok": False, "error": "GitHub gave no version to update to."}
    blob = _get(f"https://codeload.github.com/{REPO}/zip/{sha}", accept="*/*")
    zf = zipfile.ZipFile(io.BytesIO(blob))
    try:
        with open(os.path.join(HERE, MANIFEST_FILE), "r", encoding="utf-8") as fh:
            manifest = json.load(fh)
    except Exception:
        manifest = {}

    files = {}
    for n in zf.namelist():
        if n.endswith("/"):
            continue
        rel = n.split("/", 1)[1] if "/" in n else ""
        # Nothing outside this folder, ever.
        if not rel or rel.startswith(("/", "\\")) or ".." in rel.split("/"):
            continue
        files[rel] = zf.read(n)

    stamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
    backup = os.path.join(HERE, "Backup", f"before-update-{stamp}")
    written, kept_yours, new_manifest = [], [], {}
    for rel, data in sorted(files.items()):
        dest = os.path.join(HERE, *rel.split("/"))
        new_manifest[rel] = _sha(data)
        old = None
        if os.path.exists(dest):
            with open(dest, "rb") as fh:
                old = fh.read()
        if old == data:
            continue
        if old is not None:
            b = os.path.join(backup, *rel.split("/"))
            os.makedirs(os.path.dirname(b), exist_ok=True)
            shutil.copy2(dest, b)
            # Edited here since the last update (or, before any update,
            # a prompt that differs): the team's own version is in Backup.
            was = manifest.get(rel)
            if (was and was != _sha(old)) or (not was and rel.startswith("Prompts/")):
                kept_yours.append(rel)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        tmp = dest + ".updating"
        with open(tmp, "wb") as fh:
            fh.write(data)
        os.replace(tmp, dest)
        written.append(rel)

    with open(os.path.join(HERE, MANIFEST_FILE), "w", encoding="utf-8") as fh:
        json.dump(new_manifest, fh, indent=1)
    with open(os.path.join(HERE, VERSION_FILE), "w", encoding="utf-8") as fh:
        fh.write(sha)
    return {"ok": True, "version": sha, "written": written,
            "backup": backup if written else "", "kept_yours": kept_yours,
            "changes": info.get("changes", [])}
