# Book proofing prompts: what to add

> **Applied 31 Oct 2026** to both prompt files, with the section 5 defaults. The originals are in `Backup\` as `*.bak_reviewadds`. In `Get_Suggestions_Prompt_Batch.txt`, the "register" line under SOME NOTES DO NOT NAME THE PROBLEM was also brought in line with the new register rule. The copies in `Proofing with AI_Simple\` and the TTS Coworker root still have the old text.
>
> **Later the same day: a firm మీరు rule.** Sadhguru's "you" is మీరు; the AI must never flag a మీరు form or change one into నువ్వు. This is now stated in type 15, type 5, WHAT NOT TO FLAG and LANGUAGE (both prompts). The కాస్త తమాయించుకో example became "emotionally blackmail her", and verbs are now quoted in the neutral -అడం form (ఆశలు పెట్టుకోవడం, not ఆశలు పెట్టుకో) so that none reads as a నువ్వు command. The state before this is in `Backup\` as `*.bak_meeru`. The text in section 3 below is the earlier wording.

Worked out from your review work in:
- Chapter 2, pages 1–267 (5 progress files)
- Chapter 4, pages 1–50
- Chapter 4\Ramakrishna, pages 1–400 (4 progress files)

The additions are for the two prompts the Book proofing tab uses:
- `Detection_and_Suggestions_Prompt_Batch.txt`: the AI run.
- `Get_Suggestions_Prompt_Batch.txt`: the versions for hand marks.

Coverage:
- **Read in full:** every hand mark, every direct edit, and every AI correction you edited, reverted or replaced with V2/V3.
- **Only counted:** the ~1,700 AI corrections you kept as Version 1.

---

## 1. What your edits show

| | Chapter 2 | Chapter 4 pp 1–50 | Ramakrishna (Ch 4 pp 1–400) |
|---|---|---|---|
| Pages | 267 | 50 | 377 |
| AI corrections | 759 | 159 | 1,247 |
| – kept Version 1 | 645 (85%) | 135 (85%) | 937 (75%) |
| – picked V2 / V3 | 29 | 3 | 131 |
| – kept, then edited | 53 | 17 | 120 |
| – reverted to the original | 32 | 4 | 59 |
| Hand marks | 521 | 69 | 0 |
| Direct edits (outside any correction) | 572 | 87 | 12 |

- **Your hand marks are almost all word choice.**
  - 503 of 590 used Right word; 86 used Real Meaning.
  - 91% of the Right word marks are 1–3 words, and 283 are a single word.
- **The AI flags sentences, not words.** The corrections you keep are mostly meaning shifts, omissions, too-literal sentences and bracketed English. Only about 1 in 14 is about a word.
  - A typical Chapter 2 page gets about 3 AI corrections. You then hand-mark about 2 more words and type about 2 more fixes yourself.
- **When the AI does flag, it is usually right.** You kept Version 1 on 85% of its corrections and reverted only 4%.
- **The biggest single cause of hand work: the AI doesn't know this book's terms.** It sees one page at a time. Your edits settled the terms very consistently (Chapter 2 + Chapter 4 pp 1–50, occurrences across all pages):

| Term | in the translation | in your final text |
|---|---|---|
| సాన్నిధ్యం (presence) | 5 | 35 |
| &nbsp;&nbsp;సన్నిధి | 34 | 11 |
| స్వీకారభావం (openness) | 0 | 15 |
| &nbsp;&nbsp;సుముఖ- | 32 | 17 |
| జీవం (life itself) | 36 | 65 |
| తీక్షణత (intensity) | 0 | 7 |
| కరుడుగట్టు (rigid) | 0 | 6 |
| నిబద్ధత (integrity) | 2 | 6 |
| &nbsp;&nbsp;చిత్తశుద్ధి | 8 | 1 |
| జ్ఞాని (the One Who Knows) | 3 | 7 |
| &nbsp;&nbsp;'తెలిసిన వారి' | 4 | 0 |
| మమేకం | 21 | 7 |
| తర్కబుద్ధి (intellect) | 0 | 4 |

- **The Ramakrishna folder reads like a different reviewer.**
  - It has no hand marks, and picks V2/V3 three times as often.
  - It removes every English gloss in brackets.
  - It replaced సంభావ్యత (48 → 19 uses), where you keep it (30 → 35).
  - Where the two disagree, this proposal follows your Chapter 2 / Chapter 4 choices, and section 5 lists each conflict.

## 2. The changes, by how much hand work they would save

| # | Change | Prompt | Edits it covers |
|---|---|---|---|
| 1 | A glossary of this book's terms | both | ~190 |
| 2 | One-word items are valid, plus a word-by-word sense check | AI run | ~180 |
| 3 | Rewrite how Version 1 is made | both | ~150 versions you edited or passed over |
| 4 | A "what not to flag" list | AI run | ~95 reverts |
| 5 | Fix the register rule | both | ~60 |
| 6 | Smaller detection items | AI run | ~300 together (see below) |

Item 6 breaks down as:

| Smaller item | Edits |
|---|---|
| Additions and added emphasis | 66 |
| Images and idioms | 60 |
| English grammar words carried over | 57 |
| Small omissions | 50 |
| Lists and connectives | 30 |
| Mood | 29 |
| Quotations | 20 |
| Respect forms | 14 |

Two existing rules work against what you do. Changes 1, 3 and 5 fix them:
- **"Avoid … Sanskritised words (Grandhika)".** This pushes the AI away from the terms you chose: సాన్నిధ్యం, తీక్షణత, సంభావ్యత, తాదాత్మ్యం.
- **"Version 1 – closest to the English".** The AI reads this as "closest to the English wording". It then calques English idioms and English word order, and makes changes outside the problem it named.

---

## 3. Paste-ready text: `Detection_and_Suggestions_Prompt_Batch.txt`

### 3.1 After the "Hold a high bar" paragraph (line 6), add

```
A single word is a valid item. On a fluent page most of what an editor changes is one word: a word in the wrong sense, a word that is not this book's term (see THIS BOOK'S TERMS), a word weaker or stronger than the English, or a vague stand-in for a specific English word. These are errors, not preferences - flag each one on its own, as a one- or two-word item, without widening it to the sentence.
What IS a mere preference: swapping a correct word for a near-synonym only because it is closer to the English or has a slightly different shade. Flag a word only when you can say what a Telugu reader would misread, find odd, or miss in it here.
```

### 3.2 New section, just before "Detection:" (also goes into the second prompt)

```
THIS BOOK'S TERMS
Sadhguru uses some ordinary English words as fixed terms. This book has settled one Telugu rendering for each of them, listed below. Treat them as terms even where they look like everyday words.
- In detection, flag any other rendering of these English words, even when it is good Telugu. Never flag these renderings as formal, Sanskritised or technical.
- In every suggestion, use exactly these renderings.
- When the passage sets two English words against each other (involvement vs identification, project vs invest, react vs respond, personality vs presence), they must never share one Telugu word.

