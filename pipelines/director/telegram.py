"""Minimal Telegram Bot API client (raw httpx) — long-poll in, messages out.

Deliberately tiny: no python-telegram-bot dependency, just getUpdates (long
poll), sendMessage, and a cosmetic typing indicator. Outbound HTTPS only — the
listener makes calls to api.telegram.org, nothing inbound is exposed.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterator

import httpx


@dataclass
class Update:
    update_id: int
    chat_id: int
    user_id: int
    text: str


class TelegramClient:
    def __init__(self, token: str, timeout: int = 30) -> None:
        self._base = f"https://api.telegram.org/bot{token}"
        self._timeout = timeout
        # read timeout must outlast the server-side long-poll hold
        self._http = httpx.Client(timeout=httpx.Timeout(timeout + 15))

    def get_updates(self, offset: int | None = None) -> list[Update]:
        params: dict[str, Any] = {"timeout": self._timeout}
        if offset is not None:
            params["offset"] = offset
        resp = self._http.get(f"{self._base}/getUpdates", params=params)
        resp.raise_for_status()
        out: list[Update] = []
        for u in resp.json().get("result", []):
            msg = u.get("message") or u.get("edited_message")
            if not msg or msg.get("text") is None:
                continue
            out.append(
                Update(
                    update_id=u["update_id"],
                    chat_id=msg["chat"]["id"],
                    user_id=msg.get("from", {}).get("id", 0),
                    text=msg["text"],
                )
            )
        return out

    def send_message(self, chat_id: int, text: str) -> None:
        for chunk in _chunk(text or "(no reply)", 4000):  # Telegram caps at 4096
            resp = self._http.post(
                f"{self._base}/sendMessage",
                json={"chat_id": chat_id, "text": chunk},
            )
            resp.raise_for_status()

    def send_typing(self, chat_id: int) -> None:
        try:
            self._http.post(
                f"{self._base}/sendChatAction",
                json={"chat_id": chat_id, "action": "typing"},
            )
        except httpx.HTTPError:
            pass  # cosmetic only

    def set_my_commands(self, commands: list[tuple[str, str]]) -> None:
        """Register the bot's "/" autocomplete menu. Best-effort — cosmetic only."""
        try:
            self._http.post(
                f"{self._base}/setMyCommands",
                json={
                    "commands": [
                        {"command": name, "description": desc}
                        for name, desc in commands
                    ]
                },
            )
        except httpx.HTTPError:
            pass


def _chunk(text: str, n: int) -> Iterator[str]:
    for i in range(0, len(text), n):
        yield text[i : i + n]
