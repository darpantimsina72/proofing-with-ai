# Prompts — one folder per language

The app sends the AI a prompt from `Prompts/<Language>/`, where `<Language>`
is the language picked in the LANGUAGE panel at the top of the page
(Telugu, Tamil, Hindi, Kannada). Each folder holds the same seven files:

| File | Used by |
|---|---|
| `Detection_Prompt.txt` | Video tab — ✎ Detect |
| `Get_Suggestions_Prompt.txt` | Video tab — ✎ Get suggestions |
| `Detection_and_Suggestions_Prompt.txt` | Video tab — AI Proofing in one step |
| `Detection_and_Suggestions_Prompt_Batch.txt` | Book tab — AI Proofing in one step |
| `Get_Suggestions_Prompt_Batch.txt` | Book tab — ✎ Get suggestions |
| `Sync_With_Final_English_Prompt_Batch.txt` | Book tab — Corrections to sync with new version |
| `Custom_Text_Translation_Prompt.txt` | Video tab — Translate |

Edit the file in the language's own folder. That is the copy the app reads.

## `_template/` — the language-neutral masters

`Prompts/_template/` holds a language-neutral version of each file, with
`{{LANGUAGE}}` where the language is named. When a language's folder is
missing one of the seven files, the app makes it from the template the first
time that language is chosen, fills the name in, and from then on reads the
copy — the template is never read for a language that has its own file.

So:

- **Adding a language** = adding its voice table in `_voices_literal.py`
  (every language there except English appears in the LANGUAGE panel). Its
  prompt folder is made on first use.
- **Tuning one language** (its terms list, its examples, its grammar rules)
  = editing the files in that language's folder. The Telugu folder carries
  the fully worked prompts the team wrote, with THIS BOOK'S TERMS filled in;
  the other folders start from the neutral template, whose terms section is
  a placeholder waiting for that language's settled renderings.
- **Changing a rule for every language that is not yet tuned** = editing the
  template, then deleting the file from the folders that should take the
  new version (they are remade on next use).

The JSON output contracts (the "OUTPUT FORMAT" block the app appends to each
prompt) live in `review_core.py`, not here, because the parsers depend on
them. Their key names (`"telugu"`, `"not_in_telugu"`) are fixed whatever the
language; only the prose around them names the language.
