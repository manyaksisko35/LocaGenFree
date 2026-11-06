import json
import threading

import core


def upper():
    return lambda s: s.upper().replace("[VAR_0]", "[ var_0 ]")


def test_placeholders_survive_and_mangled_tokens_are_restored():
    t = core.Translator("tr", "en", backend=upper)
    assert t.translate("Hello {player}, <b>go</b>!") == ("HELLO {player}, <b>GO</b>!", True)
    assert t.translate("Value %1$s %.2f%%") == ("VALUE %1$s %.2f%%", True)


def test_lost_placeholder_keeps_original():
    t = core.Translator("tr", "en", backend=lambda: (lambda s: "lost"))
    assert t.translate("Hi {name}") == ("Hi {name}", False)


def test_backend_error_keeps_original(monkeypatch):
    monkeypatch.setattr(core.time, "sleep", lambda s: None)

    def broken():
        def fn(s):
            raise ConnectionError("offline")
        return fn

    assert core.Translator("tr", "en", backend=broken).translate("Hello") == ("Hello", False)


def test_whitespace_and_lines_are_kept():
    t = core.Translator("tr", "en", backend=lambda: (lambda s: s.upper()))
    assert t.translate("  indented  ") == ("  INDENTED  ", True)
    assert t.translate("one\ntwo") == ("ONE\nTWO", True)


def test_nested_json_keeps_shape(tmp_path):
    data = {"menu": {"start": "Start", "slots": 3, "on": True, "list": ["Quit", None]}, "title": "Game"}
    t = core.Translator("tr", "en", backend=lambda: (lambda s: "T:" + s))
    result, failed = core.translate_json(data, t)
    assert failed == 0
    assert result == {"menu": {"start": "T:Start", "slots": 3, "on": True, "list": ["T:Quit", None]}, "title": "T:Game"}
    path = tmp_path / "out" / "tr.json"
    core.save_json(str(path), result)
    assert json.loads(path.read_text(encoding="utf-8")) == result


def test_load_json_with_bom(tmp_path):
    path = tmp_path / "bom.json"
    path.write_bytes(b"\xef\xbb\xbf" + json.dumps({"a": "b"}).encode())
    assert core.load_json(str(path)) == {"a": "b"}


def test_stop_event_leaves_text_untouched():
    stop = threading.Event()
    stop.set()
    t = core.Translator("tr", "en", backend=lambda: (lambda s: "T:" + s))
    result, _ = core.translate_json({"a": "b"}, t, stop_event=stop)
    assert result == {"a": "b"}
