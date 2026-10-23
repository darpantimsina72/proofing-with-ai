"""
The review logic: contracts, parsing, matching, and the session state.

Self-contained — nothing here imports from outside this folder. Standard
library only.
"""

import difflib
import json
import re
import time
import unicodedata

# ── The reason buttons on the Manual Review panel ────────────────────────
# Each marks the selected span and pre-fills this description, which stays
# editable afterwards. The wording goes to Gemini verbatim.
ISSUE_PRESETS = [
    ("Improve flow",
     "Sentences seems broken chunks, flow needs to be improved"),
    ("Make it connected",
     "make this part connected to the previous part of the sentence by "
     "somehow linking it to the idea or subject of the preceeding portion "
     "of the sentence. essentilly chlsoing the point at the end."),
    ("Real Meaning",
     "Setence seem very literal and doesnt add anything relevant to the "
     "context. need to identify the actual intention of the speaker behind "
     "the spoken words."),
    ("Right word",
     "the word used seems not contextually rich. Need to find a word that "
     "is more contextually apt and conveys the actual specifics the speaker "
     "is intending to convey."),
    ("Make it shorter",
     "the sentence is lengthy. we need to make it a bit crisp and short. at "
     "the same time not missing any detail. may be removing the redundant "
     "information and pronouns may help."),
]

# The catch-all. It does not name the problem — the instruction for what to
# do with an unnamed problem lives in Get_Suggestions_Prompt.txt, under
# "SOME NOTES DO NOT NAME THE PROBLEM", so it is written once instead of
# being repeated in the payload for every span marked this way.
NOT_OKAY_PRESET = ("Not okay", "This Sentence or phrase needs to be evaluated")

ALL_PRESETS = ISSUE_PRESETS + [NOT_OKAY_PRESET]


# ── The target language ─────────────────────────────────────────────────
# Everything here — the contracts below, the prompt files, the page — was
# written for Telugu. A second language reuses all of it with its own name
# swapped in, so there is one set of wording to keep right instead of one
# per language.
DEFAULT_LANGUAGE = "Telugu"


def localize(text, language):
    """`text`, written for Telugu, with `language`'s name in its place."""
    if not language or language == DEFAULT_LANGUAGE:
        return text
    return (text.replace("TELUGU", language.upper())
                .replace("Telugu", language)
                .replace("telugu", language.lower()))


# ── Output contracts, appended to the prompt files at call time ──────────
# They live in code rather than the .txt because the parsers below depend on
# them: they are a code-level contract, not a content choice.
JSON_CONTRACT = """

=== OUTPUT FORMAT (STRICT — THIS OVERRIDES ANY FORMAT DESCRIBED ABOVE) ===
Return ONLY a JSON array. No markdown code fence, no commentary before it or
after it.

Each element must be an object with exactly these two keys:

  "text"   The identified sentence or phrase, copied VERBATIM from the Telugu
           script above — character for character, including every … ; - and
           comma. Do NOT translate it, re-punctuate it, shorten it, correct
           it, or tidy the spacing. It must be locatable in the script by an
           exact string search. This is the single most important
           requirement: a "text" value that is not an exact substring of the
           script cannot be shown to the user at all.

  "issue"  A one-line description of what is wrong with that sentence.

The required shape:
[
  {"text": "<verbatim telugu sentence>", "issue": "<one line issue>"},
  {"text": "<verbatim telugu phrase>",   "issue": "<one line issue>"}
]

If nothing needs improving, return exactly: []
"""

SUGG_CONTRACT = """

=== OUTPUT FORMAT (STRICT — THIS OVERRIDES ANY FORMAT DESCRIBED ABOVE) ===
Return ONLY a JSON array. No markdown code fence, no commentary before it or
after it.

One object per identified sentence, with these four keys — and a fifth
one only where it applies:

  "n"            The number of the identified sentence, copied from the
                 "Identified sentences to improve" list. This is how your
                 answer is matched back to the sentence — it must be right.

  "english_n"    The NUMBER of the sentence in the numbered English
                 transcript above that this Telugu corresponds to — the
                 number alone, never the sentence itself. Where the Telugu
                 covers more than one, give them as an array, e.g. [3, 4].
                 You are choosing a line, not writing one: the app quotes
                 the transcript from the number you give, so there is
                 nothing to copy out and nothing you write can be shown.

  "text"         The original Telugu sentence, copied VERBATIM from the
                 script — character for character.

  "suggestions"  An array of exactly three strings: version 1, version 2 and
                 version 3, in that order, as described above.

  "gesture_en"   CASE C ONLY. The words inside the sentence you chose in
                 "english_n" that correspond to the phrase the note names
                 — copied from that sentence character for character, so
                 they can be found in it. Nothing else: not the whole
                 sentence, and not a paraphrase. Leave this key out
                 entirely for any sentence that is not Case C.

The required shape:
[
  {"n": 1,
   "english_n": 3,
   "text": "<original telugu sentence>",
   "suggestions": ["<version 1>", "<version 2>", "<version 3>"]}
]
and for a Case C sentence, the same with one key more:
[
  {"n": 1,
   "english_n": 3,
   "gesture_en": "<the words in sentence 3 the phrase corresponds to>",
   "text": "<original telugu sentence>",
   "suggestions": ["<version 1>", "<version 2>", "<version 3>"]}
]

Return one object for every numbered sentence you were given, in order.
"""


