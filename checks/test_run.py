"""Session 5's checks. Each one reads an acceptance criterion the room agreed.

The session has one hands-on: the agent's code runs in an OpenSandbox sandbox, with limits. Its checks are marked
`sandbox`. They fail on `session-05-runtime-prd`, where the code still runs as a local process, and pass on
`session-05-runtime-solutions`:

    uv run pytest checks/test_run.py -m sandbox        or: uv run launchkit check sandbox

Everything else in the session is ready-made: the code tool itself, jobs, Stop and resume. Its checks are marked
`ready`, and pass on both branches. They say what the ready-made pieces promise, so the room can trust them:

    uv run pytest checks/test_run.py -m ready          or: uv run launchkit check ready

The sandbox checks need Docker. They start the sandbox server themselves when it is not already running, and stop it
afterwards. Without Docker they are skipped, with the reason, and the room treats the hands-on as a discussion.

The interface the checks expect, so the lead's prompt and the room's build agree on names:

    launchkit.tools.run_code         make_run_code(workspace, trace, message, limits) -> Entry whose .fn is
                                     run_code(code, label="") -> str
    launchkit.sandbox.opensandbox    run_in_sandbox(workspace, code, limits) -> Ran          (the hands-on)
    launchkit.sandbox.limits         RunLimits(seconds, output_chars, memory_mb, cpus, processes),
                                     stop_reason(exit_code, timed_out, oom_killed, output)
    launchkit.sandbox.engine         server_problem(), connection(), labels(brand, conversation),
                                     sandboxes_of(brand, conversation), kill_sandboxes(brand, conversation)
    launchkit.jobs.runner            start_job(settings, body, run_turn) -> {"job_id", "waiting"}, stop_job(settings, job_id)
    launchkit.jobs.steps             step_hook(settings, job_id[, emit]), resume_jobs(settings, run_turn) -> [job ids]

Criteria 2 and 11 are the room's own: Harbor did not ask for a time limit or for a rule about a second message.
"""

import csv
import io
import json
import os
import re
import signal
import threading
import time
from datetime import timedelta

import pytest

from launchkit.files.record import entries
from launchkit.files.seed import breeze_results
from launchkit.files.workspace import for_request
from launchkit.sandbox import engine
from launchkit.sandbox.limits import RunLimits
from launchkit.sandbox.opensandbox import run_in_sandbox
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


@pytest.fixture(scope="session")
def sandbox_server():
    """Docker, the sandbox images, and the sandbox server: started here when it is not running already."""
    problem = engine.docker_problem()
    if problem:
        pytest.skip(f"needs Docker: {problem}")
    if not engine.image_ready():
        engine.build_image()
    engine.pull_images()
    started = None
    if not engine.server_reachable():
        started = engine.serve(background=True)
        end = time.monotonic() + 90
        while not engine.server_reachable() and time.monotonic() < end:
            time.sleep(0.5)
        if not engine.server_reachable():
            started.kill()
            pytest.fail("the sandbox server did not start within 90 seconds: run `uv run launchkit sandbox` to see why")
    yield
    if started is not None:
        os.killpg(started.pid, signal.SIGTERM)
        started.wait(20)


@pytest.fixture
def sandbox(sandbox_server):
    """A check that needs the sandbox server."""


@pytest.fixture
def code_tool(request):
    """The code tool's ready-made checks run wherever run_code runs: in the sandbox once the hands-on is built."""
    if built(run_in_sandbox):
        request.getfixturevalue("sandbox_server")


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


# Ready-made: the code tool ---------------------------------------------------------------------------------------

@pytest.mark.ready
def test_figures_come_from_code_run_on_the_file(code_tool, harbor, trace):
    """1 · a figure comes from code run on the conversation's file, and the code is on the trace."""
    result = run_code(harbor, trace)(COST_PER_SIGNUP, label="cost-per-signup")

    channel, cost = cheapest_by_hand()
    assert f"cheapest {channel} {cost}" in result, f"the code's answer is not in what run_code returned:\n{result[:400]}"
    runs = code_runs(trace)
    assert runs and "breeze-results.csv" in runs[-1].detail["code"], "the trace does not show the code that ran"
    assert runs[-1].detail["exit_code"] == 0


@pytest.mark.ready
def test_the_agent_can_call_run_code(settings, harbor, trace):
    """1 · run_code is in the main agent's catalogue, so the agent can find it and call it."""
    from launchkit.agents.main_agent import build_catalogue

    catalogue = build_catalogue(settings, trace, lambda name, inputs: True, files=harbor, message="m1")
    assert "run_code" in catalogue.entries


