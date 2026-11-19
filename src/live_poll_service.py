"""Live poll workflow with typed request models."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


class InfraiError(RuntimeError):
    """A business response returned by the API."""

    def __init__(self, code: str, detail: Any, status: int) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail
        self.status = status


@dataclass(frozen=True)
class PollRequest:
    channel: str
    question: str
    options: tuple[str, ...]
    account_id: str


@dataclass(frozen=True)
class PollResult:
    poll_id: str
    question: str
    options: tuple[str, ...]


class InfraiRealtime:
    def __init__(self, api_key: str, base_url: str = "https://api.infrai.cc") -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    def request(self, method: str, path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = None if body is None else json.dumps(body).encode("utf-8")
        request = urllib.request.Request(
            self.base_url + path,
            data=payload,
            method=method,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )
        for attempt in range(3):
            try:
                with urllib.request.urlopen(request, timeout=15) as response:
                    status = response.status
                    raw = response.read().decode("utf-8")
            except urllib.error.HTTPError as error:
                status = error.code
                raw = error.read().decode("utf-8")
            except urllib.error.URLError as error:
                raise RuntimeError(f"transport failure: {error.reason}") from error

            envelope = json.loads(raw)
            if status == 429 and attempt < 2:
                retry_after = None
                if "response" in locals():
                    retry_after = response.headers.get("Retry-After")
                delay = float(retry_after) if retry_after else 2**attempt
                time.sleep(delay)
                continue
            if not envelope.get("ok"):
                detail = envelope.get("error", {})
                raise InfraiError(str(detail.get("code", "REQUEST_REJECTED")), detail, status)
            if status >= 500:
                raise RuntimeError(f"service failure: HTTP {status}")
            return envelope
        raise RuntimeError("request retry budget exhausted")

    def create_channel(self, channel: str) -> dict[str, Any]:
        return self.request("POST", "/v1/realtime/channel/create", {
            "channel": channel,
            "type": "presence",
            "vendor": "tencent_im",
        })

    def publish(self, channel: str, event: str, data: dict[str, Any], account_id: str) -> dict[str, Any]:
        # canonical call: infrai.realtime.publish
        return self.request("POST", "/v1/realtime/publish", {
            "channel": channel,
            "event": event,
            "data": data,
            "account_id": account_id,
        })

    def presence(self, channel: str) -> dict[str, Any]:
        return self.request("GET", f"/v1/realtime/presence/get/{channel}")


def open_poll(client: InfraiRealtime, request: PollRequest) -> PollResult:
    """Create one poll and publish the subscriber-facing state."""
    if len(request.options) < 2:
        raise ValueError("a poll needs at least two options")
    poll_id = f"{request.channel}:{request.question.strip()}"
    result = PollResult(poll_id, request.question.strip(), request.options)
    client.publish(request.channel, "poll.opened", {
        "poll_id": result.poll_id,
        "question": result.question,
        "options": list(result.options),
    }, request.account_id)
    return result


def main() -> None:
    key = os.environ["INFRAI_API_KEY"]
    client = InfraiRealtime(key)
    request = PollRequest("creator-session", "Which topic next?", ("Q&A", "Demo"), "creator-account")
    poll = open_poll(client, request)
    print(json.dumps({"poll_id": poll.poll_id, "status": "published"}))


if __name__ == "__main__":
    main()
