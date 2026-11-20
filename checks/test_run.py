"""Session 5's checks. Each one reads an acceptance criterion the room agreed, and each belongs to a stage.

The session runs in stages, like red and green in test-driven work. A failure shows live, the room writes that
stage's criteria, the lead runs the prompt, and that stage's checks go green:

    uv run pytest checks/test_run.py -m stage1        or: uv run launchkit check run1

Every stage's checks fail on `session-05-runtime-prd` and pass on `session-05-runtime-solutions`. They are the
specification written as code, and they are what "done" means for a stage. The stages, in order:

    stage1  run_code: the agent's code runs as a separate process in the conversation's folder, with a time limit
    stage2  the code runs in a throwaway container: this conversation only, no keys, no network
    stage3  limits on memory, processor, processes and disk, and the reason a run was stopped
    stage4  jobs: a record and an event log on disk, Stop, and one job at a time per conversation
    stage5  steps on disk with keys: a restart resumes, and nothing that was done is done again

Stages 2 and 3 need Docker. Without it their checks are skipped, with the reason, and the room treats stage 2 as a
discussion. Stages 4 and 5 hand the job runner a short scripted turn, so they need neither Docker nor a model.

The interface the checks expect, so the lead's prompt and the room's build agree on names:

    launchkit.tools.run_code     make_run_code(workspace, trace, message, limits) -> Entry whose .fn is
                                 run_code(code, label="") -> str
    launchkit.sandbox.limits     RunLimits(seconds, output_chars[, memory_mb, cpus, processes, disk_mb])
                                 docker_flags(limits) -> list[str], stop_reason(exit_code, timed_out, oom_killed, output)
    launchkit.sandbox.container  run_in_container(workspace, code, limits) -> Ran
    launchkit.jobs.record        create, load, current, append_event, events_after; a Job's status is running,
                                 stopping, stopped, done or failed
    launchkit.jobs.runner        start_job(settings, body, run_turn) -> {"job_id", "waiting"}, stop_job(settings, job_id)
    launchkit.jobs.steps         step_hook(settings, job_id[, emit]), resume_jobs(settings, run_turn) -> [job ids]

Criteria 2 and 11 are the room's own: Harbor did not ask for a time limit or for a rule about a second message.
"""

import csv
import io
import json
import re
import subprocess
import threading
import time

import pytest

from launchkit.files.record import entries
from launchkit.files.seed import breeze_results
from launchkit.files.workspace import for_request
from launchkit.sandbox import engine
from launchkit.sandbox.limits import RunLimits
from launchkit.tools.catalogue import built
from launchkit.tools.run_code import make_run_code


def run_code(workspace, trace, limits=None, message="m1"):
    """The agent's code tool, built the way the catalogue builds it."""
    return make_run_code(workspace, trace, message, limits).fn


def printed(result: str) -> dict:
    """The one line the check's own code prints as RESULT {...}."""
    found = re.search(r"RESULT (\{.*\})", result)
    assert found, f"the code's RESULT line is not in what run_code returned:\n{result[:600]}"
    return json.loads(found.group(1))


def code_runs(trace):
    return [e for e in trace.events if e.kind == "code_run"]


@pytest.fixture
def harbor(settings, request_for):
    """Maya's Breeze conversation, with Breeze's first week of ads in it."""
    ws = for_request(request_for(workspace_id="harbor", user_id="maya", session_id="k7c1"), settings)
    (ws.drawer("uploads") / "breeze-results.csv").write_text(breeze_results(), encoding="utf-8")
    (ws.drawer("outputs") / "campaign-brief.md").write_text("# Breeze campaign brief\n", encoding="utf-8")
    return ws


@pytest.fixture
def ember(settings, request_for, harbor):
    """Jonas's conversation at Ember. Harbor's folder exists next to it, so there is something to reach for."""
    return for_request(request_for(workspace_id="ember", user_id="jonas", session_id="t3a9"), settings)


@pytest.fixture
def sandbox():
    """Stages 2 and 3 run the code in a container: skip, with the reason, on a machine without Docker."""
    problem = engine.docker_problem()
    if problem:
        pytest.skip(f"needs Docker: {problem}")
    if not engine.image_ready():
        engine.build_image()