presence (as a quality: "the less personality, the more presence") - సాన్నిధ్యం. ఉనికి only for existing or being there.
life itself, aliveness ("a dimension of life", "life and death") - జీవం / జీవం తాలూకూ; "your being" - మీ జీవం. జీవితం only for a person's life or lifetime.
possibility (what a Guru, life or a human being is or opens up) - సంభావ్యత. A chance, "there is a possibility that…", an opportunity - అవకాశం.
openness, open, receptive (to Grace, to the Guru) - స్వీకారభావం / స్వీకారభావన. "available" to Grace - అందుబాటులో.
involvement, involve - నిమగ్నత, నిమగ్నమవు. Not మమేకం.
identification, identified with - తాదాత్మ్యం
awareness - ఎరుక
intensity, intense - తీక్షణత, తీక్షణమైన
passion - అభిరుచి
integrity - నిబద్ధత
intellect - తర్కబుద్ధి / విచక్షణా బుద్ధి. intelligence - మేధస్సు.
the One Who Knows - జ్ఞాని
dimension - పార్శ్వం, never పరిమాణం. arena - తలం.
Master, Masters (meaning Gurus) - గురువు, గురువులు, not మాస్టర్
live Guru - ప్రత్యక్ష గురువు
the elements - పంచభూతాలు
rigid, concretize (energies, a person) - కరుడుగట్టు
reverberation - ప్రకంపన
project (onto something) - ఆపాదించు. invest (energy, life) - జోడించు / వెచ్చించు.
sincere, sincerity - నిజాయితీ
expectation - ఆశ / అపేక్ష, never అంచనా. expect - ఆశలు పెట్టుకో. aspire - ఆకాంక్షించు.
privilege - భాగ్యం / అదృష్టం (opportunity is అవకాశం)
manageable / unmanageable (madness) - అదుపులో ఉండే / అదుపుతప్పిన
authoritarian - ఆధిపత్య ధోరణి
corner (someone) - ఇరుకున పెట్టు
benevolence - దాతృత్వం
flux - నిరంతర మార్పు
combination (of energies, things) - మిశ్రమం
austerity - కఠోర నియమాలు / నియమనిష్టలు, not కృచ్ఛ్రసాధన
react (as against respond) - రియాక్ట్ అవ్వు. ప్రతిస్పందించు means respond, which Sadhguru contrasts with reacting.
```

### 3.3 Additions to the detection types

**Type 3: add at the end**
```
Watch especially for these Telugu stand-ins. Each often sits where the English says something more specific - read the English and check:
- స్థితి - the English may say arena, dimension, level, situation or space, or have no "state" at all ("beyond the physical" is భౌతికమైన దానికి, not భౌతిక స్థితికి; "from one dimension to the other" is ఒక పార్శ్వం నుండి మరొక పార్శ్వానికి)
- సాధ్యపడు - work, open up, happen ("it did not work here" is వర్కవుట్ కాలేదు; "it will not open up" is తెరుచుకోదు)
- శక్తి - empowerment (సాధికారత), faculties
- జోక్యం - intrude (చొరబడు)
- మమేకం - involve (నిమగ్నమవు), identify (తాదాత్మ్యం) and relate are three different things
- an everyday word for one of Sadhguru's concepts: "knowing will never happen through a book" is about realisation - సాక్షాత్కారం, not తెలుసుకోవడం; "How can you transform yourself" - పరివర్తన చెందగలరు, not మారగలరు
```

**Type 5: replace the whole item**

The old దృగ్విషయం example goes. Its "plain" replacement (అద్భుతమైన విషయం) changes the meaning, and it was teaching the AI that plain beats exact.
```
5. Register
This is a book, and its register follows what is being said.
- Teaching passages: clear, modern written Telugu. Flag rare, learned words a general reader would stumble on (కృచ్ఛ్రసాధన, ప్రక్షేపణం, ఆత్మాశ్రయ, ఉన్మాద స్థితి) in favour of a word in common use. Sadhguru's concept terms - THIS BOOK'S TERMS, and words like పరివర్తన, సాక్షాత్కారం, తాదాత్మ్యం - are not Grandhika even though they come from Sanskrit. Never flag them as formal, and never trade them for a plainer word that loses the concept.
- Stories, jokes, quoted dialogue, the questioner's words and Sadhguru's asides: everyday Telugu. A formal word or a long formal paraphrase there is the error. "Sarah, Sarah, get a hold of yourself" is "కాస్త తమాయించుకో", not "నిన్ను నువ్వు నిగ్రహించుకో". Where Telugu speakers use the English word itself - జోక్, ప్రోగ్రామ్, క్లాసు, బిజీ, మిస్ అవ్వడం, మూడ్, హ్యాండిల్, వర్కవుట్ - a stiff Telugu coinage (హాస్యాస్పదం, కార్యక్రమం) is the error.
- Never crude or slangy, even in a story.
- Do not bring in an English word for a spiritual or abstract idea, unless Telugu has no word that keeps a distinction Sadhguru is making (react, as against respond).
```

**Type 6: add**
```
Images work in both directions.
- Keep Sadhguru's image when Telugu can carry it: "can you ride it a little bit?" - "దానిపై కాస్త స్వారీ చేయగలరా?"; "if your doors are open" - "మీ ద్వారాలు తెరిచి ఉంటే"; "I am poking at them" - "గిల్లుతూనే"; "throw yourself into the river" - "విసిరేసుకుంటే".
- When the literal image is foreign in Telugu, use the Telugu idiom: "the carrot and stick" - "సామదండాలు"; "resented this" - "జీర్ణించుకోలేకపోయేవారు"; "I am taking you for a ride" - "ఏమారుస్తున్నాను".
- Flag either kind when it has been flattened into a plain verb or replaced by an interpretation: "మీ అంతరంగం సిద్ధంగా ఉంటే" for "if your doors are open", "విమర్శిస్తూనే" for "poking", "సాధ్యపడదు" for "it will not open up".
```

**Type 7: add**
```
More of the same kind - a word with several senses, given in its first dictionary sense. This is as common with abstract nouns, adjectives and verbs as with objects:
- "a hundred times more sterile" - పరిశుద్ధంగా (germ-free), not పవిత్రంగా (holy)
- "total calm" - ప్రశాంతత, not నిశ్శబ్దం
- "used in many different, very loose ways" - బాధ్యతారహితంగా, not అస్పష్టంగా
- "he could not refuse the offer" (to take his place) - ఆ సహాయాన్ని, not ఆ ప్రతిపాదనను
- "the reminder comes" - గుర్తు, not హెచ్చరిక
- "what does it cost to get married?" - మూల్యం, not ఖర్చు
- "a bear trap" - ఉచ్చు, not బోను
One word in the wrong sense is enough to flag.
```

**Type 8: add**
```
Other everyday verbs where English uses one word and Telugu chooses:
- requested, pleaded, prayed - in a story, అన్నాడు, వేడుకున్నాడు, not అభ్యర్థించాడు, ప్రార్థించాడు
- answer - బదులిచ్చు, not స్పందించు
- know a person - పరిచయం ఉండటం; "you will not get it" - బోధపడదు
- feel (Sadhguru, an energy) - అనుభూతి చెందు, not అనుభవించు or స్పర్శించు
- look into, look at, go through - పరిశీలించు
- remember (your being) - గుర్తుచేసుకో, not గుర్తుంచుకో
- struggling with - సతమతమవు, not పోరాడు
Quotations: the verb that reports a quotation comes after it, with అని - "…" అని అన్నాడు, "…" అని బతిమాలాడు. Flag "X ఇలా అన్నాడు, "…"" and a quotation left with no verb after it. The verb that closes a quotation or an అని-clause is a form of అను (అన్నాడు, అంటూ, అని అంటారు), not చెప్పు. "When we say X" is "X అన్నప్పుడు".
```

**Type 9: add**
```
Other English shapes that read as translation:
- "There are some X who…" - కొందరు X ఉంటారు, వారు…
- "He knows that…", "Modern physics says that…" - the knower or sayer first, and the verb of knowing or saying once, at the end.
- an English abstract noun or -ly adverb that Telugu says with a verb: "a helpless dependence" - నిస్సహాయంగా ఆధారపడటం.
- an English ellipsis left incomplete: "Shiva can contain it, not you" - "…మీరు అలా చేయలేరు".
- "moment to moment" - క్షణం క్షణం, not క్షణం నుండి క్షణానికి.
- a list whose last item the English joins with "and": write the join - ఇంకా, అలాగే, or -ఊ … -ఊ for a pair (జ్ఞాపకశక్తి, ఊహాశక్తుల - జ్ఞాపకశక్తి ఇంకా ఊహాశక్తుల). A bare comma reads broken. "again" meaning "also" is అలాగే, not మళ్ళీ.
```

**New types 14–16: add at the end of Pass 1**
```
14. English grammar words carried into the Telugu
Telugu leaves out what English grammar has to say. Flag these; the fix is to delete:
- a subject pronoun or possessive (మీరు, వారు, అతను, మనం, మీ, తన) that the verb ending or the context already gives
- ఒక for English "a" (ఒక సన్యాసి దాదాపు ఎప్పుడూ ఆకలితోనే ఉంటాడు - సన్యాసి దాదాపు ఎప్పుడూ…)
- ఆ / ఈ for "the" / "this" where nothing is being pointed at
- అక్కడ / ఇక్కడ from "there is" / "here is" - "There is no 'you' right now" is ప్రస్తుతం "మీరు" అనేదే లేదు, not ప్రస్తుతం అక్కడ "మీరు" అనేదే లేదు
- a reflexive written twice: మిమ్మల్ని మీరు together with a -కొను verb
- spoken fillers translated word for word: "just", "simply", "you know", "then" after an if-clause, "I think" in a remark. Keep కేవలం only where "just" means "merely".

