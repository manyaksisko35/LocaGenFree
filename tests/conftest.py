import pytest


class FakeGoogle:
    def __init__(self, source="auto", target="en"):
        self.target = target

    def translate(self, text):
        return f"{self.target}: {text}"


@pytest.fixture(autouse=True)
def isolated_home(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("APPDATA", str(home))
    return home


@pytest.fixture
def fake_google(monkeypatch):
    import core
    monkeypatch.setattr(core, "GoogleTranslator", FakeGoogle)
    return FakeGoogle