def cheapest_by_hand() -> tuple[str, float]:
    """What the room works out by hand on the opening slide: total spend over total sign-ups, per channel."""
    totals = {}
    for row in csv.DictReader(io.StringIO(breeze_results())):
        spend, signups = totals.get(row["channel"], (0.0, 0))
        totals[row["channel"]] = (spend + float(row["spend"]), signups + int(row["signups"]))
    channel = min(totals, key=lambda c: totals[c][0] / totals[c][1])
    return channel, round(totals[channel][0] / totals[channel][1], 2)


COST_PER_SIGNUP = """import csv
totals = {}
for row in csv.DictReader(open("uploads/breeze-results.csv")):
    spend, signups = totals.get(row["channel"], (0.0, 0))
    totals[row["channel"]] = (spend + float(row["spend"]), signups + int(row["signups"]))
channel = min(totals, key=lambda c: totals[c][0] / totals[c][1])
print("cheapest", channel, round(totals[channel][0] / totals[channel][1], 2))
"""


# Stage 1: a code tool -------------------------------------------------------------------------------------------

@pytest.mark.stage1
def test_figures_come_from_code_run_on_the_file(harbor, trace):
    """1 · a figure comes from code run on the conversation's file, and the code is on the trace."""
    result = run_code(harbor, trace)(COST_PER_SIGNUP, label="cost-per-signup")

    channel, cost = cheapest_by_hand()
    assert f"cheapest {channel} {cost}" in result, f"the code's answer is not in what run_code returned:\n{result[:400]}"
    runs = code_runs(trace)
    assert runs and "breeze-results.csv" in runs[-1].detail["code"], "the trace does not show the code that ran"
    assert runs[-1].detail["exit_code"] == 0


@pytest.mark.stage1
def test_the_agent_can_call_run_code(settings, harbor, trace):
    """1 · run_code is in the main agent's catalogue, so the agent can find it and call it."""
    from launchkit.agents.main_agent import build_catalogue

    catalogue = build_catalogue(settings, trace, lambda name, inputs: True, files=harbor, message="m1")
    assert "run_code" in catalogue.entries


@pytest.mark.stage1
def test_what_the_code_printed_is_cut_to_size_and_says_so(harbor, trace):
    """1 · the model gets what the code printed, cut to a set size, with a note when something was cut."""
    result = run_code(harbor, trace, RunLimits(seconds=20, output_chars=4000))('print("x" * 50000)')

    assert len(result) < 4600, f"run_code handed back {len(result)} characters; the limit is 4000 and a short note"
    assert "cut" in result.lower(), "nothing says the output was cut"


@pytest.mark.stage1
def test_a_run_past_its_time_is_stopped_and_reported(harbor, trace):
    """2 · a run past its time limit is stopped, the agent is told why, and nothing it started keeps running."""
    code = """import subprocess, sys
subprocess.Popen([sys.executable, "-c", "import pathlib, time\\nwhile True:\\n    pathlib.Path('alive.txt').write_text(str(time.time()))\\n    time.sleep(0.2)"])
while True:
    pass
"""
    started = time.monotonic()
    result = run_code(harbor, trace, RunLimits(seconds=2))(code)
    took = time.monotonic() - started

    assert took < 15, f"a run with a 2-second limit took {took:.0f} seconds"
    assert "time" in result.lower() and "stop" in result.lower(), f"the agent is not told the run was stopped for time:\n{result[:300]}"
    assert code_runs(trace)[-1].detail["stopped"] == "time"
    alive = harbor.root / "alive.txt"
    if alive.exists():
        before = alive.stat().st_mtime
        time.sleep(1.5)
        assert alive.stat().st_mtime == before, "a process the code started is still running after the run was stopped"