@pytest.mark.ready
def test_what_the_code_printed_is_cut_to_size_and_says_so(code_tool, harbor, trace):
    """1 · the model gets what the code printed, cut to a set size, with a note when something was cut."""
    result = run_code(harbor, trace, RunLimits(seconds=20, output_chars=4000))('print("x" * 50000)')

    assert len(result) < 4600, f"run_code handed back {len(result)} characters; the limit is 4000 and a short note"
    assert "cut" in result.lower(), "nothing says the output was cut"


@pytest.mark.ready
def test_a_run_past_its_time_is_stopped_and_reported(code_tool, harbor, trace):
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


@pytest.mark.ready
def test_files_the_code_makes_land_in_this_conversation(code_tool, harbor, trace):
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


# The hands-on: the code runs in an OpenSandbox sandbox, with limits ------------------------------------------------

@pytest.mark.sandbox
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
attempt("write in /work", lambda: open("notes.txt", "w").write("x"))
seen["user id"] = os.getuid()
print("RESULT " + json.dumps(seen))
"""
    seen = printed(run_code(ember, trace)(code))

    assert seen["climb to harbor"] != "allowed", "the code listed Harbor's folder with ../"
    assert seen["harbor by its full path"] != "allowed", "the code listed Harbor's folder by its full path"
    assert seen["read the brand book"] == "allowed", "the brand's own files are not readable at /brand: a wall too tight is a defect too"
    assert seen["write the brand book"] != "allowed", "the code changed the brand book"
    assert seen["write in /work"] == "allowed", "the code cannot write in its own conversation"
    assert seen["user id"] != 0, "the code runs as root"


@pytest.mark.sandbox
def test_no_key_or_secret_is_visible_to_the_code(sandbox, harbor, trace, monkeypatch):
    """5 · no key the server holds is visible to the code."""
    monkeypatch.setenv("LITELLM_API_KEY", "sk-visible-to-the-sandbox")
    monkeypatch.setenv("IMAGESVC_KEY", "img-visible-to-the-sandbox")
    result = run_code(harbor, trace)("import os\nprint('RESULT ' + __import__('json').dumps(dict(os.environ)))")

    assert "sk-visible-to-the-sandbox" not in result and "img-visible-to-the-sandbox" not in result, "a key reached the code"
    held = [k for k in os.environ if any(word in k for word in ("KEY", "TOKEN", "SECRET", "PASSWORD"))]
    assert not [k for k in printed(result) if k in held], "a key the server holds is in the code's environment"


@pytest.mark.sandbox
def test_the_code_has_no_network(sandbox, harbor, trace):
    """6 · the code cannot reach the internet, by address or by name."""
    code = """import json, socket
seen = {}
for name, address in (("by address", ("1.1.1.1", 443)), ("by name", ("pypi.org", 443))):
    try:
        socket.create_connection(address, timeout=3).close()
        seen[name] = "connected"
    except OSError as error:
        seen[name] = type(error).__name__
print("RESULT " + json.dumps(seen))
"""
    seen = printed(run_code(harbor, trace)(code))

    assert seen["by address"] != "connected" and seen["by name"] != "connected", f"the code reached the internet: {seen}"


@pytest.mark.sandbox
def test_the_code_runs_in_a_sandbox_that_is_gone_after_the_run(sandbox, harbor, trace):
    """4 · the code runs in a sandbox of its own, and when the run ends the sandbox is gone."""
    before = set(engine.sandboxes_of("harbor", "k7c1"))
    result = run_code(harbor, trace)("import json, os\nprint('RESULT ' + json.dumps({'cwd': os.getcwd(), 'brand': os.path.isdir('/brand')}))")

    seen = printed(result)
    assert seen == {"cwd": "/work", "brand": True}, f"the code did not run in the sandbox, in /work with /brand next to it: {seen}"
    assert not set(engine.sandboxes_of("harbor", "k7c1")) - before, "a sandbox from this run is still there after it ended"


@pytest.mark.sandbox
def test_without_the_sandbox_the_code_does_not_run(harbor, trace, monkeypatch):
    """4 · when no sandbox can be made, the code does not run at all: the tool fails closed, and says so."""
    monkeypatch.setattr(engine, "HOST", "127.0.0.1:9")
    marker = harbor.root / "ran.txt"
    result = run_code(harbor, trace)("open('ran.txt', 'w').write('ran')")

    assert not marker.exists(), "the code ran without a sandbox"
    assert "did not run" in result, f"the agent is not told the code did not run:\n{result[:300]}"
    assert any(e.kind == "refused" for e in trace.events), "the trace does not say the run was refused"


@pytest.mark.sandbox
def test_every_limit_reaches_the_sandbox(sandbox, harbor, trace):
    """7 · memory, processor and processes each have a number, and the sandbox's own cgroup holds it."""
    code = """import json
read = lambda name: open("/sys/fs/cgroup/" + name).read().split()
print("RESULT " + json.dumps({"cpu": read("cpu.max"), "memory": read("memory.max"), "pids": read("pids.max")}))
"""
    seen = printed(run_code(harbor, trace)(code))
    limits = RunLimits()

    quota, period = seen["cpu"]
    assert quota != "max" and int(quota) / int(period) <= limits.cpus, f"no processor limit on the sandbox: cpu.max is {seen['cpu']}"
    assert seen["memory"][0] != "max" and int(seen["memory"][0]) <= limits.memory_mb * 1024 * 1024, f"no memory limit: {seen['memory']}"
    assert seen["pids"][0] != "max" and int(seen["pids"][0]) <= limits.processes, f"no process limit: {seen['pids']}"


