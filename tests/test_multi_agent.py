"""Tests for multi-agent communication via Session + inbox."""

import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

from claude_tui_automation.automation import Session
from claude_tui_automation import inbox

FAKE_CLAUDE = [
    sys.executable,
    os.path.join(os.path.dirname(__file__), "fake_claude.py"),
]

FAST = dict(command=FAKE_CLAUDE, rows=30, cols=120, quiet_ms=50)


def _send_and_wait(session, text, timeout=5):
    """Send a prompt and wait for the response to appear on screen."""
    session.send_line(text)
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if text.startswith("ECHO: "):
            marker = text.split("ECHO: ", 1)[1]
            if marker in session.display_text():
                time.sleep(0.1)
                return session.display_text()
        time.sleep(0.1)
    raise TimeoutError(f"Response not found after {timeout}s")


def _extract_last_response(session):
    """Extract the last assistant response from conversation lines."""
    for line in reversed(session.conversation_lines()):
        if "●" in line:
            idx = line.index("●")
            return line[idx + 1:].strip()
    return ""


class TestTwoAgentConversation(unittest.TestCase):
    """Two Sessions exchange messages through the inbox system."""

    def test_relay_via_inbox(self):
        """Agent A produces output, relayed to Agent B through inbox."""
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)

            with Session(**FAST) as a, Session(**FAST) as b:
                a.wait_for_idle(timeout=5)
                b.wait_for_idle(timeout=5)

                # Agent A processes a prompt
                _send_and_wait(a, "ECHO: HELLO_FROM_A")
                response_a = _extract_last_response(a)
                self.assertIn("HELLO_FROM_A", response_a)

                # Drop message into B's inbox
                inbox.send(base, "b", "a", response_a)

                # B picks it up
                messages = inbox.receive(base, "b")
                self.assertEqual(len(messages), 1)
                self.assertIn("HELLO_FROM_A", messages[0])

                # B processes the relayed content
                _send_and_wait(b, f"ECHO: {messages[0]}")
                b_text = b.display_text()
                self.assertIn("HELLO_FROM_A", b_text)

    def test_multi_turn(self):
        """A -> B -> A, each session sees the other's output."""
        with Session(**FAST) as a, Session(**FAST) as b:
            a.wait_for_idle(timeout=5)
            b.wait_for_idle(timeout=5)

            # Turn 1: A
            _send_and_wait(a, "ECHO: TURN1")
            r1 = _extract_last_response(a)
            self.assertIn("TURN1", r1)

            # Turn 2: B sees A's response
            _send_and_wait(b, f"ECHO: SAW_{r1}")
            r2 = _extract_last_response(b)
            self.assertIn("SAW_TURN1", r2)

            # Turn 3: A sees B's response
            _send_and_wait(a, f"ECHO: SAW_{r2}")
            r3 = _extract_last_response(a)
            self.assertIn("SAW_SAW_TURN1", r3)

    def test_orchestrated_loop(self):
        """N-turn orchestrated conversation between two agents."""
        with Session(**FAST) as a, Session(**FAST) as b:
            a.wait_for_idle(timeout=5)
            b.wait_for_idle(timeout=5)

            agents = [a, b]
            message = "SEED"

            for turn in range(4):
                speaker = agents[turn % 2]
                prompt = f"ECHO: TURN{turn}_{message}"
                _send_and_wait(speaker, prompt)
                message = _extract_last_response(speaker)
                self.assertIn(f"TURN{turn}", message)


if __name__ == "__main__":
    unittest.main()