ONESHOT_CONTRACT = """

=== OUTPUT FORMAT (STRICT — THIS OVERRIDES ANY FORMAT DESCRIBED ABOVE) ===
Return ONLY a JSON array. No markdown code fence, no commentary before it or
after it.

One object per identified sentence, in the order the sentences appear in the
script, with exactly these four keys:

  "text"         The identified sentence or phrase, copied VERBATIM from the
                 Telugu script — character for character, including every … ;
                 - and comma. Do NOT translate it, re-punctuate it, shorten
                 it, correct it, or tidy the spacing.

                 This is the ONLY thing that ties your answer back to the
                 script — there is no sentence number to fall back on. An
                 entry whose "text" is not an exact substring of the script
                 is dropped whole, its three versions with it. It is worth
                 more to copy the sentence exactly than to improve it.

  "issue"        A one-line description of what is wrong with that sentence.

  "english"      The corresponding sentence from the English transcript,
                 copied VERBATIM from it — character for character, the
                 way "text" is copied from the Telugu. Do NOT translate the
                 Telugu back into English, and do not paraphrase, shorten,
                 re-order or tidy the transcript's wording. Where the Telugu
                 covers more than one English sentence, copy all of them;
                 where it covers part of one, copy that part.

  "suggestions"  An array of exactly three strings: version 1, version 2 and
                 version 3, in that order, as described above. Each one is a
                 complete drop-in replacement for "text".

The required shape:
[
  {"text": "<verbatim telugu sentence>",
   "issue": "<one line issue>",
   "english": "<corresponding english sentence>",
   "suggestions": ["<version 1>", "<version 2>", "<version 3>"]}
]

If nothing needs improving, return exactly: []
"""


# ── Grapheme clusters ────────────────────────────────────────────────────
# Used to trim a selection onto whole characters. The browser's own
# selection is already grapheme-aware, so this is a belt-and-braces check
# for spans that arrive from anywhere else.
_ZERO_WIDTH = ("‌", "‍")


def is_combining(ch):
    if ch in _ZERO_WIDTH:
        return True
    return unicodedata.category(ch) in ("Mn", "Mc", "Me")


def cluster_bounds(text):
    """Offsets where a grapheme cluster starts, plus len(text).

    Script-agnostic: keys off Unicode categories, not the Telugu block. A
    virama (combining class 9) or a ZWJ binds the FOLLOWING consonant into
    the same cluster, which is what makes conjuncts like క్ష one unit."""
    bounds, i, n = [0], 0, len(text)
    while i < n:
        i += 1
        while i < n:
            ch = text[i]
            if not is_combining(ch):
                break
            joins_next = (unicodedata.combining(ch) == 9
                          or ch == "‍")
            i += 1
            if joins_next and i < n:
                i += 1
        bounds.append(i)
    return bounds


# ── Matching a model's answer back into the script ───────────────────────
def normalise(s):
    """Collapse whitespace runs to one space, keeping a map back to the
    original offsets so a match can be reported in the original string."""
    out, imap, prev_ws = [], [], False
    for i, ch in enumerate(s):
        if ch.isspace():
            if prev_ws:
                continue
            out.append(" ")
            imap.append(i)
            prev_ws = True
        else:
            out.append(ch)
            imap.append(i)
            prev_ws = False
    return "".join(out), imap


def locate(haystack, needle, used):
    """Find `needle` in `haystack`, tolerating whitespace differences and
    stray wrapping punctuation from the model.

    `used` holds (start, end) spans already claimed, so two findings never
    cover the same characters. Returns (start, end) or None."""
    needle = (needle or "").strip().strip('"“”‘’')
    # Trailing sentence punctuation is often added or dropped by the model.
    # Stripping it from the NEEDLE is safe: the shorter string is still a
    # substring when the script has the mark.
    needle = needle.strip().strip(".,;!?")
    if not needle.strip():
        return None

    nh, imap = normalise(haystack)
    nn, _ = normalise(needle)
    nn = nn.strip()
    if not nn:
        return None

    from_i = 0
    while True:
        j = nh.find(nn, from_i)
        if j < 0:
            return None
        s = imap[j]
        e = imap[j + len(nn) - 1] + 1
        # Re-attach a sentence-final mark stripped off above, so the span
        # covers the script's own punctuation. Without this, replacing the
        # span leaves the old "." in place and a suggestion ending in "."
        # produces ".." — which in this script IS a pause marker. Never
        # extend over a pause run.
        if e < len(haystack) and haystack[e] in ".,;!?":
            if not (haystack[e] == "." and haystack[e:e + 2] == ".."):
                e += 1
        if not any(s < u_e and e > u_s for u_s, u_e in used):
            return (s, e)
        from_i = j + 1


