"""Session 4's checks. Each one reads an acceptance criterion the room agreed, and each belongs to a stage.

The session runs in stages, like red and green in test-driven work. A failure shows live, the room writes that
stage's criteria, the lead runs the prompt, and that stage's checks go green:

    uv run pytest checks/test_files.py -m stage1

Every stage's checks fail on `session-04-filesystem-prd` and pass on `session-04-filesystem-solutions`. They are the specification
written as code, and they are what "done" means for a stage.

The interface the checks expect, so the lead's prompt and the room's build agree on names:

    launchkit.files.workspace   for_request(request, settings) -> Workspace(brand, conversation, root)
                                Workspace.drawer(name) -> Path, Workspace.shared -> Path
    launchkit.files.paths       resolve_in_workspace(root, asked) -> Path, or raises OutsideWorkspace
    launchkit.files.record      record(root, path, by, message), entries(root) -> list[Entry]
    launchkit.tools.*           make_read_file / make_list_files / make_write_file / make_search_files /
                                make_edit_file, each taking (workspace, trace[, message]) and returning an Entry
                                whose .fn is the tool

The checks read `Workspace` as a folder per conversation, because that is the answer the branch expects the room
to reach. If the room chooses another layout, the lead adapts them.

Criteria 2, 8 and 12 are read from the chat page in the room rather than from here, because what the marketer
sees is the point of them. Criterion 9 is stage 6, which has no build: it holds once stages 1 and 3 do.
"""

import importlib
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from launchkit.files.paths import OutsideWorkspace, resolve_in_workspace
from launchkit.files.record import entries, record
from launchkit.files.workspace import DRAWERS, for_request


def tool(module: str, factory: str, workspace, trace, message: str = "m1"):
    """One of the file tools, built the way the agent's catalogue builds it. The stage that owns it makes it exist."""
    make = getattr(importlib.import_module(f"launchkit.tools.{module}"), factory)
    try:
        return make(workspace, trace, message).fn
    except TypeError:
        return make(workspace, trace).fn


@pytest.fixture
def workspace(settings, request_for):
    return for_request(request_for(workspace_id="harbor", session_id="k7c1"), settings)


# Stage 1: the file tools, in a workspace per conversation ------------------

@pytest.mark.stage1
def test_a_workspace_belongs_to_one_brand_and_one_conversation(settings, request_for):
    """1 · every file the agent writes lands inside the workspace for the signed-in brand and conversation."""
    one = for_request(request_for(workspace_id="harbor", session_id="k7c1"), settings)
    two = for_request(request_for(workspace_id="harbor", session_id="t3a9"), settings)
    other_brand = for_request(request_for(workspace_id="ember", session_id="t3a9"), settings)

    assert one.root != two.root, "two conversations at one brand share a folder"
    assert two.root != other_brand.root, "two brands share a folder"
    assert one.root.is_relative_to(settings.data_dir), "the workspace is outside the data directory"


@pytest.mark.stage1
def test_the_workspace_comes_from_the_request(settings, request_for):
    """1 · the workspace comes from the request rather than from anything the model supplies."""
    asked = request_for(workspace_id="harbor", session_id="k7c1")
    assert for_request(asked, settings).brand == "harbor"
    assert for_request(asked, settings).conversation == "k7c1"


@pytest.mark.stage1
def test_every_drawer_is_made_on_first_use(workspace):
    """1 · finished work and drafts are kept apart, which is what the chat page reads later."""
    for name in DRAWERS:
        assert workspace.drawer(name).is_dir()
    with pytest.raises(ValueError):
        workspace.drawer("anything-else")


@pytest.mark.stage1
def test_the_agent_can_come_back_for_what_it_made(workspace, trace):
    """1 · Maya's first sentence: come back to the same campaign and get the file it already made, not a new one."""
    write = tool("write_file", "make_write_file", workspace, trace)
    read = tool("read_file", "make_read_file", workspace, trace)
    listing = tool("list_files", "make_list_files", workspace, trace)

    write("outputs/breeze-brief.md", "avoid the lifetime-guarantee framing")
    assert "avoid the lifetime-guarantee framing" in read("outputs/breeze-brief.md")
    assert "outputs/breeze-brief.md" in listing(".")


