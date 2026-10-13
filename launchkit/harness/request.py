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
    # TODO step 4: accept only ids that match WORKSPACE_ID and name an existing folder; else raise UnknownWorkspace
    return request.workspace_id