# ── Parsing what comes back ──────────────────────────────────────────────
def _strip_fence(raw):
    s = (raw or "").strip()
    s = re.sub(r"^```(?:json)?\s*", "", s)
    return re.sub(r"\s*```$", "", s).strip()


def _loads_array(s):
    """json.loads on a JSON array, with a salvage pass for a reply that was
    cut off part way through.

    Returns (data, truncated). The one-step reply is by far the longest the
    app asks for — a detection plus three Telugu versions for every finding —
    so it is the one that can run into the model's output limit and stop
    mid-object. Throwing away every complete finding for the sake of the
    half-written last one is the wrong trade, so this walks back to the end of
    the last complete object and closes the array there."""
    try:
        return json.loads(s), False
    except Exception:
        pass
    depth, in_str, esc, cut = 0, False, False, -1
    for i, ch in enumerate(s):
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                cut = i
    if cut < 0:
        return None, False
    try:
        return json.loads(s[:cut + 1] + "]"), True
    except Exception:
        return None, False


def parse_oneshot(raw):
    """(items, note) for the combined detect-and-suggest reply.

    Each item is {"text", "issue", "english", "suggestions": [str, …]}.
    Unlike parse_suggestions there is no "n": the item carries the sentence it
    belongs to, and the caller locates that in the script. That is the whole
    point of the one-step path — the two-step one matches the second reply
    back to the first by a number, and a number can slip."""
    if not raw:
        return [], "the model returned an empty response"
    s = _strip_fence(raw)
    i = s.find("[")
    if i < 0:
        return [], "the response was not a JSON array"
    # Trim to the last "]" first, which drops any trailing chatter. On a reply
    # that was cut off there IS no closing bracket, and rfind lands on one
    # belonging to a nested "suggestions" array instead — chopping the reply
    # mid-object and leaving nothing for the salvage walk to find. So fall
    # back to everything from the opening bracket on.
    data, truncated = (None, False)
    j = s.rfind("]")
    if j > i:
        data, truncated = _loads_array(s[i:j + 1])
    if data is None:
        data, truncated = _loads_array(s[i:])
    if data is None:
        return [], "could not parse the JSON"
    if not isinstance(data, list):
        return [], "the JSON was not an array"

    out = []
    for el in data:
        if not isinstance(el, dict):
            continue
        t = str(el.get("text", "") or "").strip()
        if not t:
            continue
        sug = el.get("suggestions")
        if isinstance(sug, str):
            sug = [sug]
        sug = [str(x).strip() for x in (sug or []) if str(x).strip()]
        out.append({
            "text": t,
            "issue": str(el.get("issue", "") or "").strip()
                     or "(no description given)",
            "english": str(el.get("english", "") or "").strip(),
            "suggestions": sug,
        })
    note = ("the reply was cut off — the last, incomplete finding was dropped"
            if truncated else "")
    return out, note


def parse_findings(raw):
    """(findings, note). findings is [{"text","issue"}, …]; note is a
    human-readable warning, empty when the parse was clean."""
    if not raw:
        return [], "the model returned an empty response"
    s = _strip_fence(raw)
    i, j = s.find("["), s.rfind("]")
    if i < 0 or j <= i:
        return [], "the response was not a JSON array"
    try:
        data = json.loads(s[i:j + 1])
    except Exception as exc:
        return [], f"could not parse the JSON ({exc})"
    if not isinstance(data, list):
        return [], "the JSON was not an array"

    out = []
    for el in data:
        if not isinstance(el, dict):
            continue
        t = str(el.get("text", "") or "").strip()
        d = str(el.get("issue", "") or "").strip()
        if t:
            out.append({"text": t, "issue": d or "(no description given)"})
    return out, ""


def parse_suggestions(raw):
    """(items, note). Each item is
    {"n": int|None, "english": str, "text": str, "suggestions": [str, …]}."""
    if not raw:
        return [], "the model returned an empty response"
    s = _strip_fence(raw)
    i, j = s.find("["), s.rfind("]")
    if i < 0 or j <= i:
        return [], "the response was not a JSON array"
    try:
        data = json.loads(s[i:j + 1])
    except Exception as exc:
        return [], f"could not parse the JSON ({exc})"
    if not isinstance(data, list):
        return [], "the JSON was not an array"

    out = []
    for el in data:
        if not isinstance(el, dict):
            continue
        sug = el.get("suggestions")
        if isinstance(sug, str):
            sug = [sug]
        sug = [str(x).strip() for x in (sug or []) if str(x).strip()]
        if not sug:
            continue
        try:
            n = int(el.get("n"))
        except (TypeError, ValueError):
            n = None
        out.append({
            "n": n,
            "english": str(el.get("english", "") or "").strip(),
            "english_n": el.get("english_n"),
            "gesture_en": str(el.get("gesture_en", "") or "").strip(),
            "text": str(el.get("text", "") or "").strip(),
            "suggestions": sug,
        })
    return out, ""




