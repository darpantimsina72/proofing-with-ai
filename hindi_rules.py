"""Hindi house-style rules that need no AI: checked exactly, in code.

The model cannot be trusted with these - सद्‌गुरु and अद्‌भुत differ from
the wrong forms only by an invisible joining character (U+200C, ZWNJ), and a
nukta is one dot. So the batch flags them itself, as ordinary findings on the
page with the corrected text as the version. Nothing is applied: the reviewer
picks the version, as with any other finding.

    findings(text, used)  ->  [{"start", "end", "orig", "fix", "issue"}]

Offsets are code points into `text` (Python str indices), the same as the
page's own findings. `used` holds (start, end) spans already taken by other
findings; nothing returned overlaps them or each other.
"""
import re

ZWNJ = "‌"
SADHGURU = "सद्‌गुरु"   # सद्‌गुरु
ADBHUT = "अद्‌भुत"           # अद्‌भुत

# सद्गुरु / अद्भुत written without the joiner (or with ZWJ in its place).
_SADHGURU_BAD = re.compile("सद्(?:‍)?गुरु")
_ADBHUT_BAD = re.compile("अद्(?:‍)?भुत")
_JARURI_BAD = re.compile("ज़?रुरी")   # जरुरी / ज़रुरी
JARURI = "जरूरी"                          # जरूरी

# Nukta letters of Urdu and English words: क़ ख़ ग़ ज़ फ़, precomposed or as
# letter + nukta. ड़ and ढ़ are Hindi letters and are never touched.
_PRECOMP = {"क़": "क", "ख़": "ख", "ग़": "ग",
            "ज़": "ज", "फ़": "फ"}
_NUKTA_BASES = "कखगजफ"                    # क ख ग ज फ
_NUKTA = "़"

# A Devanagari word: letters, marks, digits and the joiners.
_WORD = re.compile("[ऀ-ॿ‌‍]+")
# A hyphen with a space on either side, between two non-spaces. Only the
# plain hyphen (and the Unicode hyphens); dashes (– —) are left alone.
_HYPHEN = re.compile(r"(\S+)([ \t]*)([-‐‑])([ \t]*)(\S+)")


def _strip_nukta(w):
    out, i = [], 0
    while i < len(w):
        ch = w[i]
        if ch in _PRECOMP:
            out.append(_PRECOMP[ch])
        elif ch == _NUKTA and out and out[-1] in _NUKTA_BASES:
            pass                                    # drop the dot
        else:
            out.append(ch)
        i += 1
    return "".join(out)


def fix_word(w):
    """(fixed word, [reasons]) for one word."""
    reasons, new = [], w
    if _SADHGURU_BAD.search(new):
        new = _SADHGURU_BAD.sub(SADHGURU, new)
        reasons.append("write " + SADHGURU + " (with the joiner), not the other form")
    if _ADBHUT_BAD.search(new):
        new = _ADBHUT_BAD.sub(ADBHUT, new)
        reasons.append("write " + ADBHUT + " (with the joiner), not the other form")
    if _JARURI_BAD.search(new):
        new = _JARURI_BAD.sub(JARURI, new)
        reasons.append("जरूरी, not जरुरी")
    stripped = _strip_nukta(new)
    if stripped != new:
        new = stripped
        reasons.append("Urdu/English word - remove the nukta")
    return new, reasons


def findings(text, used=()):
    text = text or ""
    taken = list(used)
    out = []

    def free(s, e):
        return not any(s < b and e > a for a, b in taken)

    # Spaces around a hyphen first: the words either side are fixed in the
    # same version, so a word there is not flagged twice.
    for m in _HYPHEN.finditer(text):
        if not (m.group(2) or m.group(4)):
            continue
        s, e = m.start(), m.end()
        if not free(s, e):
            continue
        lw, lr = fix_word(m.group(1))
        rw, rr = fix_word(m.group(5))
        fix = lw + m.group(3) + rw
        why = ["no space before or after the hyphen"] + lr + rr
        out.append({"start": s, "end": e, "orig": text[s:e], "fix": fix,
                    "issue": "[Proofing rule] " + "; ".join(dict.fromkeys(why))})
        taken.append((s, e))

    for m in _WORD.finditer(text):
        s, e = m.start(), m.end()
        new, why = fix_word(m.group(0))
        if not why or new == m.group(0) or not free(s, e):
            continue
        out.append({"start": s, "end": e, "orig": m.group(0), "fix": new,
                    "issue": "[Proofing rule] " + "; ".join(why)})
        taken.append((s, e))

    out.sort(key=lambda f: f["start"])
    return out
