from __future__ import annotations

import datetime as dt
import os
import subprocess
import webbrowser
from dataclasses import dataclass


@dataclass
class CommandResult:
    executed: bool
    response: str = ""
    should_exit: bool = False


class CommandHandler:
    """Small local command router for common spoken commands."""

    @staticmethod
    def _open_notepad() -> None:
        if os.name == "nt":
            subprocess.Popen(["notepad"])
            return
        # Linux/macOS fallback
        for candidate in (["gedit"], ["xdg-open", "."], ["open", "-a", "TextEdit"]):
            try:
                subprocess.Popen(candidate)
                return
            except Exception:
                continue

    def handle(self, text: str) -> CommandResult:
        normalized = text.strip().lower()
        if not normalized:
            return CommandResult(executed=False)

        if "open youtube" in normalized:
            webbrowser.open("https://youtube.com")
            return CommandResult(executed=True, response="Opening YouTube.")

        if "open google" in normalized:
            webbrowser.open("https://google.com")
            return CommandResult(executed=True, response="Opening Google.")

        if "open notepad" in normalized:
            self._open_notepad()
            return CommandResult(executed=True, response="Opening notepad.")

        if "what time is it" in normalized or normalized == "time":
            now = dt.datetime.now().strftime("%I:%M %p")
            return CommandResult(executed=True, response=f"It is {now}.")

        if normalized in {"exit", "quit", "stop assistant"}:
            return CommandResult(executed=True, response="Stopping voice assistant.", should_exit=True)

        return CommandResult(executed=False)

