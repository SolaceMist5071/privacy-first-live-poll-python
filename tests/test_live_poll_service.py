from src.live_poll_service import PollRequest, open_poll


class RecordingClient:
    def __init__(self) -> None:
        self.calls = []

    def publish(self, channel, event, data, account_id):
        self.calls.append((channel, event, data, account_id))
        return {"ok": True}


def test_open_poll_publishes_private_poll_state():
    client = RecordingClient()
    request = PollRequest("session-7", "  Pick a format  ", ("Live demo", "Questions"), "acct-7")

    result = open_poll(client, request)

    assert result.poll_id == "session-7:Pick a format"
    assert client.calls[0][1] == "poll.opened"
    assert client.calls[0][2]["options"] == ["Live demo", "Questions"]
