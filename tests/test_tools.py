import pytest

import tools as t


@pytest.mark.parametrize("expr,expected", [("2+3*4", "14"), ("23*5", "115"), ("10/4", "2.5"),
                                           ("7//2", "3"), ("-(2+3)", "-5"), ("2**10", "1024")])
def test_calculate(expr, expected):
    assert t.calculate(expr) == expected


@pytest.mark.parametrize("expr", ["__import__('os')", "2**99999", "abs(1)", "1+"])
def test_calculate_refuses_anything_unsafe(expr):
    with pytest.raises(Exception):
        t.calculate(expr)


def test_execute_returns_an_error_instead_of_raising():
    assert t.execute("calculate", {"expression": "1/0"}).startswith("Error")
    assert t.execute("does_not_exist", {}).startswith("Error")


SITES = ["youtube.com", "github.com"]


@pytest.mark.parametrize("url,ok", [
    ("https://youtube.com/watch?v=1", True),
    ("https://www.youtube.com", True),
    ("http://music.youtube.com/x", True),
    ("https://youtube.com.malicious.com", False),
    ("https://malicious.com/youtube.com", False),
    ("https://youtube.com@malicious.com", False),
    ("https://notyoutube.com", False),
    ("file:///C:/Windows/System32/calc.exe", False),
    ("javascript:alert(1)", False),
])
def test_site_allowed(url, ok):
    assert t.site_allowed(url, SITES) is ok


def test_site_allowed_wildcard_and_empty_list():
    assert t.site_allowed("https://anything.com", ["*"])
    assert not t.site_allowed("https://anything.com", [])
    assert not t.site_allowed("ftp://anything.com", ["*"])


def test_reminder_in_the_past_and_invalid_date():
    assert t.reminder("2000-01-01T10:00", "x") == "That time has already passed."
    with pytest.raises(ValueError):
        t.reminder("tomorrow", "x")


def test_timer_is_persisted_and_removed_when_fired(tmp_path, monkeypatch):
    monkeypatch.setattr(t.config, "TIMERS_FILE", tmp_path / "timers.json")
    spoken = []
    monkeypatch.setattr(t.speak, "say", spoken.append)

    t._schedule(t.time.time() + 3600, "future")
    t._fire("missing", "hi")
    assert [x["message"] for x in t._read_timers()] == ["future"]
    assert spoken == ["hi"]

    timer_id = t._read_timers()[0]["id"]
    t._fire(timer_id, "future", late=True)
    assert t._read_timers() == []
    assert "future" in spoken[-1]


def test_schemas_are_valid_and_open_target_lists_the_sites():
    names = [s["name"] for s in t.schemas()]
    assert len(names) == len(set(names))
    assert all(n in t._FUNCTIONS for n in names)
    open_target = next(s for s in t.schemas() if s["name"] == "open_target")
    assert t.config.ALLOWED_SITES[0] in open_target["description"]


def test_date_and_time_has_a_weekday():
    assert t.date_and_time().split(",")[0] in ("Monday", "Tuesday", "Wednesday", "Thursday",
                                              "Friday", "Saturday", "Sunday")
