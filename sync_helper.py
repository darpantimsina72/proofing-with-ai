"""Corrections to sync with new version — the chapter's helper file.

The book's English was revised after the Telugu was translated and proofed.
A helper file holds, for one chapter, every sentence of the earlier draft
against the final English: unchanged, changed, deleted or added. It is made
once, from the chapter's "Final English … tracked changes" Word file, and
shared with everyone working on that chapter; the Book tab picks the pages of
the batch out of it by their text, so any batch of the chapter uses the same
file.

Build one:
    python sync_helper.py "…Final English Ch 1 - tracked changes.docx"
           [--out FOLDER] [--old "Chapter 01 for translation.docx"]
           [--final "…Pre-Press Version.docx"]

--old / --final check the helper: its earlier draft must be the old chapter
and its final English must be in the final book, word for word.

At run time (server.py) `page_changes` lines a page's English paragraphs up
with the helper and returns the changes on that page, each with an id, and
the page's English with a tag after every changed sentence.
"""
import datetime
import difflib
import json
import os
import re
import sys
import zipfile
import xml.etree.ElementTree as ET

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
KIND = "proofing-sync-helper"
VERSION = 1


# ── Reading the tracked Word file ────────────────────────────────────────
def _runs(el, mode, out):
    """Every run under `el`, in order, as (mode, text): mode "eq" for text
    the edit left alone, "ins" for inserted, "del" for deleted."""
    for ch in el:
        tag = ch.tag
        if tag == W + "r":
            txt = []
            for t in ch:
                if t.tag in (W + "t", W + "delText"):
                    txt.append(t.text or "")
                elif t.tag == W + "tab":
                    txt.append(" ")
                elif t.tag in (W + "br", W + "cr"):
                    txt.append("\n")
                elif t.tag == W + "noBreakHyphen":
                    txt.append("-")
            if txt:
                out.append((mode, "".join(txt)))
        elif tag in (W + "ins", W + "moveTo"):
            _runs(ch, "ins", out)
        elif tag in (W + "del", W + "moveFrom"):
            _runs(ch, "del", out)
        elif tag in (W + "pPr", W + "rPr", W + "sdtPr"):
            continue
        else:                          # hyperlink, smartTag, sdtContent …
            _runs(ch, mode, out)


def _para(p):
    segs = []
    _runs(p, "eq", segs)
    ppr = p.find(W + "pPr")
    style, num, mark = "", False, ""
    if ppr is not None:
        ps = ppr.find(W + "pStyle")
        style = ps.get(W + "val", "") if ps is not None else ""
        num = ppr.find(W + "numPr") is not None
        rpr = ppr.find(W + "rPr")
        if rpr is not None:
            mark = ("del" if rpr.find(W + "del") is not None else
                    "ins" if rpr.find(W + "ins") is not None else "")
    # The tracked file writes some of the earlier draft's footnotes inline,
    # "[footnote: …]", where the old chapter has a real footnote: not text of
    # the sentence, so not a change to it.
    old = re.sub(r"\[footnote:[^\]]*\]", "", "".join(t for m, t in segs if m != "ins"))
    return {"old": old,
            "new": "".join(t for m, t in segs if m != "del"),
            "style": style, "num": num, "mark": mark}


def read_tracked(path):
    """(body paragraphs, footnotes) of a tracked .docx, each with its earlier
    ("old") and final ("new") text."""
    with zipfile.ZipFile(path) as z:
        body = ET.fromstring(z.read("word/document.xml")).find(W + "body")
        paras = [_para(p) for p in body.iter(W + "p")]
        notes = []
        if "word/footnotes.xml" in z.namelist():
            root = ET.fromstring(z.read("word/footnotes.xml"))
            for fn in root.findall(W + "footnote"):
                if fn.get(W + "type") in ("separator", "continuationSeparator",
                                          "continuationNotice"):
                    continue
                segs = []
                for p in fn.iter(W + "p"):
                    if segs:
                        segs.append(("eq", "\n"))
                    _runs(p, "eq", segs)
                notes.append({
                    "fn": fn.get(W + "id"),
                    "old": "".join(t for m, t in segs if m != "ins").strip(),
                    "new": "".join(t for m, t in segs if m != "del").strip()})
    return paras, notes


