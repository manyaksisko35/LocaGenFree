# LocaGen FREE

LocaGen FREE is a small, open-source desktop tool I made for translating game localization files. You pick a JSON file, choose a target language, and it translates every text value with Google Translate while leaving the keys and the structure alone. Before sending a string to the translator it swaps placeholders such as `{name}`, `<b>`, `%s` and `%d` for temporary tokens, then puts the originals back, so the variables your game code depends on stay as they were.

This is the free edition of LocaGen. The paid **LocaGen PRO** edition adds 12 more file formats (CSV, Excel, PO, Ren'Py, RPG Maker, YAML, XLIFF and more), 28 languages, DeepL and offline translation, a glossary, a review window and more.

- LocaGen PRO on itch.io: [LocaGen Pro - Universal Game Localization Tool](https://hasan-alp-gungor.itch.io/locagen-pro-universal-game-localization-tool)
- Separate web version: [LocaGen PHP](https://github.com/manyaksisko35/LocaGenPHP) (PHP + MySQL web app, translates with the Gemini API)
- Project page: [hasanalpgungor.com/en/projects/locagen](https://hasanalpgungor.com/en/projects/locagen)

## Features

- Liquid Glass desktop interface: frosted glass panels, smooth animations, two themes (Neon Void and Frost) and a borderless window.
- Loads `.json` files, including nested objects and arrays. Numbers, `true`/`false` and `null` are left untouched.
- Drag and drop a `.json` file onto the window, or pick one with the file dialog.
- Translates with Google Translate through `deep-translator`. The source language can be detected automatically or picked by hand.
- Target languages: English, Turkish, German, Spanish, French and Italian.
- Keys are never translated, only values.
- Placeholder protection: `{...}`, `{{...}}`, `<...>`, `%s`, `%d`, `%1$s`, `%.2f`, `%%` and `\n` are replaced with `[VAR_0]`, `[VAR_1]`, ... before translation and restored afterwards. If a placeholder gets lost, the original text is kept so your game does not break.
- Multi-line values are translated line by line, and leading/trailing spaces are kept.
- If a single string fails to translate, the original text is kept and the number of kept strings is shown at the end.
- Translation runs in the background with a progress bar and can be stopped at any time.
- Output is written as UTF-8 with 4-space indentation and non-ASCII characters kept as-is.
- Remembers your languages and theme between runs.
- On start it checks the latest release of this repository on GitHub and offers to update the packaged build.

## Free vs PRO

| | FREE | PRO |
|---|---|---|
| File formats | JSON | JSON, CSV, Excel, TXT, PO/POT, Ren'Py, RPG Maker MV/MZ, YAML, Android XML, XLIFF, .properties |
| Languages | 6 | 28, many at once |
| Engines | Google Translate | Google Translate, DeepL, offline packs |
| Glossary | | Per-language rules and "don't translate" names |
| Review & quality report | | Review window, issue checks, `locagen_report.csv` |
| Only new & changed strings | | Yes, with translation memory |
| Themes | 2 | 8 |
| Source code | Open source (GPL-3.0) | Closed source |

## Built with

- Python 3 and tkinter
- [Pillow](https://python-pillow.org/) and [NumPy](https://numpy.org/) for rendering the glass interface
- [deep-translator](https://github.com/nidhaloff/deep-translator) (`GoogleTranslator`)
- [tkinterdnd2](https://github.com/Eliav2/tkinterdnd2) for drag and drop
- [requests](https://requests.readthedocs.io/) for the GitHub release check

## Getting started

### Option 1: download a build

A packaged Windows build is published on the [Releases](https://github.com/manyaksisko35/LocaGenFree/releases) page.

### Option 2: run from source

Requirements:

- Python 3.10 or newer with tkinter (included in the standard Python installers for Windows and macOS; on Linux you may need a package such as `python3-tk`)
- An internet connection (Google Translate and the update check both go online)

```bash
git clone https://github.com/manyaksisko35/LocaGenFree.git
```

```bash
cd LocaGenFree
```

```bash
pip install -r requirements.txt
```

```bash
python locagenfree.py
```

The self-update replaces the running `.exe`, so it is meant for the packaged Windows build. When running from source it only offers to open the download page.

### Usage

1. Click **Choose a JSON file** or drop a `.json` file on the window.
2. Pick the source language (or leave it on Auto-Detect) and the target language.
3. Click **Translate**, choose where to save the result, and wait for the progress bar to finish. **Open folder ›** takes you to the saved file.

### Running the tests

```bash
pip install pytest
```

```bash
python -m pytest
```

## Example

Input (`en.json`):

```json
{
    "greeting": "Welcome back, {player_name}!",
    "coins": "You found %d coins.",
    "menu": {
        "hint": "Press <b>E</b> to open the chest.",
        "slots": 3
    }
}
```

Output with Turkish selected (exact wording comes from Google Translate):

```json
{
    "greeting": "Tekrar hoş geldin, {player_name}!",
    "coins": "%d jeton buldun.",
    "menu": {
        "hint": "Sandığı açmak için <b>E</b> tuşuna basın.",
        "slots": 3
    }
}
```

`{player_name}`, `%d`, `<b>` and `</b>` come back unchanged, and the nested `menu` object and the number keep their shape.

## License

LocaGen FREE is free software released under the [GNU General Public License v3.0](LICENSE). You can use, study, change and share it; if you distribute a changed version, it has to stay under the same license with its source code available.

## Türkçe

LocaGen FREE, oyun yerelleştirme JSON dosyalarını Google Translate ile çeviren, açık kaynaklı (GPL-3.0) bir masaüstü uygulamasıdır. Liquid Glass arayüzü, sürükle-bırak desteği ve iç içe JSON desteği vardır. Anahtarlara dokunmaz, sadece metinleri çevirir; `{name}`, `<b>`, `%s` ve `%d` gibi yer tutucuları çeviri sırasında korur. Hedef dil olarak İngilizce, Türkçe, Almanca, İspanyolca, Fransızca ve İtalyanca desteklenir. Çalıştırmak için `pip install -r requirements.txt` komutundan sonra `python locagenfree.py` yeterlidir. Daha fazla format, dil, DeepL, çevrimdışı çeviri ve glossary için [LocaGen PRO](https://hasan-alp-gungor.itch.io/locagen-pro-universal-game-localization-tool)'ya göz atabilirsin.

Made by [Hasan Alp Güngör](https://hasanalpgungor.com/en)