15. Respect and person
- The reader, and the general "you", is always మీరు - never నువ్వు or నీ. A story's own dialogue may keep నువ్వు between its characters.
- An ordinary seeker or person in the third person is అతను or ఆమె; Gurus, saints and Sadhguru are ఆయన.
- Goddesses take దేవి (పార్వతీ దేవి). A woman who asks a question is సాధకురాలు, not సాధకుడు.

16. Spelling
A misspelt word, a word split by a space (చూసి నప్పుడు), or two words run together is its own item, with the corrected spelling as every version. Never bundle a spelling fix into a wording change - if the wording is rejected, the spelling fix is lost with it. An English gloss in brackets never separates a word from its suffix.
```

**Pass 2: add after "…check the Telugu against it, sentence by sentence."**
```
Within each sentence, go through the English content words one by one - nouns, verbs, adjectives, adverbs. Decide which sense each word has in THIS sentence, and check that the Telugu word carries that sense and is this book's term. Do this for the sentences that read well too: a single wrong word inside a fluent sentence is the most common thing the reviewer has to fix by hand.
```

**Type 10: add**
```
The small words are not only these five. Also: yet, all, also, nor, anyway, at all, anymore, even if, altogether, other, every bit, a single, any number of, certain (meaning "a specific"), could, most probably; the speaker's own frame ("I would say"); an adjective on a key noun ("compulsive gambling" - అదుపులేని జూదం); and steps of degree ("pretty strong" is కాస్త ఎక్కువ బలంగానే, not చాలా శక్తివంతంగా).
But do not flag as omitted a word whose sense the Telugu already carries, or an emphatic doublet that adds nothing in Telugu ("the cells… at the cellular level", "Something, somehow").
```

**Type 11: add**
```
This includes small colourings that read as harmless fluency:
- an intensifier or adjective the English does not have - ఎంతో, నిజమైన, అసలైన, నిరంతర, నిత్య, పూర్తి, ప్రత్యేకమైన, మరింత, తగినంత, కేవలం ("It is not love" is అది ప్రేమ కాదు, not అది నిజమైన ప్రేమ కాదు)
- an emphatic -ఏ (కోసమే, నాతోనే, శరీరంలోనే) where the English has no "only", "itself" or "very"
- "tries to" added to a plain verb ("it will run away" is పారిపోతుంది, not పారిపోవడానికి ప్రయత్నిస్తుంది)
- two renderings of one English word joined by లేదా
- స్థితి, అనుభూతి or another interpreting word added to a plain English noun
- a word that interprets the English ("many things may come up" is ఎన్నో విషయాలు ఎదురుకావచ్చు, not ఎన్నో అడ్డంకులు రావచ్చు)
```

**Type 12: add**
```
Check mood as well as tense: "can be" (కాగలదు) is not "is"; "don't" (అందుకోరు) is not "can't" (అందుకోలేరు); "are" is not "may be" (కావచ్చు); "the way is there" (ఉంది) is not "will be seen" (కనిపిస్తుంది); "by now" (ఈపాటికి) is not "at least now" (ఇప్పటికైనా).
Check force as well as sense - the Telugu word must be as blunt or as mild as the English: "slaughter" వధించు, not బలి ఇవ్వు; "it invades you" ఆక్రమించేస్తుంది, not ఆవరించేస్తుంది; "nonsense" చెత్త; "starve yourself" మాడ్చుకో. But "some people will run away" (from the ashram) వెళ్లిపోవచ్చు, not పారిపోవచ్చు; "becoming corrupt" దారి తప్పుతున్నాడని, not భ్రష్టుడైపోతున్నాడని.
```

**Type 13: add**
```
Terms are not checked within this page only. Use THIS BOOK'S TERMS, and check a recurring English word even when the page renders it the same way every time - a consistent wrong word is still wrong ("involve" given as మమేకం ten times on one page). Two English words set against each other on the page must not share one Telugu word.
```

### 3.4 New block after the Pass 3 paragraph, before "All passes go into ONE list"

```
WHAT NOT TO FLAG
The reviewer put the original back for these, so do not report them:
- A free or idiomatic rendering that makes the same point as the English in its own way - a Telugu idiom, a different image, a word that fits the context, a small link to the next sentence. "more easily said than done" as "కానీ ఇది చెప్పినంత సులభం కాదు" is right; do not turn it back into the English wording. Before calling something a meaning shift, ask whether a Telugu reader would come away with a different idea than an English reader. If not, leave it, even when the words differ.
- A correct word swapped for a near-synonym only because it is closer to the English or has a slightly different shade. "Fits better", "more natural" or "slightly" is not a reason.
- THIS BOOK'S TERMS and other settled renderings (ప్రత్యక్ష గురువు, పంచభూతాలు, జనన మరణ చక్రాలు). Never flag them as formal, technical or Sanskritised.
- An English word in brackets after a Telugu term - కృప (Grace), ప్రతిష్ఠాపన (consecration), లోలకం (pendulum). It is a deliberate gloss. Remove one only when it repeats a transliteration (మాస్టర్ (Master)) or the same gloss already appeared earlier on the page.
- Two English sentences given as one Telugu sentence, or one as two, when nothing is lost; or an order that is one of several natural Telugu orders.
- Spacing, paragraph breaks and stray quote marks on their own.
- Anything whose Version 1 would read the same as the original.
```

### 3.5 The suggestions part

**THE THREE VERSIONS: replace the Version 1 paragraph**
```
Version 1 - the smallest change.
Copy the identified text word for word and change only the words that carry the problem in your description. Every other word, ending, connective, spelling and bracket, and the word order, stays as it is - even a word you would not have chosen yourself. Do not swap a correct word for a synonym, make a word plainer, replace a loan word, add or drop యొక్క, or reorder, unless that is the problem. If your description names a replacement, use exactly that replacement.
"Smallest" is not "closest to the English wording". The words Version 1 brings in must be the ones a Telugu writer uses for this sense here: the Telugu idiom for an English idiom, the verb that fits the context, this book's term. Never a word-for-word rendering of the English word, a transliteration of it, or its word order or sentence breaks. Where the problem is one of meaning (types 10 to 13), Version 1 restores the English meaning - in Telugu words.
Version 1 must still read as correct Telugu: if your change needs a neighbouring word to change with it (agreement, a case ending), change that too.
```

**Replace the Version 3 paragraph, and add the one-word paragraph after it**

When you picked V3, it was almost always because it found the Telugu idiom. Splitting into short sentences won 2 times out of 50 Real Meaning marks.
```
Version 3 - the freest idiomatic Telugu.
The turn of phrase a native Telugu writer would reach for - often a Telugu idiom. Restructure as needed; split a long sentence into shorter ones only when that is what makes it clear. It may move furthest from the English structure - but never from its meaning, and it must not add anything that is not in the English.