def read_plain(path):
    """The text of an ordinary .docx, accepting any tracked changes in it —
    for the --old / --final checks only."""
    with zipfile.ZipFile(path) as z:
        body = ET.fromstring(z.read("word/document.xml")).find(W + "body")
    return "\n".join(_para(p)["new"] for p in body.iter(W + "p"))


# ── Sentences ────────────────────────────────────────────────────────────
_ABBR = re.compile(r"(?:\b(?:Mr|Mrs|Ms|Dr|St|Sr|Jr|vs|etc|No|Nos|ca|viz|"
                   r"i\.e|e\.g|b|d|c)\.|\b[A-Z]\.)$")
_END = re.compile(r"[.?!…]+[\"”’)\]]*(?=\s+[\"“‘(\[]?[A-Z0-9—–])")


def split_sentences(text):
    """Sentences of `text`, raw. A line break always ends one."""
    out = []
    for line in (text or "").split("\n"):
        start = 0
        for m in _END.finditer(line):
            if _ABBR.search(line[:m.end()]):
                continue
            s = line[start:m.end()].strip()
            if s:
                out.append(s)
            start = m.end()
        s = line[start:].strip()
        if s:
            out.append(s)
    return out


def _key(s):
    return re.sub(r"\s+", " ", s or "").strip()


def _words(s):
    return re.findall(r"[a-z0-9’']+", (s or "").lower())


def _ratio(a, b):
    wa, wb = _words(a), _words(b)
    if not wa or not wb:
        return 0.0
    return difflib.SequenceMatcher(None, wa, wb, autojunk=False).ratio()


def _pair(A, B):
    """Order-keeping alignment of the old sentences A with the new ones B in
    a replaced stretch: the pairing with the most word overlap. Unpaired old
    ones are deleted, unpaired new ones added."""
    n, m = len(A), len(B)
    R = [[_ratio(a, b) for b in B] for a in A]
    best = [[0.0] * (m + 1) for _ in range(n + 1)]
    for i in range(n - 1, -1, -1):
        for j in range(m - 1, -1, -1):
            take = R[i][j] + best[i + 1][j + 1] if R[i][j] >= 0.3 else -1
            best[i][j] = max(take, best[i + 1][j], best[i][j + 1])
    ents, i, j = [], 0, 0
    while i < n and j < m:
        if R[i][j] >= 0.3 and best[i][j] == R[i][j] + best[i + 1][j + 1]:
            ents.append({"k": "chg", "old": A[i], "new": B[j]})
            i += 1
            j += 1
        elif best[i][j] == best[i + 1][j]:
            ents.append({"k": "del", "old": A[i]})
            i += 1
        else:
            ents.append({"k": "add", "new": B[j]})
            j += 1
    ents += [{"k": "del", "old": a} for a in A[i:]]
    ents += [{"k": "add", "new": b} for b in B[j:]]
    return _absorb(ents)


def _absorb(ents):
    """Two sentences joined into one (or one split in two) show up as a
    change beside a deletion (or an addition). Fold the neighbour into the
    change when the pair then matches better."""
    changed = True
    while changed:
        changed = False
        for k, e in enumerate(ents):
            if e["k"] != "chg":
                continue
            for nb, side in ((k - 1, "before"), (k + 1, "after")):
                if not (0 <= nb < len(ents)):
                    continue
                o = ents[nb]
                if o["k"] == "del":
                    old2 = (o["old"] + " " + e["old"] if side == "before"
                            else e["old"] + " " + o["old"])
                    if _ratio(old2, e["new"]) > _ratio(e["old"], e["new"]) + 0.05:
                        e["old"] = old2
                        del ents[nb]
                        changed = True
                        break
                elif o["k"] == "add":
                    new2 = (o["new"] + " " + e["new"] if side == "before"
                            else e["new"] + " " + o["new"])
                    if _ratio(e["old"], new2) > _ratio(e["old"], e["new"]) + 0.05:
                        e["new"] = new2
                        del ents[nb]
                        changed = True
                        break
            if changed:
                break
    return ents


