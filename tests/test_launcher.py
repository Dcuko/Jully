import subprocess

import launcher


def _runner(outputs):
    """Fake subprocess runner: {command prefix: (returncode, stdout)}; anything else is 'not found'."""
    def run(cmd):
        for prefix, (code, out) in outputs.items():
            if tuple(cmd[:len(prefix)]) == prefix:
                return subprocess.CompletedProcess(cmd, code, out, "")
        raise FileNotFoundError(cmd[0])
    return run


def test_find_python_prefers_a_new_enough_version():
    runner = _runner({("py", "-3.13"): (1, ""), ("py", "-3.12"): (0, "3 12\n")})
    assert launcher.find_python(runner) == ["py", "-3.12"]


def test_find_python_skips_old_versions_and_missing_commands():
    runner = _runner({("py", "-3"): (0, "3 9\n"), ("python",): (0, "3 11\n")})
    assert launcher.find_python(runner) == ["python"]


def test_find_python_returns_none_without_a_suitable_python():
    assert launcher.find_python(_runner({("python",): (0, "3 8\n")})) is None
    assert launcher.find_python(_runner({("python",): (0, "garbage")})) is None
    assert launcher.find_python(_runner({})) is None


def test_marker_makes_the_check_instant(tmp_path, monkeypatch):
    monkeypatch.setattr(launcher, "MARKER", tmp_path / "marker")
    (tmp_path / "marker").write_text("ok")

    def explode(cmd):
        raise AssertionError("must not run anything when the marker exists")

    assert launcher.is_installed(explode)


def test_a_manual_install_is_recognised_and_marked(tmp_path, monkeypatch):
    pythonw = tmp_path / "pythonw.exe"
    pythonw.write_text("")
    monkeypatch.setattr(launcher, "MARKER", tmp_path / "marker")
    monkeypatch.setattr(launcher, "VENV_PYTHONW", pythonw)
    monkeypatch.setattr(launcher, "VENV_PYTHON", tmp_path / "python.exe")

    assert launcher.is_installed(lambda cmd: subprocess.CompletedProcess(cmd, 0))
    assert (tmp_path / "marker").exists()


def test_missing_modules_mean_not_installed(tmp_path, monkeypatch):
    pythonw = tmp_path / "pythonw.exe"
    pythonw.write_text("")
    monkeypatch.setattr(launcher, "MARKER", tmp_path / "marker")
    monkeypatch.setattr(launcher, "VENV_PYTHONW", pythonw)
    monkeypatch.setattr(launcher, "VENV_PYTHON", tmp_path / "python.exe")

    assert not launcher.is_installed(lambda cmd: subprocess.CompletedProcess(cmd, 1))
    assert not (tmp_path / "marker").exists()
    monkeypatch.setattr(launcher, "VENV_PYTHONW", tmp_path / "nope.exe")
    assert not launcher.is_installed(lambda cmd: subprocess.CompletedProcess(cmd, 0))
