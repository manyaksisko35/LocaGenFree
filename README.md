# LocaGen FREE

LocaGen FREE is a small desktop tool I made for translating game localization files. You pick a JSON file, choose a target language, and it translates every value with Google Translate while leaving the keys alone. Before sending a string to the translator it swaps placeholders such as `{name}`, `<b>`, `%s` and `%d` for temporary tokens, then puts the originals back, so the variables your game code depends on stay as they were. This is the free version of LocaGen; the bigger version is LocaGen PRO.

- Other version: [LocaGen PRO](https://github.com/manyaksisko35/LocaGenPHP) (PHP + MySQL web app, translates with the Gemini API)
- itch.io: [LocaGen PRO - Universal Game Localization Tool](https://hasan-alp-gungor.itch.io/locagen-pro-universal-game-localization-tool)
- Project page: [hasanalpgungor.com/en/projects/locagen](https://hasanalpgungor.com/en/projects/locagen)

## Features

- Desktop GUI built with CustomTkinter (dark theme, small typing and hover animations).
- Loads `.json` files only; other file types are rejected.
- Translates with Google Translate through `deep-translator`. The source language is detected automatically.
- Target languages: English, Turkish, German, Spanish, French and Italian.
- Keys are never translated, only values.
- Works with two JSON shapes:
  - an object of key/value pairs (`{"key": "text", ...}`)
  - a list of strings or a list of flat objects (`[{"key": "text"}, ...]`)
- Placeholder protection: anything matching `{...}`, `<...>`, `%s` or `%d` is replaced with `[VAR_0]`, `[VAR_1]`, ... before translation and restored afterwards.
- If a single string fails to translate, the original text is kept instead of stopping the whole job.
- Translation runs in a background thread with a progress bar, so the window stays responsive.
- Output is written as UTF-8 with 4-space indentation and non-ASCII characters kept as-is (no `\u` escapes). The save dialog suggests a name like `translated_Turkish.json`.
- On start it checks the latest release of this repository on GitHub. If the tag differs from the running version (`v2.0.0-Free`), it asks whether to download and install the new build.

## Built with

- Python 3
- [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) for the UI (on top of tkinter)
- [deep-translator](https://github.com/nidhaloff/deep-translator) (`GoogleTranslator`)
- [requests](https://requests.readthedocs.io/) for the GitHub release check

## Getting started

### Option 1: download a build

A packaged build is published on the [Releases](https://github.com/manyaksisko35/LocaGenFree/releases) page.

### Option 2: run from source

Requirements:

- Python 3 with tkinter (included in the standard Python installers for Windows and macOS; on Linux you may need a package such as `python3-tk`)
- An internet connection (Google Translate and the update check both go online)

```bash
git clone https://github.com/manyaksisko35/LocaGenFree.git
cd LocaGenFree
pip install customtkinter deep-translator requests
python locagenv2free.py
```

Keep `app_icon.ico` in the folder you run the script from if you want the window icon.

The self-update replaces the running `.exe`, so it is meant for the packaged Windows build. When running from source, answer "No" if it asks to update.

### Usage

1. Click **SELECT_FILE** and choose your `.json` file.
2. Pick the target language.
3. Click **INITIATE**, choose where to save the result, and wait for the progress bar to finish.

### Limitations

Only the first level of the file is translated. Nested objects, nested arrays and numbers are converted to strings, so flat key/value files give the best results. `glossary.json` is in the repository but this version does not read it.

## Example

Input (`en.json`):

```json
{
    "greeting": "Welcome back, {player_name}!",
    "coins": "You found %d coins.",
    "hint": "Press <b>E</b> to open the chest."
}
```

Output with Turkish selected (exact wording comes from Google Translate):

```json
{
    "greeting": "Tekrar hoş geldin, {player_name}!",
    "coins": "%d jeton buldun.",
    "hint": "Sandığı açmak için <b>E</b> tuşuna basın."
}
```

`{player_name}`, `%d`, `<b>` and `</b>` come back unchanged.

## Türkçe

LocaGen FREE, oyun yerelleştirme JSON dosyalarını Google Translate ile çeviren bir masaüstü uygulamasıdır. Anahtarlara dokunmaz, sadece değerleri çevirir; `{name}`, `<tag>`, `%s` ve `%d` gibi yer tutucuları çeviri sırasında korur. Hedef dil olarak İngilizce, Türkçe, Almanca, İspanyolca, Fransızca ve İtalyanca desteklenir. Çalıştırmak için `pip install customtkinter deep-translator requests` komutundan sonra `python locagenv2free.py` yeterlidir.

Made by [Hasan Alp Güngör](https://hasanalpgungor.com/en)