@pytest.mark.stage1
def test_files_the_code_makes_land_in_this_conversation(harbor, trace):
    """3 · a file the code writes lands in this conversation's workspace, recorded against the message that asked."""
    code = """import os
os.makedirs("outputs", exist_ok=True)
open("outputs/channel-costs.csv", "w").write("channel,cost per sign-up\\nSocial,6.49\\n")
print("saved")
"""
    result = run_code(harbor, trace, message="m7")(code, label="channel-costs")

    assert (harbor.root / "outputs" / "channel-costs.csv").is_file()
    recorded = [e for e in entries(harbor.root) if e.path == "outputs/channel-costs.csv"]
    assert recorded and recorded[-1].message == "m7" and recorded[-1].by == "run_code", "the file is not in the record"
    assert "outputs/channel-costs.csv" in result, "the agent is not told which files the code wrote"
    assert "outputs/channel-costs.csv" in code_runs(trace)[-1].detail["files"]


# Stage 2: a container ------------------------------------------------------------------------------------------

@pytest.mark.stage2
def test_the_code_reaches_only_this_conversation_and_the_brand_read_only(sandbox, ember, harbor, trace):
    """4 · code run for Jonas reaches his conversation and Ember's files, read only, and nothing of Harbor's."""
    code = f"""import json, os
seen = {{}}
def attempt(name, action):
    try:
        action()
        seen[name] = "allowed"
    except OSError as error:
        seen[name] = type(error).__name__
attempt("climb to harbor", lambda: os.listdir("../../harbor"))
attempt("harbor by its full path", lambda: os.listdir({str(harbor.root)!r}))
attempt("read the brand book", lambda: open("/brand/brand-book.md").read())
attempt("write the brand book", lambda: open("/brand/brand-book.md", "a").write("x"))
attempt("write outside /work", lambda: open("/usr/local/planted.txt", "w").write("x"))
attempt("write in /work", lambda: open("notes.txt", "w").write("x"))
seen["user id"] = os.getuid()
print("RESULT " + json.dumps(seen))
"""
    seen = printed(run_code(ember, trace)(code))

    assert seen["climb to harbor"] != "allowed", "the code listed Harbor's folder with ../"
    assert seen["harbor by its full path"] != "allowed", "the code listed Harbor's folder by its full path"
    assert seen["read the brand book"] == "allowed", "the brand's own files are not readable: a fence too tight is a defect too"
    assert seen["write the brand book"] != "allowed", "the code changed the brand book"
    assert seen["write outside /work"] != "allowed", "the container's root disk can be written"
    assert seen["write in /work"] == "allowed", "the code cannot write in its own conversation"
    assert seen["user id"] != 0, "the code runs as root"


@pytest.mark.stage2
def test_no_key_or_secret_is_visible_to_the_code(sandbox, harbor, trace, monkeypatch):
    """5 · no key the server holds is visible to the code."""
    monkeypatch.setenv("LITELLM_API_KEY", "sk-visible-to-the-sandbox")
    monkeypatch.setenv("IMAGESVC_KEY", "img-visible-to-the-sandbox")
    result = run_code(harbor, trace)("import os\nprint('RESULT ' + __import__('json').dumps(dict(os.environ)))")

    assert "sk-visible-to-the-sandbox" not in result and "img-visible-to-the-sandbox" not in result, "a key reached the code"
    import os

    held = [k for k in os.environ if any(word in k for word in ("KEY", "TOKEN", "SECRET", "PASSWORD"))]
    assert not [k for k in printed(result) if k in held], "a key the server holds is in the code's environment"


@pytest.mark.stage2
def test_the_code_has_no_network(sandbox, harbor, trace):
    """6 · the code cannot reach the internet, by address or by name."""
    code = """import json, socket
seen = {}
for name, address in (("by address", ("1.1.1.1", 53)), ("by name", ("pypi.org", 443))):
    try:
        socket.create_connection(address, timeout=3).close()
        seen[name] = "connected"
    except OSError as error:
        seen[name] = type(error).__name__
print("RESULT " + json.dumps(seen))
"""
    seen = printed(run_code(harbor, trace)(code))

    assert seen["by address"] != "connected" and seen["by name"] != "connected", f"the code reached the internet: {seen}"