def split_sentences(text):
    """The English transcript's own sentences, in order.

    Split on . ? ! so each piece keeps the transcript's exact wording — the
    app hands these back to the reviewer, so they must not be reflowed or
    tidied in any way."""
    out, start = [], 0
    for m in re.finditer(r"[.?!]+(?=\s|$)", text):
        piece = text[start:m.end()].strip()
        if piece:
            out.append(piece)
        start = m.end()
    tail = text[start:].strip()
    if tail:
        out.append(tail)
    return out


def number_sentences(sentences):
    """The transcript as the model sees it, one numbered sentence a line."""
    return "\n".join("[%d] %s" % (i, s) for i, s in enumerate(sentences, 1))


def english_from(sentences, item):
    """The transcript's own wording for the sentence(s) the model chose.

    It returns numbers rather than text, so what the reviewer reads is the
    script itself. Falls back to any text it sent anyway, which keeps a
    reply from an older prompt showing something rather than nothing."""
    n = item.get("english_n")
    nums = n if isinstance(n, (list, tuple)) else ([] if n is None else [n])
    picked = []
    for x in nums:
        try:
            i = int(x)
        except (TypeError, ValueError):
            continue
        if 1 <= i <= len(sentences) and sentences[i - 1] not in picked:
            picked.append(sentences[i - 1])
    if picked:
        return " ".join(picked)
    return str(item.get("english", "") or "").strip()


# ── The change log ───────────────────────────────────────────────────────
#
# One block per selection, put on the clipboard to be pasted wherever the
# reviewer keeps their notes: the English line the selection belongs to,
# the Telugu sentence as it stood before the review, and the Telugu
# sentence as it stands now.
#
# A selection is usually only PART of a sentence — the reason buttons flag
# exactly what was dragged — so both Telugu lines are widened to the whole
# sentence the selection sits in. The "before" line is not a snapshot: it
# is rebuilt by putting every flagged span inside that sentence back to the
# text it held when it was flagged, which stays right even when two
# selections landed in the same sentence. A change typed straight into the
# box, with no version applied, leaves no earlier text behind and so reads
# as part of the original.
#
# THE TWIN: this block is duplicated, near enough word for word, in the
# other implementation of this same surface — `review_core.py` under
# "Proofing with AI" and the Review tab in `End_to_End_Pipeline.py`. Search
# for EXPORT_SENT_ENDS to find the other copy, and change both together.

EXPORT_SENT_ENDS = ".?!;"
FOCUS_OPEN, FOCUS_CLOSE = "<Focus>", "</Focus>"

# How much of the two sentences has to still be shared, word for word,
# before tagging the differences is worth doing at all. Below this they
# have been rewritten rather than edited, and a scatter of tags across
# them tells the reader nothing — so the whole of each is tagged instead.
EXPORT_FOCUS_FLOOR = 0.34

_EXPORT_WORD_RE = re.compile(r"\S+")


def export_sentence_bounds(text, start, end):
    """Offsets of the sentence the span [start, end) sits in.

    Boundaries are . ? ! and ; only: a comma or a dash is punctuation
    inside a sentence rather than the end of one, and a dubbing script
    leans on both. The same rule Match Gesture already uses to widen a
    span, so a gesture note and an exported line agree on what a sentence
    is."""
    a = start
    while a > 0 and text[a - 1] not in EXPORT_SENT_ENDS:
        a -= 1
    # Forward from the LAST selected character, not from the end of the
    # selection: one that already takes in its own full stop should end
    # there rather than run on into the sentence after it.
    b = max(start, end - 1)
    while b < len(text) and text[b] not in EXPORT_SENT_ENDS:
        b += 1
    b = min(len(text), b + 1)            # the stop belongs to the sentence
    while a < b and text[a].isspace():
        a += 1
    while b > a and text[b - 1].isspace():
        b -= 1
    return a, b


def _export_wrap(text, runs):
    """`text` with <Focus> tags around each [start, end) run in `runs`."""
    if not runs:
        return text
    merged = []
    for s, e in sorted(runs):
        if merged and s <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([s, e])
    out = text
    for s, e in reversed(merged):        # right to left, so the offsets
        out = out[:s] + FOCUS_OPEN + out[s:e] + FOCUS_CLOSE + out[e:]
    return out                           # still mean what they meant


def export_focus_diff(before, after):
    """(before, after) with <Focus> tags around the parts that differ.

    Compared word by word rather than letter by letter: a Telugu word whose
    ending changed reads as one changed word, and tagging three letters
    inside it would be noise."""
    if before == after:
        return before, after
    aw = [m.span() for m in _EXPORT_WORD_RE.finditer(before)]
    bw = [m.span() for m in _EXPORT_WORD_RE.finditer(after)]
    a_words = [before[s:e] for s, e in aw]
    b_words = [after[s:e] for s, e in bw]
    sm = difflib.SequenceMatcher(None, a_words, b_words, autojunk=False)
    shared = sum(bl.size for bl in sm.get_matching_blocks())
    if not shared or shared < EXPORT_FOCUS_FLOOR * max(len(a_words),
                                                       len(b_words), 1):
        return (FOCUS_OPEN + before + FOCUS_CLOSE,
                FOCUS_OPEN + after + FOCUS_CLOSE)
    a_runs, b_runs = [], []
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == "equal":
            continue
        # An insertion has nothing to tag on the "before" side and a
        # deletion has nothing to tag on the "after" side, which is why
        # each side is tested for itself.
        if i2 > i1:
            a_runs.append((aw[i1][0], aw[i2 - 1][1]))
        if j2 > j1:
            b_runs.append((bw[j1][0], bw[j2 - 1][1]))
    return _export_wrap(before, a_runs), _export_wrap(after, b_runs)