@pytest.mark.stage1
def test_two_conversations_do_not_see_each_others_files(settings, request_for, trace):
    """1 · a second conversation at the same brand starts with none of the first one's files."""
    one = for_request(request_for(workspace_id="harbor", session_id="k7c1"), settings)
    two = for_request(request_for(workspace_id="harbor", session_id="t3a9"), settings)
    tool("write_file", "make_write_file", one, trace)("outputs/brief.md", "mine")
    assert "brief.md" not in tool("list_files", "make_list_files", two, trace)(".")


def _media(settings, request_for, trace):
    """A photo attached, then a poster, a size and a voice-over made, the way one turn in conversation k7c1 makes them."""
    from launchkit.agents.main_agent import build_catalogue
    from launchkit.memory.attached_pictures import Pictures
    from launchkit.settings import ROOT

    req = request_for(workspace_id="harbor", session_id="k7c1")
    pictures = Pictures(settings, "harbor", "maya", "k7c1")
    attached = pictures.attach(ROOT / "samples" / "approved" / "tidal-poster.jpg")
    tools = build_catalogue(settings, trace, lambda name, inputs: False, pictures=pictures, files=for_request(req, settings), message="m1").entries
    poster = Path(tools["generate_image"].fn("the bottle on a misty lakeshore at dawn")["file"])
    size = Path(tools["scale"].fn(1080, 1080)["file"])
    voice = Path(tools["text_to_speech"].fn("Cold for twenty-four hours.")["file"])
    return req, attached, poster, size, voice


@pytest.mark.stage1
def test_pictures_sizes_and_voice_overs_land_in_the_conversations_workspace(settings, request_for, trace):
    """1 · a poster, a size and a voice-over land in this conversation's outputs/, and an attached photo in its uploads/, never in a folder shared with every brand."""
    req, attached, poster, size, voice = _media(settings, request_for, trace)
    ws = for_request(req, settings)

    assert attached.is_relative_to(ws.drawer("uploads")), f"{attached} is outside this conversation's uploads/"
    for made in (poster, size, voice):
        assert made.is_relative_to(ws.drawer("outputs")), f"{made} is outside this conversation's outputs/"


# Stage 2: a capped search ---------------------------------------------------

BRIEFS = {
    "figma": "Positioning: the tool teams already have open.\nClaims: no lifetime guarantee anywhere in their copy.\n",
    "canva": "Positioning: anyone can make something designed.\nClaims: 'lifetime access' on the one-off licence page.\n",
    "affinity": "Positioning: buy it once, own it.\nClaims: 'lifetime guarantee' is the headline of their pricing page.\n",
}


@pytest.mark.stage2
def test_a_search_returns_a_path_a_line_and_a_snippet(workspace, trace):
    """3 · a search returns a path, a line number and a snippet."""
    write = tool("write_file", "make_write_file", workspace, trace)
    for name, text in BRIEFS.items():
        write(f"competitors/{name}.md", text)
    out = tool("search_files", "make_search_files", workspace, trace)("lifetime")

    assert re.search(r"competitors/affinity\.md:\d+:", out), f"no path and line in: {out!r}"
    assert "headline of their pricing page" in out


@pytest.mark.stage2
def test_a_search_stops_after_a_set_number_of_matches_and_says_so(workspace, trace):
    """3 · it stops after a set number of matches, and says when it stopped early."""
    write = tool("write_file", "make_write_file", workspace, trace)
    for n in range(40):
        write(f"competitors/c{n}.md", "lifetime guarantee\n")
    out = tool("search_files", "make_search_files", workspace, trace)("lifetime")

    matches = [line for line in out.splitlines() if re.search(r"\.md:\d+:", line)]
    assert 0 < len(matches) <= 20, f"{len(matches)} matches came back"
    assert "stopped" in out.lower(), "it stopped early and did not say so"


@pytest.mark.stage2
def test_a_search_skips_files_that_are_not_text_or_are_too_big(workspace, trace):
    """3 · it skips files that are not text or are over a size limit."""
    folder = workspace.drawer("work")
    (folder / "poster.png").write_bytes(b"\x89PNG lifetime \x00\x01")
    (folder / "huge.md").write_text("lifetime\n" * 200_000, encoding="utf-8")
    (folder / "small.md").write_text("lifetime\n", encoding="utf-8")
    out = tool("search_files", "make_search_files", workspace, trace)("lifetime")

    assert "small.md" in out
    assert "poster.png" not in out
    assert "huge.md" not in out


