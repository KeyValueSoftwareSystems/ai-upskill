"""Stage 2: run the agent's code in a throwaway container.

Not built yet. The room builds this in stage 2, after watching Jonas at Ember ask the agent to tidy his results file,
and the code it wrote print LaunchKit's keys and list Harbor's folder.

What it must do. One `docker run` per run of the agent's code, from the image in launchkit/sandbox/engine.py, that
sees only what this conversation may see:

    /work     this conversation's workspace, read and write
    /brand    the brand's own files, read only
    nothing   no environment variables from the server, no network, a user that is not root, a read-only root disk

The container is named with engine.container_name(brand, conversation), so it can be found again later.

Reference page 6, How strong the isolation is, and page 7, What running code can reach.
"""

from launchkit.files.workspace import Workspace
from launchkit.sandbox import Ran
from launchkit.sandbox.limits import RunLimits
from launchkit.tools.catalogue import todo


@todo
def run_in_container(workspace: Workspace, code: str, limits: RunLimits) -> Ran:
    """Run `code` with Python in a new container that sees only this conversation, and give back what happened."""
    raise NotImplementedError("stage 2 builds the container")