@pytest.mark.sandbox
@pytest.mark.parametrize("reason, code, limits", [
    ("memory", "chunks = []\nwhile True:\n    chunks.append(bytearray(32 * 1024 * 1024))",
     dict(seconds=25, memory_mb=256)),
    ("processes", "import subprocess, sys\nchildren = [subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)']) for _ in range(100)]",
     dict(seconds=25)),
], ids=["memory", "processes"])
def test_a_runaway_is_stopped_with_the_reason_on_the_trace(sandbox, harbor, trace, reason, code, limits):
    """7 · a run that uses too much is stopped, and the reason is on the trace and in what the agent is told."""
    started = time.monotonic()
    result = run_code(harbor, trace, RunLimits(**limits))(code)

    assert time.monotonic() - started < 40
    assert code_runs(trace)[-1].detail["stopped"] == reason, f"the trace says {code_runs(trace)[-1].detail['stopped']!r}, not {reason!r}"
    assert reason in result.lower(), f"the agent is not told the run was stopped for {reason}:\n{result[:300]}"


@pytest.mark.sandbox
def test_one_run_never_slows_another_conversation(sandbox, harbor, ember, trace):
    """8 · while one conversation's code burns every processor it can, another conversation's code still runs at once."""
    burner = """import os
print("RESULT " + __import__("json").dumps({"cpu": open("/sys/fs/cgroup/cpu.max").read().split()}), flush=True)
for _ in range((os.cpu_count() or 4) - 1):
    if os.fork() == 0:
        break
while True:
    pass
"""
    busy_result = {}
    busy = threading.Thread(target=lambda: busy_result.update(out=run_code(ember, trace, RunLimits(seconds=12))(burner)))
    busy.start()
    time.sleep(5)
    started = time.monotonic()
    result = run_code(harbor, trace, RunLimits(seconds=12))("print('RESULT ' + str({'total': sum(range(2_000_000))}).replace(\"'\", '\"'))")
    took = time.monotonic() - started
    still_busy = busy.is_alive()
    busy.join()

    assert printed(result)["total"] == sum(range(2_000_000))
    assert still_busy, "the busy run ended before the second one finished, so this shows nothing"
    quota, period = printed(busy_result["out"])["cpu"]
    assert quota != "max" and int(quota) / int(period) <= RunLimits().cpus, f"the busy run's sandbox has no processor limit: {quota} {period}"
    assert took < 8, f"the second conversation waited {took:.1f} seconds behind the first"


# Ready-made: jobs, Stop, one job per conversation -----------------------------------------------------------------

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


@pytest.mark.ready
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


@pytest.mark.ready
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


@pytest.mark.ready
def test_stop_kills_the_sandbox_the_job_started(settings, sandbox):
    """10 · nothing the job started keeps running: Stop kills this conversation's sandboxes."""
    from opensandbox.sync.sandbox import SandboxSync

    from launchkit.jobs.runner import start_job, stop_job

    def turn(body, emit, hooks=()):
        SandboxSync.create(engine.IMAGE, connection_config=engine.connection(), timeout=timedelta(minutes=2),
                           metadata=engine.labels("harbor", "k7c1")).close()
        for _ in range(300):
            through(hooks, "run_tool", lambda **a: time.sleep(0.05), {"name": "crop", "inputs": {}})

    job = start_job(settings, body(), turn)["job_id"]
    assert wait_for(lambda: bool(engine.sandboxes_of("harbor", "k7c1")), 30), "the scripted turn's sandbox never started"
    stop_job(settings, job)

    assert wait_for(lambda: not engine.sandboxes_of("harbor", "k7c1"), 15), "the job's sandbox is still there after Stop"
    assert wait_for(lambda: status(settings, job) == "stopped", 5)


@pytest.mark.ready
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


# Ready-made: steps on disk, resume after a restart ---------------------------------------------------------------

def size_step(n: int) -> dict:
    return {"name": "run_code", "inputs": {"code": f"make size {n}", "label": f"size-{n}"}}


@pytest.mark.ready
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


@pytest.mark.ready
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


@pytest.mark.ready
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