def _export_restore(telugu, a, b, spans):
    """The sentence at [a, b) with every flagged span inside it put back to
    the text it held when it was flagged."""
    out = telugu[a:b]
    for s, e, orig in sorted(spans, reverse=True):
        if a <= s and e <= b and s < e:
            out = out[:s - a] + orig + out[e - a:]
    return out


def _export_oneline(s):
    """`s` as a single line: a field in the export is one line, and a note
    typed into Findings — or a sentence the script broke across lines —
    would otherwise split its block in two."""
    return " ".join((s or "").split())


def _export_split_sentences(text):
    """(start, end, sentence) for every sentence in `text`.

    The same boundaries export_sentence_bounds uses, walked end to end, so
    a sentence found here and a sentence found around a selection are the
    same sentence."""
    out, i, n = [], 0, len(text)
    while i < n:
        j = i
        while j < n and text[j] not in EXPORT_SENT_ENDS:
            j += 1
        j = min(n, j + 1)                # the stop belongs to the sentence
        a, b = i, j
        while a < b and text[a].isspace():
            a += 1
        while b > a and text[b - 1].isspace():
            b -= 1
        if b > a:
            out.append((a, b, text[a:b]))
        i = j
    return out


def _export_align(before_sents, after_sents):
    """Pair the baseline's sentences with the script's as it stands now.

    Returns (before, after, [indexes into after_sents]) per pair. A run
    that changed is paired one to one when both sides hold the same number
    of sentences — the ordinary case, one sentence rewritten — and joined
    into a single pair when they do not, which is what splitting one
    sentence in two, or merging two into one, looks like from here."""
    a_txt = [_export_oneline(s[2]) for s in before_sents]
    b_txt = [_export_oneline(s[2]) for s in after_sents]
    sm = difflib.SequenceMatcher(None, a_txt, b_txt, autojunk=False)
    pairs = []
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if (i2 - i1) == (j2 - j1):       # covers "equal" as well
            for k in range(i2 - i1):
                pairs.append((a_txt[i1 + k], b_txt[j1 + k], [j1 + k]))
        else:
            pairs.append((" ".join(a_txt[i1:i2]), " ".join(b_txt[j1:j2]),
                          list(range(j1, j2))))
    return pairs


# A baseline this unlike the script in front of us is not a baseline: the
# box was filled after it was taken, or the reviewer started over. Reporting
# every sentence as newly typed would be worse than saying nothing.
EXPORT_BASELINE_FLOOR = 0.3

EXPORT_NO_ENGLISH = ("(not recorded — no suggestions were fetched for this "
                     "selection)")
EXPORT_NO_BASELINE = (
    "Direct edits — sentences changed by typing into the script rather than\n"
    "by applying a version — are not in this list. Working them out needs\n"
    "the script as it stood at the start of the review, and this session\n"
    "does not have it: the script arrived before the app was watching, or\n"
    "it was cleared and started again.\n")


