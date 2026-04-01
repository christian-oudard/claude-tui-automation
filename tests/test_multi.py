"""Tests for multi-agent orchestration helpers."""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

from claude_tui_automation.multi import agent_env, make_workspace, MCP_SERVER


class TestAgentEnv(unittest.TestCase):

    def test_writes_mcp_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            inbox_base = Path(tmp) / "inboxes"
            inbox_base.mkdir()
            peers = {"bob": "code reviewer"}

            env = agent_env("alice", inbox_base, cwd, peers=peers)

            mcp_json = cwd / ".mcp.json"
            self.assertTrue(mcp_json.exists())

            config = json.loads(mcp_json.read_text())
            server = config["mcpServers"]["agent-inbox"]
            self.assertEqual(server["env"]["AGENT_ID"], "alice")
            self.assertEqual(server["env"]["AGENT_INBOX_BASE"], str(inbox_base))
            self.assertEqual(server["args"], [str(MCP_SERVER)])
            self.assertEqual(
                json.loads(server["env"]["AGENT_PEERS"]),
                {"bob": "code reviewer"},
            )

    def test_env_dict_has_agent_vars(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = agent_env("bob", Path(tmp), Path(tmp))
            self.assertEqual(env["AGENT_ID"], "bob")
            self.assertEqual(env["AGENT_INBOX_BASE"], tmp)
            self.assertEqual(env["TERM"], "xterm-256color")


class TestMakeWorkspace(unittest.TestCase):

    def test_creates_subdirectory(self):
        with tempfile.TemporaryDirectory() as tmp:
            inbox_base = Path(tmp) / "inboxes"
            inbox_base.mkdir()
            base_dir = Path(tmp) / "workspaces"
            base_dir.mkdir()
            peers = {"agent_2": "partner"}

            cwd, env = make_workspace("agent_1", inbox_base, peers=peers, base_dir=base_dir)
            self.assertEqual(cwd, base_dir / "agent_1")
            self.assertTrue(cwd.exists())
            self.assertTrue((cwd / ".mcp.json").exists())

    def test_creates_temp_dir_without_base(self):
        with tempfile.TemporaryDirectory() as tmp:
            inbox_base = Path(tmp) / "inboxes"
            inbox_base.mkdir()

            cwd, env = make_workspace("agent_2", inbox_base)
            self.assertTrue(cwd.exists())
            self.assertIn("agent-agent_2-", str(cwd))
            self.assertTrue((cwd / ".mcp.json").exists())


if __name__ == "__main__":
    unittest.main()
