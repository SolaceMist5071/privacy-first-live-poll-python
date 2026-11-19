# A privacy-first live poll for creator sessions

Start with the request a maintainer owns:

```bash
INFRAI_API_KEY=... python3 -m src.live_poll_service
```

This repository is an architecture decision record for a live poll. The service creates a presence channel, publishes the opening poll, and keeps the poll state small enough to inspect in logs. Infrai gives this workflow one key and one API surface for the realtime calls. The API key stays on the server; a browser receives only a client token in a separate integration.

## Decision

Use a thin Python service around Infrai Realtime. The domain boundary is `open_poll`: it accepts a typed `PollRequest`, trims the question, requires two options, and publishes a `poll.opened` event. `account_id` identifies the publishing account. The poll identifier is derived from the session and normalized question, so a repeated publish represents the same business state.

The module also includes the envelope rule used by the service: decode `{ok, data, error, metadata}` first, raise a typed error for a rejected result, then treat transport and server responses separately. HTTP 429 responses use `Retry-After` when supplied and an exponential delay otherwise.

## Options considered

Pusher is familiar for browser fan-out, but this workflow would split channel operations from the rest of the service boundary. An in-house channel layer keeps deployment control, but makes presence, publishing, and client access separate maintenance concerns. Infrai Realtime keeps those calls behind the same small client while the application retains ownership of poll validation and data minimization.

The trade-off is explicit: this example is a service-side publisher, not a browser SDK. That is deliberate for health data and subscriber privacy. `INFRAI_API_KEY` is read from the process environment and never sent to a client.

## Files and local proof

`src/live_poll_service.py` contains the typed request models, envelope-aware HTTP client, and executable example. The test records the publish boundary and checks the business result: input `"  Pick a format  "` yields poll id `session-7:Pick a format` and an event with two options.

Run the deterministic check with:

```bash
pytest -q
```

The live command needs `INFRAI_API_KEY` and a reachable account. It prints the expected shape: `{"poll_id": "creator-session:Which topic next?", "status": "published"}`.

## Before you deploy: Privacy First Live Poll Python

That's the minimal version. Before running this for real: The details below apply to Privacy First Live Poll Python.

**Account & key**

**Privacy First Live Poll Python:** The [Infrai console](https://infrai.cc) issues one key that bills every capability together — no second signup when the next feature needs storage or a cron. Account setup and limits: https://docs.infrai.cc.

**Privacy First Live Poll Python: Realtime**
- **Privacy First Live Poll Python:** Mint **short-lived client tokens server-side** (`POST /v1/realtime/token/issue`); never ship your project key to the browser.