def export_changes_text(telugu, findings, when=None, baseline=None,
                        language=DEFAULT_LANGUAGE):
    """The whole change log, as one string.

    `findings` is a list of dicts in the order they should be written, each
    carrying `label`, `kind`, `start`, `end`, `orig`, `issue` and
    `english`. The offsets are into `telugu`, which is the script as it
    stands now.

    `baseline` is the script as it stood at the start of the review. With
    it, a flagged sentence's "before" is the real original rather than one
    rebuilt from the selection alone, and sentences the reviewer retyped —
    which leave no other trace at all — get a section of their own. Without
    it everything still works, minus those two things."""
    spans = []
    for f in findings:
        try:
            spans.append((int(f.get("start", 0)), int(f.get("end", 0)),
                          f.get("orig", "") or ""))
        except (TypeError, ValueError):
            continue

    # ── the baseline, and what it lines up with ──────────────────────────
    cur_sents = _export_split_sentences(telugu)
    base_sents = _export_split_sentences(baseline or "")
    pairs = _export_align(base_sents, cur_sents) if base_sents else []
    same = sum(1 for b, a, _ in pairs if b and b == a)
    usable = bool(base_sents) and (
        same > 0
        or len((baseline or "").strip()) >= EXPORT_BASELINE_FLOOR
                                            * max(len(telugu.strip()), 1))
    # Which pair a current sentence belongs to, so a finding can find its
    # own sentence's original.
    pair_of = {}
    for p, (_b, _a, idxs) in enumerate(pairs):
        for i in idxs:
            pair_of[i] = p

    blocks, changed, n_ai, covered = [], 0, 0, set()
    for n, f in enumerate(findings, 1):
        try:
            s, e = int(f.get("start", 0)), int(f.get("end", 0))
        except (TypeError, ValueError):
            continue
        is_ai = str(f.get("kind", "ai")) == "ai"
        if is_ai:
            n_ai += 1
        a, b = export_sentence_bounds(telugu, s, e)
        # Folded to one line before the diff rather than after it, so the
        # offsets the diff hands back index the string being tagged.
        after = _export_oneline(telugu[a:b])
        # EVERY sentence inside the span, not just the one it starts in: a
        # sentence ends at ; and a flagged line often runs across two
        # clauses, so one span can hold several.
        idxs = [i for i, cs in enumerate(cur_sents)
                if cs[0] >= a and cs[1] <= b]
        covered.update(idxs)
        # The baseline's own wording for those sentences, joined back in
        # their own order. Only when every pair sits wholly inside the
        # span: one that straddles the edge is a sentence the reviewer
        # split or merged, and joining it against this span would tag far
        # more than actually changed — so that falls back to rebuilding
        # the sentence from the selection.
        before = None
        if usable and idxs:
            picked = []
            for i in idxs:
                p = pair_of.get(i)
                if p is not None and p not in picked:
                    picked.append(p)
            if picked and all(all(j in idxs for j in pairs[p][2])
                              for p in picked):
                before = " ".join(pairs[p][0]
                                  for p in picked if pairs[p][0]) or None
        if before is None:
            before = _export_oneline(_export_restore(telugu, a, b, spans))
        if before != after:
            changed += 1
        marked_before, marked_after = export_focus_diff(before, after)
        english = _export_oneline(f.get("english")) or EXPORT_NO_ENGLISH
        blocks.append(
            "=" * 70 + "\n"
            + "[%s]  %s  —  %s\n" % (
                f.get("label") or n,
                "found by AI" if is_ai else "marked by hand",
                "changed" if before != after else "unchanged")
            + "-" * 70 + "\n"
            + "Selected : %s\n" % (_export_oneline(f.get("orig"))
                                   or "(nothing)")
            + "Issue    : %s\n" % (_export_oneline(f.get("issue"))
                                   or "(none given)")
            + "English  : %s\n" % english
            + "Before   : %s\n" % marked_before
            + "After    : %s\n" % marked_after)

    # ── what changed with no selection behind it ─────────────────────────
    # Every pair that moved and that no block above already reports. There
    # is nothing else to say about these: no selection was made, so there
    # is no phrase, no note and no English line to quote.
    direct = []
    if usable:
        for p_before, p_after, p_idxs in pairs:
            if p_before == p_after:
                continue
            if any(i in covered for i in p_idxs):
                continue
            # One side can be empty — a sentence deleted outright, or one
            # typed in where there was none. There is nothing to tag
            # there, and asking for a diff against "" would hand back a
            # pair of tags with nothing between them.
            if not p_before:
                mb = "(not in the original)"
                ma = FOCUS_OPEN + p_after + FOCUS_CLOSE
            elif not p_after:
                mb = FOCUS_OPEN + p_before + FOCUS_CLOSE
                ma = "(removed from the script)"
            else:
                mb, ma = export_focus_diff(p_before, p_after)
            direct.append(
                "=" * 70 + "\n"
                + "[D%d]  typed in directly  —  %s\n" % (
                    len(direct) + 1,
                    "removed" if not p_after else
                    "added" if not p_before else "changed")
                + "-" * 70 + "\n"
                + "Before   : %s\n" % mb
                + "After    : %s\n" % ma)

    head = (
        "PROOFING WITH AI — CHANGES MADE\n"
        + "Generated   : %s\n" % (when or time.strftime("%Y-%m-%d %H:%M:%S"))
        + "Selections  : %d  (%d found by AI, %d marked by hand)\n"
          % (len(blocks), n_ai, len(blocks) - n_ai)
        + "Changed     : %d   Unchanged: %d\n"
          % (changed, len(blocks) - changed)
        + "Direct edits: %s\n\n" % (len(direct) if usable else "not available")
        + "Each block is ONE selection, until the DIRECT EDITS banner at\n"
          "the end — past that they are sentences changed by typing into\n"
          "the script, with no selection behind them. Issue is the note a\n"
          "selection was flagged with — a reason button's wording, or\n"
          "whatever was typed into the Findings box. The two Telugu lines\n"
          "are the whole sentence the selection sits in — sentences end\n"
          "at . ? ! or ; — as it was before the review and as the script\n"
          "stands now. The parts that differ are wrapped in <Focus> tags;\n"
          "where the two have almost nothing in common the whole line is\n"
          "wrapped. The English line is the one recorded against the\n"
          "selection when its suggestions were fetched.\n\n")

    tail = ""
    if not usable:
        tail = "\n" + "#" * 70 + "\n" + EXPORT_NO_BASELINE + "#" * 70 + "\n"
    elif direct:
        tail = ("\n" + "#" * 70 + "\n"
                + "DIRECT EDITS — %d sentence(s) changed by typing into the "
                  "script,\nwith no selection made. Nothing else is recorded "
                  "about these.\n" % len(direct)
                + "#" * 70 + "\n\n" + "\n".join(direct))
    if not blocks:
        return localize(
            head + "No selections were made.\n"
            + (tail or "\nNothing was typed into the script either.\n"),
            language)
    return (localize(head, language) + "\n".join(blocks)
            + localize(tail, language))