def diff_unit(old, new):
    """The sentences of one paragraph, earlier draft against final:
    [{"k": "same"|"chg"|"del"|"add", "old", "new"}]."""
    a, b = split_sentences(old), split_sentences(new)
    sm = difflib.SequenceMatcher(None, [_key(x) for x in a],
                                 [_key(x) for x in b], autojunk=False)
    ents = []
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == "equal":
            ents += [{"k": "same", "new": b[j]} for j in range(j1, j2)]
        elif op == "delete":
            ents += [{"k": "del", "old": a[i]} for i in range(i1, i2)]
        elif op == "insert":
            ents += [{"k": "add", "new": b[j]} for j in range(j1, j2)]
        else:
            ents += _pair(a[i1:i2], b[j1:j2])
    return ents


# ── Matching text by its words ───────────────────────────────────────────
# Lekhak's English is the final English, but numbered: "CHAPTER 1." before
# the title, "1." before a question, a footnote number glued to the word it
# belongs to ("sanyasis1") and in front of the footnote itself. Words are
# compared without any of that, and without punctuation or case.
# Letters and digits apart, so the footnote mark in "sanyasis1" is a word of
# its own, and dropped.
_TOK = re.compile(r"[a-z]+|[0-9]+")
# Lekhak puts a page's footnotes one after the other on one line:
# "2 Yogic postures. 3 Ancient Indian sage …" — found one by one.
_FN_SPLIT = re.compile(r"(?<=[.?!”’\")\]])\s+(?=\d{1,3}\s+\S)")


def tokens(text, para_start=True):
    """[(word, start, end)] — the comparable words of `text` with their raw
    offsets. A footnote number glued to a word is dropped; at a paragraph's
    start, so are "CHAPTER n" and a 1–3 digit number."""
    low = (text or "").lower().replace("’", "'")
    out = []
    for m in _TOK.finditer(low):
        w, s = m.group(), m.start()
        if w.isdigit() and s > 0 and low[s - 1] not in " \t\n([{\"“‘—–-/":
            # "asanas2", "exam8.", "Namaskaram,12" — a footnote mark; but
            # "24,996" and "3.5" are numbers.
            if not (low[s - 1] in ".," and s > 1 and low[s - 2].isdigit()):
                continue
        out.append((w, s, m.end()))
    if para_start:
        if len(out) >= 2 and out[0][0] == "chapter" and out[1][0].isdigit():
            out = out[2:]
        elif (len(out) >= 2 and out[0][0].isdigit() and len(out[0][0]) <= 3
              and re.match(r"\s*\d{1,3}[.)]?\s", low)):
            out = out[1:]
    return out


# ── Building the helper ──────────────────────────────────────────────────
def build(tracked_path):
    paras, notes = read_tracked(tracked_path)
    units = []
    for p in paras:
        if not p["old"].strip() and not p["new"].strip():
            continue
        units.append({"part": "body", "style": p["style"], "num": p["num"],
                      "old": p["old"], "new": p["new"],
                      "ents": diff_unit(p["old"], p["new"])})
    for n in notes:
        if not n["old"] and not n["new"]:
            continue
        units.append({"part": "footnote", "fn": n["fn"],
                      "old": n["old"], "new": n["new"],
                      "ents": diff_unit(n["old"], n["new"])})
    # A sentence deleted in one place and added, near enough word for word,
    # in another: moved.
    dels = [(u, e) for u, U in enumerate(units) for e in U["ents"]
            if e["k"] == "del" and len(_words(e["old"])) >= 4]
    adds = [(u, e) for u, U in enumerate(units) for e in U["ents"]
            if e["k"] == "add" and len(_words(e["new"])) >= 4]
    for du, d in dels:
        for au, a in adds:
            if au != du and "moved" not in a and _ratio(d["old"], a["new"]) >= 0.9:
                d["moved"] = {"to": au}
                a["moved"] = {"from": du, "old": d["old"]}
                break
    title = next((u["new"].strip() for u in units
                  if u["style"].lower().startswith("heading") and u["new"].strip()), "")
    m = re.search(r"\bCh(?:apter)?\s*(\d+)", os.path.basename(tracked_path), re.I)
    counts = {}
    for u in units:
        for e in u["ents"]:
            counts[e["k"]] = counts.get(e["k"], 0) + 1
    return {"kind": KIND, "version": VERSION,
            "chapter": int(m.group(1)) if m else None, "title": title,
            "source": os.path.basename(tracked_path),
            "made": datetime.datetime.now().isoformat(timespec="seconds"),
            "counts": counts, "units": units}


