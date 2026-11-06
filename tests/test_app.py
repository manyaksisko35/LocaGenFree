import json
import time

import pytest

tk = pytest.importorskip("tkinter")


@pytest.fixture
def app(monkeypatch, fake_google, tmp_path):
    try:
        probe = tk.Tk()
        probe.destroy()
    except tk.TclError:
        pytest.skip("no display available")
    import locagenfree as L

    def offline(*a, **k):
        raise RuntimeError("offline")

    monkeypatch.setattr(L.requests, "get", offline)
    monkeypatch.setattr(L.filedialog, "asksaveasfilename", lambda **k: str(tmp_path / "out" / "tr.json"))
    opened = []
    monkeypatch.setattr(L.webbrowser, "open", opened.append)
    instance = L.LocaGenFreeApp()
    instance.opened_urls = opened
    yield instance
    try:
        instance.destroy()
    except tk.TclError:
        pass


def pump(app, seconds=0.3):
    end = time.time() + seconds
    while time.time() < end:
        app.update()
        time.sleep(0.01)


def dialog_open(app):
    return bool(app.g.canvas.find_withtag("sheet"))


def test_translate_json(app, tmp_path):
    src = tmp_path / "en.json"
    src.write_text(json.dumps({"menu": {"start": "Start Game", "slots": 3}}), encoding="utf-8")
    app.load_file(str(src))
    app._set_target("tr")
    app.on_translate()
    end = time.time() + 20
    while app.busy and time.time() < end:
        pump(app, 0.05)
    out = json.loads((tmp_path / "out" / "tr.json").read_text(encoding="utf-8"))
    assert out == {"menu": {"start": "tr: Start Game", "slots": 3}}
    assert "Done" in app.g.canvas.itemcget(app.lbl_status, "text")


def test_other_formats_point_to_pro(app, tmp_path):
    src = tmp_path / "strings.csv"
    src.write_text("key,en\na,b\n", encoding="utf-8")
    app.load_file(str(src))
    pump(app, 0.5)
    assert app.data is None and dialog_open(app)


def test_pro_language_and_theme_open_upgrade(app):
    import locagenfree as L
    app._set_target("ja")
    pump(app, 0.5)
    assert app.target_code != "ja" and dialog_open(app)
    app.g.canvas.delete("sheet")
    app.apply_theme("Rose")
    pump(app, 0.3)
    assert L.P.name != "Rose" and dialog_open(app)
    app.g.canvas.delete("sheet")
    app.apply_theme("Frost")
    pump(app, 0.3)
    assert L.P.name == "Frost"


def test_upgrade_button_opens_store(app):
    import locagenfree as L
    dialog = app.show_upgrade()
    pump(app, 0.6)
    c, s = app.g.canvas, app.g.scale
    x0, y0, x1, y1 = dialog.primary_box
    x, y = int((x0 + x1) / 2 * s), int((y0 + y1) / 2 * s)
    c.event_generate("<Motion>", x=x, y=y)
    c.event_generate("<ButtonRelease-1>", x=x, y=y)
    pump(app, 0.4)
    assert app.opened_urls == [L.PRO_URL]
    assert not c.find_withtag("sheet")


def test_maybe_later_closes_without_opening(app):
    dialog = app.show_upgrade()
    pump(app, 0.6)
    c, s = app.g.canvas, app.g.scale
    x0, y0, x1, y1 = dialog.secondary_box
    x, y = int((x0 + x1) / 2 * s), int((y0 + y1) / 2 * s)
    c.event_generate("<Motion>", x=x, y=y)
    c.event_generate("<ButtonRelease-1>", x=x, y=y)
    pump(app, 0.4)
    assert app.opened_urls == [] and not c.find_withtag("sheet")
