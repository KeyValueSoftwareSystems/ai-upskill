"""Ready-made: the plumbing around the sandbox, so nobody spends session time on it.

The agent's code runs in OpenSandbox (github.com/opensandbox-group/OpenSandbox), an open-source sandbox server. The
server runs on this laptop, next to LaunchKit, and starts each sandbox as a Docker container. LaunchKit talks to it
with the `opensandbox` SDK. This file holds everything around that conversation:

    docker_problem()      why Docker cannot run here, in a sentence, or None
    build_image()         builds sandbox/Dockerfile once: Python and the four libraries the code may use
    pull_images()         fetches OpenSandbox's two helper images: execd, which runs commands inside a sandbox, and
                          egress, the sidecar that enforces a sandbox's network policy
    serve()               writes data/sandbox.toml and runs the server: `uv run launchkit sandbox`
    server_problem()      why no sandbox can be made right now, in a sentence, or None
    connection()          the SDK's connection settings for that server
    labels(...)           the metadata every LaunchKit sandbox carries: its brand and its conversation
    sandboxes_of(...)     the ids of a conversation's sandboxes that are still there
    kill_sandboxes(...)   kills them; Stop calls it

The server's settings are LaunchKit's choices, written into data/sandbox.toml each time it starts:

    127.0.0.1:8090        the server listens on this laptop only, behind a fixed local key
    bridge network        each sandbox gets its own network, so a network policy can apply to it
    egress "dns+nft"      a deny rule is enforced on every packet, not only on names looked up through DNS
    pids_limit            the process limit is a server setting: one number for every sandbox (limits.py)
    allowed_host_paths    the only host folders a sandbox may mount: the workspaces, and pytest's temporary folder

Reference page 6, How strong the isolation is, and page 7, Hosted sandboxes.
"""

import getpass
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import timedelta
from pathlib import Path

from launchkit.settings import settings

IMAGE = "launchkit-sandbox:5"
DOCKERFILE_DIR = Path(__file__).resolve().parent.parent.parent / "sandbox"

SERVER_PACKAGE = "opensandbox-server==1.2.1"
EXECD_IMAGE = "opensandbox/execd:v1.1.0"
EGRESS_IMAGE = "opensandbox/egress:v1.1.7"
HOST = os.environ.get("LAUNCHKIT_SANDBOX_HOST", "127.0.0.1:8090")
# The server listens on 127.0.0.1 only, so this key keeps out other programs on the laptop, not other people.
API_KEY = os.environ.get("LAUNCHKIT_SANDBOX_KEY", "launchkit-local-sandbox-key")


def docker_problem() -> str | None:
    """None when Docker is installed and running, otherwise what to do about it."""
    if shutil.which("docker") is None:
        return "Docker is not installed. Install Docker Desktop (Mac, Windows) or Docker Engine (Linux), start it, and run `uv run launchkit setup` again"
    try:
        subprocess.run(["docker", "info"], capture_output=True, check=True, timeout=20)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return "Docker is installed but not running. Start Docker Desktop (or the Docker service) and try again"
    return None


def image_ready(image: str = IMAGE) -> bool:
    return subprocess.run(["docker", "image", "inspect", image], capture_output=True).returncode == 0


def build_image(quiet: bool = True) -> None:
    """Builds the sandbox image from sandbox/Dockerfile. Needs the internet once; after that the image is local."""
    command = ["docker", "build", "-t", IMAGE, str(DOCKERFILE_DIR)]
    subprocess.run(command + (["-q"] if quiet else []), check=True, capture_output=quiet)


def pull_images() -> None:
    """OpenSandbox's helper images. The server would pull them on its first sandbox, too slowly for a live room."""
    for image in (EXECD_IMAGE, EGRESS_IMAGE):
        if not image_ready(image):
            subprocess.run(["docker", "pull", "-q", image], check=True, capture_output=True)


# The server -----------------------------------------------------------------------------------------------------

def config_path() -> Path:
    return settings.data_dir / "sandbox.toml"


def mountable_folders() -> list[str]:
    """Host folders a sandbox may mount. The server refuses every other path, whatever a request asks for."""
    folders = [settings.workspaces_dir, settings.data_dir, Path(tempfile.gettempdir()) / f"pytest-of-{getpass.getuser()}"]
    return [str(Path(folder).resolve()) for folder in folders]


