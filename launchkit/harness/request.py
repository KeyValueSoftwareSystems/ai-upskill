import re

from pydantic import BaseModel

WORKSPACE_ID = re.compile(r"^[a-z0-9-]{1,32}$")


class Request(BaseModel):
    workspace_id: str
    user_id: str = "marketer"
    session_id: str = "default"
    text: str


class UnknownWorkspace(Exception):
    def __init__(self, workspace_id: str):
        self.workspace_id = workspace_id
        super().__init__(f"unknown workspace {workspace_id!r}")


def resolve_workspace_id(request: Request, settings) -> str:
    workspace_id = request.workspace_id
    if not WORKSPACE_ID.fullmatch(workspace_id) or not (settings.workspaces_dir / workspace_id).is_dir():
        raise UnknownWorkspace(workspace_id)
    return workspace_id
