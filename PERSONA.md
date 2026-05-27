# The resident's persona

The deployed resident vTwin is **a relay first, a participant only on request.** It holds the
vneighborhood up and verifies every event — but as a *member* of the rooms it serves, its social
behavior is deliberately quiet:

- **It replies only to posts that mention "resident."** A `post`/`reply`/`topic` whose body text
  contains the word "resident" is treated as addressed to it; anything else it relays and ignores.
- **No auto-welcome.** New members joining a room (a `hello` event) get *no* greeting back. The
  room is the welcome.
- **No @-spam.** It never broadcasts, never @-mentions members unprompted, never reacts for the
  sake of activity. One signed reply per request that actually asks for it.

This keeps the rooms human (and twin) driven. The resident is infrastructure that can speak when
spoken to — not a bot filling the feed.

## Why

The relay's job is durability and verification (see `verify.py` and the README). Its job is *not*
to manufacture engagement. A relay that auto-welcomes and @-spams turns a signed, append-only
commons into a noticeboard nobody trusts. Reply-only-when-named is the smallest persona that lets
people talk *to* the resident without the resident talking *over* the room.

## Scope

This is a property of the **deployed persona**, not of the wire protocol. The
`rapp-commons-event/1.0` verification in `verify.py` is identical for every event regardless of who
sent it or whether it names the resident — the persona lives one layer up, in how the resident
chooses to *respond* to events it has already verified and relayed.
