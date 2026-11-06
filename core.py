import json
import os
import re
import sys
import threading
import time

try:
    from deep_translator import GoogleTranslator
except ImportError:
    GoogleTranslator = None

FREE_LANGUAGES = [
    ("English", "en"), ("Turkish", "tr"), ("German", "de"), ("Spanish", "es"), ("French", "fr"), ("Italian", "it"),
]
PRO_LANGUAGES = [
    ("Portuguese", "pt"), ("Russian", "ru"), ("Japanese", "ja"), ("Chinese (Simplified)", "zh-CN"),
    ("Chinese (Traditional)", "zh-TW"), ("Korean", "ko"), ("Dutch", "nl"), ("Polish", "pl"), ("Arabic", "ar"),
    ("Indonesian", "id"), ("Vietnamese", "vi"), ("Thai", "th"), ("Czech", "cs"), ("Ukrainian", "uk"),
    ("Greek", "el"), ("Swedish", "sv"), ("Romanian", "ro"), ("Finnish", "fi"), ("Danish", "da"),
    ("Norwegian", "no"), ("Hungarian", "hu"), ("Hebrew", "iw"),
]
LANG_NAMES = {code: name for name, code in FREE_LANGUAGES + PRO_LANGUAGES}
AUTO = "auto"

VAR_PATTERN = re.compile(
    r"\{\{.*?\}\}"
    r"|\{[^{}\n]*\}"
    r"|<[^<>\n]+>"
    r"|%(?:\d+\$)?[-+0#]*(?:\d+)?(?:\.\d+)?[sdif@]"
    r"|%%"
    r"|\\[nrt]"
)
TOKEN_PATTERN = re.compile(r"[\[【［]\s*VAR\s*_?\s*(\d+)\s*[\]】］]", re.IGNORECASE)
HAS_LETTER = re.compile(r"[^\W\d_]")
LEAD_TRAIL = re.compile(r"^(\s*)(.*?)(\s*)$", re.S)


def data_dir():
    base = os.environ.get("APPDATA") if sys.platform == "win32" else None
    path = os.path.join(base, "LocaGenFree") if base else os.path.join(os.path.expanduser("~"), ".locagenfree")
    os.makedirs(path, exist_ok=True)
    return path


def write_json_atomic(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


class Translator:
    def __init__(self, target, source=AUTO, backend=None):
        self.target, self.source = target, source
        if backend is None:
            if GoogleTranslator is None:
                raise RuntimeError("deep-translator is not installed")
            backend = lambda: GoogleTranslator(source=source, target=target).translate
        self._factory = backend
        self._local = threading.local()
        self.cache = {}

    def _backend(self):
        fn = getattr(self._local, "fn", None)
        if fn is None:
            fn = self._local.fn = self._factory()
        return fn

    @staticmethod
    def protect(text):
        values = []

        def keep(m):
            values.append(m.group(0))
            return f"[VAR_{len(values) - 1}]"

        return VAR_PATTERN.sub(keep, text), values

    @staticmethod
    def restore(text, values):
        found = set()

        def put(m):
            idx = int(m.group(1))
            if idx < len(values):
                found.add(idx)
                return values[idx]
            return m.group(0)

        return TOKEN_PATTERN.sub(put, text), len(found) == len(values)

    def _call(self, text):
        last_error = None
        for attempt in range(3):
            try:
                result = self._backend()(text)
                if result:
                    return result
                last_error = ValueError("empty result")
            except Exception as e:
                last_error = e
            time.sleep(0.8 * (attempt + 1))
        raise last_error

    def translate(self, text):
        if not isinstance(text, str) or not text.strip():
            return text, True
        if "\n" in text:
            parts = [self.translate(part) for part in text.split("\n")]
            return "\n".join(p for p, _ in parts), all(ok for _, ok in parts)
        m = LEAD_TRAIL.match(text)
        core = m.group(2)
        if core not in self.cache:
            protected, values = self.protect(core)
            if not HAS_LETTER.search(TOKEN_PATTERN.sub("", protected)):
                self.cache[core] = (core, True)
            else:
                try:
                    restored, complete = self.restore(self._call(protected), values)
                    self.cache[core] = (restored, True) if complete else (core, False)
                except Exception:
                    self.cache[core] = (core, False)
        result, ok = self.cache[core]
        return m.group(1) + result + m.group(3), ok


def count_strings(node):
    if isinstance(node, str):
        return 1
    if isinstance(node, dict):
        return sum(count_strings(v) for v in node.values())
    if isinstance(node, list):
        return sum(count_strings(v) for v in node)
    return 0


def map_strings(node, fn):
    if isinstance(node, str):
        return fn(node)
    if isinstance(node, dict):
        return {k: map_strings(v, fn) for k, v in node.items()}
    if isinstance(node, list):
        return [map_strings(v, fn) for v in node]
    return node


def load_json(path):
    with open(path, "rb") as f:
        raw = f.read()
    return json.loads(raw.decode("utf-8-sig"))


def translate_json(data, translator, progress=None, stop_event=None):
    total = max(count_strings(data), 1)
    done, failed = [0], [0]

    def step(text):
        if stop_event is not None and stop_event.is_set():
            return text
        result, ok = translator.translate(text)
        done[0] += 1
        if not ok:
            failed[0] += 1
        if progress:
            progress(done[0] / total)
        return result

    return map_strings(data, step), failed[0]


def save_json(path, data):
    folder = os.path.dirname(path)
    if folder:
        os.makedirs(folder, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
