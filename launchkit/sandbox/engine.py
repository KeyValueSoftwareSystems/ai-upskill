"""Ready-made: the Docker plumbing the stages share, so nobody spends session time on it.

docker_problem() says, in a sentence, why the sandbox cannot run on this machine, or None when it can. `launchkit
setup` and the setup check call it, and the checks skip the container stages with its sentence when Docker is
missing. build_image() builds sandbox/Dockerfile once.

Every container the agent's code runs in is named after its conversation, lk-<brand>-<conversation>-<6 letters>, so
anything that has to find a conversation's containers later, such as Stop in stage 4, can find them by name.
"""

import shutil
import subprocess
import uuid
from pathlib import Path

IMAGE = "launchkit-sandbox:5"
DOCKERFILE_DIR = Path(__file__).resolve().parent.parent.parent / "sandbox"


def docker_problem() -> str | None:
    """None when Docker is installed and running, otherwise what to do about it."""
    if shutil.which("docker") is None:
        return "Docker is not installed. Install Docker Desktop (Mac, Windows) or Docker Engine (Linux), start it, and run `uv run launchkit setup` again"
    try:
        subprocess.run(["docker", "info"], capture_output=True, check=True, timeout=20)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return "Docker is installed but not running. Start Docker Desktop (or the Docker service) and try again"
    return None


def image_ready() -> bool:
    return subprocess.run(["docker", "image", "inspect", IMAGE], capture_output=True).returncode == 0


def build_image(quiet: bool = True) -> None:
    """Builds the sandbox image from sandbox/Dockerfile. Needs the internet once; after that the image is local."""
    command = ["docker", "build", "-t", IMAGE, str(DOCKERFILE_DIR)]
    subprocess.run(command + (["-q"] if quiet else []), check=True, capture_output=quiet)


def name_prefix(brand: str, conversation: str) -> str:
    return f"lk-{brand}-{conversation}-"


def container_name(brand: str, conversation: str) -> str:
    """A new container's name: its conversation, then six letters so two runs never clash."""
    return name_prefix(brand, conversation) + uuid.uuid4().hex[:6]