@pytest.mark.stage2
def test_finding_a_line_costs_a_search_not_the_folder(workspace, trace):
    """4 · answering "where did this line come from" costs a search and a read or two, not every file."""
    write = tool("write_file", "make_write_file", workspace, trace)
    for name, text in BRIEFS.items():
        write(f"competitors/{name}.md", text * 50)
    out = tool("search_files", "make_search_files", workspace, trace)("headline of their pricing")

    assert len(out) < sum(len(t * 50) for t in BRIEFS.values()) / 4, "the search cost about as much as reading the folder"


@pytest.mark.stage2
def test_a_read_can_take_just_the_lines_it_needs(workspace, trace):
    """4 · the search says which line, and a read can then take just that part of the file."""
    tool("write_file", "make_write_file", workspace, trace)("outputs/brief.md", "one\ntwo\nthree\nfour\n")
    got = tool("read_file", "make_read_file", workspace, trace)("outputs/brief.md", 2, 3)
    assert got.splitlines() == ["two", "three"]


# Stage 3: one check every path passes ---------------------------------------

@pytest.mark.stage3
@pytest.mark.parametrize(
    "asked, why",
    [
        ("../../ember/t3a9/campaign-brief.md", "climbing out with .., into a sibling brand"),
        ("/etc/passwd", "an absolute path"),
        ("work/../../../../etc/passwd", "climbing out from inside a drawer"),
    ],
)
def test_a_path_that_leaves_the_workspace_is_refused(workspace, asked, why):
    """5 · a path that resolves outside the workspace is refused, in every form."""
    with pytest.raises(OutsideWorkspace):
        resolve_in_workspace(workspace.root, asked)


@pytest.mark.stage3
def test_jonas_at_ember_cannot_read_harbors_brief(settings, request_for, trace):
    """5 · the session's attack, as it is told: a path that looks local and resolves into Harbor's workspace."""
    harbor = for_request(request_for(workspace_id="harbor", session_id="k7c1"), settings)
    tool("write_file", "make_write_file", harbor, trace)("campaign-brief.md", "under embargo until the fourteenth")
    jonas = for_request(request_for(workspace_id="ember", user_id="jonas", session_id="t3a9"), settings)

    out = tool("read_file", "make_read_file", jonas, trace)("../../harbor/k7c1/campaign-brief.md")

    assert out.lower().startswith("refused"), f"Jonas read Harbor's embargoed brief: {out!r}"
    assert "embargo" not in out


@pytest.mark.stage3
def test_a_symbolic_link_out_is_refused(workspace, tmp_path):
    """5 · a symbolic link counts as leaving, which is why the check resolves before it compares."""
    outside = tmp_path / "outside.md"
    outside.write_text("not yours", encoding="utf-8")
    link = workspace.drawer("work") / "looks-local.md"
    link.symlink_to(outside)
    with pytest.raises(OutsideWorkspace):
        resolve_in_workspace(workspace.root, "work/looks-local.md")


@pytest.mark.stage3
def test_a_folder_whose_name_starts_the_same_is_refused(settings, request_for):
    """5 · t3a9-old is not t3a9. Comparing the text of a path says it is."""
    ember = for_request(request_for(workspace_id="ember", session_id="t3a9"), settings)
    (ember.root.parent / "t3a9-old").mkdir(parents=True, exist_ok=True)
    with pytest.raises(OutsideWorkspace):
        resolve_in_workspace(ember.root, "../t3a9-old/brand-book.md")


@pytest.mark.stage3
def test_a_legitimate_path_still_resolves(workspace):
    """10 · a legitimate read still succeeds, because a fence that is too tight is also a defect."""
    real = resolve_in_workspace(workspace.root, "outputs/poster.png")
    assert real.is_relative_to(workspace.root)


@pytest.mark.stage3
@pytest.mark.parametrize("module, factory, args", [
    ("read_file", "make_read_file", ("../../harbor/x.md",)),
    ("write_file", "make_write_file", ("../../harbor/x.md", "nope")),
    ("list_files", "make_list_files", ("../..",)),
    ("search_files", "make_search_files", ("lifetime", "../..")),
])
def test_every_tool_refuses_through_the_same_door_and_says_so_on_the_trace(workspace, trace, module, factory, args):
    """5, 11 · every tool refuses, and every refusal is on the trace with the tool name and the reason."""
    out = tool(module, factory, workspace, trace)(*args)

    assert out.lower().startswith("refused"), f"{module} did not refuse: {out!r}"
    refusals = [e for e in trace.events if e.kind == "file_refused"]
    assert refusals and refusals[-1].detail["tool"] == module and refusals[-1].detail["reason"]


