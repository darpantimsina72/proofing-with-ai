"""House-style rules that need no AI: checked exactly, in code.

The model cannot be trusted with these - सद्\u200Cगुरु and अद्\u200Cभुत differ
from the wrong forms only by an invisible joining character (U+200C, ZWNJ),
and a nukta is one dot. So the batch flags them itself, as ordinary findings
on the page with the corrected text as the version. Nothing is applied: the
reviewer picks the version, as with any other finding. The rest of each
team's checklist goes to the model (Prompts/<language>/).

    fix(text, language)              -> text with every rule applied (used
                                        on the versions the model writes)
    findings(text, language, used)   -> [{"start", "end", "orig", "fix",
                                          "issue", "auto"}]

Offsets are code points into `text` (Python str indices), the same as the
page's own findings. `used` holds (start, end) spans already taken by other
findings; nothing returned overlaps them or each other. "auto" is true for
a word whose only fix is its quotation marks: the team asked for those to be
put in without a click, since a mark changes no word (and never the length).

Every language here: no space before or after a hyphen, and curly quotation
marks only (‘ ’ “ ”). Hindi also: सद्\u200Cगुरु / अद्\u200Cभुत with the
joiner, जरूरी, no nukta on Urdu or English words (ड़ and ढ़ keep theirs), and
chandrabindu in the words where it is certain.
"""
import re

LANGUAGES = {"Hindi", "Kannada"}       # Telugu's list is speaker labels only
QUOTES_ISSUE = "curly quotation marks only"

_DEV = "\u0900-\u0963\u0966-\u097F"     # Devanagari, less the danda । ॥
_END = f"(?![{_DEV}\u200C])"            # end of a Devanagari word

# A hyphen (or a Unicode hyphen; not a dash – —) with a space on either
# side, between two non-spaces.
_HYPHEN = re.compile("(?<=\\S)(?:[ \\t]+[-\u2010\u2011][ \\t]*"
                     "|[-\u2010\u2011][ \\t]+)(?=\\S)")
# Straight quotation marks: opening after a space, a bracket, a dash or the
# start of a line; closing anywhere else.
_QUOTES = re.compile("['\"]")
_OPENS_AFTER = " \t\n([{\u2014\u2013-"

# Nukta letters of Urdu and English words: क़ ख़ ग़ ज़ फ़, precomposed or as
# letter + nukta. ड़ and ढ़ are Hindi letters and are never touched.
_NUKTA = re.compile("[\u0958\u0959\u095A\u095B\u095E]|(?<=[कखगजफ])\u093C")
_PRECOMP = {"\u0958": "क", "\u0959": "ख", "\u095A": "ग",
            "\u095B": "ज", "\u095E": "फ"}

_HINDI_WORDS = [
    (re.compile("सद(?:्\u200D?)?गुरु"), "सद्\u200Cगुरु",
     "write सद्\u200Cगुरु (with the joiner), not the other form"),
    (re.compile("अद(?:्\u200D?)?भुत"), "अद्\u200Cभुत",
     "write अद्\u200Cभुत (with the joiner), not the other form"),
    (re.compile("जरुर(?=[ीत])"), "जरूर", "जरूरी, not जरुरी"),
    # Chandrabindu: a nasal vowel at the end of a word. Not शांत, संबंध,
    # हैं, में - those are right with anusvara.
    (re.compile(f"ां{_END}"), "ाँ", "chandrabindu missing"),
    (re.compile(f"ूं{_END}"), "ूँ", "chandrabindu missing"),
    (re.compile(f"ऊं{_END}"), "ऊँ", "chandrabindu missing"),
]
# Common words with a chandrabindu inside them, exactly.
# सांस(?![ा्]): not सांसारिक, सांस्कृतिक - those are right.
_HINDI_CHANDRA = {"आंख": "आँख", "गांव": "गाँव", "पांच": "पाँच",
                  "पांव": "पाँव", "सांस(?![ा्])": "साँस", "सांप": "साँप",
                  "चांद": "चाँद", "दांत": "दाँत", "बांध": "बाँध",
                  "कांप": "काँप", "झांक": "झाँक", "मुंह": "मुँह",
                  "पहुंच": "पहुँच", "ऊंच": "ऊँच"}


def _rules(language):
    """[(compiled pattern, fix(text, match) -> str, issue)]"""
    out = [(_HYPHEN, lambda t, m: "-", "no space before or after the hyphen"),
           (_QUOTES, lambda t, m: _curly(t, m), QUOTES_ISSUE)]
    if language == "Hindi":
        out.append((_NUKTA, lambda t, m: _PRECOMP.get(m.group(0), ""),
                    "Urdu/English word - remove the nukta"))
        for pat, repl, issue in _HINDI_WORDS:
            out.append((pat, lambda t, m, r=repl: r, issue))
        for wrong, right in _HINDI_CHANDRA.items():
            out.append((re.compile("(?<![" + _DEV + "])" + wrong),
                        lambda t, m, r=right: r, "chandrabindu missing"))
    return out


def _curly(text, m):
    i, single = m.start(), m.group(0) == "'"
    opening = i == 0 or text[i - 1] in _OPENS_AFTER
    if single:
        return "\u2018" if opening else "\u2019"
    return "\u201C" if opening else "\u201D"


def _edits(text, language):
    """[(start, end, replacement, issue)] for every rule match, the
    earlier rule winning where two overlap."""
    if language not in LANGUAGES or not text:
        return []
    got = []
    for pat, f, issue in _rules(language):
        for m in pat.finditer(text):
            s, e = m.span()
            if any(s < b and a < e for a, b, _, _ in got):
                continue
            got.append((s, e, f(text, m), issue))
    return sorted(got)


def _apply(text, edits):
    for s, e, r, _ in sorted(edits, reverse=True):
        text = text[:s] + r + text[e:]
    return text


def fix(text, language):
    """`text` with every rule for `language` applied."""
    return _apply(text, _edits(text, language)) if text else text


def findings(text, language, used=()):
    """One finding per word (or run of words joined by a fix) that a rule
    changes. The span is widened to whole words so the reviewer sees the
    word, and hits on the same word are one finding naming every rule."""
    text = text or ""
    groups = []                        # [start, end, [issues], [edits]]
    for ed in _edits(text, language):
        s, e = ed[0], ed[1]
        while s > 0 and not text[s - 1].isspace():
            s -= 1
        while e < len(text) and not text[e].isspace():
            e += 1
        if groups and s <= groups[-1][1]:
            g = groups[-1]
            g[1] = max(g[1], e)
            if ed[3] not in g[2]:
                g[2].append(ed[3])
            g[3].append(ed)
        else:
            groups.append([s, e, [ed[3]], [ed]])
    taken = list(used)
    out = []
    for s, e, issues, eds in groups:
        if any(s < b and a < e for a, b in taken):
            continue
        orig = text[s:e]
        new = _apply(orig, [(a - s, b - s, r, i) for a, b, r, i in eds])
        if new == orig:
            continue
        out.append({"start": s, "end": e, "orig": orig, "fix": new,
                    "issue": "[Proofing rule] " + "; ".join(issues),
                    "auto": issues == [QUOTES_ISSUE] and len(new) == len(orig)})
        taken.append((s, e))
    return out