# ── Reading a proofed script back in ─────────────────────────────────────
#
# The Proofing stage's own deliverable — three sections, written by
# _write_proofed_file in End_to_End_Pipeline.py — read back so a reviewer
# can pick the episode up where the pipeline left it: the English, the
# Telugu with Version 1 already applied, and every flagged sentence with
# its original, its note and its three versions.
#
# Nothing here trusts the file's own numbering to line up with the script.
# Each entry is found in the Telugu by its text: Version 1 for an entry the
# stage applied, the original for one it marked NOT LOCATED (which left the
# script holding the original). That is what turns a flat text file back
# into spans the tab can highlight.
#
# THE TWIN: duplicated in review_core.py and End_to_End_Pipeline.py, like
# the change-log block above it. Search for PROOFED_ENGLISH_HEAD.

PROOFED_ENGLISH_HEAD = "=== ENGLISH TRANSCRIPTION ==="
PROOFED_TELUGU_HEAD = "=== PROOFED TELUGU TRANSLATION ==="
# The same head for whichever language the pipeline proofed in, so a Hindi
# deliverable reads back the same way a Telugu one does.
_PROOFED_TARGET_RE = re.compile(r"=== PROOFED [A-Z]+ TRANSLATION ===")
PROOFED_SUGG_HEAD = "=== SUGGESTIONS ==="

# "--- [3]", and the tail the writer adds when Version 1 could not be put in.
_PROOFED_ENTRY_RE = re.compile(r"^---\s*\[(\d+)\](.*)$")
# "4. Version 1        : ..." — the number and the spacing are the writer's,
# so the name is what is matched on.
_PROOFED_FIELD_RE = re.compile(r"^\s*\d+\.\s*([A-Za-z0-9 ]+?)\s*:\s?(.*)$")
_PROOFED_FIELDS = {
    "english sentence": "english",
    "original telugu": "orig",
    "issue": "issue",
    "version 1": "v1",
    "version 2": "v2",
    "version 3": "v3",
}


def parse_proofed_script(text):
    """(english, telugu, entries, note) from a proofed script file.

    `entries` are in the file's own order, each with `n`, `english`, `orig`,
    `issue`, `versions` and `applied` — the last false for one the writer
    marked NOT LOCATED, meaning the script still holds the original.

    `note` is empty when the file parsed cleanly and says what is wrong when
    it did not. A file missing the Telugu section returns no Telugu, and the
    caller decides whether that is worth refusing."""
    if not (text or "").strip():
        return "", "", [], "the file is empty"
    body = text.replace("\r\n", "\n").replace("\r", "\n")
    i_en = body.find(PROOFED_ENGLISH_HEAD)
    m_te = _PROOFED_TARGET_RE.search(body)
    i_te, head_te = ((m_te.start(), m_te.group(0)) if m_te
                     else (-1, PROOFED_TELUGU_HEAD))
    i_sg = body.find(PROOFED_SUGG_HEAD)
    if i_te < 0:
        return "", "", [], ("this does not look like a proofed script — "
                            "there is no \"%s\" section" % PROOFED_TELUGU_HEAD)

    def section(start, head, *ends):
        if start < 0:
            return ""
        start += len(head)
        stop = min([e for e in ends if e > start] or [len(body)])
        return body[start:stop].strip()

    english = section(i_en, PROOFED_ENGLISH_HEAD, i_te, i_sg)
    telugu = section(i_te, head_te, i_sg)

    entries, cur, field = [], None, None
    for line in (body[i_sg:].split("\n") if i_sg >= 0 else []):
        m = _PROOFED_ENTRY_RE.match(line.strip())
        if m:
            cur = {"n": int(m.group(1)), "english": "", "orig": "",
                   "issue": "", "v1": "", "v2": "", "v3": "",
                   # The writer flags the ones it could not place. Anything
                   # it does not flag was applied.
                   "applied": "NOT LOCATED" not in m.group(2).upper()}
            entries.append(cur)
            field = None
            continue
        if cur is None:
            continue
        m = _PROOFED_FIELD_RE.match(line)
        if m:
            name = m.group(1).strip().lower()
            # "Original Telugu", "Original Hindi" — whichever language the
            # file was written in names the script's own line.
            field = ("orig" if name.startswith("original")
                     else _PROOFED_FIELDS.get(name))
            if field:
                cur[field] = m.group(2).strip()
            continue
        # Not a new field, so it belongs to the one before it: a note long
        # enough to wrap, or a version the writer broke across lines.
        if field and line.strip():
            cur[field] = (cur[field] + " " + line.strip()).strip()

    out = []
    for e in entries:
        versions = [v for v in (e["v1"], e["v2"], e["v3"]) if v]
        if not (e["orig"] or versions):
            continue
        out.append({"n": e["n"], "english": e["english"], "orig": e["orig"],
                    "issue": e["issue"], "versions": versions,
                    "applied": e["applied"] and bool(e["v1"])})

    note = ""
    if not telugu:
        note = "the Telugu section is empty"
    elif i_sg < 0:
        note = "there is no suggestions section, so nothing is highlighted"
    return english, telugu, out, note


