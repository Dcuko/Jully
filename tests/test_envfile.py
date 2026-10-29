import envfile


def test_save_updates_keeps_comments_and_appends(tmp_path):
    path = tmp_path / ".env"
    path.write_text("# key\nLLM_API_KEY=old\nFOLLOW_UP=1  # comment\n", encoding="utf-8")
    envfile.save(path, {"LLM_API_KEY": "new", "FOLLOW_UP": "0", "CITY": "São Paulo"})
    lines = path.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "# key"
    assert "LLM_API_KEY=new" in lines and "FOLLOW_UP=0" in lines
    assert envfile.read(path)["CITY"] == "São Paulo"


def test_special_values_round_trip(tmp_path):
    path = tmp_path / ".env"
    values = {"A": 'with "quotes" and # hash', "B": "", "C": "a\\b"}
    envfile.save(path, values)
    assert envfile.read(path) == values


def test_save_starts_from_template(tmp_path):
    template = tmp_path / ".env.example"
    template.write_text("# help\nLLM_API_KEY=\n", encoding="utf-8")
    path = tmp_path / ".env"
    envfile.save(path, {"LLM_API_KEY": "x"}, template=template)
    assert path.read_text(encoding="utf-8").startswith("# help\nLLM_API_KEY=x")


def test_read_missing_file(tmp_path):
    assert envfile.read(tmp_path / "does_not_exist") == {}


def test_rename_keys(tmp_path):
    path = tmp_path / ".env"
    path.write_text("# top\nVOZ=pt-BR-AntonioNeural\nREPLICA=0  # old\nOTHER=1\n", encoding="utf-8")
    assert envfile.rename_keys(path, {"VOZ": "VOICE", "REPLICA": "FOLLOW_UP"})
    assert envfile.read(path) == {"VOICE": "pt-BR-AntonioNeural", "FOLLOW_UP": "0", "OTHER": "1"}
    assert path.read_text(encoding="utf-8").startswith("# top\n")
    assert not envfile.rename_keys(path, {"VOZ": "VOICE"})  # nothing left to rename


def test_rename_keys_keeps_the_new_one_when_both_exist(tmp_path):
    path = tmp_path / ".env"
    path.write_text("VOZ=old\nVOICE=new\n", encoding="utf-8")
    envfile.rename_keys(path, {"VOZ": "VOICE"})
    assert envfile.read(path) == {"VOICE": "new"}