def write_config() -> Path:
    from launchkit.sandbox.limits import RunLimits

    host, port = HOST.rsplit(":", 1)
    folders = ", ".join(f'"{folder}"' for folder in mountable_folders())
    text = f"""# Written by `uv run launchkit sandbox` each time it starts; edit launchkit/sandbox/engine.py, not this file.
[server]
host = "{host}"
port = {port}
api_key = "{API_KEY}"
max_sandbox_timeout_seconds = 3600

[log]
level = "WARNING"

[runtime]
type = "docker"
execd_image = "{EXECD_IMAGE}"

[storage]
allowed_host_paths = [{folders}]

[store]
type = "sqlite"
path = "{(settings.data_dir / 'sandbox.db').resolve()}"

[docker]
network_mode = "bridge"
port_range_min = 40000
port_range_max = 60000
drop_capabilities = ["AUDIT_WRITE", "MKNOD", "NET_ADMIN", "NET_RAW", "SYS_ADMIN", "SYS_MODULE", "SYS_PTRACE", "SYS_TIME", "SYS_TTY_CONFIG"]
no_new_privileges = true
pids_limit = {RunLimits().processes}

[ingress]
mode = "direct"

[egress]
image = "{EGRESS_IMAGE}"
mode = "dns+nft"
readiness_timeout_seconds = 30.0
"""
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def server_command() -> list[str]:
    uvx = shutil.which("uvx")
    run = [uvx] if uvx else [sys.executable, "-m", "uv", "tool", "run"]
    return [*run, "--from", SERVER_PACKAGE, "opensandbox-server", "--config", str(write_config())]


def serve(background: bool = False) -> subprocess.Popen | int:
    """Run the sandbox server. In the foreground for `uv run launchkit sandbox`; in the background for the checks."""
    if background:
        return subprocess.Popen(server_command(), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    return subprocess.run(server_command()).returncode


def server_reachable(seconds: float = 3.0) -> bool:
    import httpx

    try:
        return httpx.get(f"http://{HOST}/health", timeout=seconds).status_code == 200
    except httpx.HTTPError:
        return False


def server_problem() -> str | None:
    """None when a sandbox can be made right now, otherwise why not and what to do about it."""
    problem = docker_problem()
    if problem:
        return problem
    if not server_reachable():
        return f"the sandbox server is not running at {HOST}. Start it in a second terminal with `uv run launchkit sandbox`"
    return None


def connection():
    """The SDK's connection settings. Creating a sandbox takes a second or two; the first one after a restart longer."""
    from opensandbox.config.connection_sync import ConnectionConfigSync

    return ConnectionConfigSync(domain=HOST, api_key=API_KEY, request_timeout=timedelta(seconds=120))


# Finding a conversation's sandboxes ------------------------------------------------------------------------------

def labels(brand: str, conversation: str) -> dict[str, str]:
    """The metadata every sandbox LaunchKit makes carries, so Stop and the checks can find a conversation's sandboxes.
    The server matches metadata exactly, key by key, so Harbor's k7c1 never matches k7c1-old."""
    return {"launchkit-brand": brand, "launchkit-conversation": conversation}


def sandboxes_of(brand: str, conversation: str) -> list[str]:
    """The ids of this conversation's sandboxes that still exist, running or not."""
    if server_problem():
        return []
    from opensandbox.models.sandboxes import SandboxFilter
    from opensandbox.sync.manager import SandboxManagerSync

    manager = SandboxManagerSync.create(connection_config=connection())
    try:
        found = manager.list_sandbox_infos(SandboxFilter(metadata=labels(brand, conversation), page_size=100))
        return [info.id for info in found.sandbox_infos if info.status.state not in ("Stopping", "Terminated")]
    finally:
        manager.close()


def kill_sandboxes(brand: str, conversation: str) -> list[str]:
    """Kill every sandbox this conversation's code is running in. Stop calls it."""
    ids = sandboxes_of(brand, conversation)
    if not ids:
        return []
    from opensandbox.sync.manager import SandboxManagerSync

    manager = SandboxManagerSync.create(connection_config=connection())
    try:
        for sandbox_id in ids:
            try:
                manager.kill_sandbox(sandbox_id)
            except Exception:  # already gone between the list and the kill
                pass
    finally:
        manager.close()
    return ids
