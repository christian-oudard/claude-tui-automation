"""Multi-agent orchestration helpers.

Generates MCP configuration and working directories so that each Claude
Code Session gets an agent-inbox MCP server with the right AGENT_ID.
"""

import json
import os
import sys
import tempfile
from pathlib import Path

MCP_SERVER = Path(__file__).parent / "mcp_inbox.py"


def agent_env(
    agent_id: str,
    inbox_base: Path,
    cwd: Path,
    peers: dict[str, str] | None = None,
) -> dict[str, str]:
    """Build environment dict for a Claude Code agent session.

    Writes .mcp.json into cwd so Claude Code discovers the inbox tools
    on startup. Returns env dict to pass to Session(env=...).

    peers: mapping of other agent IDs to their descriptions, e.g.
        {"agent_b": "code reviewer", "agent_c": "researcher"}
    """
    python = sys.executable
    peers = peers or {}

    config = {
        "mcpServers": {
            "agent-inbox": {
                "command": python,
                "args": [str(MCP_SERVER)],
                "env": {
                    "AGENT_ID": agent_id,
                    "AGENT_INBOX_BASE": str(inbox_base),
                    "AGENT_PEERS": json.dumps(peers),
                },
            },
        },
    }

    mcp_json = cwd / ".mcp.json"
    mcp_json.write_text(json.dumps(config, indent=2))

    env = os.environ.copy()
    env["AGENT_ID"] = agent_id
    env["AGENT_INBOX_BASE"] = str(inbox_base)
    env["TERM"] = "xterm-256color"
    return env


def make_workspace(
    agent_id: str,
    inbox_base: Path,
    peers: dict[str, str] | None = None,
    base_dir: Path | None = None,
) -> tuple[Path, dict[str, str]]:
    """Create a working directory for an agent and return (cwd, env).

    peers: other agents this agent can message (id -> description).
    If base_dir is given, creates a subdirectory under it.
    Otherwise creates a temp directory.
    """
    if base_dir:
        cwd = base_dir / agent_id
        cwd.mkdir(parents=True, exist_ok=True)
    else:
        cwd = Path(tempfile.mkdtemp(prefix=f"agent-{agent_id}-"))

    env = agent_env(agent_id, inbox_base, cwd, peers)
    return cwd, env