@pytest.mark.stage3
def test_the_brands_own_files_can_still_be_read(settings, request_for, trace):
    """10 · a legitimate read of a shared brand file still succeeds, because a fence that is too tight is also a defect."""
    ws = for_request(request_for(workspace_id="harbor", session_id="k7c1"), settings)
    out = tool("read_file", "make_read_file", ws, trace)("brand/brand-book.md")
    assert not out.lower().startswith(("refused", "no file")), out
    assert len(out) > 0


@pytest.mark.stage3
def test_the_download_route_goes_through_the_same_door(settings, request_for, trace, monkeypatch):
    """5, 12 · the download route is the fourth caller: a file the conversation owns downloads, a path out of it does not."""
    from fastapi.testclient import TestClient

    from launchkit.web import app as web

    monkeypatch.setattr(web, "settings", settings)
    harbor = for_request(request_for(workspace_id="harbor", session_id="k7c1"), settings)
    tool("write_file", "make_write_file", harbor, trace)("outputs/brief.md", "the brief")
    tool("write_file", "make_write_file", for_request(request_for(workspace_id="ember", session_id="t3a9"), settings), trace)("outputs/other.md", "ember's")

    page = TestClient(web.app)
    assert page.get("/workspace/harbor/k7c1/outputs/brief.md").text == "the brief"
    # The client flattens a literal `..` before sending, so the attack that reaches the server is the encoded one.
    assert page.get("/workspace/harbor/k7c1/..%2F..%2Fember%2Ft3a9%2Foutputs%2Fother.md").status_code == 404
    assert page.get("/workspace/harbor/k7c1/outputs/missing.md").status_code == 404


# Stage 4: an edit tool ------------------------------------------------------

@pytest.mark.stage4
def test_an_edit_changes_the_one_line_and_nothing_else(workspace, trace):
    """6 · an edit replaces the text it was asked to replace and nothing else."""
    write = tool("write_file", "make_write_file", workspace, trace)
    edit = tool("edit_file", "make_edit_file", workspace, trace)
    original = "Positioning\navoid the lifetime-guarantee framing\nTone\nwarm and plain\nPlacements\nsquare\n"
    write("outputs/brief.md", original)

    edit("outputs/brief.md", "avoid the lifetime-guarantee framing", "lean into the five-year warranty")
    after = (workspace.root / "outputs/brief.md").read_text(encoding="utf-8")

    assert after == original.replace("avoid the lifetime-guarantee framing", "lean into the five-year warranty")


@pytest.mark.stage4
def test_an_edit_refuses_when_the_old_text_is_missing(workspace, trace):
    """6 · it refuses when the old text is missing, and the file is untouched."""
    write = tool("write_file", "make_write_file", workspace, trace)
    edit = tool("edit_file", "make_edit_file", workspace, trace)
    write("outputs/brief.md", "Tone\nwarm and plain\n")

    out = edit("outputs/brief.md", "never clever", "playful")

    assert "not found" in out.lower() or "no match" in out.lower() or "missing" in out.lower()
    assert (workspace.root / "outputs/brief.md").read_text(encoding="utf-8") == "Tone\nwarm and plain\n"


@pytest.mark.stage4
def test_an_edit_refuses_when_the_old_text_appears_twice(workspace, trace):
    """6 · it refuses when the old text appears more than once, and says how many."""
    write = tool("write_file", "make_write_file", workspace, trace)
    edit = tool("edit_file", "make_edit_file", workspace, trace)
    write("outputs/brief.md", "lifetime\nlifetime\n")

    out = edit("outputs/brief.md", "lifetime", "five-year")

    assert "2" in out, f"it did not say how many matched: {out!r}"
    assert (workspace.root / "outputs/brief.md").read_text(encoding="utf-8") == "lifetime\nlifetime\n"


# Stage 5: the artifact record -----------------------------------------------

