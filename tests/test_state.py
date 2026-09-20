from console import state as store


def test_flag_updates_do_not_clobber_paused_game(tmp_path, monkeypatch):
    path = tmp_path / "console.state"
    monkeypatch.setenv("CONSOLE_STATE", str(path))
    store.save_paused("dino", {"distance_ran": 123, "high_score": 12}, wipe_on_escape=False)
    store.update_flags(busy=True, session_id="abc")
    data = store.load_state()
    assert data["busy"] is True
    assert data["paused"]["snapshot"]["distance_ran"] == 123
    assert data["session_id"] == "abc"


def test_task_done_sets_wipe_on_escape(tmp_path, monkeypatch):
    monkeypatch.setenv("CONSOLE_STATE", str(tmp_path / "console.state"))
    store.update_flags(task_done=True)
    data = store.load_state()
    assert data["task_done"] is True
    assert data["wipe_on_escape"] is True
    assert data["busy"] is False


def test_clear_paused(tmp_path, monkeypatch):
    monkeypatch.setenv("CONSOLE_STATE", str(tmp_path / "console.state"))
    store.save_paused("dino", {"high_score": 9}, wipe_on_escape=True)
    store.clear_paused()
    data = store.load_state()
    assert data["paused"] is None
    assert data["task_done"] is False