@pytest.mark.stage2
def test_nothing_of_the_run_is_left_behind(sandbox, harbor, trace):
    """4 · the container lives for one run: when the run ends, the container is gone."""
    mine = lambda: set(subprocess.run(["docker", "ps", "-aq", "--filter", f"name={engine.name_prefix('harbor', 'k7c1')}"], capture_output=True, text=True).stdout.split())  # noqa: E731
    before = mine()
    run_code(harbor, trace)("print('done')")

    assert not mine() - before, "a container from this run is still there after it ended"


# Stage 3: limits -----------------------------------------------------------------------------------------------

@pytest.mark.stage3
def test_every_limit_reaches_the_container():
    """7 · memory, processor, processes, disk and time each have a number, and each number reaches docker run."""
    limits = RunLimits()
    for name in ("seconds", "memory_mb", "cpus", "processes", "disk_mb"):
        assert getattr(limits, name), f"RunLimits has no number for {name}"
    from launchkit.sandbox.limits import docker_flags

    flags = " ".join(docker_flags(limits))
    for flag in ("--memory", "--cpus", "--pids-limit", "/tmp"):
        assert flag in flags, f"{flag} is not in the container's options: {flags}"


@pytest.mark.stage3
@pytest.mark.parametrize("reason, code, limits", [
    ("memory", "chunks = []\nwhile True:\n    chunks.append(bytearray(32 * 1024 * 1024))",
     dict(seconds=20, memory_mb=256)),
    ("processes", "import subprocess, sys\nchildren = [subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)']) for _ in range(60)]",
     dict(seconds=20, processes=16)),
    ("disk", "with open('/tmp/big', 'wb') as out:\n    for _ in range(80):\n        out.write(b'0' * 1024 * 1024)",
     dict(seconds=20, disk_mb=20)),
], ids=["memory", "processes", "disk"])
def test_a_runaway_is_stopped_with_the_reason_on_the_trace(sandbox, harbor, trace, reason, code, limits):
    """7 · a run that uses too much is stopped, and the reason is on the trace and in what the agent is told."""
    started = time.monotonic()
    result = run_code(harbor, trace, RunLimits(**limits))(code)

    assert time.monotonic() - started < 25
    assert code_runs(trace)[-1].detail["stopped"] == reason, f"the trace says {code_runs(trace)[-1].detail['stopped']!r}, not {reason!r}"
    assert reason in result.lower(), f"the agent is not told the run was stopped for {reason}:\n{result[:300]}"


@pytest.mark.stage3
def test_one_run_never_slows_another_conversation(sandbox, harbor, ember, trace):
    """8 · while one conversation's code burns every processor it can, another conversation's code still runs at once."""
    burner = """import os
for _ in range((os.cpu_count() or 4) - 1):
    if os.fork() == 0:
        break
while True:
    pass
"""
    busy = threading.Thread(target=lambda: run_code(ember, trace, RunLimits(seconds=8))(burner))
    busy.start()
    time.sleep(2)
    burning = subprocess.run(["docker", "ps", "-q", "--filter", f"name={engine.name_prefix('ember', 't3a9')}"], capture_output=True, text=True).stdout.split()
    caps = [subprocess.run(["docker", "inspect", "-f", "{{.HostConfig.NanoCpus}}", c], capture_output=True, text=True).stdout.strip() for c in burning]
    started = time.monotonic()
    result = run_code(harbor, trace, RunLimits(seconds=8))("print('RESULT ' + str({'total': sum(range(2_000_000))}).replace(\"'\", '\"'))")
    took = time.monotonic() - started
    still_busy = busy.is_alive()
    busy.join()

    assert printed(result)["total"] == sum(range(2_000_000))
    assert still_busy, "the busy run ended before the second one finished, so this shows nothing"
    assert caps and all(c.isdigit() and 0 < int(c) <= RunLimits().cpus * 1e9 for c in caps), f"the busy run's container has no processor limit: {caps}"
    assert took < 5, f"the second conversation waited {took:.1f} seconds behind the first"


# Stage 4: jobs -------------------------------------------------------------------------------------------------