@pytest.mark.stage5
def test_an_artifact_is_recorded_against_its_message_and_writer(workspace):
    """7 · every artifact is recorded against the session and the message, by the code that wrote it."""
    record(workspace.root, Path("outputs/poster.png"), by="generate_image", message="m1")
    got = entries(workspace.root)
    assert len(got) == 1
    assert (got[0].path, got[0].by, got[0].message) == ("outputs/poster.png", "generate_image", "m1")


@pytest.mark.stage5
def test_a_tool_writes_its_own_record_entry(workspace, trace):
    """7 · the code that writes a file is the code that records it, so nothing has to be collected afterwards."""
    tool("write_file", "make_write_file", workspace, trace, "m7")("outputs/brief.md", "text")
    assert [(e.path, e.by, e.message) for e in entries(workspace.root)] == [("outputs/brief.md", "write_file", "m7")]


@pytest.mark.stage5
def test_the_record_survives_a_turn_that_fails_partway(workspace):
    """7 · the record survives a turn that fails partway."""
    record(workspace.root, Path("competitors/figma.md"), by="research", message="m1")
    try:
        raise RuntimeError("the turn died here")
    except RuntimeError:
        pass
    assert len(entries(workspace.root)) == 1, "the artifact written before the failure was lost"


def _page(monkeypatch, settings):
    from launchkit.web import app as web

    monkeypatch.setattr(web, "settings", settings)
    return web


@pytest.mark.stage5
def test_the_chat_page_lists_a_brief_it_used_to_miss(settings, request_for, trace, monkeypatch):
    """2, 8 · a research brief is a .md file. The old scan only knew pictures and sounds, so it never appeared."""
    web = _page(monkeypatch, settings)
    req = request_for(workspace_id="harbor", session_id="k7c1")
    ws = for_request(req, settings)
    tool("write_file", "make_write_file", ws, trace, "m1")("competitors/figma.md", "brief")

    assert web.listed_files(settings, req, "m1") == ["/workspace/harbor/k7c1/competitors/figma.md"]


@pytest.mark.stage5
def test_drafts_exist_and_are_not_shown(settings, request_for, trace, monkeypatch):
    """2 · the chat page shows finished work only. Drafts and rejected variants exist and are not shown."""
    web = _page(monkeypatch, settings)
    req = request_for(workspace_id="harbor", session_id="k7c1")
    ws = for_request(req, settings)
    write = tool("write_file", "make_write_file", ws, trace, "m1")
    write("work/rejected-variant.md", "draft")
    write("outputs/approved.md", "final")

    shown = web.listed_files(settings, req, "m1")
    assert shown == ["/workspace/harbor/k7c1/outputs/approved.md"]
    assert (ws.root / "work/rejected-variant.md").exists()


@pytest.mark.stage5
def test_nothing_another_brand_made_in_the_same_minute_is_listed(settings, request_for, trace, monkeypatch):
    """12 · no file made for one brand is listed for another, even when both were written during the same turn."""
    web = _page(monkeypatch, settings)
    maya = request_for(workspace_id="harbor", session_id="k7c1")
    jonas = request_for(workspace_id="ember", user_id="jonas", session_id="t3a9")
    tool("write_file", "make_write_file", for_request(maya, settings), trace, "m1")("outputs/brief.md", "harbor's")
    tool("write_file", "make_write_file", for_request(jonas, settings), trace, "m1")("outputs/poster-notes.md", "ember's")

    assert web.listed_files(settings, maya, "m1") == ["/workspace/harbor/k7c1/outputs/brief.md"]


@pytest.mark.stage5
def test_a_turn_that_dies_partway_still_shows_what_it_made(settings, request_for, trace, monkeypatch):
    """7 · the record survives a turn that fails partway, and so does the page's view of it."""
    web = _page(monkeypatch, settings)
    req = request_for(workspace_id="harbor", session_id="k7c1")
    tool("write_file", "make_write_file", for_request(req, settings), trace, "m9")("outputs/half-done.md", "text")

    assert web._made_before_failing(settings, req, "m9") == ["/workspace/harbor/k7c1/outputs/half-done.md"]


@pytest.mark.stage5
def test_a_picture_or_a_voice_over_is_recorded_by_the_tool_that_made_it(settings, request_for, trace):
    """7 · a poster, a size and a voice-over go in the record the moment they are written, under the tool that wrote each."""
    req, attached, poster, size, voice = _media(settings, request_for, trace)
    ws = for_request(req, settings)

    recorded = {(e.by, e.path) for e in entries(ws.root) if e.message == "m1"}
    assert recorded == {("generate_image", f"outputs/{poster.name}"), ("scale", f"outputs/{size.name}"), ("text_to_speech", f"outputs/{voice.name}")}


