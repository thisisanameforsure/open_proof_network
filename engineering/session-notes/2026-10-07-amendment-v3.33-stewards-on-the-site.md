# Proposed decisions amendment v3.33: stewards and curators on the site

**Status (2026-10-07): approved by the owner ("alright get building!") and applied as decisions v3.33 in F23-T0.**

Source: the owner's conversation of 2026-10-06/07. Nobody can sign in on the site. Every steward
link ends on the long Docs page. A steward record and every signature need an SSH key. Nobody can
edit words without curl or an MCP client.

The owner's rulings:
- sign in with GitHub on the site;
- anyone may draft words, but only a steward or curator makes them final, and a steward or curator
  may rewrite a draft;
- GitHub sign-in is enough, no SSH;
- for now anyone who claims to be a steward is admitted, with vetting to come later;
- curators are by the owner's invitation, the owner first;
- GitHub is required for both roles for now.

## 1. D-32: a steward record is made through the service, signed by the service's key

> **v3.33 — stewards through the site.** A steward record may be made by signing in with GitHub on
> the network's site. The service writes the record from the signed-in login, signs it with the
> network's **approval key**, and opens the pull request in the steward's name. The approval key's
> public half is published on the graph (`keys/approval.pub`), and the key is used for nothing else.
>
> Such a record says the service saw that login sign in and ask for the role. It does not say the
> steward holds a key. An SSH-signed record (v3.17) stays valid, and either kind may step down a
> commitment made by the other kind for the same login.
>
> **Admission is a policy, not a rule of the record.** `policy.json` carries `steward_admission`:
> - `open`: a record merges unattended and is marked `admitted_by: self`;
> - `reviewed`: a curator merges it and the record names that curator in `admitted_by`.
>
> The graph starts `open`. D-22's identity check (an institutional page or ORCID record that links
> the GitHub account) applies under `reviewed` only. Under `open` the site shows every self-admitted
> steward as **self-admitted**.

Rationale: an SSH key was the only door, and no mathematician the network has approached used it.
The owner accepted the trade:
- a forged approval now needs the service's key, not the steward's;
- every approval is its own commit on the graph, so it stays trackable and comes out with one revert.

Overturns if: an approval on the record is shown to be forged. Then the key is rotated, the
approvals it signed are withdrawn, and SSH becomes the only route again until the service's custody
is fixed.

Also changed in D-32's detail: "A steward record is signed with the contributor's SSH key and
submitted by pull request" becomes "...signed with the contributor's SSH key or the network's
approval key (v3.33) and submitted by pull request".

## 2. D-22: curators by invitation, stewards by policy

> **v3.33.** Until a curator rule is written, curators are named by the owner in the graph's
> `curators.json`, by a curator pull request. No one may add themselves.
>
> A steward is admitted under D-32's `steward_admission` policy. While it is `open`, the identity
> check above is suspended, and the site says so on each self-admitted steward.

## 3. D-3: signing words through the service; a steward's or curator's own version

> **v3.33 — approval through the site.** An explainer or gloss signature (v3.17, v3.30, v3.31) may
> be made through the service by a signed-in steward of the target or a curator. The service signs
> it with the approval key over the same canonical body, naming the signer's login. It means what
> an SSH signature means, and is accountable under D-22 in the same way.
>
> A version written by a steward of the target or a curator, through the site or otherwise, may be
> signed by its own author. Its sections are then **verified**: the author is accountable for the
> words both as their writer and as their approver.
>
> It earns once, on the write-up line, as the author's work (D-19). The signature earns nothing
> beyond that, so v3.31's "a signature on one's own version earns nothing" stands.

Rationale: the owner's ruling, "it could be rewritten by a steward or curator". v3.31 left a
steward's own rewrite pending until a second steward signed it. With one steward on a target, that
version could never become final.

## 4. D-35 and D-28: the new service surface

> **v3.33.** The service adds four routes:
> - `GET /session`: who is signed in, and their roles per target;
> - `POST /session/end`: sign out;
> - `POST /stewards`: commit or step down, as the signed-in login;
> - `POST /approvals`: sign a gloss or explainer version's sections.
>
> GitHub sign-in may return to a page on the network's own site and leave a **web session**:
> - an HttpOnly cookie on the service's host, eight hours long;
> - accepted only from the site's own origin;
> - accepted only by the routes above and the words routes.
>
> A web session is the same identity as the login's bearer token, never a second one.
>
> No MCP tool is added: an agent cannot sign in with GitHub, and only a person may hold either role.

## 5. Constitution C8 (not a decision, the same commit)

> **Approval signing key (ed25519):** held by the service, in the service's own secret store and
> nowhere else. Its public half is committed to the graph as `keys/approval.pub`. It signs steward
> records and words approvals made through the site (D-32 v3.33, D-3 v3.33), and nothing else.
>
> Losing it costs approvals until it is rotated. Leaking it lets its holder forge a steward or an
> approval: visible on the record, and undone by withdrawal and rotation. It cannot change a
> verdict, because no gate step reads an approval (D-5).
