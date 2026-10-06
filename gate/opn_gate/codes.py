"""Every error code the network emits, with what it means and what to do (F13-T29).

The gate names a refusal by a ``Diagnostic``'s ``code`` (D-34) and the service by an
``ApiError``'s; an agent that meets one needs the rule behind it and the next move, in the
guide's plain voice. This module is the one table of both. A test walks the source of
``opn_gate`` and ``opn_api`` and holds the table's keys to the codes the code can emit, exactly,
so a code cannot ship without its row and a row cannot outlive its code.

``source`` says where a code is met: ``gate`` in a verdict's diagnostic (``pregate.sh``, a
precheck, the pull request's gate run, the post-merge job and the curator's commands), ``api``
in a service response's ``error`` field or an MCP tool's error result, and ``both`` when the
service refuses by the gate's own rule before anything is opened. ``step`` is the D-4 step that
emits it, when one does.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Literal

Source = Literal["gate", "api", "both"]
SOURCES: tuple[Source, ...] = ("gate", "api", "both")


@dataclass(frozen=True)
class Code:
    source: Source
    step: int | None
    meaning: str
    remedy: str

    def as_dict(self, code: str) -> dict[str, Any]:
        return {
            "code": code,
            "source": self.source,
            "step": self.step,
            "meaning": self.meaning,
            "remedy": self.remedy,
        }


#: code -> (source, step, meaning, remedy).
_ROWS: dict[str, tuple[Source, int | None, str, str]] = {
    # --- a ------------------------------------------------------------------------------------
    "acknowledged-hazards-invalid": (
        "api",
        None,
        "A proposal's acknowledged_hazards is not a list of {checker, location, justification} "
        "entries.",
        "Copy each entry from the hazard-unacknowledged finding the gate or POST /check (mode "
        "hazards) printed, add a justification, and send the proposal again.",
    ),
    "activation-refused": (
        "gate",
        None,
        "A curator's status record tried to declare a target active while a rule of D-6 or D-33 "
        "still holds it back; the message names the rule.",
        "Meet the named rule first (for example a steward or a complete fidelity record), then "
        "open the activation again.",
    ),
    "active-claims-cap": (
        "api",
        None,
        "You already hold as many active claims as the published cap allows.",
        "Release a claim you no longer need (DELETE /claims/<id>, MCP release_claim; "
        "list_my_claims gives the ids) or wait for one to expire, then claim again.",
    ),
    "affirmation-differs": (
        "gate",
        None,
        "A signed explainer's affirmation is not the fixed sentence the protocol requires.",
        "Sign again with the affirmation copied exactly from the guide's explainer section.",
    ),
    "alternate-duplicate": (
        "gate",
        None,
        "The alternate proof is byte-identical to a proof the node already has.",
        "Nothing to add: the node keeps every different proof and never a copy. Submit only a "
        "proof that differs.",
    ),
    "alternate-multiple": (
        "gate",
        2,
        "The pull request adds more than one alternate proof; one pull request carries one.",
        "Split the alternates into separate submissions, one per pull request.",
    ),
    "alternate-not-proof": (
        "gate",
        2,
        "The file under attempts/ declares a counterexample or a vacuity certificate of a "
        "statement that is already proved, so it is not an alternate proof.",
        "If you believe the merged proof is wrong, file a defect claim (POST /defect-claims) "
        "with a Lean exhibit; an alternate must be another proof of the same statement.",
    ),
    "alternate-submission": (
        "gate",
        2,
        "Not an error: the submission was read as an alternate proof of an already proved node, "
        "and the node's Proof.lean is left as it is.",
        "Nothing to do.",
    ),
    "alternate-unproved": (
        "both",
        2,
        "An alternate proof was submitted for a node with no merged Proof.lean, so there is "
        "nothing for it to be an alternate to.",
        "Submit the proof as the node's Proof.lean (artifact_type proof) instead.",
    ),
    "annex-malformed": (
        "gate",
        2,
        "The skeleton's annex citation line is not a SHA-256 hash.",
        "Cite the annex by the 64-character hash POST /annexes returned for it, on the citation "
        "line the guide shows.",
    ),
    "annex-pending": (
        "api",
        None,
        "The skeleton cites an annex that is still an open pull request and not yet on the node.",
        "Wait for the annex's pull request to merge and the products to render, then precheck "
        "again.",
    ),
    "annex-step-missing": (
        "gate",
        4,
        "The skeleton cites a stepped annex, and some of its holes are not named after any of "
        "that annex's steps.",
        "Rename each hole to the step it proves, or cite an annex whose steps the skeleton "
        "follows.",
    ),
    "annex-steps-unsupported": (
        "api",
        None,
        "The gate this target pins cannot read a stepped annex yet; it will after the target's "
        "next re-pin.",
        "Submit the annex without steps for now.",
    ),
    "annex-too-large": (
        "gate",
        None,
        "The annex file is over the size cap.",
        "Shorten the annex below the cap the message names, or split the mathematics across "
        "annexes.",
    ),
    "annex-uncited": (
        "gate",
        2,
        "The skeleton cites an annex that is not on this node.",
        "Submit the annex first through POST /annexes (MCP submit_informal_annex), wait for it "
        "to merge, and cite the hash it returned.",
    ),
    "annex-unknown": (
        "api",
        None,
        "The skeleton cites an annex that is neither on the node nor in any open pull request.",
        "Submit the annex first through POST /annexes and cite the hash it returns.",
    ),
    "append-invalid": (
        "gate",
        None,
        "An appended record (postmortem, annex, approach record, claim and so on) does not "
        "satisfy its schema; the message names the field.",
        "Fix the field the message names; get_schema (or schemas/<name>.json in the graph) gives "
        "the record's shape.",
    ),
    "append-unreadable": (
        "gate",
        None,
        "An appended file could not be read from the checkout.",
        "Check the file is committed as a regular UTF-8 file and push again.",
    ),
    "arguments-invalid": (
        "api",
        None,
        "An MCP tool's arguments do not match its input schema; the message names the argument.",
        "Read the tool's inputSchema from tools/list and call it again with the named argument "
        "corrected.",
    ),
    "artifact-counterexample": (
        "gate",
        4,
        "Not an error: the submission was checked as a counterexample to the node's statement.",
        "Nothing to do.",
    ),
    "artifact-decl-unknown": (
        "gate",
        4,
        "Proof.lean declares a theorem that is none of the permitted artifacts: a proof, a "
        "counterexample or a vacuity certificate of the statement.",
        "Declare exactly one of the names the message lists; a proof keeps the statement's own "
        "theorem name.",
    ),
    "artifact-elaboration": (
        "gate",
        4,
        "The submitted artifact does not elaborate against the node's statement and dependencies.",
        "Run it locally (pregate.sh) or through POST /check and fix the Lean errors the message "
        "carries.",
    ),
    "artifact-partial": (
        "gate",
        4,
        "Not an error: the submission was checked as a partial proof, and the message lists its "
        "holes.",
        "Nothing to do; once it merges each hole becomes a child node.",
    ),
    "artifact-path-mismatch": (
        "api",
        None,
        "The bundle's file is at the wrong path for its artifact_type: a partial is an assembly "
        "under attempts/, a proof is Proof.lean.",
        "Move the file to the path the message names, or send the artifact_type that matches "
        "where it is.",
    ),
    "artifact-proof": (
        "gate",
        4,
        "Not an error: the submission was checked as a proof of the node.",
        "Nothing to do.",
    ),
    "artifact-reduction": (
        "gate",
        4,
        "Not an error: the partial was checked as a reduction to a new node.",
        "Nothing to do.",
    ),
    "artifact-shape": (
        "gate",
        2,
        "The file must declare exactly one theorem and declares another number.",
        "Keep a single theorem in the file; helper lemmas go inside the proof as `have`.",
    ),
    "artifact-type-invalid": (
        "api",
        None,
        "artifact_type is not one of the accepted values.",
        "Send one of the values the message lists (proof, counterexample, vacuity, partial, ...).",
    ),
    "artifact-type-mismatch": (
        "gate",
        4,
        "The artifact's theorem has a different type from the one this kind of artifact must "
        "have for this node.",
        "Make the declared type exactly the expected type the message prints (details.expected).",
    ),
    "artifact-vacuity": (
        "gate",
        4,
        "Not an error: the submission was checked as a vacuity certificate (the statement's "
        "hypotheses cannot all hold).",
        "Nothing to do.",
    ),
    "author-not-opener": (
        "gate",
        None,
        "A hand-opened gloss or explainer version names an author and changes words that author "
        "wrote, which would show at once as their own edit, but someone else opened the pull "
        "request (F21-Q14).",
        "File it through POST /glosses (the service writes the author from your token), or open "
        "the pull request as the author; to change another person's words, file under your own "
        "name and a steward or curator will review it.",
    ),
    "signer-not-opener": (
        "gate",
        None,
        "A gloss or explainer signature names a signer who did not open the pull request. A "
        "signature verifies under the key it carries, so only the opener says who signed "
        "(F21-Q18).",
        "Open the pull request yourself, as the steward or curator the signature names.",
    ),
    "author-names-another": (
        "api",
        None,
        "Your pseudonym is spelled like the GitHub login of an active steward of the target or a "
        "listed curator, and your identity did not prove that login. The gate reads the author of "
        "a gloss, explainer or withdrawal the service files as the person acting, so the record "
        "would read as theirs (F20-T6).",
        "File it under an identity whose pseudonym names nobody else; a steward or curator files "
        "under the identity that proved their own login.",
    ),
    "attestation-unparseable": (
        "api",
        None,
        "An attestation file in the graph is not valid JSON, so the service cannot read it.",
        "Nothing for you to fix; report it to the graph's curators. Other submissions are "
        "unaffected.",
    ),
    "axiom-not-allowed": (
        "gate",
        5,
        "The proof rests on an axiom outside the target's axiom_allowlist.",
        "Remove the use of the named axioms (get_gate_spec shows the allowlist); a sorry "
        "anywhere also shows up as sorryAx.",
    ),
    "axioms-unreadable": (
        "gate",
        5,
        "The gate could not read the set of axioms the proof rests on.",
        "Re-run the check; if it repeats, report the verdict, since this is the gate's failure "
        "rather than the proof's.",
    ),
    # --- b ------------------------------------------------------------------------------------
    "body-too-large": (
        "api",
        None,
        "The request body is over the service's size limit.",
        "Send a smaller body; a bundle over 512 KiB will not be accepted whatever the route.",
    ),
    "bounced": (
        "gate",
        None,
        "The pull request carries no valid precheck attestation for this node and statement "
        "(missing, wrongly signed or too old), so no build ran.",
        "Run a precheck (POST /precheck or pregate.sh with the hosted signer) and submit with "
        "its attestation; the attestation must be younger than precheck_max_age_s.",
    ),
    "brief-print": (
        "gate",
        None,
        "A QA brief could not print the definitions it needs (curator QA tooling).",
        "Curators: fix the Lean error the message names in the definitions and run the brief "
        "again.",
    ),
    "bundle-invalid": (
        "api",
        None,
        "bundle is not a non-empty object of path to file content.",
        "Send bundle as an object mapping each file's path to its text.",
    ),
    "bundle-too-large": (
        "api",
        None,
        "The bundle is over the size limit.",
        "Send a smaller bundle; only the files your submission adds belong in it.",
    ),
    # --- c ------------------------------------------------------------------------------------
    "callback-incomplete": (
        "api",
        None,
        "GitHub's callback arrived without its code and state parameters.",
        "Start the GitHub sign-in again from GET /auth/github/start.",
    ),
    "certificate-attestor": (
        "gate",
        None,
        "A fidelity certificate's attestor is not the person who opened its pull request.",
        "The signer opens their own certificate's pull request.",
    ),
    "certificate-author": (
        "gate",
        None,
        "The certificate names a different author for its subject than the record does.",
        "Name the author on record for the subject.",
    ),
    "certificate-invalid": (
        "gate",
        None,
        "The fidelity certificate does not satisfy a certificate schema.",
        "Fix the field the message names; get_schema gives the certificate's shape.",
    ),
    "certificate-name": (
        "gate",
        None,
        "The certificate's file name does not match the subject it grades.",
        "Name it fidelity/<subject>-<n>.yaml for the subject it signs.",
    ),
    "certificate-qa-incomplete": (
        "gate",
        None,
        "A signature at this rung needs a complete QA pass for the statement as it stands, and "
        "there is none.",
        "Complete the QA pass for the statement first (the message names what is missing), then "
        "sign.",
    ),
    "certificate-self-signed": (
        "gate",
        None,
        "The attestor authored the subject, and the rung needs a non-author's signature.",
        "Ask someone other than the statement's author to sign.",
    ),
    "certificate-stale": (
        "gate",
        None,
        "The certificate was signed against a statement hash that is no longer the subject's.",
        "Sign a new certificate against the statement as it stands now.",
    ),
    "certificate-subject": (
        "gate",
        None,
        "The certificate grades something that is not a fidelity subject of the target (the root "
        "or a definition).",
        "Grade one of the subjects the message lists.",
    ),
    "certificate-subjects": (
        "gate",
        None,
        "One pull request carries certificates for several subjects; a certificate pull request "
        "signs one.",
        "Open one pull request per subject.",
    ),
    "certificate-uncurated": (
        "gate",
        None,
        "The target has no target.yaml, and certificates stand beside a curated target.",
        "Wait for the target's intake to merge; a new target's certificates ride in its intake.",
    ),
    "certificate-unpinned": (
        "gate",
        None,
        "The certificate uses an older schema that pins no statement, so it counts for nothing.",
        "Write it in the current certificate schema, pinned to the statement it signs.",
    ),
    "check-order": (
        "gate",
        None,
        "An admission check ran before a check it depends on had passed; the earlier failure is "
        "the real one.",
        "Read the first failing check in the verdict and fix that.",
    ),
    "check-timeout": (
        "api",
        None,
        "The fast check did not finish within its time budget.",
        "Make the proof cheaper: replace search tactics such as exact?, apply? and rw? with the "
        "lemma they find. POST /precheck has the gate's full budget if you need it.",
    ),
    "check-unknown": (
        "api",
        None,
        "No fast-check record with that id exists for your identity.",
        "Use a check_id from one of your own POST /check answers.",
    ),
    "checker-busy": (
        "api",
        None,
        "The hosted checker already has as many checks in flight as the service allows.",
        "Retry after the Retry-After header's seconds.",
    ),
    "circular-ancestor": (
        "both",
        None,
        "A circularity defect claim's ancestor field is wrong for its class: missing, not an "
        "ancestor of the node, or present on a claim that is not circular.",
        "Name an ancestor of the node, the statement the node was cut from, only on a circular "
        "claim.",
    ),
    "circular-axiom": (
        "gate",
        None,
        "The circularity exhibit rests on axioms outside the allowlist.",
        "Prove the implication without them.",
    ),
    "circular-direction": (
        "gate",
        None,
        "The circularity exhibit proves the implication the wrong way round. It must prove that "
        "the node implies the ancestor.",
        "State the exhibit as `<node's statement> → <ancestor's statement>`.",
    ),
    "circular-elaboration": (
        "gate",
        None,
        "The circularity exhibit could not be checked against the two statements.",
        "Fix the Lean error in the message; check the exhibit with POST /check first.",
    ),
    "circular-exhibit": (
        "gate",
        None,
        "The circularity exhibit is not the one theorem `<node's statement> → <ancestor's "
        "statement>`.",
        "Declare exactly that one theorem.",
    ),
    "circular-sorry": (
        "gate",
        None,
        "The circularity exhibit uses sorry, so the implication is claimed, not proved.",
        "Finish the proof of the implication.",
    ),
    "claim-unknown": (
        "api",
        None,
        "No claim with that id exists.",
        "list_my_claims (GET /claims/mine) lists your claims with their ids.",
    ),
    "compile": (
        "gate",
        None,
        "A curator QA screen could not compile the statement it screens.",
        "Curators: fix the Lean error the message names and run the screen again.",
    ),
    "config-unknown-checker": (
        "gate",
        6,
        "The graph's gate-spec.json names a hazard checker this gate does not ship.",
        "This is the gate owner's configuration error, not your submission's; report it.",
    ),
    "consequence-shape": (
        "gate",
        None,
        "A QA consequence file does not have the one-theorem shape a consequence takes.",
        "Curators: fix the file the message names.",
    ),
    "content-hash-name": (
        "gate",
        None,
        "An annex or explainer is not named for the SHA-256 of its content.",
        "Name the file <sha256 of its bytes>.md, as the message's expected name says.",
    ),
    "content-missing": (
        "api",
        None,
        "POST /check was sent no Lean text in content.",
        "Put the Lean text to check in content.",
    ),
    "content-not-used": (
        "api",
        None,
        "content was sent in a mode that reads a statement, not a proof text (mode hazards).",
        "Send node_id or statement and leave content out.",
    ),
    "content-too-large": (
        "api",
        None,
        "The text sent to the fast check is over its size limit.",
        "Shorten the proof; a proof this long rarely fits the gate's heartbeat budget either.",
    ),
    "context-invalid": (
        "api",
        None,
        "A node's CONTEXT.json in the graph declares a schema the MCP server cannot read.",
        "Read the node's raw files instead (the error names the path); report it to the curators.",
    ),
    "context-missing-dep": (
        "gate",
        8,
        "Context.lean has no signature for one of the node's declared dependencies. Context.lean "
        "is not a submission path, so this is a defect in the graph.",
        "Report it to the curators; a submission cannot fix it.",
    ),
    "context-signature-mismatch": (
        "gate",
        8,
        "Context.lean's signature for a dependency differs from that dependency's "
        "Statement.lean: a defect in the graph.",
        "Report it to the curators; a submission cannot fix it.",
    ),
    "context-underivable": (
        "api",
        None,
        "The MCP server could not build a node's context bundle from its files.",
        "Read the node's raw files directly; report the node to the curators.",
    ),
    "counterexample-submission": (
        "gate",
        2,
        "Not an error: Proof.lean declares a counterexample, and step 4 checks its type.",
        "Nothing to do.",
    ),
    "credit-correction-same-identity": (
        "gate",
        None,
        "A curator's credit correction moves a ledger line to the identity that already holds "
        "it (F07-T66, D-19 v3.27).",
        "Name the identity that should hold the line as `to`, or null for none.",
    ),
    "credit-correction-unknown-entry": (
        "gate",
        None,
        "A curator's credit correction names a ledger line that its `from` identity does not hold "
        "active on this target (F07-T66, D-19 v3.27).",
        "Copy merge_commit, line, node, artifact (and route_class on an attempts line) from the "
        "entry in ledger/<from>.json as it stands on main, and open the pull request again.",
    ),
    "curator-unlisted": (
        "gate",
        None,
        "The change is a curator's act (status records, versioned nodes, definitions and so on) "
        "and the pull request's author is not a listed curator.",
        "Ask a curator; or, for a statement's correction, file a revision request (POST "
        "/revision-requests).",
    ),
    # --- d ------------------------------------------------------------------------------------
    "dco-not-accepted": (
        "api",
        None,
        "The token request did not accept the Developer Certificate of Origin.",
        "Send dco.accepted: true with the version from GET /dco.json (MCP get_dco).",
    ),
    "dco-version-stale": (
        "api",
        None,
        "dco.version is not the current DCO text's hash.",
        "Read the version from GET /dco.json (MCP get_dco) and send that.",
    ),
    "declaration-clash": (
        "both",
        5,
        "The statement's theorem name is already declared by another node of the target.",
        "Give the theorem a name of its own; the message names the node that holds it.",
    ),
    "defect-class": (
        "both",
        None,
        "The defect claim's class is not one this route or this kind of pull request accepts.",
        "Use a class the schema lists (get_schema defect-claim/v1); a circularity claim is filed "
        "with its own schema.",
    ),
    "defect-line": (
        "both",
        None,
        "The defect claim points at a line beyond the end of the file it names.",
        "Point at a line that exists in that file (a claim names a specific line).",
    ),
    "defect-ref": (
        "gate",
        None,
        "The defect record's stmt_ref is not the statement it sits under.",
        "A node's defects/ names that node; defs/defects/ names a defs/ file. Move the record or "
        "fix stmt_ref.",
    ),
    "defect-route": (
        "gate",
        None,
        "A screen-finding routing names a claim that is not a screen finding in the same "
        "directory.",
        "Curators: route an existing screen-finding claim from its own directory.",
    ),
    "definition-shape": (
        "gate",
        None,
        "A definition file must declare exactly one definition (curator QA).",
        "Curators: keep one definition per defs/ file.",
    ),
    "defs-clash": (
        "gate",
        None,
        "A new defs/ file differs from an existing one only in letter case.",
        "Choose a name that differs in more than case.",
    ),
    "defs-cycle": (
        "both",
        None,
        "The target's definition files import each other in a cycle.",
        "Curators: break the cycle the message prints.",
    ),
    "defs-elaboration": (
        "gate",
        None,
        "A definition file does not elaborate.",
        "Curators: fix the Lean error in the defs/ file the message names.",
    ),
    "defs-import": (
        "gate",
        None,
        "A definition file imports a module that is not a definition of this target.",
        "Import library modules and this target's Defs.* only.",
    ),
    "defs-name": (
        "gate",
        None,
        "A defs/ file name is not a Lean module name.",
        "Name it <Identifier>.lean; it becomes the module Defs.<Identifier>.",
    ),
    "defs-unknown": (
        "api",
        None,
        "The text imports a Defs.* module the target does not have.",
        "Import only the target's own definitions (get_defs lists them).",
    ),
    "dep-cycle": (
        "gate",
        4,
        "The node's declared dependencies form a cycle.",
        "Report it to the curators: a dependency cycle is a defect in the graph.",
    ),
    "dep-meta": (
        "gate",
        4,
        "A dependency's META.yaml could not be read while staging the build.",
        "Report it to the curators, naming the dependency in the message.",
    ),
    "dep-missing": (
        "gate",
        4,
        "A declared dependency is not a node of the target.",
        "Report it to the curators; a submission cannot change a node's dependencies.",
    ),
    "dep-statement": (
        "gate",
        8,
        "A dependency's Statement.lean could not be parsed.",
        "Report it to the curators, naming the dependency in the message.",
    ),
    "dep-unknown": (
        "both",
        8,
        "A declared dependency is not a node of this target.",
        "Declare only node ids that exist in the target (get_target lists them).",
    ),
    "dep-unproved": (
        "gate",
        4,
        "A dependency has no merged Proof.lean, so this node is blocked until it does.",
        "Prove the dependency first, or work on a node the frontier lists as claimable.",
    ),
    "dependency-cycle": (
        "gate",
        8,
        "The proposed node's dependencies would form a cycle in the statement graph.",
        "Remove the dependency that closes the cycle the message prints.",
    ),
    "deps-invalid": (
        "api",
        None,
        "deps is not a list of node ids.",
        "Send deps as a list of node id strings.",
    ),
    "deps-unreadable": (
        "gate",
        8,
        "The gate could not determine which nodes the proof depends on.",
        "Re-run; if it repeats, report the verdict, since this is the gate's failure rather than "
        "the proof's.",
    ),
    "deps-without-statement": (
        "api",
        None,
        "deps was sent without a statement; deps only make sense beside a proposal's statement "
        "text.",
        "Send statement with deps, or leave deps out.",
    ),
    "dispatch-failed": (
        "api",
        None,
        "The precheck job could not be started on the hosted runner.",
        "Retry shortly; if it persists, the service's runner is down.",
    ),
    "dispute-claim-unnamed": (
        "gate",
        None,
        "A curator's disputed status record does not name a valid, standing defect claim on its "
        "own node, so it accepts no dispute and could never lift when a claim is withdrawn "
        "(D-18 v3.28, F08-T38).",
        "Write the record with `opn-gate curator status <node> disputed --cause <why> --reference "
        "defects/<file>`, naming a claim on that node that is on main and not withdrawn.",
    ),
    "draft-not-accepted": (
        "gate",
        None,
        "An added gloss or explainer carries a drafter block. The network drafts nothing and "
        "accepts no new drafts, whoever opens the pull request; the merged drafts stay readable "
        "and can be superseded (F21-R2, D-3 v3.31).",
        "File the version with yourself as its author (drafter: null), by hand or through "
        "POST /glosses; name a model that helped in drafted_with.",
    ),
    "duplicate-submission": (
        "api",
        None,
        "The same submission (comments and whitespace aside) is already merged or open for this "
        "node, a node keeping every different proof and never a copy (D-25 v3.21); or, for "
        "words, another open pull request is already writing a new chain on this file (one "
        "writer per file, F21-R5).",
        "Nothing to submit: details names the existing pull request. For a proof, send only "
        "something that differs; for words, pick another file (list_words_needed) or wait for "
        "that pull request, then supersede what it shows.",
    ),
    # --- e ------------------------------------------------------------------------------------
    "elaboration-failed": (
        "gate",
        None,
        "A Lean module the step builds does not elaborate.",
        "Fix the Lean errors the verdict carries; pregate.sh or POST /check reproduces them "
        "faster.",
    ),
    "evidence-invalid": (
        "api",
        None,
        "evidence is not an object of {text, exhibit?}.",
        'Send evidence as {"text": ..., "exhibit": <optional Lean file>}.',
    ),
    "evidence-stale": (
        "gate",
        None,
        "A catalog-evidence record is pinned to a root statement hash that is no longer the "
        "root's.",
        "Curators: record the evidence again against the root as it stands.",
    ),
    "evidence-unreadable": (
        "gate",
        None,
        "The root's statement could not be read to check a catalog-evidence record against it.",
        "Curators: fix the root's files first.",
    ),
    "exhibit-elaboration": (
        "both",
        None,
        "The Lean exhibit does not elaborate.",
        "Check it with POST /check first and fix the errors; a defect claim's exhibit is Lean "
        "the gate checks, not prose.",
    ),
    "exhibit-hash-mismatch": (
        "gate",
        None,
        "A QA row's exhibit does not hash to what the row recorded.",
        "Curators: record the exhibit's actual hash, or restore the file the row was written "
        "against.",
    ),
    "exhibit-invalid": (
        "api",
        None,
        "exhibit is not the text of a Lean file.",
        "Send exhibit as a string holding the Lean file's text.",
    ),
    "exhibit-missing": (
        "both",
        None,
        "A required Lean exhibit is absent (on a defect claim) or not in the graph (on a QA row).",
        "Send the exhibit as Lean text; a defect claim needs one the gate can check.",
    ),
    "exhibit-node": (
        "gate",
        None,
        "A node a circularity claim relates does not load.",
        "Name two nodes that exist and load; the message says which did not.",
    ),
    "exhibit-replay": (
        "gate",
        None,
        "A QA exhibit could not be replayed against the root.",
        "Curators: fix what the message names and run the replay again.",
    ),
    "exhibit-sorry": (
        "gate",
        None,
        "A QA exhibit uses sorry, so nothing in it was proved.",
        "Curators: finish the exhibit's proof.",
    ),
    "exhibit-timeout": (
        "gate",
        None,
        "Checking the exhibit took longer than the wall-clock cap.",
        "Make the exhibit cheaper to check.",
    ),
    "explainer-absent": (
        "gate",
        None,
        "An explainer signature names an explainer that is not on the node.",
        "Sign an explainer that has merged on the node, by its hash.",
    ),
    "explainer-invalid": (
        "gate",
        None,
        "An explainer's front matter declares a schema and does not satisfy explainer/v1, or its "
        "body is not sections under level-2 headings (F20-R2).",
        "Fix what the message names: exactly one of author and drafter, the target and node it "
        "sits under, and a body of ## sections; rename the file to the SHA-256 of its content.",
    ),
    "explainer-name-unanchored": (
        "gate",
        None,
        "A warning, never a refusal: an explainer section cites a qualified Lean name in "
        "backticks that none of the constants its named outline steps use contains (F20-R5).",
        "Check the section describes the steps it names; cite the name the outline records, or "
        "move the sentence to the section whose steps use it. The pull request may merge as is.",
    ),
    "explainer-proof-unknown": (
        "gate",
        None,
        "An explainer names a proof that is not a merged proof artifact of its node: its "
        "Proof.lean, an alternate or a merged partial assembly (F20-R4).",
        "Set proof to the SHA-256 of one of the artifacts the message lists.",
    ),
    "explainer-step-unknown": (
        "gate",
        None,
        "An explainer's section names an outline step the proof's outline does not have, or "
        "names steps of a proof that has no outline (F20-R4, F20-Q2).",
        "Name only step ids from targets/<id>/outlines/<proof-hash>.json, or drop the "
        "{steps: ...} anchor from the heading.",
    ),
    "explainer-unproved": (
        "gate",
        None,
        "An explainer was filed on a node with no merged proof; it is an annex.",
        "Submit it as an annex (POST /annexes) instead.",
    ),
    # --- f ------------------------------------------------------------------------------------
    "failed": (
        "gate",
        None,
        "A check failed without giving a reason.",
        "Report the verdict: every refusal should say why, and this one did not.",
    ),
    "field-too-long": (
        "api",
        None,
        "A text field is longer than its cap.",
        "Shorten the field the message names.",
    ),
    "filter-unknown": (
        "api",
        None,
        "list_frontier was given a filter on a field the frontier does not have.",
        "Use one of the fields the message lists.",
    ),
    "formalization-declaration": (
        "gate",
        None,
        "A formalization's Statement.lean declares a different theorem name from its record.",
        "Curators: make the record and the file name the same declaration.",
    ),
    "formalization-hash": (
        "gate",
        None,
        "A formalization's Statement.lean hashes to a different value from its record.",
        "Curators: record the file's actual statement hash.",
    ),
    "formalization-incomplete": (
        "gate",
        None,
        "A formalization is missing its record or its Statement.lean.",
        "Curators: add the missing file the message names.",
    ),
    "formalization-name": (
        "gate",
        None,
        "A formalization's record names a different formalization from its directory.",
        "Curators: make the record's name match its directory.",
    ),
    "formalization-shape": (
        "gate",
        None,
        "A formalization's Statement.lean does not have a statement's shape.",
        "Curators: fix the problem the message names.",
    ),
    # --- g ------------------------------------------------------------------------------------
    "github-exchange-failed": (
        "api",
        None,
        "GitHub refused to exchange the sign-in code for an identity.",
        "Start the GitHub sign-in again from GET /auth/github/start.",
    ),
    "github-login-taken": (
        "api",
        None,
        "An identity already exists for this GitHub login.",
        "Use the token you were issued before; one GitHub login holds one identity.",
    ),
    "gloss-absent": (
        "gate",
        None,
        "A gloss signature signs a gloss that is not beside it under gloss/ (F20-R8).",
        "Sign a gloss that is on the record; opn-gate gloss sign refuses before writing one "
        "that is not.",
    ),
    "gloss-invalid": (
        "gate",
        None,
        "A gloss's front matter is missing or does not satisfy gloss/v1: it must name its target "
        "and its subject, set exactly one of author and drafter, and sit under the node (or, for "
        "a definition module, the target) it describes (F20-R1).",
        "Fix the front matter as the message says, rename the file to the SHA-256 of its new "
        "content, and open the pull request again; opn-gate gloss revise writes a valid one.",
    ),
    "gloss-subject-mismatch": (
        "gate",
        None,
        "A gloss's lean_hash is not the hash of the Lean file it describes as the tree holds it "
        "now (F20-R3).",
        "Read the file as it stands, revise the gloss against it and set lean_hash to the current "
        "hash the message names.",
    ),
    "gloss-subject-unknown": (
        "gate",
        None,
        "A gloss describes a Lean file that is not in the tree: a relation on a node with no "
        "Relation.lean, or a definition module not under defs/ (F20-R1).",
        "Name a file that exists: a statement, witness or relation of the node the gloss is filed "
        "under, or a module under the target's defs/.",
    ),
    "glosses-invalid": (
        "api",
        None,
        "The graph's committed targets/<id>/glosses.json does not validate against the glosses "
        "version the service reads, so get_node cannot serve its gloss and explainer chains "
        "(F20-R11).",
        "Report it to the curator: the products need re-rendering by the pinned gate. The raw "
        "files under the node's gloss/ and explainer/ are still readable through the plain path.",
    ),
    "graph-unreachable": (
        "api",
        None,
        "The service could not read the graph repository.",
        "Retry shortly; the graph host may be down or rate-limited.",
    ),
    "graph-unreadable": (
        "gate",
        8,
        "The target's dependency graph could not be read.",
        "Report it to the curators; a META.yaml in the target is malformed.",
    ),
    "graph-unrendered": (
        "api",
        None,
        "The graph's products have no rendered_from commit yet, so there is nothing to pin a "
        "precheck to.",
        "Retry once the post-merge job has rendered the products.",
    ),
    # --- h ------------------------------------------------------------------------------------
    "hazard-unacknowledged": (
        "both",
        6,
        "A hazard checker found something in the statement (a division by zero, a natural "
        "subtraction, an off-by-one range...) that META.yaml does not acknowledge.",
        "Fix the statement, or acknowledge the finding in META.yaml's acknowledged_hazards with "
        "its checker, location and a justification. POST /check mode hazards shows the findings "
        "early.",
    ),
    "hazards-acknowledged": (
        "gate",
        6,
        "Not an error: hazard findings were acknowledged in META.yaml and the step passed, with "
        "the acknowledgments recorded.",
        "Nothing to do; a reviewer sees what was waved through.",
    ),
    "hazards-derived-statement": (
        "gate",
        6,
        "Not an error: hazard findings on a statement the gate itself derived from a merged "
        "skeleton are recorded and not refused.",
        "Nothing to do.",
    ),
    "hazards-preflight-inconclusive": (
        "api",
        None,
        "The proposal asked for a hazard verdict before opening, and the hosted checkers gave "
        "none. Nothing was opened.",
        "Check with POST /check mode hazards whether the checkers are answering and retry, or "
        "send the proposal without the flag and let step 6 decide on the pull request.",
    ),
    "hazards-program-unreadable": (
        "api",
        None,
        "The service's copy of the hazard checkers is missing or unreadable.",
        "Nothing for you to fix; report it. The pull request's own step 6 still runs.",
    ),
    "hazards-unreadable": (
        "gate",
        6,
        "The hazard checkers could not run over the statement.",
        "Check the statement elaborates; if it does, report the verdict.",
    ),
    "heartbeats-invalid": (
        "api",
        None,
        "heartbeats is not true or false.",
        "Send heartbeats as a boolean.",
    ),
    "heartbeats-not-used": (
        "api",
        None,
        "heartbeats was asked for in a mode with no proof to measure.",
        "Use heartbeats in modes check and verify only.",
    ),
    "hole-not-roundtrip": (
        "gate",
        4,
        "A hole's printed type does not elaborate back to the obligation it came from, so its "
        "child node would state a different proposition.",
        "Ascribe types where a bound variable or a numeral is used, or restate the hole over one "
        "type; details shows the text as printed.",
    ),
    "hole-unnamed": (
        "gate",
        4,
        "A sorry in the partial is not bound by a `have`, so it names no child node.",
        "Write every hole as `have <name> : <type> := sorry`.",
    ),
    "hole-witness-ambiguous": (
        "gate",
        7,
        "A carried witness names a hole that several holes of the assembly share.",
        "Give each hole a name of its own.",
    ),
    "hole-witness-context": (
        "gate",
        7,
        "The context a carried witness is checked in does not elaborate.",
        "Fix the Lean error the message names in the assembly.",
    ),
    "hole-witness-duplicate": (
        "gate",
        2,
        "Two carried witnesses name the same hole; a hole takes one witness.",
        "Keep one witness file per hole.",
    ),
    "hole-witness-sorry": (
        "gate",
        2,
        "A carried witness uses sorry; a carried witness is a finished one.",
        "Finish it, or leave the file out and the hole is created with an open witness slot.",
    ),
    "hole-witness-unattached": (
        "gate",
        2,
        "A carried witness is not named after the assembly it belongs to.",
        "Name it as the message shows: the assembly's name with a running number.",
    ),
    "hole-witness-unchecked": (
        "api",
        None,
        "The precheck did not check the carried witnesses, because the gate this target pins "
        "cannot read them yet.",
        "Submit the partial without them, and send each hole's witness through POST "
        "/proposals/witness once the hole exists.",
    ),
    "hole-witness-unknown": (
        "gate",
        7,
        "A carried witness names a hole the assembly does not have.",
        "Use one of the hole names the message lists, as the precheck printed them.",
    ),
    "hole-witness-unnamed": (
        "gate",
        2,
        "A carried witness does not say which hole it is for.",
        "Add a line `-- hole: <name>` with the hole's name.",
    ),
    "hole-witness-unplaced": (
        "gate",
        7,
        "The gate could not work out where a hole's child node would be written.",
        "Report the verdict; the message says what failed.",
    ),
    "hole-witness-unwritable": (
        "gate",
        7,
        "A hole's witness file could not be written for checking.",
        "Report the verdict; the message says what failed.",
    ),
    "hole-witness-without-partial": (
        "gate",
        2,
        "A carried witness was submitted without a partial's assembly beside it.",
        "An existing hole's witness goes in as its Witness.lean (POST /proposals/witness, MCP "
        "propose_witness).",
    ),
    "hole-witnesses": (
        "gate",
        7,
        "Not an error: the partial carries witnesses for some of its holes, each checked as step "
        "7 checks a node's.",
        "Nothing to do.",
    ),
    "host-budget-exhausted": (
        "api",
        None,
        "The service's hourly allowance of calls to the graph host is spent; reads are served "
        "from cache meanwhile.",
        "Retry after the time the message gives.",
    ),
    "hosted-checkers-unreadable": (
        "api",
        None,
        "The service's mapping of hosted checker environments is missing or invalid.",
        "Nothing for you to fix; report it. pregate.sh and POST /precheck do not need it.",
    ),
    # --- i ------------------------------------------------------------------------------------
    "import-forbidden": (
        "gate",
        2,
        "A file imports a module it may not: a statement or proof imports library modules, the "
        "target's Defs.* and its own Context only, plus the use lines a proof declares.",
        "Remove the import the message names. A proof cannot add an import its statement lacks; "
        "declare a use line for a merged node's proof instead.",
    ),
    "intake-incomplete": (
        "gate",
        None,
        "A new target's intake is missing a file it must add.",
        "Curators: add the file the message names to the intake.",
    ),
    "intake-root": (
        "gate",
        None,
        "An intake must add exactly one node, the root.",
        "Curators: add the root node alone in the intake; other nodes come later.",
    ),
    "internal": (
        "api",
        None,
        "The service or the MCP adapter failed in a way it did not expect.",
        "Retry once; if it repeats, report it with the time and the route or tool.",
    ),
    "invalid-token": (
        "api",
        None,
        "The bearer token is unknown, has been revoked, or was replaced by a renewal (D-19).",
        "If it was renewed, use the token the renewal returned. Otherwise get a new token: a "
        "passing tutorial precheck then POST /tokens (MCP get_token), or the GitHub sign-in.",
    ),
    # --- j ------------------------------------------------------------------------------------
    "job-unknown": (
        "api",
        None,
        "No precheck job with that id exists.",
        "Use the job id POST /precheck answered; jobs are kept for a limited time.",
    ),
    # --- k ------------------------------------------------------------------------------------
    "kernel-replay-failed": (
        "gate",
        4,
        "The proof elaborated, but the kernel replay (leanchecker) refused it.",
        "Look for tactics or options that bypass the kernel (debug.skipKernelTC, unsafe code, "
        "implemented_by) and remove them; details carries the replay output.",
    ),
    # --- l ------------------------------------------------------------------------------------
    "layout-extra": (
        "gate",
        2,
        "The node directory holds an entry the layout does not allow.",
        "Remove the unexpected file; the guide's permitted-paths section lists what a node holds.",
    ),
    "layout-misnamed": (
        "gate",
        2,
        "A node entry has the wrong kind (a file where a directory belongs, or the reverse).",
        "Make it the kind the message names.",
    ),
    "layout-missing": (
        "gate",
        2,
        "The node directory lacks a required file or directory.",
        "Add the entry the message names, or check you are submitting against the right node.",
    ),
    "licence-invalid": (
        "api",
        None,
        "The annex's licence is not one of the accepted licences.",
        "Send one of the licences the message lists.",
    ),
    "licence-required": (
        "api",
        None,
        "An annex needs a licence: its author licenses it at submission.",
        "Send licence with one of the accepted values (details.accepted).",
    ),
    "locked-by-a-person": (
        "gate",
        None,
        "A gloss or explainer version naming drafted_with changes or omits a section its chain "
        "shows as written or verified: a person's words are locked against models (F21-R12).",
        "Keep the section the message names exactly as the chain shows it (get_node's shown "
        "sections), changing only drafted ones; or file the version as your own words "
        "(drafted_with: null), and a steward or curator will review the change.",
    ),
    # --- m ------------------------------------------------------------------------------------
    "malformed-body": (
        "api",
        None,
        "The request body is not valid JSON (or not an object).",
        "Send a JSON object with Content-Type: application/json.",
    ),
    "mathlib-pinned": (
        "gate",
        1,
        "Not an error: Mathlib was resolved from the pinned checkout.",
        "Nothing to do.",
    ),
    "memory-exceeded": (
        "gate",
        4,
        "Step 4 was killed at the memory cap, not by the clock.",
        "Make the proof cheaper in memory: split it into smaller `have` steps and avoid huge "
        "`decide` or `simp` calls over large terms.",
    ),
    "meta-dep": (
        "gate",
        2,
        "META.yaml declares a dependency that is not a node.",
        "Report it to the curators; a submission does not change META.yaml.",
    ),
    "meta-id": (
        "gate",
        2,
        "META.yaml's id differs from the node's directory name.",
        "Report it to the curators (or, in a proposal, make the id the directory name).",
    ),
    "meta-invalid": (
        "gate",
        2,
        "META.yaml does not validate against its schema.",
        "Fix the field the message names; get_schema meta/v<n> gives the shape.",
    ),
    "meta-schema": (
        "gate",
        2,
        "META.yaml declares a schema version this gate does not accept.",
        "Use a META schema version the gate accepts (the newest meta/v<n> in schemas/).",
    ),
    "metaprogram-failed": (
        "gate",
        None,
        "One of the gate's Lean metaprograms exited without a verdict.",
        "Check the file elaborates locally; if it does, report the verdict with its output.",
    ),
    "mode-empty": (
        "gate",
        None,
        "The pull request changes no file.",
        "Push the files your submission adds.",
    ),
    "mode-invalid": (
        "api",
        None,
        "POST /check's mode is not one of check, verify, witness or hazards.",
        "Send one of the modes the message lists, or leave mode out for check.",
    ),
    "mode-mixed": (
        "gate",
        None,
        "The pull request mixes kinds of change that each go in a pull request of their own.",
        "Split it: one pull request per kind of change the message lists.",
    ),
    "mode-multi-node": (
        "gate",
        None,
        "The submission touches more than one node; a submission touches one.",
        "Split it into one pull request per node.",
    ),
    "mode-multi-target": (
        "gate",
        None,
        "The submission touches more than one target.",
        "Split it into one pull request per target.",
    ),
    "model": (
        "gate",
        None,
        "The model behind a curator QA brief failed to answer.",
        "Curators: run the brief again; the QA row records it as inconclusive.",
    ),
    # --- n ------------------------------------------------------------------------------------
    "native-decide-unwaived": (
        "gate",
        5,
        "The proof uses native_decide, which trusts the compiler instead of the kernel, and has "
        "no recorded waiver.",
        "Use `decide +kernel` instead: the kernel evaluates the decision and no axiom is left "
        "behind.",
    ),
    "native-decide-waived": (
        "gate",
        5,
        "Not an error: the proof uses native_decide under a recorded waiver; the approving "
        "review must name it.",
        "Nothing to do unless asked; the node is flagged permanently.",
    ),
    "network-mismatch": (
        "gate",
        None,
        "The network repository checked out is not the commit the graph's gate-spec.json pins "
        "(or has local changes), so the run would not speak for the pinned gate.",
        "Check the network repository out at the pinned commit (network_commit in "
        "gate-spec.json), clean, and run again.",
    ),
    "no-hosted-environment": (
        "api",
        None,
        "The target has no hosted checker environment, so the fast check cannot serve it.",
        "Use POST /precheck or pregate.sh instead; GET /hosted-checkers.json lists which targets "
        "are served.",
    ),
    "node-ambiguous": (
        "api",
        None,
        "The node id exists in several targets.",
        "Send target_id as well.",
    ),
    "node-blocked": (
        "api",
        None,
        "The node is blocked (waiting on a dependency, a witness or a revision), so it cannot be "
        "prechecked or submitted.",
        "Work on what blocks it (the message says), or pick a claimable node from list_frontier.",
    ),
    "node-circular": (
        "api",
        None,
        "The node is circular: a merged circularity claim proves an ancestor implies it, so it "
        "is no easier than what it was meant to reduce.",
        "Work on a different node; the message says where the circular path is.",
    ),
    "node-id-invalid": (
        "api",
        None,
        "node_id is not a valid node id.",
        "Send an id matching ^[a-z0-9][a-z0-9-]*$, as the frontier spells it.",
    ),
    "node-id-missing": ("api", None, "node_id is required on this route.", "Send node_id."),
    "node-id-required": (
        "api",
        None,
        "This POST /check mode reads a node's statement and no node_id (or statement) was sent.",
        "Send node_id, or the statement's text as statement where the mode allows it.",
    ),
    "node-missing": (
        "gate",
        2,
        "The node directory does not exist.",
        "Check the node id and target; get_target lists the nodes.",
    ),
    "node-not-claimable": (
        "api",
        None,
        "The node's target is not claimable; the message gives each reason.",
        "Pick a node from list_frontier whose claimable is true.",
    ),
    "node-not-open": (
        "api",
        None,
        "Only an open node on the frontier can be claimed, and this one is not (proved, blocked, "
        "or not yet on the frontier).",
        "Pick a node from list_frontier; the message names a successor if there is one.",
    ),
    "node-pending": (
        "api",
        None,
        "The node is still a proposal in an open pull request.",
        "Wait for that pull request to merge and the products to render, then try again.",
    ),
    "node-superseded": (
        "api",
        None,
        "The node has been replaced by a revision; a proof of a replaced statement closes nothing.",
        "Work on the node that supersedes it (the message names it).",
    ),
    "node-target-mismatch": (
        "api",
        None,
        "node_id belongs to a different target from target_id.",
        "Send the node's own target_id, or leave target_id out and it is derived from the node.",
    ),
    "node-unknown": (
        "api",
        None,
        "The node id is not a node of this graph at the commit the service reads; a node merged "
        "a moment ago may not be rendered yet.",
        "Check the id against list_frontier or get_target; if it merged just now, retry shortly.",
    ),
    "not-configured": (
        "api",
        None,
        "The service is missing configuration and answers 503 until it is set.",
        "Nothing for you to fix; retry later.",
    ),
    "not-found": (
        "api",
        None,
        "No such route, or the graph has no file at the path a read tool asked for.",
        "Check the path against GET / (MCP list_routes), or the file against the graph.",
    ),
    "not-holder": (
        "api",
        None,
        "Only the holder may do this: release a claim, or withdraw a submission.",
        "Use the token of the identity that made the claim or opened the pull request.",
    ),
    # --- o ------------------------------------------------------------------------------------
    "offload-restated-goal": (
        "gate",
        4,
        "A hole is the node's own goal under a new name, so nothing was reduced.",
        "Make each hole strictly smaller work than the node; prove the node directly or "
        "decompose it differently.",
    ),
    "offload-restates-ancestor": (
        "gate",
        4,
        "A hole restates a node this one decomposes, so the statement graph would wait on itself.",
        "Replace the hole with new work that is not an ancestor's statement.",
    ),
    "offload-whole-goal": (
        "gate",
        4,
        "The assembly is a single hole: nothing has been decomposed.",
        "Prove some of the goal in the assembly, or split it into several holes.",
    ),
    "open-pull-requests-cap": (
        "api",
        None,
        "You have as many pull requests open on the graph as the cap allows.",
        "Wait for one to merge or close, or withdraw one (DELETE /submissions/<id>), then send "
        "this again.",
    ),
    # --- p ------------------------------------------------------------------------------------
    "partial-multiple": (
        "gate",
        2,
        "A partial submission adds more than one assembly under attempts/.",
        "Submit one assembly per pull request.",
    ),
    "partial-submission": (
        "gate",
        2,
        "Not an error: the submission was read as a partial proof.",
        "Nothing to do.",
    ),
    "partial-without-holes": (
        "gate",
        4,
        "The partial has no holes, so it is a proof.",
        "Submit it as the node's Proof.lean with artifact_type proof.",
    ),
    "pass-incomplete": (
        "gate",
        None,
        "The statement's QA pass is not complete enough for the signature being asked for.",
        "Curators: run the checks the message lists as missing or awaiting routing.",
    ),
    "path-forbidden": (
        "both",
        2,
        "The submission changes a path it may not: a merged file, another node's files, or "
        "anything outside the permitted paths for its kind.",
        "Change only the paths the guide's permitted-paths table allows for your submission; the "
        "message lists each offending path.",
    ),
    "path-invalid": (
        "api",
        None,
        "A bundle path is not an acceptable path (absolute, too long, or with `..`).",
        "Use relative paths under the node, as the graph lays them out.",
    ),
    "posting-absent": (
        "gate",
        None,
        "A curator's change to target.yaml records no D-10 posting, which is the only change "
        "allowed.",
        "Curators: record the posting, and nothing else, in the change.",
    ),
    "posting-fields": (
        "gate",
        None,
        "A curator's change to target.yaml edits fields besides the posting.",
        "Curators: change the posting alone.",
    ),
    "posting-recorded": (
        "gate",
        None,
        "The target's posting is already recorded and is never rewritten.",
        "Nothing to change; the posting stands.",
    ),
    "posting-unverified": (
        "gate",
        None,
        "Whether the target had a posting before is a fact about the base commit, which this "
        "check was not given.",
        "Run the check with the base commit (the pull request's own gate run has it).",
    ),
    "precheck-bundle-differs": (
        "api",
        None,
        "The bundle differs from the one that was prechecked.",
        "Precheck this exact bundle, then submit it with that job's id.",
    ),
    "precheck-expired": (
        "api",
        None,
        "The precheck's result is past its retention window.",
        "Precheck again and submit with the new job id.",
    ),
    "precheck-not-done": (
        "api",
        None,
        "The precheck job has not finished.",
        "Poll GET /precheck/<id> (MCP get_precheck) until its state is done, then submit.",
    ),
    "precheck-not-passing": (
        "api",
        None,
        "The precheck's verdict is not a pass.",
        "Fix what the precheck's diagnostic names and precheck again.",
    ),
    "precheck-not-yours": (
        "api",
        None,
        "The precheck was run by a different identity.",
        "Precheck with your own token, then submit.",
    ),
    "precheck-required": (
        "api",
        None,
        "A submission needs the id of a passing precheck.",
        "Send precheck_job_id (MCP: attestation) from a passing POST /precheck.",
    ),
    "precheck-statement-differs": (
        "api",
        None,
        "The precheck ran against a proposal's statement, and the node merged with a different "
        "Statement.lean.",
        "Precheck the proof again against the merged node.",
    ),
    "precheck-unknown": (
        "api",
        None,
        "No precheck job with that id exists.",
        "Use the id POST /precheck answered.",
    ),
    "precheck-used": (
        "api",
        None,
        "That precheck has already opened a pull request; a precheck is used once.",
        "Find the pull request in GET /submissions.json, or precheck again for a new submission.",
    ),
    "products-pending": (
        "api",
        None,
        "The node merged a moment ago and its products are not rendered yet.",
        "Retry shortly.",
    ),
    "proof-empty": ("gate", 2, "Proof.lean has no body after `:=`.", "Write the proof after `:=`."),
    "proof-invalid": (
        "api",
        None,
        "The token request's proof is unknown, already used or expired, or an identity already "
        "exists for it.",
        "Start again: run a new tutorial precheck (or the GitHub sign-in) and request the token "
        "with its fresh proof.",
    ),
    "proof-missing": (
        "gate",
        2,
        "The claimed node has no Proof.lean, and the submission adds no partial assembly either.",
        "Add Proof.lean (the statement with sorry replaced), or an assembly under attempts/ for "
        "a partial.",
    ),
    "proof-not-statement": (
        "gate",
        2,
        "Proof.lean is not Statement.lean with only the body replaced: the header or the "
        "signature differs at the line the message gives.",
        "Copy Statement.lean exactly and replace only `sorry` after `:=`; details shows the "
        "expected and the actual line.",
    ),
    "proof-replaces-merged": (
        "both",
        None,
        "The submission modifies a merged Proof.lean, which is never modified.",
        "Submit a later proof as an alternate under attempts/ (the message gives the path).",
    ),
    "proof-unsupported": (
        "api",
        None,
        "proof.kind is not one of the accepted kinds of identity proof.",
        "Send proof.kind tutorial (with the precheck job and nonce) or github.",
    ),
    "proposal-incomplete": (
        "gate",
        None,
        "A proposal must add a whole node directory and this one is missing files.",
        "Add the files the message names; POST /proposals/* builds the directory for you.",
    ),
    "proposal-invalid": (
        "api",
        None,
        "The proposal cannot be built into a node directory; the message says why.",
        "Fix the field the message names and send the proposal again.",
    ),
    "proposal-status": (
        "gate",
        None,
        "A proposal may mark its node speculative and nothing else; other statuses are a "
        "curator's record.",
        "Leave status as the proposal tool writes it.",
    ),
    "proposed-for-author": (
        "gate",
        None,
        "A proposed-for record must be written by the node's proposer or a listed curator.",
        "Have the proposer (or a curator) open it.",
    ),
    "proposed-for-malformed": (
        "both",
        None,
        "A proposed-for record does not have its required shape.",
        "Fix the field the message names; get_schema gives the shape.",
    ),
    "proposed-for-multiple": (
        "gate",
        None,
        "A pull request adds more than one proposed-for record.",
        "Add one per pull request.",
    ),
    "proposed-for-self": (
        "both",
        None,
        "A statement was proposed for itself; it is proposed for another node of its target.",
        "Name the node it was proposed to help prove.",
    ),
    "proposed-for-superseded": (
        "both",
        None,
        "The named node has been superseded by a revision.",
        "Name the live node instead (the message names the successor).",
    ),
    "proposed-for-unknown-node": (
        "both",
        None,
        "The named node is not a node of the target.",
        "Name a node that exists; get_target lists them.",
    ),
    "pseudonym-invalid": (
        "api",
        None,
        "The pseudonym is not 1 to 39 characters of letters, digits and hyphens.",
        "Choose a pseudonym that fits that pattern.",
    ),
    "pseudonym-reserved": (
        "api",
        None,
        "The pseudonym is reserved: the operator's or the gate's own name, or a name on the "
        "published list (D-19), compared without regard to case or to hyphens and underscores.",
        "Choose another; the proof you sent survives the refusal, so send it again with the new "
        "name.",
    ),
    "pseudonym-taken": (
        "api",
        None,
        "Another identity already uses this pseudonym.",
        "Choose another; the proof you sent survives a clash, so send it again with the new name.",
    ),
    "pull-request-failed": (
        "api",
        None,
        "The graph host refused to open the pull request.",
        "Retry shortly; if it persists, the host is down or refusing the service.",
    ),
    # --- q ------------------------------------------------------------------------------------
    "qa-rerun-disagrees": (
        "gate",
        None,
        "A QA row recorded as a pass with no exhibit does not reproduce when the gate re-runs it.",
        "Curators: re-run the check and record what it now says.",
    ),
    "qa-rerun-unverifiable": (
        "gate",
        None,
        "A QA record named for re-running is not a QA record path, or is not in the tree.",
        "Curators: name a record under targets/<id>/qa/ that is committed.",
    ),
    "queue-full": (
        "api",
        None,
        "The graph's queue of pull requests opened through the service is at its cap; nothing "
        "was opened.",
        "Send it again after the Retry-After header's seconds.",
    ),
    # --- r ------------------------------------------------------------------------------------
    "rate-limited": (
        "api",
        None,
        "You reached a rate limit; the message names which, and its window.",
        "Wait for the Retry-After header's seconds. GET /info.json gives the limits in force.",
    ),
    "record": (
        "gate",
        None,
        "A QA record cannot be written or read as evidence (curator QA tooling); the message "
        "says why.",
        "Curators: fix what the message names.",
    ),
    "record-invalid": (
        "both",
        None,
        "A record does not validate against its schema, or is not parseable YAML or JSON.",
        "Fix the field the message names; get_schema gives the record's shape.",
    ),
    "record-not-head": (
        "gate",
        None,
        "A gloss or explainer supersedes a version that is not the current head of a chain of "
        "its own subject: one already superseded, withdrawn, of another file or proof, or not "
        "on the record (F20-R6, F21-R13, D-3 v3.31).",
        "Supersede the head the message names (opn-gate gloss revise writes it), or set "
        "supersedes to null to start a chain of your own.",
    ),
    "record-name-taken": (
        "api",
        None,
        "A record of yours is already being filed this second under the same timestamped file "
        "name.",
        "Send it again after Retry-After; a record's file name is <timestamp>-<pseudonym> to the "
        "second.",
    ),
    "relation-axiom": (
        "both",
        9,
        "A variant's relation proof rests on axioms outside the allowlist.",
        "Prove the relation without them.",
    ),
    "relation-decl": (
        "both",
        9,
        "Relation.lean declares the wrong theorem.",
        "Declare the one relation theorem the message names.",
    ),
    "relation-direction": (
        "both",
        9,
        "A variant's relation proof proves the implication the wrong way round for its label.",
        "A `resolves` variant proves variant → root; a `partial` one proves root → variant. "
        "Prove the one the message names.",
    ),
    "relation-elaboration": (
        "both",
        9,
        "A variant's relation proof does not elaborate.",
        "Fix the Lean errors in the message; POST /check checks it first.",
    ),
    "relation-invalid": (
        "api",
        None,
        "relation is not one of the accepted labels.",
        "Send one of the labels the message lists.",
    ),
    "relation-not-a-variant": (
        "gate",
        9,
        "Relation.lean belongs to variants only, and this node is not one.",
        "Remove Relation.lean, or propose the node as a variant.",
    ),
    "relation-program-unreadable": (
        "api",
        None,
        "The service's copy of the relation checker is missing or unreadable.",
        "Nothing for you to fix; report it. Admission still checks the relation on the pull "
        "request.",
    ),
    "relation-proof-required": (
        "api",
        None,
        "A variant whose label claims an implication needs a relation_proof.",
        "Send relation_proof: a Lean proof of the implication the message names.",
    ),
    "relation-root-context": (
        "gate",
        9,
        "The root's context does not elaborate, so the root's statement cannot be read to check "
        "the relation.",
        "Report it to the curators.",
    ),
    "relation-root-invalid": (
        "gate",
        9,
        "The target's root node does not load.",
        "Report it to the curators.",
    ),
    "relation-root-unknown": (
        "gate",
        9,
        "The target's root is not known, so there is nothing to relate the variant to.",
        "Report it to the curators; a target declares its root.",
    ),
    "relation-sorry": (
        "both",
        9,
        "The relation proof uses sorry, so the implication is claimed, not proved.",
        "Finish the relation proof, or propose the variant with a label that claims no "
        "implication.",
    ),
    "relation-unlabelled": (
        "gate",
        9,
        "Relation.lean is present but claims nothing.",
        "Add a `-- relation: partial` or `-- relation: resolves` line, or drop the file.",
    ),
    "relation_proof-invalid": (
        "api",
        None,
        "relation_proof is not the text of a Lean file.",
        "Send relation_proof as a string holding the Lean file's text.",
    ),
    "require-hazards-preflight-invalid": (
        "api",
        None,
        "The flag asking for a hazard pre-flight is not true or false.",
        "Send it as a boolean, or leave it out.",
    ),
    "row-incoherent": (
        "gate",
        None,
        "A QA row contradicts itself (an exhibit without a finding, or the reverse).",
        "Curators: fix the row the message names.",
    ),
    # --- s ------------------------------------------------------------------------------------
    "section-duplicate": (
        "gate",
        None,
        "An explainer has two sections with the same key: the same set of outline steps named in "
        "two headings, or two unanchored sections beside anchored ones (F21-R11, Q8).",
        "Give each set of steps one section: merge the two, or name different steps; keep one "
        "unanchored overview section.",
    ),
    "service-error": (
        "api",
        None,
        "A service route an MCP tool called refused without naming a code.",
        "Read the message and status; call the plain route (list_routes) to see its full answer.",
    ),
    "signature-invalid": (
        "gate",
        None,
        "An explainer signature does not verify under the record's key.",
        "Sign again with the key the record names.",
    ),
    "signature-section-unknown": (
        "gate",
        None,
        "A gloss or explainer signature approves a section the signed version does not have "
        "(F21-R13): a gloss is one section, whole; an explainer's are overview and steps: keys.",
        "Name only sections the version has (its keys are in glosses.json), or omit sections to "
        "approve them all.",
    ),
    "signature-name": (
        "gate",
        None,
        "An explainer signature's file is named for a different explainer than it signs.",
        "Name the signature file after the explainer it signs.",
    ),
    "signature-node": (
        "gate",
        None,
        "An explainer signature names a different node from the one it sits under.",
        "File the signature under the node it signs.",
    ),
    "signer-unlisted": (
        "gate",
        None,
        "The signer is neither an active steward of the target nor a listed curator.",
        "At Stage 0 only a steward or a curator signs; ask one.",
    ),
    "state-invalid": (
        "api",
        None,
        "The GitHub sign-in's state is unknown, used or expired.",
        "Start the sign-in again from GET /auth/github/start.",
    ),
    "statement-axiom": (
        "gate",
        5,
        "The proposed statement rests on axioms outside the allowlist.",
        "Remove whatever brings them in (a sorry in a definition shows as sorryAx).",
    ),
    "statement-axioms-unreadable": (
        "gate",
        5,
        "The gate could not read the statement's axioms.",
        "Check the statement elaborates; if it does, report the verdict.",
    ),
    "statement-command-forbidden": (
        "both",
        2,
        "A Statement.lean or Context.lean holds a command other than its imports, open, "
        "namespace and end lines, doc comments and sorry-bodied theorems: an attribute, "
        "instance, notation, set_option, #eval, initialize and the like. The checks import "
        "these files as modules of record, so nothing in them may run or change meaning "
        "(D-3 v3.28). The message names the file, the line and the command.",
        "Delete the command the message names. State any definition the statement needs in the "
        "target's defs/ through its curators, and write the theorem without attributes or "
        "modifiers.",
    ),
    "statement-elaboration": (
        "gate",
        5,
        "The proposed Statement.lean does not elaborate.",
        "Fix the Lean errors; POST /check with the statement's text shows them first.",
    ),
    "statement-fails": (
        "api",
        None,
        "The hosted fast checker found Lean errors in the proposed statement, which admission "
        "would refuse; nothing was opened.",
        "Fix the statement's errors (check it with POST /check) and propose it again.",
    ),
    "statement-hash": (
        "gate",
        2,
        "Statement.lean does not hash to META.yaml's statement-hash: the statement was changed.",
        "Never edit Statement.lean; restore it from the graph. A correction is a revision "
        "request (POST /revision-requests).",
    ),
    "statement-invalid": (
        "api",
        None,
        "statement is not the text of a Lean file.",
        "Send statement as a string holding the Lean file's text.",
    ),
    "statement-meaning-changed": (
        "gate",
        4,
        "With the artifact's use lines, its text states a different proposition from the node's "
        "own statement.",
        "Remove the use line that changes the meaning (an instance, a notation or a clashing "
        "name); a use may only add names to prove with.",
    ),
    "statement-meaning-unreadable": (
        "gate",
        4,
        "The gate could not compare the artifact's statement with the node's.",
        "Check the artifact elaborates; if it does, report the verdict.",
    ),
    "statement-missing": (
        "api",
        None,
        "statement is required on this route.",
        "Send statement: the Lean text of the statement you propose.",
    ),
    "statement-not-used": (
        "api",
        None,
        "statement is read in modes witness and hazards only.",
        "Check a statement's text as content in mode check, or switch mode.",
    ),
    "statement-shape": (
        "gate",
        2,
        "Statement.lean must declare exactly one theorem, with sorry as its body.",
        "Keep one sorry-bodied theorem in the file.",
    ),
    "statement-unparsable": (
        "api",
        None,
        "A node's Statement.lean in the graph has no single sorry-bodied theorem.",
        "Report the node to the curators.",
    ),
    "statement-with-node": (
        "api",
        None,
        "Both node_id and statement were sent; a node's statement is its own.",
        "Send one of them.",
    ),
    "step-order": (
        "gate",
        None,
        "A gate step ran without the steps it needs having passed; the earlier failure is the "
        "real one.",
        "Read the first failing step in the verdict and fix that.",
    ),
    "steward-key": (
        "gate",
        None,
        "A steward's step-down is signed with a different key from the one they committed with.",
        "Sign the step-down with the commitment's key.",
    ),
    "steward-login": (
        "gate",
        None,
        "The steward record's login is not a GitHub login.",
        "Use the steward's GitHub login.",
    ),
    "steward-name": (
        "gate",
        None,
        "A steward record is not named stewards/<n>.yaml, numbered.",
        "Name it with the next number.",
    ),
    "steward-not-active": (
        "gate",
        None,
        "A step-down names someone with no counting commitment to step down from.",
        "Only an active steward steps down.",
    ),
    "steward-sentence": (
        "gate",
        None,
        "The steward record's sentence is not the fixed one for its action.",
        "Copy the commitment or step-down sentence exactly from the guide.",
    ),
    "steward-signature": (
        "gate",
        None,
        "The steward record's signature does not verify under its key.",
        "Sign again with the key the record names.",
    ),
    "steward-target": (
        "gate",
        None,
        "The steward record names a different target from the directory it sits in.",
        "File it under the target it names.",
    ),
    "steward-uncurated": (
        "gate",
        None,
        "A steward commits to a curated target, and this one has no target.yaml.",
        "Wait for the target's intake to merge.",
    ),
    "stmt-ref-invalid": (
        "api",
        None,
        "stmt_ref is not a node id or <target>/defs/<file>.lean.",
        "Send the node id, or the defs/ path, of the statement the record is about.",
    ),
    "stmt-ref-missing": ("api", None, "stmt_ref is required.", "Send stmt_ref."),
    "stmt-ref-unknown": (
        "api",
        None,
        "stmt_ref names a file the graph does not have.",
        "Name an existing node or defs/ file.",
    ),
    "subject-invalid": (
        "api",
        None,
        "POST /glosses's subject is not one the route takes: an object of kind, node_id, "
        "target_id, module, proof and lean_hash, its kind a statement, witness, relation, "
        "definition or proof, an explainer's naming the artifact's hash (F20-R10).",
        "Send {kind, node_id} for a node's Lean file, {kind: definition, target_id, module} for a "
        "definition module, or {kind: proof, node_id, proof} for an explainer; the author is your "
        "token's identity and is never sent.",
    ),
    "submission-id-invalid": (
        "api",
        None,
        "The submission id is neither a ULID the service issued nor a pull-request number.",
        "Use the id POST /submissions answered, or the pull-request number.",
    ),
    "submission-merged": (
        "api",
        None,
        "The pull request has merged; a merged submission is part of the record and cannot be "
        "withdrawn.",
        "To correct it, file a revision request or a defect claim.",
    ),
    "submission-unknown": (
        "api",
        None,
        "The id is neither a pull request the service opened nor one the graph has attested.",
        "Check the id against GET /submissions.json (MCP list_submissions).",
    ),
    # --- t ------------------------------------------------------------------------------------
    "target-id-invalid": (
        "api",
        None,
        "target_id is not a valid target id.",
        "Send an id matching ^[a-z0-9][a-z0-9-]*$, as list_targets spells it.",
    ),
    "target-id-missing": ("api", None, "target_id is required on this route.", "Send target_id."),
    "target-id-required": (
        "api",
        None,
        "POST /check needs to know the target.",
        "Send target_id, or a node_id and the node's own target is used.",
    ),
    "target-unknown": (
        "api",
        None,
        "The id is not a target of this graph.",
        "Use an id from list_targets (targets/index.json).",
    ),
    "text-missing": ("api", None, "text is required.", "Send text."),
    "timeout": (
        "gate",
        None,
        "A step exceeded its wall-clock cap.",
        "Make the proof cheaper (name lemmas instead of searching, split heavy steps); the "
        "gate-spec's step caps are fixed.",
    ),
    "token-expired": (
        "api",
        None,
        "The write token lapsed after a long stretch without use: 180 days at the pilot "
        "(OPN_API_TOKEN_IDLE_DAYS); a token in use never lapses (D-19 v3.29). The identity is "
        "kept.",
        "Ask your human operator for the identity's recovery code and call POST /tokens/recover "
        "{pseudonym, recovery_code} (recover_token) for a new token. A GitHub identity may "
        "instead prove the same login again (GET /auth/github/start, then POST /tokens with the "
        "same pseudonym).",
    ),
    "too-many-holes": (
        "gate",
        4,
        "The partial has more holes than the cap allows.",
        "Prove more inside the assembly, or decompose in stages.",
    ),
    "tool-unknown": (
        "api",
        None,
        "The MCP server has no tool by that name.",
        "Call tools/list for the tool names.",
    ),
    "toolchain-missing": (
        "gate",
        1,
        "The pinned Lean toolchain (or Mathlib) is not installed where the gate runs.",
        "Install it with $NETWORK/gate/scripts/install-toolchain.sh, or use the devcontainer.",
    ),
    "tooling-invalid": (
        "api",
        None,
        "The tooling field is not a string.",
        "Send model_and_tooling (or tooling) as a short string naming what you used.",
    ),
    "ttl-above-cap": (
        "api",
        None,
        "ttl_hours is above the published cap.",
        "Ask for at most the cap the message names.",
    ),
    "ttl-invalid": (
        "api",
        None,
        "ttl_hours is not a positive integer.",
        "Send a whole number of hours.",
    ),
    # --- u ------------------------------------------------------------------------------------
    "unauthenticated": (
        "api",
        None,
        "This route or tool needs a bearer token and none was sent.",
        "Send `Authorization: Bearer <token>`; the guide's token section says how to get one "
        "without an account.",
    ),
    "undeclared-dependency": (
        "gate",
        8,
        "The proof uses a theorem from another node that META.yaml does not declare as a "
        "dependency.",
        "Prove it without that node, or declare a use line for that node's merged proof.",
    ),
    "unexpected-error": (
        "gate",
        None,
        "The gate raised an error it did not expect.",
        "Report the verdict with its details; it is the gate's failure, not the proof's.",
    ),
    "unknown-field": (
        "api",
        None,
        "The request has fields this route does not accept.",
        "Send only the fields the message lists.",
    ),
    "unparseable": (
        "api",
        None,
        "A graph file an MCP read tool fetched is not a record it can parse.",
        "Read the raw file instead; report it to the curators.",
    ),
    "upstream-unavailable": (
        "api",
        None,
        "The hosted fast checker did not answer.",
        "Retry shortly, or use POST /precheck, which does not depend on it.",
    ),
    "use-ancestor": (
        "gate",
        2,
        "The proof uses a node that itself rests on this node, so the statement graph would wait "
        "on itself.",
        "Prove the node from what lies beside or below it, never from a node it was written to "
        "help prove.",
    ),
    "use-duplicate": (
        "gate",
        2,
        "The header imports the same module twice, or a module the statement already imports.",
        "Name each used module once.",
    ),
    "use-redundant": (
        "gate",
        2,
        "The used node is already a dependency, reached through the node's Context.",
        "Remove the use line; the dependency's theorem is already available.",
    ),
    "use-self": ("gate", 2, "The proof uses its own node's proof.", "Remove the use line."),
    "use-superseded": (
        "gate",
        2,
        "The used node has been replaced by a revision.",
        "Use the successor's proof (the message names it).",
    ),
    "use-unknown-defs": (
        "gate",
        2,
        "The proof uses a definition module the target does not have.",
        "Use only definitions already on the graph; a new definition is a curator's pull request.",
    ),
    "use-unknown-node": (
        "gate",
        2,
        "The proof uses a node that does not exist in the target.",
        "Use only nodes of the target; get_target lists them.",
    ),
    "use-unproved": (
        "gate",
        2,
        "The proof uses a node that has no merged proof.",
        "Wait for that node's Proof.lean to merge, or prove without it.",
    ),
    "use-unused": (
        "gate",
        8,
        "The header declares a use the proof term does not make.",
        "Remove the unused use line.",
    ),
    "used-constants": (
        "gate",
        None,
        "The gate could not list the constants a QA subject uses (curator QA tooling).",
        "Curators: check the subject elaborates and run the QA step again.",
    ),
    # --- v ------------------------------------------------------------------------------------
    "vacuity-submission": (
        "gate",
        2,
        "Not an error: Proof.lean declares a vacuity certificate, and step 4 checks its type.",
        "Nothing to do.",
    ),
    # --- w ------------------------------------------------------------------------------------
    "waiver-invalid": (
        "gate",
        5,
        "The native_decide waiver file does not validate against its schema.",
        "Fix the waiver file the message names, or replace native_decide with `decide +kernel` "
        "and drop the waiver.",
    ),
    "waiver-unapproved": (
        "gate",
        None,
        "The proof merged using native_decide under a waiver, but no approving review names the "
        "waiver.",
        "The reviewer adds the line the message gives to their approval.",
    ),
    "waiver-unneeded": (
        "gate",
        5,
        "A waiver file is present but the proof does not use native_decide.",
        "Remove the waiver file.",
    ),
    "withdraw-failed": (
        "api",
        None,
        "The pull request could not be closed; it is still open.",
        "Retry shortly.",
    ),
    "withdrawal-unknown-record": (
        "gate",
        None,
        "A withdrawal names a record that is not a valid status record or defect claim of the "
        "withdrawal's own node, nor a gloss or explainer version beside it (F08-T31, D-18 v3.27; "
        "F20-R7).",
        "Name the record as status/<file>, defects/<file>, gloss/<hash>.md or "
        "explainer/<hash>.md of the node (or, for a definition gloss, the target) the withdrawal "
        "is filed under, as it stands on main, and open the pull request again.",
    ),
    "withdrawal-unauthorized": (
        "gate",
        None,
        "A gloss or explainer version is withdrawn by someone who is neither its author, an "
        "active steward of the target nor a listed curator (F20-R7, D-3 v3.30).",
        "Ask the version's author, a steward of the target or a curator to withdraw it, or file a "
        "chain of your own.",
    ),
    "witness-axiom": (
        "both",
        7,
        "Witness.lean rests on axioms outside the allowlist.",
        "Build the witness without them.",
    ),
    "witness-completion-unverified": (
        "gate",
        None,
        "Whether the witness slot was still open is a fact about the base commit, which this "
        "check was not given.",
        "Run the check with the base commit (the pull request's own gate run has it).",
    ),
    "witness-elaboration": (
        "gate",
        7,
        "Witness.lean does not elaborate.",
        "Fix the Lean errors; POST /check mode witness shows the expected type and the errors "
        "first.",
    ),
    "witness-fails": (
        "api",
        None,
        "The witness has the type step 7 wants but does not compile on the hosted checker; "
        "nothing was opened.",
        "Fix the errors (POST /check mode witness) and send it again.",
    ),
    "witness-filled": (
        "gate",
        None,
        "The node already has a real witness, and a witness is immutable once it is real.",
        "Nothing to add; a different witness is a different node.",
    ),
    "witness-invalid": (
        "api",
        None,
        "witness is not the text of a Lean file.",
        "Send witness as a string holding the Lean file's text.",
    ),
    "witness-missing": (
        "both",
        7,
        "The node has no Witness.lean, or the request sent no witness.",
        "Supply the witness: POST /proposals/witness (MCP propose_witness) for an open slot.",
    ),
    "witness-not-a-hole": (
        "gate",
        None,
        "Only a hole's witness slot is filled in after the node exists; any other witness is "
        "immutable.",
        "Nothing to add here; propose a new node if the statement needs a different witness.",
    ),
    "witness-not-missing": (
        "api",
        None,
        "The node's witness slot is not open; only a hole blocked for want of a witness takes one.",
        "Check the node's status and cause with get_node.",
    ),
    "witness-program-unreadable": (
        "api",
        None,
        "The service's copy of the witness-type program is missing or unreadable.",
        "Nothing for you to fix; report it. Step 7 still runs on the pull request.",
    ),
    "witness-shape": (
        "gate",
        7,
        "Witness.lean does not declare the one theorem named `witness`.",
        "Declare `theorem witness : <expected type>`; POST /check mode witness prints the "
        "expected type.",
    ),
    "witness-slot-open": (
        "gate",
        7,
        "Not an error: a revision of a hole carries the hole's unfilled witness slot and is "
        "admitted blocked until a witness is supplied.",
        "Supply the witness through POST /proposals/witness once it is admitted.",
    ),
    "witness-sorry": (
        "both",
        7,
        "Witness.lean rests on sorry, directly or through a Context declaration it uses.",
        "Finish the witness; a carried or proposed witness must be complete.",
    ),
    "witness-type-mismatch": (
        "both",
        7,
        "The witness's type is not the one the statement's hypotheses need.",
        "Make the witness's type exactly the expected type; POST /check mode witness prints it.",
    ),
    "writeup-name": (
        "gate",
        None,
        "A write-up record is not named writeup/<n>.yaml, numbered.",
        "Name it with the next number.",
    ),
    "writeup-signature": (
        "gate",
        None,
        "The write-up record's signature does not verify under its key.",
        "Sign again with the key the record names.",
    ),
    "writeup-signer": (
        "gate",
        None,
        "The write-up's signer is neither an active steward of the target nor a listed curator.",
        "Have a steward or a curator sign it.",
    ),
    "writeup-target": (
        "gate",
        None,
        "The write-up record names a different target from the directory it sits in.",
        "File it under the target it names.",
    ),
    # --- y ------------------------------------------------------------------------------------
    "yaml-invalid": (
        "api",
        None,
        "The yaml field is not parseable YAML, or not a mapping.",
        "Send the record as a YAML mapping (or a JSON object).",
    ),
}

CATALOG: dict[str, Code] = {code: Code(*row) for code, row in _ROWS.items()}


def document(prefix: str | None = None) -> dict[str, Any]:
    """The catalog as one JSON document, in code order; ``prefix`` keeps the codes that start
    with it (``witness-`` for every witness refusal)."""
    rows = [
        CATALOG[code].as_dict(code)
        for code in sorted(CATALOG)
        if prefix is None or code.startswith(prefix)
    ]
    return {
        "about": "Every error code the Open Proof Network emits: where it is met, what it "
        "means and what to do about it.",
        "prefix": prefix,
        "count": len(rows),
        "codes": rows,
    }


def render_json(prefix: str | None = None) -> str:
    """``document`` as the bytes ``GET /errors.json`` serves: sorted keys, UTF-8, a newline."""
    return json.dumps(document(prefix), ensure_ascii=False, indent=2, sort_keys=True) + "\n"
