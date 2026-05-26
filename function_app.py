"""rapp-resident — the permanent cloud host for kited vneighborhoods.

A kited vTwin holds up a vneighborhood (commons, forum, …) only while a browser tab is
open. This Azure Function is the **always-on graduation**: a resident host that serves
the same signed, append-only `rapp-commons-event/1.0` stream over plain HTTP, durably,
for any room. It verifies every event server-side (so the rules hold without trusting
the host) and never sleeps. Clients try a cloud host first, then fall back to a kited
WebRTC host — kited is the floor, this is the ceiling.

Routes (anonymous — open join, CORS *):
  GET  /api/health
  GET  /api/rooms/{room}/events?since=<n>   -> { room, count, events:[...] }
  POST /api/rooms/{room}/events             body = a signed event -> { ok, id } | 403
"""

import json
import re
from datetime import datetime, timezone

import azure.functions as func

import store as store_mod
from verify import event_id, verify_event

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

ROOM_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,40}$")
CORS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
    "Access-Control-Allow-Headers": "content-type",
    "Cache-Control": "no-store",
}


def _json(obj, status=200):
    return func.HttpResponse(json.dumps(obj), status_code=status,
                             mimetype="application/json", headers=CORS)


@app.route(route="health", methods=["GET"])
def health(req: func.HttpRequest) -> func.HttpResponse:
    return _json({"ok": True, "service": "rapp-resident/1.0",
                  "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")})


@app.route(route="rooms/{room}/events", methods=["GET", "POST", "OPTIONS"])
def events(req: func.HttpRequest) -> func.HttpResponse:
    if req.method == "OPTIONS":
        return func.HttpResponse(status_code=204, headers=CORS)

    room = req.route_params.get("room", "")
    if not ROOM_RE.match(room):
        return _json({"error": "bad room id (use [a-z0-9-], 2-41 chars)"}, 400)

    st = store_mod.store()

    if req.method == "GET":
        try:
            since = max(0, int(req.params.get("since", "0")))
        except ValueError:
            since = 0
        evs = st.read(room, since)
        return _json({"room": room, "count": len(evs), "events": evs})

    # POST — verify the signature, enforce the rules, append
    try:
        ev = req.get_json()
    except ValueError:
        return _json({"error": "body must be a JSON event"}, 400)
    ok, reason = verify_event(ev)
    if not ok:
        return _json({"error": "rejected", "reason": reason}, 403)
    rid = event_id(ev)
    st.append(room, ev, rid)
    return _json({"ok": True, "id": rid, "room": room})