For an item of one or two words, all three versions are one or two words, and each is a different choice: Version 1 the word a Telugu writer uses for this sense, Version 2 a natural alternative, Version 3 the Telugu idiom if there is one.
```

**LANGUAGE: replace the first three bullets ("Avoid needlessly formal…", "Avoid slang…", "Use an English loan word only…") with**
```
- Use THIS BOOK'S TERMS exactly.
- Teaching passages: clear written Telugu, without rare learned words a general reader would stumble on. Sadhguru's concept terms are not such words.
- Stories, jokes, dialogue and asides: everyday Telugu, with the English words Telugu speakers actually use there (జోక్, ప్రోగ్రామ్, బిజీ, మిస్ అవ్వడం). Never crude or slangy.
- Add nothing the English does not have: no intensifier, no emphatic -ఏ, no కూడా / కలిసి / ఇక / మళ్ళీ, no adjective, and do not name what a pronoun refers to unless the English names it.
- Keep every small qualifier of the English in all three versions - anymore (ఇక), also (కూడా), even if (…అయినా సరే), altogether (పూర్తిగా), like (లాంటిది). Versions 2 and 3 must not lose them while rewriting.
- Each version is one finished reading: no "X/Y", no "X లేదా Y" for one English word, no second word in brackets.
```
Keep the remaining three bullets as they are: the dictionary word, near-synonyms, and Telugu sentence structure.

**WHAT EACH VERSION MUST COVER: add after "Do not reach beyond it either…"**

Five of these joins are wrong in the book now (section 6).
```
Read the words just before and just after the identified text, and make the version join them: it must not repeat a word that already stands outside it (a version that begins with అది right after "…అది" makes "అది అది"), and its last word must take the form the next word needs.
```

**Replace "Before you answer, read each version back…"**
```
Before you answer, read each version back against the identified text it replaces and against the English. Check that everything in the original is still accounted for - carried across, or deliberately changed as part of the fix; that nothing has been added that is not in the English; and that every small qualifier of the English is still there. Then compare Version 1 with the original word by word and undo every change you cannot tie to your description. Spell-check every version.
```

---

## 4. Paste-ready text: `Get_Suggestions_Prompt_Batch.txt`

1. **Before "READING THE REVIEWER'S NOTE":** add the same THIS BOOK'S TERMS block (3.2).
2. **In READING THE REVIEWER'S NOTE:** replace the two bullets "the sentence is too literal…" and "a word is correct but flat…" with:
```
  - "the word used seems not contextually rich…" (Right word) - the word does not say exactly what is meant here. The fix may be a more specific word, the word in the right sense, this book's term, the Telugu idiom, Sadhguru's own image put back, or an English word Telugu speakers use - and sometimes a plainer or more literal word. These marks are usually one or two words: return one or two words.
  - "Setence seem very literal…" (Real Meaning) - the sentence carries the words but not the intention. Fix the intention and keep the sentence's structure. Do not replace Sadhguru's own image or plain words with your interpretation of them, and do not split the sentence unless the meaning needs it.

