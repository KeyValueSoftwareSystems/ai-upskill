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
    # TODO step 4: take the id from the request only; accept ids that match WORKSPACE_ID and name an existing folder; else raise UnknownWorkspace
    for folder in sorted(settings.workspaces_dir.iterdir()):
        if folder.is_dir() and folder.name in request.text.lower():
            return folder.name
    return request.workspace_id