def body(text="Every size of the Breeze poster, please.", session="k7c1", user="maya", brand="harbor"):
    return {"workspace_id": brand, "user_id": user, "session_id": session, "text": text, "model": None, "attached": []}


def through(hooks, name, fn, arguments):
    """Call a tool the way Agno does when an agent has tool hooks: each hook wraps the next, and the last wraps the tool."""
    call = fn
    for hook in reversed(list(hooks)):
        call = (lambda h, inner: lambda **a: h(name, inner, a))(hook, call)
    return call(**arguments)


def wait_for(check, seconds=10.0):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        if check():
            return True
        time.sleep(0.05)
    return False


def status(settings, job_id):
    from launchkit.jobs.record import load

    return load(settings, job_id).status


@pytest.mark.stage4
def test_closing_the_page_does_not_stop_the_job(settings):
    """9 · a job runs apart from the page that started it, and a page that comes back can replay it from any point."""
    from launchkit.jobs.record import current, events_after
    from launchkit.jobs.runner import start_job

    def turn(body, emit, hooks=()):
        for n in range(1, 6):
            time.sleep(0.1)
            emit({"type": "trace", "kind": "note", "line": f"step {n}"})
        emit({"type": "result", "reply": "done"})

    started = time.monotonic()
    job = start_job(settings, body(), turn)
    assert time.monotonic() - started < 0.5, "start_job waited for the turn instead of returning at once"
    assert not job["waiting"]
    assert current(settings, "harbor", "k7c1") is not None, "the running job cannot be found from its conversation"

    assert wait_for(lambda: status(settings, job["job_id"]) == "done"), "the job did not finish with nobody watching"
    every = events_after(settings, job["job_id"], 0)
    assert [e["line"] for e in every if e["type"] == "trace"] == [f"step {n}" for n in range(1, 6)]
    assert [e["seq"] for e in every] == list(range(1, len(every) + 1)), "events are not numbered 1, 2, 3 in order"
    assert events_after(settings, job["job_id"], 3)[0]["seq"] == 4, "a page cannot replay from where it got to"
    assert every[-1]["type"] == "end" and every[-1]["status"] == "done"
    assert current(settings, "harbor", "k7c1") is None, "a finished job still counts as running"


@pytest.mark.stage4
def test_stop_ends_the_job_in_seconds(settings):
    """10 · Stop ends a running job within a few seconds, and the job says it was stopped."""
    from launchkit.jobs.record import events_after
    from launchkit.jobs.runner import start_job, stop_job

    def turn(body, emit, hooks=()):
        for _ in range(600):
            through(hooks, "run_tool", lambda **a: time.sleep(0.05), {"name": "crop", "inputs": {}})

    job = start_job(settings, body(), turn)["job_id"]
    time.sleep(0.3)
    pressed = time.monotonic()
    stop_job(settings, job)

    assert wait_for(lambda: status(settings, job) == "stopped", 5), f"the job is {status(settings, job)!r} five seconds after Stop"
    assert time.monotonic() - pressed < 5
    last = events_after(settings, job, 0)[-1]
    assert last["type"] == "end" and last["status"] == "stopped"


@pytest.mark.stage4
def test_stop_kills_the_sandbox_the_job_started(settings, sandbox):
    """10 · nothing the job started keeps running: Stop kills this conversation's containers."""
    from launchkit.jobs.runner import start_job, stop_job

    name = engine.container_name("harbor", "k7c1")

    def turn(body, emit, hooks=()):
        subprocess.run(["docker", "run", "--rm", "--name", name, "--network", "none", engine.IMAGE, "sleep", "60"], capture_output=True)
        for _ in range(100):
            through(hooks, "run_tool", lambda **a: time.sleep(0.05), {"name": "crop", "inputs": {}})

    job = start_job(settings, body(), turn)["job_id"]
    running = lambda: subprocess.run(["docker", "ps", "-q", "--filter", f"name={name}"], capture_output=True, text=True).stdout.strip()
    assert wait_for(lambda: bool(running()), 20), "the scripted turn's container never started"
    stop_job(settings, job)

    assert wait_for(lambda: not running(), 10), "the job's container is still running after Stop"
    assert wait_for(lambda: status(settings, job) == "stopped", 5)


