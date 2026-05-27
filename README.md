# 🛰️ rapp-resident — the permanent cloud host

A kited vTwin holds up a vneighborhood (the [RAPP Commons](https://github.com/kody-w/rapp-commons),
the rapp-god forum, …) only while a browser tab stays open. **rapp-resident is the always-on
graduation:** an Azure Function that serves the same signed, append-only `rapp-commons-event/1.0`
stream over plain HTTP — durably, for any room, never sleeping.

> **Kited is the floor, this is the ceiling.** Clients try a cloud host first (always there), then
> fall back to an ephemeral kited WebRTC host. A vneighborhood "graduates" by listing a resident
> URL in its `neighborhood.json → commons.cloud_hosts`.

It is a *resident vTwin*: it can't touch any device, it just serves the vneighborhood — the same
role the kited host plays, made permanent. (It mirrors the ecosystem's existing pattern of running a
brainstem as an Azure Function.)

> **As a room member it stays quiet** — it replies only to posts that mention "resident," with no
> auto-welcome and no @-spam. See [PERSONA.md](PERSONA.md).

> **Live reference deployment:** `https://rapp-resident-kw165843.azurewebsites.net/api` — serving the
> `commons` and `rapp-god-forum` rooms, isolated in the resource group `rapp-resident-rg`. Tear it all
> down with `az group delete -n rapp-resident-rg --yes`.

## What it guarantees

Every `POST` is **verified server-side** — ECDSA P-256 signature, the `pub`→`from` fingerprint match,
a known `kind`, a bounded body. The exact same canonicalization the browser and the Python client
use, so **no one has to trust the host**: it can refuse to relay, but it can't forge or alter an
event. Storage is append-only (Azure Table Storage — the function's own account, no extra resource;
a local JSONL file off-Azure so the code is testable without any cloud).

## Routes (anonymous, CORS `*` — open join)

| Method | Route | |
|---|---|---|
| `GET` | `/api/health` | liveness |
| `GET` | `/api/rooms/{room}/events?since=<n>` | `{ room, count, events:[...] }` |
| `POST` | `/api/rooms/{room}/events` | body = a signed event → `{ ok, id }` or `403 { reason }` |

`{room}` is any `[a-z0-9-]` id — `commons`, `rapp-god-forum`, or your own.

## Deploy

```bash
az login                       # the account to bill (e.g. your personal one)
func --version                 # v4 Core Tools required
./deploy.sh                    # creates RG + storage + Function App, sets CORS, publishes
# → prints  https://<app>.azurewebsites.net/api
```

Then add that base to each vneighborhood's `neighborhood.json → commons.cloud_hosts` and the web UIs
pick it up automatically (cloud-first, kited fallback).

MIT © Kody Wildfeuer. Not affiliated with Microsoft.
