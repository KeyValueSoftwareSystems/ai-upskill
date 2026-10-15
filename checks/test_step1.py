from launchkit.harness.run import run_request


def test_harbor_and_ember_differ(settings, images, request_for, echo):
    """Harbor and Ember get different tone and rules from the same code."""
    harbor = run_request(request_for("harbor"), settings=settings, model=echo, images=images)
    ember = run_request(request_for("ember"), settings=settings, model=echo, images=images)
    assert harbor.spec.body != ember.spec.body
    assert "Harbor" in harbor.spec.body
    assert "Ember" in ember.spec.body


def test_editing_agents_md_changes_the_next_turn(settings, images, request_for, echo):
    """Editing AGENTS.md changes the next turn without a code change."""
    before = run_request(request_for("harbor"), settings=settings, model=echo, images=images)
    agents = settings.workspaces_dir / "harbor" / "AGENTS.md"
    agents.write_text("Always open with the word Tidal.\n" + agents.read_text())
    after = run_request(request_for("harbor", session_id="t2"), settings=settings, model=echo, images=images)
    assert before.spec != after.spec


def test_three_files_are_read(settings, images, trace, request_for, echo):
    """The trace lists exactly three files read, all under the Harbor workspace."""
    run_request(request_for("harbor"), settings=settings, model=echo, images=images, trace=trace)
    files = trace.files_read()
    assert len(files) == 3
    assert all(str(settings.workspaces_dir / "harbor") in f for f in files)
