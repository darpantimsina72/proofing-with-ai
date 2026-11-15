"""House-style rules that need no judgement — the mechanical half of each
language team's "points to check after proofing" list.

The judgement half (grammar, something odd, repeated or missing
translation, the speaker labels, question numbers) goes to the model with
the detection prompt, from Prompts/<language>/Extra_Checks.txt. What is
here is exact and is applied by code, because a model copying a quote
character for character cannot be trusted with an invisible joiner
(सद्\u200Cगुरु) or a dot under a letter.

    fix(text, language)       -> text with every rule applied
    problems(text, language)  -> [(start, end, fixed, issue)], one per
                                 word (or words) a rule changes
"""
import re

ZWNJ = "\u200C"
_DEV = "\u0900-\u0963\u0966-\u097F"   # Devanagari, less the danda । ॥
_END = f"(?![{_DEV}{ZWNJ}])"                  # end of a Devanagari word


_HYPHEN_RE = re.compile(r"(?<=\S)(?:[ \t]+-[ \t]*|-[ \t]+)(?=\S)")


def _quote_style(text, straight, opening, closing):
    """One kind of inverted comma on the page: whichever of straight or
    curly it uses more (curly on a tie). Returns (pattern, fix) for the
    minority kind, or None when the page uses only one."""
    n_straight = text.count(straight)
    n_curly = text.count(opening) + text.count(closing)
    if not n_straight or not n_curly:
        return None
    if n_straight > n_curly:
        return (re.compile(f"[{opening}{closing}]"),
                lambda t, i: straight)
    # Straight to curly: opening after a space, a bracket or the start of
    # a line, closing anywhere else.
    return (re.compile(re.escape(straight)),
            lambda t, i: opening if i == 0 or t[i - 1] in " \t\n([{—-–"
            else closing)


# Hindi: Urdu-origin words lose the nukta; ड़ ढ़ are Hindi and keep it.
# क़ ख़ ग़ are only ever Urdu sounds, so they always lose it. ज़ and फ़ are
# in English words too (यूज़र, फ़ोन), which the list does not cover — so they
# lose it only in the Urdu words below (and anything built on them:
# ज्यादातर, हजारों); the rest is left to the model (Extra_Checks point 12).
_NUKTA_URDU = {"\u0958": "क", "\u0959": "ख", "\u095A": "ग",
               "\u095B": "ज", "\u095E": "फ"}
_NUKTA_ALWAYS = re.compile("[\u0958\u0959\u095A]|(?<=[कखग])\u093C")
_NUKTA_ZF = re.compile("[\u095B\u095E]|(?<=[जफ])\u093C")
_URDU_ZF = (
    "ज्यादा जरूर जरा जरिय जरिए जिंदा जिन्दा जिंदगी जिन्दगी चीज फरिश्त जोर "
    "जमीन जमान जमाने जमानत जब्त मजदूर जेवर गुजर गुजार रफ्तार फिक्र फिक्रमंद "
    "अंदाज आवाज इज्जत नजर नजदीक नजारा सजा मजा मजे मजेदार तेज फैसल फर्क "
    "साफ माफ तरफ जाहिर जिक्र जुबान जहर कमजोर बाजार हजार मिजाज सफर फायद "
    "फौरन फकीर फुरसत फुर्सत जुल्म जनाब दफा दफ्तर लफ्ज कागज मौजूद नाराज "
    "रोज अजीब लिहाज इजाजत जायज तकलीफ तारीफ शरीफ खिलाफ लिफाफ इंसाफ सिर्फ "
    "हफ्त सफेद जंजीर जख्म जनाजा जज्बा जज्बात जालिम जुर्म गिरफ्त फरमा "
    "फरमान फर्ज फितरत फिजूल फिलहाल फिर्का फौज बर्दाश्त मंजिल मंजूर मर्ज "
    "मरीज मिजाज मुफ्त मेज लजीज वजह वजन वाजिब हफ्ता हिफाजत होशियार "
    "अफसोस अफसर अजनबी आजाद आजादी आराम इंतजार इंतजाम खुदगर्ज गुजारिश "
    "जनाब तजुर्बा तमीज दरवाज परहेज पोशाक बेजार मजबूत मजबूर मजहब "
    "मजाक मजार राजी रिवाज लाजिम शुरुआत हाजिर हुजूर").split()
_WORD = re.compile("[\u0900-\u0963\u0966-\u097F\u200C\u200D]+")


def _urdu_zf_words(text):
    """(start, end) of each nukta ज़ / फ़ inside a listed Urdu word."""
    for w in _WORD.finditer(text):
        word = w.group(0)
        if not _NUKTA_ZF.search(word):
            continue
        plain = _NUKTA_ZF.sub(lambda m: _NUKTA_URDU.get(m.group(0), ""), word)
        if any(plain.startswith(stem) for stem in _URDU_ZF):
            for m in _NUKTA_ZF.finditer(word):
                yield w.start() + m.start(), w.start() + m.end(), m.group(0)