def check(helper, old_docx=None, final_docx=None):
    """[(what, ok, detail)] — the earlier draft against the old chapter and
    the final English against the final book, word for word."""
    out = []
    body = [u for u in helper["units"] if u["part"] == "body"]
    if old_docx:
        a = [w for w, _, _ in tokens(" \n".join(u["old"] for u in body), False)]
        b = [w for w, _, _ in tokens(read_plain(old_docx), False)]
        sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
        bad = [(op, " ".join(a[i1:i2])[:80], " ".join(b[j1:j2])[:80])
               for op, i1, i2, j1, j2 in sm.get_opcodes() if op != "equal"]
        out.append(("earlier draft = old chapter", not bad,
                    f"{len(a)} words, {len(bad)} difference(s)"
                    + "".join(f"\n      {x}" for x in bad[:8])))
    if final_docx:
        a = " ".join(w for w, _, _ in tokens(" \n".join(u["new"] for u in body), False))
        book = " ".join(w for w, _, _ in tokens(read_plain(final_docx), False))
        ok = a in book
        detail = f"{len(a.split())} words"
        if not ok:
            # Where the first paragraph that is not in the book is.
            for u in body:
                t = " ".join(w for w, _, _ in tokens(u["new"], False))
                if t and t not in book:
                    detail += f"; first not found: {u['new'][:100]!r}"
                    break
        out.append(("final English is in the final book", ok, detail))
    return out


# ── Run time: one page ───────────────────────────────────────────────────
class Helper:
    """A loaded helper file, indexed for finding a page's paragraphs."""

    def __init__(self, data):
        if not isinstance(data, dict) or data.get("kind") != KIND:
            raise ValueError("this is not a sync helper file")
        self.data = data
        self.units = data["units"]
        # One stream of words per part: every sentence's final words in
        # order. Each entry with final words knows where they are in it; a
        # deleted one knows the place between words where it was.
        self.stream = {"body": [], "footnote": []}
        self.refs = []                 # (part, unit index, entry index, start, end)
        for ui, u in enumerate(self.units):
            st = self.stream[u["part"]]
            for ei, e in enumerate(u["ents"]):
                w = [t for t, _, _ in tokens(e.get("new", ""), False)]
                e["_s"], e["_e"] = len(st), len(st) + len(w)
                st.extend(w)
                e["_u"], e["_i"] = ui, ei
        self.text = {k: " " + " ".join(v) + " " for k, v in self.stream.items()}
        self.word_at = {}
        for k, v in self.stream.items():
            pos, at = 1, {}
            for i, w in enumerate(v):
                at[pos] = i
                pos += len(w) + 1
            self.word_at[k] = at

    def find(self, words, part, cursor=0):
        """(start, end) word indices of `words` in the stream of `part`, at or
        after word `cursor`; None if not there."""
        if not words:
            return None
        txt, at = self.text[part], self.word_at[part]
        needle = " " + " ".join(words) + " "
        # The char position of word `cursor`.
        from_c = 0
        if cursor:
            from_c = next((c for c, i in at.items() if i == cursor), 0)
        j = txt.find(needle, max(0, from_c - 1))
        if j < 0:
            return None
        s = at.get(j + 1)
        return None if s is None else (s, s + len(words))


def _paras(text):
    """[(start, end)] of the blank-line-separated paragraphs of `text`."""
    out, pos = [], 0
    for m in re.finditer(r"\n[ \t]*\n\s*", text):
        if text[pos:m.start()].strip():
            out.append((pos, m.start()))
        pos = m.end()
    if text[pos:].strip():
        out.append((pos, len(text.rstrip())))
    return out