@pytest.mark.stage5
def test_a_picture_is_shown_through_the_fenced_route_only(settings, request_for, trace, monkeypatch):
    """12 · what a turn made is listed and served through the conversation's own route; the old door that served any media under data/ is closed."""
    from fastapi.testclient import TestClient

    web = _page(monkeypatch, settings)
    req, attached, poster, size, voice = _media(settings, request_for, trace)

    shown = web.listed_files(settings, req, "m1")
    assert shown == [f"/workspace/harbor/k7c1/outputs/{name}" for name in (poster.name, size.name, voice.name)]
    page = TestClient(web.app)
    assert page.get(shown[0]).status_code == 200
    assert page.get(f"/files/{poster.relative_to(settings.data_dir).as_posix()}").status_code == 404


# Stage 6: shared files, a discussion with no build ----------------------------

@pytest.mark.stage6
def test_the_brands_shared_files_are_outside_the_workspace_and_cannot_be_written(workspace, trace):
    """9 · shared brand files are readable by the agent and not writable by it."""
    assert not workspace.shared.is_relative_to(workspace.root), "the brand's files are a drawer of the conversation"
    out = tool("write_file", "make_write_file", workspace, trace)(f"../../{workspace.brand}/brand-book.md", "tidied")
    assert out.lower().startswith("refused"), "the agent could overwrite the brand book"


# The ticket: five writers, four entries lost ---------------------------------

@pytest.mark.ticket
def test_two_writers_both_survive(workspace):
    """The ticket as a check: five subagents write at once and no entry is lost.

    It interleaves the reads the way five parallel writers do, with no sleeps and nothing to force, so it fails the
    same way every time on a record that is read, appended to and written back. Every one of the five edits would
    match exactly once, because each appends a different line, which is why the edit tool's check does not help.
    """
    names = ["figma", "canva", "adobe", "affinity", "penpot"]
    with ThreadPoolExecutor(max_workers=5) as pool:
        list(pool.map(lambda n: record(workspace.root, Path(f"competitors/{n}.md"), by="research", message="m1"), names))

    got = {e.path for e in entries(workspace.root)}
    assert got == {f"competitors/{n}.md" for n in names}, f"entries were lost: only {sorted(got)} survived"


@pytest.mark.ticket
def test_five_tools_built_together_keep_every_entry(workspace, trace):
    """The ticket as it happens live, with no threads and nothing to time.

    A research subagent builds its own write tool when it starts, before it has searched anything. Five of them
    are built together, then each finishes and writes its brief. Each tool loaded the same empty record, so on a
    record that is loaded once and written back whole the last one to write wins and four entries are gone.
    """
    writers = [tool("write_file", "make_write_file", workspace, trace, "m1") for _ in range(5)]
    for number, write in enumerate(writers):
        write(f"competitors/c{number}.md", "brief")

    assert len(entries(workspace.root)) == 5, f"only {len(entries(workspace.root))} of 5 survived"


@pytest.mark.ticket
def test_a_retry_does_not_record_the_same_artifact_twice(workspace):
    """A tool call that times out and runs again must not put the same entry in twice."""
    for _ in range(2):
        record(workspace.root, Path("outputs/poster.png"), by="generate_image", message="m1")
    assert len(entries(workspace.root)) == 1, "a retry doubled the entry"


# The starting state -----------------------------------------------------------

def test_the_seed_gives_the_room_conversations_it_can_name(settings, monkeypatch):
    """The stage 3 attack names Harbor's workspace, so the conversation ids have to be ones everyone can type."""
    from launchkit.files.seed import build

    from launchkit.web import app as web

    build(settings.data_dir)
    monkeypatch.setattr(web, "settings", settings)

    maya = web._load_conversation("harbor", "maya", "k7c1")
    jonas = web._load_conversation("ember", "jonas", "t3a9")
    assert maya["session_id"] == "k7c1" and any("lifetime" in (t.get("reply") or "") for t in maya["turns"])
    assert jonas["session_id"] == "t3a9" and jonas["turns"]
    assert (settings.data_dir / "files" / "ember" / "t3a9-old").is_dir(), "the lookalike conversation is missing"
