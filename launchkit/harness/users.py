import yaml


def list_logins(settings) -> list[dict]:
    logins = []
    for folder in sorted(p for p in settings.workspaces_dir.iterdir() if p.is_dir()):
        users_file = folder / "users.yaml"
        if not users_file.exists():
            continue
        data = yaml.safe_load(users_file.read_text(encoding="utf-8")) or {}
        brand = data.get("brand", folder.name)
        for user in data.get("users", []):
            logins.append(
                {
                    "workspace_id": folder.name,
                    "user_id": user["id"],
                    "name": user.get("name", user["id"]),
                    "role": user.get("role", ""),
                    "label": f"{user.get('name', user['id'])} · {brand}",
                }
            )
    return logins