def page_changes(helper, english, cursor=None):
    """The changes on one page.

    Returns {"paras": [{"en": (s, e), "tagged": str, "found": bool}],
             "changes": [{"id", "kind", "para", "old", "new", "moved", "edge"}],
             "unfound": [paragraph text], "cursor": {...}}.

    Each English paragraph is found in the helper by its words, in order.
    A changed or added sentence belongs to the page its first word is on; a
    deleted one to the page holding the sentence before it in its paragraph
    (the one after it, at a paragraph's start) — so across the pages of a
    chapter every change is on exactly one page."""
    cur = dict(cursor or {"body": 0, "footnote": 0})
    paras = _paras(english)
    if cursor is None:
        # The first page of a batch: start the search a little before the
        # page's longest paragraph, so a short paragraph near its top ("Seeker:
        # Yes.") is not taken from an earlier part of the chapter.
        sized = [(len(tokens(english[s:e])), k) for k, (s, e) in enumerate(paras)]
        sized = [x for x in sized if x[0] >= 8]
        if sized:
            n_w, k = max(sized)
            s, e = paras[k]
            hit = helper.find([w for w, _, _ in tokens(english[s:e])], "body", 0)
            if hit:
                before = sum(len(tokens(english[a:b])) for a, b in paras[:k])
                cur["body"] = max(0, hit[0] - before - 40)
    out_paras, spans = [], []          # spans: (para index, part, ws, we, toks)
    unfound = []
    def locate(raw):
        """(part, start, end, toks) for one stretch of English, or None."""
        toks = tokens(raw)
        words = [w for w, _, _ in toks]
        if not words:
            return None
        for part in ("body", "footnote"):
            hit = helper.find(words, part, cur[part] if part == "body" else 0)
            if hit:
                return part, hit[0], hit[1], toks
        hit = helper.find(words, "body", 0)   # anywhere, as a last try
        return ("body", hit[0], hit[1], toks) if hit else None

    for pi, (ps, pe) in enumerate(paras):
        raw = english[ps:pe]
        if not tokens(raw):
            out_paras.append({"en": (ps, pe), "found": True})
            continue
        got = locate(raw)
        pieces = [(0, got)] if got else []
        if not got:
            # Footnotes run together on one line: each on its own.
            cuts = [0] + [m.end() for m in _FN_SPLIT.finditer(raw)]
            if len(cuts) > 1:
                bounds = cuts + [len(raw)]
                pieces = [(bounds[k], locate(raw[bounds[k]:bounds[k + 1]]))
                          for k in range(len(cuts))]
                if not all(g for _, g in pieces):
                    pieces = []
        for off, (part, ws, we, toks) in pieces:
            if part == "body":
                cur["body"] = we
            spans.append((pi, part, ws, we,
                          [(w, s + off, e + off) for w, s, e in toks]))
        if not pieces:
            unfound.append(raw)
        out_paras.append({"en": (ps, pe), "found": bool(pieces)})

    changes, tags = [], {}              # tags: para index -> [(raw pos, text)]
    n = 0

    def on_page(part, w):
        for pi, pt, ws, we, toks in spans:
            if pt == part and ws <= w < we:
                return pi, ws, we, toks
        return None

    for u in helper.units:
        part = u["part"]
        ents = u["ents"]
        for ei, e in enumerate(ents):
            if e["k"] == "same":
                continue
            if e["k"] in ("chg", "add"):
                hit = on_page(part, e["_s"])
                if not hit:
                    continue
                pi, ws, we, toks = hit
                end_w = min(e["_e"], we) - 1
                edge = e["_e"] > we
                raw_end = toks[end_w - ws][2] if end_w >= ws else 0
            else:                       # deleted: the sentence before it, or after
                prev = next((x for x in reversed(ents[:ei]) if x.get("new")), None)
                nxt = next((x for x in ents[ei + 1:] if x.get("new")), None)
                anchor = prev or nxt
                if anchor is None:
                    # A whole paragraph deleted: hang it on the one before.
                    w0 = ents[0]["_s"] - 1 if ents else -1
                    hit = on_page(part, w0) if w0 >= 0 else None
                    if not hit:
                        continue
                    pi, ws, we, toks = hit
                    raw_end, edge = None, False
                else:
                    w0 = anchor["_e"] - 1 if prev else anchor["_s"]
                    hit = on_page(part, w0)
                    if not hit:
                        continue
                    pi, ws, we, toks = hit
                    edge = False
                    if prev:
                        raw_end = toks[w0 - ws][2]
                    else:
                        raw_end = -1    # before the paragraph's first word
            n += 1
            cid = f"C{n}"
            ps = paras[pi][0]
            # A deleted line that is word for word a line that stays (a title
            # written twice in the earlier draft): its Telugu, if there once,
            # belongs to the one that stays.
            dup = False
            if e["k"] == "del":
                ow = [w for w, _, _ in tokens(e.get("old", ""), False)]
                dup = bool(ow) and any(
                    [w for w, _, _ in tokens(x.get("new", ""), False)] == ow
                    for x in ents if x is not e and x.get("new")) or bool(ow) and any(
                    [w for w, _, _ in tokens(x.get("new", ""), False)] == ow
                    for k2 in (e["_u"] - 1, e["_u"] + 1)
                    if 0 <= k2 < len(helper.units)
                    for x in helper.units[k2]["ents"] if x.get("new"))
                e["_dup"] = dup
            changes.append({"id": cid, "kind": e["k"], "para": pi + 1, "dup": dup,
                            "old": e.get("old", ""), "new": e.get("new", ""),
                            "moved": e.get("moved"), "edge": edge,
                            "whole_para": e["k"] == "del" and raw_end is None,
                            "ref": [e["_u"], e["_i"]]})
            tags.setdefault(pi, []).append((raw_end, cid, e))

    # The page's English with a tag after each changed sentence.
    for pi, (ps, pe) in enumerate(paras):
        raw = english[ps:pe]
        ins = []
        for raw_end, cid, e in tags.get(pi, []):
            t = _tag(cid, e, helper)
            if raw_end is None:
                ins.append((len(raw), "\n" + t))
            elif raw_end == -1:
                ins.append((0, t + " "))
            else:
                k = raw_end
                while k < len(raw) and not raw[k].isspace():
                    k += 1             # past the sentence's own punctuation
                ins.append((k, " " + t))
        for k, t in sorted(ins, key=lambda x: x[0], reverse=True):
            raw = raw[:k] + t + raw[k:]
        out_paras[pi]["tagged"] = raw
    return {"paras": out_paras, "changes": changes, "unfound": unfound,
            "cursor": cur}


