"""Scaffold Workday AI Agent artifacts (.agent + .agentskill + optional A2UI page)."""
from __future__ import annotations

from .common import app_root, slug, write_text, write_json, result


def create_agent(app: str, name: str, description: str = "",
                 skills: list[str] | None = None, with_a2ui: bool = True) -> str:
    app_dir = app_root(app)
    agents = app_dir / "agents"
    pres = app_dir / "presentation"
    created: list[str] = []
    agent_name = slug(name).replace("_", "-")
    skill_name = f"{agent_name}-main"
    skills = skills or [skill_name]
    if with_a2ui and "display-image" not in skills:
        skills = skills + ["display-image"]

    agent_md = f"""---
name: {agent_name}
description: "{description or name}"
skills:
{chr(10).join(f'  - {s}' for s in skills)}
---

# {name}

You are {name}: {description or 'a helpful Workday assistant'}.

## Guidelines
- Use skills explicitly before looking for other tools.
- If you cannot fulfill a request, explain what you can do.
- Be concise, friendly, and helpful.

## Error Handling
- Stop immediately on unexpected errors and report them to the user.
"""
    write_text(agents / f"{agent_name}.agent", agent_md, created)

    skill_md = f"""---
name: {skill_name}
description: >
  Primary skill for {name}. Describe the capability and the tools it uses.
metadata:
  tags: []
allowed-tools:
  - generate_a2ui
tool-wids:
  - name: generate_a2ui
    wid: generate_a2ui
---

# {name} — Main Skill

## Steps
1. Gather the inputs you need from the user or context.
2. Call the appropriate Workday tools (add them under allowed-tools + tool-wids).
3. Format the result and, when a rich card helps, call `generate_a2ui`.

## Error Handling
- On API failure: report the error and suggest a next step.
"""
    write_text(agents / f"{skill_name}.agentskill", skill_md, created)

    if with_a2ui:
        # reusable display-image skill + A2UI page
        display_skill = """---
name: display-image
description: >
  Internal skill to display an image inline in Workday chat. The agent calls
  this with a URL it already determined — never ask the user for a URL.
metadata:
  tags: []
allowed-tools:
  - generate_a2ui
tool-wids:
  - name: generate_a2ui
    wid: generate_a2ui
---

# Display Image

## Steps
1. Determine the image URL from context (do not ask the user).
2. Call `generate_a2ui` with pageId "displayImage" and queryParams { "imageUrl": "<url>" }.
"""
        write_text(agents / "display-image.agentskill", display_skill, created)
        write_json(pres / "displayImage.pmd", {
            "id": "displayImage", "a2ui": True, "endPoints": [],
            "presentation": {"body": {"type": "chatCard", "children": [
                {"type": "chatImage", "url": "<% queryParams.imageUrl %>", "fit": "SCALE_DOWN"}
            ]}},
        }, created)

    notes = [
        f"Agent '{agent_name}' with skills: {skills}",
        "Register A2UI pages in the .amd tasks list (routingPattern + page.id).",
        "Fill allowed-tools + tool-wids with real Workday tool names/WIDs from App Builder.",
    ]
    return result(created, notes)