If the marked word is already this book's term and the only problem is that a reader may not recognise it, Version 1 may keep the word and add the English in brackets: వ్యక్తిత్వం (personality).
```
3. **The same Version 1, Version 3 and one-word paragraphs** as 3.5. In Version 1, write "where the note is about meaning" instead of "(types 10 to 13)".
4. **LANGUAGE:** the same bullets as 3.5.
5. **WHAT EACH VERSION MUST COVER:** the same "read the words just before and after" line.
6. **"Before you answer":** the same replacement.

---

## 5. Decisions for you: where your edits pull both ways

| # | Question | What the edits show | Proposal assumes |
|---|---|---|---|
| 1 | English glosses in brackets | Chapter 2 detail is below the table. Ramakrishna: removed every gloss (0 of 25 removals reverted). | Keep glosses; add one on the first use of a key term whose Telugu only approximates it |
| 2 | possibility | You: సంభావ్యత (30 → 35). Ramakrishna: replaced it (48 → 19). | సంభావ్యత |
| 3 | identify with | Both use తాదాత్మ్యం (Ch 2: 2 → 7; Ramakrishna: 4 → 24). You also typed గుర్తింపు ఏర్పరచుకో 6 times ("So, identify yourself with everything"). | తాదాత్మ్యం only. Or keep both, noun vs instruction? |
| 4 | mystic | మార్మికుడు (Ch 2 p202; Ramakrishna p321) vs మర్మజ్ఞుడు (kept twice when the AI tried to change it) | Not in the glossary yet; pick one |
| 5 | relate (to) | సత్సంబంధం కలిగి ఉండటం (direct edits, 4) vs మమేకం (hand marks, 2) | Not in the glossary yet |
| 6 | receptivity | Four renderings in Chapter 2: గ్రహణశీలత, గ్రహణశక్తి, స్వీకరణా సామర్థ్యం, స్వీకరించే స్థితిలో. openness is స్వీకారభావం. | Not in the glossary; same as openness? |
| 7 | vulnerable | సులభంగా హానికి గురయ్యే / రక్షణ లేని, and ప్రభావానికి లోనయ్యే, both chosen in different places | Not in the glossary yet |
| 8 | react | You: రియాక్ట్ అవ్వు, for react vs respond. Ramakrishna accepted removing రియాక్ట్ / మేనేజ్ / డిస్టర్బ్. | In the glossary, as your choice |
| 9 | Additions that only make the meaning explicit | You strip added words (స్థితి, intensifiers, -ఏ), but accepted a few versions that add a specific: చేసే పనుల, అప్రయత్నంగా. Ramakrishna accepts more. | "Add nothing", strictly |
| 10 | Ramakrishna's own habits | అను after quotations; literary words (అచ్చెరువొందు, మిన్నకుండు); freer V2/V3 | Only అను is included; it agrees with the prompt's existing అంటారు rule |

Your Chapter 2 bracket detail (row 1):
- **Kept:** you put back కృప (Grace) and the like when the AI removed them (7 of 20 removals reverted).
- **Added:** (personality) ×8, (Projecting), (Expectations), (fluid), (Individuality).
- **Removed:** (clarity), (Rigid), and glosses that just repeat a transliteration, like మాస్టర్ (Master).

---

## 6. Slips in the finished pages

Each of these is in the final text now and was not in the translation.

| Page | Now reads | Should read |
|---|---|---|
| Ch 2 p80 | …కొండ పైన నాటారు. | నాటరు. The English is "You don't … plant it on top of the mountain"; the negation was reversed. |
| Ch 2 p154 | మాండలిక కథలు | మాండలిక means "dialect". For "dialectical stories", use the translation's తార్కిక or సంవాద రూపంలోని. |
| Ch 2 p105 | జన్మజన్మల కర్మ మిమ్మల్ని మీ ముందుకొస్తాయి | …కర్మ మీ ముందుకొస్తాయి (EN "…confront you") |
| Ch 2 p108 | కొంత శక్తిని శక్తిని జోడించడం | కొంత శక్తిని జోడించడం |
| Ch 2 p182 | నెమ్మదిగా కరిగించి, …‘నేను’ అనే భావాన్ని క్రమంగా కరిగించి | one కరిగించి |
| Ch 2 p72 | అది అది తయారు; శ్రద్ద | అది తయారు; శ్రద్ధ |
| Ch 2 p86 | సాధకుడు: సద్గురు, సాధకుడు: సద్గురు, | once |
| Ch 2 p27 | అనుతమించాలి | అనుమతించాలి |
| Ch 2 p180 | మేదస్సే | మేధస్సే |
| Ch 2 p200 | కుర్చుని | కూర్చుని |
| Ch 2 p263 | మారో వైపు | మరో వైపు |
| Ch 2 p68 | అత్యంతహా | typo; check the intended word |
| Ch 2 p4 | "దయచేసి, పద వెళ్దాంపద" | పద, వెళ్దాం పద |
| Ch 2 p99, p100, p101 | బుద్ది | బుద్ధి |
| Ch 2 p190 | మాలచబడేలా | మలచబడేలా |
| Ch 2 p199 | కట్టివేయబనట్టు | కట్టివేయబడినట్టు |
| Ch 2 p205 | వక్రీకరించుబడ్డ | వక్రీకరించబడ్డ |
| Ch 2 p252 | స్తబ్ధుగా | స్తబ్దుగా |
| Ch 2 p94, p188; Ch 4 p15 | a space before a full stop | no space |
| Ch 4 p34 | పార్స్వానికిచేరుస్తుంది; నిర్దారనలకు | పార్శ్వానికి చేరుస్తుంది; నిర్ధారణలకు |
| Ramakrishna p359 | ఆ రోజు, ఆ రోజు, | ఆ రోజు, |
| Ramakrishna p193 | ""ఓహ్, నేను ఇదివరకే చూశాను" | "ఓహ్, … |

The analyses also reported terms left mixed on a page. These were not checked one by one:
- తీవ్ర- left beside తీక్షణత: Ch 2 p66, p83, p91, p99, p214.
- చిత్తశుద్ధి in the sentence after the one you changed to నిబద్ధత: p80.
- మమేకం and గుర్తింపు on the same page: p141. p112 still has మమేకమైపోయారంటే.
- కలయిక on p34 beside మిశ్రమం on p35–36.

---

## 7. Two follow-ups worth considering

- **Test before switching over.** Run the new prompts on about 10 Chapter 2 pages you've already finished, starting from their original Telugu. Then count:
  - how many of your hand marks and direct edits the AI now catches;
  - how many of its new flags you would have reverted.

  That shows whether the additions work, and whether the prompt got too long.
- **Keep the glossary in its own file.** It will grow with every chapter. The server could read a `Book_Glossary.txt` from the app folder and add it to both prompts, so there's one place to edit.

---

## 8. Chapter 3: Chandramohan's review (added 31 Oct 2026)

Chapter 3 went through three stages: the translation, then Ramakrishna (who processed the AI suggestions), then Chandramohan (who proofed by hand). All 127 pages line up. Every one of Chandramohan's changes was read.

| What | Count |
|---|---|
| AI corrections Ramakrishna kept as Version 1 | 375. Chandramohan still changed 164 of them (44%). |
| AI flags Ramakrishna rejected | 47. Chandramohan changed 24 of them anyway, so the AI was right to flag those. |
| Changes on text the AI never flagged | about 2,490, around 20 a page. 1,103 of them are single words. |

### What was added to both prompts

Backups of the state before this: `Backup\*.bak_ch3`.

**Glossary**
- **Sense rules for existing terms:**
  - a sense rule for జీవం / జీవితం / ప్రాణం;
  - conscious → ఎరుకతో, and unconscious → అచేతనంగా / ఎరుకలేని స్థితిలో / ఎరుక లేకుండా, or తెలియకుండానే for "without knowing it" (your decision: ఎరుకలేని స్థితిలో is one of the accepted forms);
  - intensity by sense: తీక్షణ for a quality, తీవ్ర for physical effort, గాఢ for love or meditation;
  - the presence of an object or an ordinary person → ఉనికి;
  - a questioner addressing Sadhguru as "Master" → మాస్టర్ stays;
  - react, only where it is set against respond;
  - expect, in the sense of anticipate.
- **Your identification line:** extended, not replaced.
- **25 new terms:**
  - human beings మనిషి / మనుషులు, program ప్రోగ్రామ్, time కాలం
  - Prarabdha ప్రారబ్ధ కర్మ, work out karma కరిగించుకోవడం, accumulate పోగుచేసుకోవడం, karmic structure / body / substance
  - Ultimate పరమోన్నత, Liberation ముక్తి, tendencies ప్రవృత్తులు, compulsive నిర్బంధ, duty కర్తవ్యం
  - practice సాధన, yoga యోగా, mystic మార్మికుడు, the Devil సైతాను, and others

**Detection**
- **Phrases and stand-ins:**
  - English set phrases: "far from the truth", "the moment X", and "there is no way to X", which is not X-కు వేరే మార్గం లేదు;
  - రాశి used as a catch-all;
  - 11 more wrong-sense examples.
- **Verbs and structure:**
  - perception verbs: "you will see that…" → …అని మీకు తెలుస్తుంది;
  - passives that name a doer;
  - the మీకు form for states;
  - -కొను for actions done for oneself;
  - "X or Y" written the Telugu way.
- **Grammar words and respect:**
  - యొక్క;
  - generic "one" or "a person";
  - Sadhguru's "we" is మేము when it means Isha;
  - story characters take -ాడు verbs and no గారు.
- **Mechanical:**
  - grammar forms such as రాతి బుడగ, దానంతట అదే and నేను … కాను;
  - repeated sentences;
  - two problems make two items.

**What not to flag (narrowed)**
- A word in a different sense is not a "shade".
- A free rendering is protected; a literal English figure is not.
- Glosses after everyday words go; glosses after concepts stay.

**Suggestions**
- No words built from the parts of the English word.
- English names only for modern or technical things (ప్రోగ్రామ్, మైక్రోస్కోప్).
- Version 1 rebuilds a structure its description names.
- A sense check for every new word.
- No English phrase shapes, no explanations, no new యొక్క.

### Where Chandramohan and you differ: your choice was kept

| # | Point | You | Chandramohan | In the prompts now |
|---|---|---|---|---|
| 1 | open, openness | స్వీకారభావం (0 → 15) | సుముఖత ×18, including "open to the teachings" | your decision: openness సుముఖత / అంగీకార భావం; receptivity స్వీకరణా సామర్థ్యం / స్వీకార భావన |
| 2 | lists of nouns | you add ఇంకా (జ్ఞాపకశక్తి ఇంకా ఊహాశక్తుల) | shared ending (జ్ఞాపకశక్తి, ఊహాశక్తుల) ×8 | yours |
| 3 | మిమ్మల్ని మీరు with a -కొను verb | deleted 4 times | kept 36 of 38 | softened: flag only where the sentence stumbles |
| 4 | transform | పరివర్తన (once) | మార్పు ×3 | example removed; no rule either way |
| 5 | "your being" | మీ జీవం | మీ అంతరంగ ఉనికి (once) | yours |
| 6 | concretize | కరుడుగట్టడం (typed 6×) | బిగించు (once) | yours |
| 7 | mystic | మార్మికుడు | మార్మికుడు ×5 | added as మార్మికుడు; మర్మజ్ఞుడు no longer listed |
| 8 | Jesus | — | జీసస్ ×3 (the translation had ఏసు) | not added: decide |

### Slips in Chapter 3's final script

Each of these was checked in `…Chapter_03_The_Only_Bondage_Final Script.json`. The full sentences, before and after, for Chapters 2, 3 and 4 are in `Slip fixes - Chapters 2 and 3.txt`.

| Page | Now reads | Should read |
|---|---|---|
| p94 | …రోజంతా ఎందుకు పని చేస్తున్నారని | EN "working twenty hours a day": రోజుకు ఇరవై గంటలు |
| p121 | మీరు శరీరం నుండి దూరం జరిగితే, కాలాన్ని అధిగమిస్తారు | EN "you deceive time": కాలాన్ని మోసం చేస్తారు. The line just before says "You will not be deceiving time". |
| p1 | ప్రతి ప్రతి వ్యర్థ ప్రయత్నంతోనూ | ప్రతి వ్యర్థ ప్రయత్నంతోనూ |
| p17 | ఒక చిన్న పిల్లాడు చనిపోయారనుకుందాం | …చనిపోయాడనుకుందాం |
| p25 | శారీరక శారీరక వైకల్యం | శారీరక వైకల్యం |
| p26 | రికార్డ్ అవుతుంది,, | one comma |
| p28 | ఆనందం- - వీటితో | ఆనందం - వీటితో |
| p31 | క్క యోగి కాకుండా | a letter is missing, probably ఒక్క యోగి |
| p54 | కీటకాల కోసం- ఆహారం కోసం | stray dash |
| p61 | మేము మీకు మరో స్థాయికి తీసుకెళ్తాం | మేము మిమ్మల్ని… |
| p68 | ణికంగానైనా | క్షణికంగానైనా |
| p72 | అలవడుతాయనివిన్నాను | అలవడుతాయని విన్నాను |
| p79 | ““అంతం | “అంతం |
| p80 | ంచి పనులను | మంచి పనులను |
| p86 | తీక్షణతో | తీక్షణతతో |
| p102 | ఆ ఆ ఘట్టాన్నంతటినీ | ఆ ఘట్టాన్నంతటినీ |
| p108 | ఉంటుంది.. | one full stop |
| p109 | అదృశ్యమైపోతుంది . | no space before the full stop |
| p121 | ‘పార్శ్వం’. . | one full stop |
| p123 | …దొరకలేదు అని. | stray trailing అని |
| p125 | తవ్వడానికి సాధ్యం కాదు | తవ్వడం సాధ్యం కాదు |

**Prompt size:** the AI-run prompt is now about 56 KB, roughly three times its original 16 KB. That's well within what Gemini takes, but each page's call costs more. Section 7's test on finished pages is the way to check the longer prompt still flags what it should.

---

## 9. First run with the new prompts (Chapter 4, pages 51–67)

This compares the new run with the old prompts' run on the same 17 pages. The old run is kept as `…p51-100_Old.progress.json`.

| | Old prompts | New prompts |
|---|---|---|
| Flags | 55 (3.2 a page) | 96 (5.6 a page) |
| Typical span | 13 words | 4 words |
| Text in all versions | 16,285 characters | 11,902 characters |

- **59 flags only the new run made:**
  - about 25 book terms;
  - about 19 grammar or structure fixes;
  - about 15 meaning catches. On p63, "unlike physical wheels" had been translated as "like physical wheels".
- **19 old flags the new run lost.** About half of them are real problems:
  - p55, twice: "it should be me" read as a wish;
  - p67: "This is one reason" → అందుకే, with "always" dropped;
  - p62: "goes unexplored" → స్పృశించరు;
  - p56: an unfinished sentence;
  - p65: a case error;
  - p61, three times: ఇడ vs ఇడా.
- **Reverted by you:** 1 (p52, "pressure").

**Added after this run** (backup: `Backup\*.bak_sentence`):
- Word-level items come on top of the sentence-level checks, never instead of them.
- Pass 3 re-reads each sentence whole.
- Mood examples go in type 12 and in LANGUAGE (both prompts).
- "goes unexplored" and "predominate" go in type 7.
- Unfinished sentences and wrong case endings go in type 16.

**Still open:** ఇడ or ఇడా for the Ida nadi. The old run asked for ఇడా three times. Not added.

**Pages 72–78 with the tuned prompts:**
- 40 flags (5.7 a page), with a typical span of 4 words, the same as before tuning.
- Some long items merged two separate word fixes:
  - p75: ప్రజలు plus an added లోపలికి;
  - p78: ఈ భూమి మీద plus a dropped "just".
- On p75, "that first option is not a possibility" was wrongly "corrected" to సంభావ్యత.

**Added after this** (backup: `Backup\*.bak_split`):
- Two separate problems in one sentence stay two items unless they share words.
- In the glossary, "not a possibility" meaning it cannot be done is సాధ్యం కాదు, not సంభావ్యత కాదు.