def _tag(cid, e, helper):
    k = e["k"]
    mv = e.get("moved") or {}
    if k == "chg":
        t = f"⟦{cid} CHANGED · earlier draft: “{e['old']}”"
    elif k == "add":
        t = f"⟦{cid} ADDED · not in the earlier draft"
        if "from" in mv:
            t += " · MOVED here from elsewhere in the chapter (earlier draft had it there)"
    else:
        t = f"⟦{cid} DELETED · the earlier draft had here: “{e['old']}”"
        if e.get("_dup"):
            t += (" · the earlier draft had this line TWICE; the final English keeps"
                  " one. Only a second copy in the translation is the deleted one")
        if "to" in mv:
            t += " · MOVED: the same sentence is now elsewhere in the chapter"
    return t + "⟧"


def load(path):
    with open(path, "r", encoding="utf-8") as fh:
        return Helper(json.load(fh))


# ── Command line ─────────────────────────────────────────────────────────
def _main(argv):
    import argparse
    ap = argparse.ArgumentParser(description="Build a chapter's sync helper file.")
    ap.add_argument("tracked", help="the chapter's 'Final English … tracked changes' .docx")
    ap.add_argument("--out", help="folder for the helper (default: beside the .docx)")
    ap.add_argument("--old", help="the old chapter .docx, to check the earlier draft")
    ap.add_argument("--final", help="the final book .docx, to check the final English")
    a = ap.parse_args(argv)
    h = build(a.tracked)
    for what, ok, detail in check(h, a.old, a.final):
        print(("OK   " if ok else "FAIL ") + what + " — " + detail)
    out_dir = a.out or os.path.dirname(os.path.abspath(a.tracked))
    os.makedirs(out_dir, exist_ok=True)
    name = f"Chapter {h['chapter']} - sync helper.json" if h["chapter"] else \
        os.path.splitext(os.path.basename(a.tracked))[0] + " - sync helper.json"
    path = os.path.join(out_dir, name)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(h, fh, ensure_ascii=False, indent=0)
    print(f"wrote {path} — {len(h['units'])} paragraphs, sentences {h['counts']}")


if __name__ == "__main__":
    _main(sys.argv[1:])