def proofed_to_findings(telugu, entries, locate):
    """(rows, baseline, missed) — the entries placed in the script.

    `locate` is the app's own matcher, locate(haystack, needle, used) →
    (start, end) or None, so a sentence still matches when the only
    difference is the whitespace around it.

    `baseline` is the Telugu as it was BEFORE the stage applied Version 1:
    every placed span put back to its original. That is what the change log
    wants — without it every applied version would read as untouched, since
    the file arrives with them already in place."""
    used, rows, missed = [], [], []
    for e in entries:
        v1 = (e.get("versions") or [""])[0] if e.get("versions") else ""
        orig = e.get("orig", "")
        # An entry the stage applied left Version 1 in the script; one it
        # could not place left the original there. Try the likely one first
        # and the other second, so a hand-edited file still lands.
        wanted = [v1, orig] if e.get("applied") else [orig, v1]
        span = None
        for needle in wanted:
            if not needle:
                continue
            span = locate(telugu, needle, used)
            if span:
                break
        if not span:
            missed.append(e)
            continue
        used.append(span)
        rows.append({
            "n": e.get("n"), "start": span[0], "end": span[1],
            "current": telugu[span[0]:span[1]],
            # What the sentence said before the stage touched it. An entry
            # that was never applied has nothing earlier than what is there.
            "orig": orig or telugu[span[0]:span[1]],
            "issue": e.get("issue", ""), "english": e.get("english", ""),
            "options": list(e.get("versions") or []),
        })

    baseline = telugu
    for r in sorted(rows, key=lambda r: r["start"], reverse=True):
        baseline = baseline[:r["start"]] + r["orig"] + baseline[r["end"]:]
    return rows, baseline, missed

# ── Session state ────────────────────────────────────────────────────────
class Session:
    """The script and its findings.

    Spans are plain character offsets into `telugu`. When a version is
    applied the text is spliced and every later span shifts explicitly —
    see apply_version."""

    def __init__(self):
        self.english = ""
        self.telugu = ""
        # The Telugu as it stood at the start of the review, kept so the
        # change log can tell a sentence the reviewer retyped from one that
        # was never touched. Set once, by whoever first puts a script here,
        # and replaced only when a different script arrives.
        self.baseline = ""
        self.findings = []
        # `id` is unique across both kinds and is what the API addresses.
        # `label` is what the user sees, numbered PER KIND so a hand-marked
        # span reads [M1] rather than continuing the AI sequence — the same
        # convention the main app uses, and without it the first manual pick
        # after eleven AI finds shows up as [12] and looks like it was
        # lumped in with them.
        self._next_id = 1
        self._next_ai = 1
        self._next_man = 1

    def reset_findings(self, kind=None):
        if kind is None:
            self.findings = []
            self._next_ai = self._next_man = 1
        else:
            self.findings = [f for f in self.findings if f["kind"] != kind]
            if kind == "ai":
                self._next_ai = 1
            elif kind == "man":
                self._next_man = 1

    def new_finding(self, start, end, issue, kind="ai", mark=None):
        text = self.telugu[start:end]
        if kind == "man":
            label = "M%d" % self._next_man
            self._next_man += 1
        else:
            label = str(self._next_ai)
            self._next_ai += 1
        # `mark` is [start, end] WITHIN this span, or None. Relative, not
        # absolute, so it survives the span being pushed about as text
        # above it is edited.
        f = {"id": self._next_id, "label": label, "kind": kind,
             "start": start, "end": end, "mark": mark,
             "issue": issue, "english": "", "gesture_en": "",
             "orig": text, "current": text, "options": []}
        self._next_id += 1
        self.findings.append(f)
        return f

    def get(self, fid):
        return next((f for f in self.findings if f["id"] == fid), None)

    def apply_version(self, fid, text):
        """Splice `text` in and shift every span that starts after it."""
        f = self.get(fid)
        if f is None:
            return None
        start, end = f["start"], f["end"]
        delta = len(text) - (end - start)
        self.telugu = self.telugu[:start] + text + self.telugu[end:]
        f["current"] = text
        f["end"] = start + len(text)
        for other in self.findings:
            if other is not f and other["start"] >= end:
                other["start"] += delta
                other["end"] += delta
        return f

    def spans(self):
        return sorted(self.findings, key=lambda f: f["start"])

    def as_json(self):
        keys = ("id", "label", "kind", "start", "end", "mark", "issue",
                "english", "gesture_en", "orig", "current", "options")
        return {"english": self.english, "telugu": self.telugu,
                "findings": [{k: f[k] for k in keys} for f in self.spans()]}