@pytest.mark.stage4
def test_a_message_mid_job_waits_and_says_so(settings):
    """11 · a second message to a conversation with a job running waits for it, is told so, and never runs beside it."""
    from launchkit.jobs.record import events_after
    from launchkit.jobs.runner import start_job

    ran = []

    def turn(body, emit, hooks=()):
        began = time.monotonic()
        time.sleep(0.6)
        ran.append((body["text"], began, time.monotonic()))
        emit({"type": "result", "reply": body["text"]})

    first = start_job(settings, body("Every size, please."), turn)
    second = start_job(settings, body("Also make the headline blue."), turn)
    elsewhere = start_job(settings, body("A poster for Night Shift.", session="t3a9", user="jonas", brand="ember"), turn)

    assert second["waiting"] is True and second["job_id"] == first["job_id"], "the second message did not wait"
    assert elsewhere["waiting"] is False, "a message to another conversation waited for this one"
    assert any(e["type"] == "waiting" for e in events_after(settings, first["job_id"], 0)), "the page is not told the message waits"
    assert wait_for(lambda: len(ran) == 3, 10), "the waiting message never ran"
    texts = {text: (began, ended) for text, began, ended in ran}
    assert texts["Also make the headline blue."][0] >= texts["Every size, please."][1], "the second message ran beside the first"


# Stage 5: steps on disk ----------------------------------------------------------------------------------------

def size_step(n: int) -> dict:
    return {"name": "run_code", "inputs": {"code": f"make size {n}", "label": f"size-{n}"}}


@pytest.mark.stage5
def test_a_step_with_a_key_runs_once(settings):
    """12 · a step that is done is not done again: the second call gets the first call's result back."""
    from launchkit.jobs.steps import step_hook

    effects = []

    def make_size(**inputs):
        effects.append(inputs)
        return f"made size {len(effects)}"

    hook = step_hook(settings, "j7")
    first = through([hook], "run_tool", make_size, size_step(1))
    again = through([step_hook(settings, "j7")], "run_tool", make_size, size_step(1))

    assert len(effects) == 1, "the step ran twice"
    assert again == first
    assert through([hook], "run_tool", make_size, size_step(2)) == "made size 2", "a new step was not run"


@pytest.mark.stage5
def test_a_restart_resumes_and_no_step_happens_twice(settings):
    """12 · a job a restart left running starts again, carries on from its last done step, and repeats none."""
    from launchkit.jobs.record import create, events_after
    from launchkit.jobs.steps import resume_jobs, step_hook

    made = settings.data_dir / "made.txt"

    def make(n):
        def tool(**inputs):
            with open(made, "a") as out:
                out.write(f"size {n}\n")
            return f"made size {n}"
        return tool

    def turn(body, emit, hooks=()):
        for n in range(1, 6):
            through(hooks, "run_tool", make(n), size_step(n))
            emit({"type": "trace", "kind": "note", "line": f"size {n}"})

    job = create(settings, body())
    before_the_restart = step_hook(settings, job.id)
    for n in (1, 2):  # the old server got this far, then stopped
        through([before_the_restart], "run_tool", make(n), size_step(n))

    resumed = resume_jobs(settings, turn)

    assert job.id in resumed, "the job a restart left running was not started again"
    assert wait_for(lambda: status(settings, job.id) == "done"), f"the resumed job is {status(settings, job.id)!r}"
    assert made.read_text().splitlines() == [f"size {n}" for n in range(1, 6)], "a step's effect happened twice, or not at all"
    assert events_after(settings, job.id, 0)[-1]["status"] == "done"


@pytest.mark.stage5
def test_a_finished_job_is_not_started_again(settings):
    """12 · only a job the restart interrupted is resumed: one that finished stays finished."""
    from launchkit.jobs.record import create, save
    from launchkit.jobs.steps import resume_jobs

    job = create(settings, body())
    job.status = "done"
    save(settings, job)
    calls = []

    assert job.id not in resume_jobs(settings, lambda *a, **k: calls.append(a))
    time.sleep(0.3)
    assert not calls