# Hindi words written wrong, and how the book writes them.
_HINDI_WORDS = [
    # सद्‌गुरु and अद्‌भुत with the halant showing, not as a ligature.
    (re.compile("सद(?:्\u200D?)?गुरु"), "सद्\u200Cगुरु",
     "सद्\u200Cगुरु is written with the halant showing (सद्\u200Cगुरु, not सद्गुरु)"),
    (re.compile("अद(?:्\u200D?)?भुत"), "अद्\u200Cभुत",
     "अद्\u200Cभुत is written with the halant showing (अद्\u200Cभुत, not अद्भुत)"),
    (re.compile("जरुर(?=[ीत])"), "जरूर", "जरूरी / जरूरत, not जरुरी / जरुरत"),
    # Chandrabindu: a nasal vowel at the end of a word, and the common
    # words with one inside. Not शांत, संबंध, हैं, में — those are right.
    (re.compile(f"ां{_END}"), "ाँ", "chandrabindu missing (ाँ)"),
    (re.compile(f"ूं{_END}"), "ूँ", "chandrabindu missing (ूँ)"),
    (re.compile(f"ऊं{_END}"), "ऊँ", "chandrabindu missing (ऊँ)"),
]
# Common words with a chandrabindu inside them, exactly.
_HINDI_CHANDRA = {"आंख": "आँख", "गांव": "गाँव", "पांच": "पाँच",
                  "पांव": "पाँव", "सांस(?![ा्])": "साँस", "सांप": "साँप",
                  "चांद": "चाँद", "दांत": "दाँत", "बांध": "बाँध",
                  "कांप": "काँप", "झांक": "झाँक", "मुंह": "मुँह",
                  "पहुंच": "पहुँच", "ऊंच": "ऊँच"}


class _Hit:
    def __init__(self, s, e, g):
        self._s, self._e, self._g = s, e, g

    def span(self):
        return self._s, self._e

    def group(self, _=0):
        return self._g


class _UrduZF:
    """The listed-word nukta rule, shaped like a compiled pattern."""
    def finditer(self, text):
        return (_Hit(*h) for h in _urdu_zf_words(text))


_URDU_ZF_HITS = _UrduZF()


def _rules(text, language):
    """[(compiled pattern, fix(text, i, match) -> str, issue)]"""
    out = [(_HYPHEN_RE, lambda t, i, m: "-",
            "no space before or after the hyphen")]
    for straight, o, c in (("'", "‘", "’"), ('"', "“", "”")):
        q = _quote_style(text, straight, o, c)
        if q:
            pat, f = q
            out.append((pat, lambda t, i, m, f=f: f(t, i),
                        "one kind of inverted comma on the page"))
    if language == "Hindi":
        out.append((_NUKTA_ALWAYS,
                    lambda t, i, m: _NUKTA_URDU.get(m.group(0), ""),
                    "nukta removed from an Urdu word"))
        out.append((_URDU_ZF_HITS,
                    lambda t, i, m: _NUKTA_URDU.get(m.group(0), ""),
                    "nukta removed from an Urdu word"))
        for pat, repl, issue in _HINDI_WORDS:
            out.append((pat, lambda t, i, m, r=repl: r, issue))
        for wrong, right in _HINDI_CHANDRA.items():
            # सांस(?![ा्]): not सांसारिक, सांस्कृतिक — those are right.
            out.append((re.compile("(?<![" + _DEV + "])" + wrong),
                        lambda t, i, m, r=right: r,
                        "chandrabindu missing"))
    return out


# Languages whose list has the mechanical rules. Telugu's list is the
# speaker labels only; Tamil has no list yet.
LANGUAGES = {"Hindi", "Kannada"}


def _edits(text, language):
    """[(start, end, replacement, issue)] for every rule match, the
    earlier rule winning where two overlap."""
    if language not in LANGUAGES:
        return []
    got = []
    for pat, f, issue in _rules(text, language):
        for m in pat.finditer(text):
            s, e = m.span()
            if any(s < b and a < e for a, b, _, _ in got):
                continue
            got.append((s, e, f(text, s, m), issue))
    return sorted(got)


def _apply(text, edits):
    for s, e, r, _ in sorted(edits, reverse=True):
        text = text[:s] + r + text[e:]
    return text


def fix(text, language):
    """`text` with every house-style rule for `language` applied."""
    if not text:
        return text
    return _apply(text, _edits(text, language))


def problems(text, language):
    """One item per word (or run of words) a rule changes: (start, end,
    fixed text, issue). The span is widened to whole words so the reviewer
    sees the word, and hits that touch the same word are one item naming
    every rule that hit it."""
    edits = _edits(text, language)
    items = []                         # [start, end, [issues], [edits]]
    for ed in edits:
        s, e = ed[0], ed[1]
        while s > 0 and not text[s - 1].isspace():
            s -= 1
        while e < len(text) and not text[e].isspace():
            e += 1
        if items and s <= items[-1][1]:
            it = items[-1]
            it[1] = max(it[1], e)
            if ed[3] not in it[2]:
                it[2].append(ed[3])
            it[3].append(ed)
        else:
            items.append([s, e, [ed[3]], [ed]])
    out = []
    for s, e, issues, eds in items:
        old = text[s:e]
        # The page's own edits, moved into the word: a quote mark's fix
        # depends on the whole page, so it is not worked out again here.
        new = _apply(old, [(a - s, b - s, r, i) for a, b, r, i in eds])
        if new != old:
            out.append((s, e, new, "House style: " + "; ".join(issues)))
    return out
