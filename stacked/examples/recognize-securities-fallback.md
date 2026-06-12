# Security Recognition: ISIN fast-path + name-filter fallback

## Context

Three gaps in the `recognize_securities` tool that cause user-facing failures:

**Gap 1 — No ISIN fast-path (fin).**
When a user provides an ISIN (e.g. `INE040A01034`), it falls through to Pinecone
vector search, which embeds the raw ISIN string and returns a semantically
unrelated security. Example: `INE040A01034` (HDFC Bank) → returned Tata Nifty500
MF at score 0.68. There is no direct `etf_mf_security_master.isin` lookup.

**Gap 3 — `"name"` in `HASH_FIELDS` masks security names in cortex logs (redaction_policy.py).**
`cortex/app/observability/redaction_policy.py:20` lists `"name"` in `HASH_FIELDS`.
`redact.py:_redact_dict()` is called by `log_event()` before every structured log emit.
When `fin_client.py` logs the recognize_securities request body, the field `queries[].name`
matches `"name"` and is hashed: `"hdfc bank"` → `"sha256:f43d0727cfb6bf30"`.
This is **log-only** — `redact.py` is used in exactly one place (`events.py:158`).
It does not modify the actual HTTP request body sent to fin.
Origin: commit `e764aca6` (2026-06-01, canonical logging PR) — `"name"` was added as a broad
PII catch-all. Too wide: it catches `queries[].name` (security names, which are public), not
just person names. `"client_name"` is already separately listed and covers the PII case.
Fix: remove `redact.py` + `redaction_policy.py` entirely and drop the `redact_event()` call from `log_event()`.

**Gap 2 — Contradictory fallback instructions (cortex).**
When recognition returns `ticker=None`, the system prompt says two contradictory
things: "MAY fall back to name filtering" (line 432) vs "surface that via
`final_answer` instead of guessing" (line 458). The model follows the conservative
instruction and gives up. Screenshot: user asked "which members … have exposure to
hdfc stock?" → agent replied "I couldn't identify 'hdfc stock', please share the
NSE symbol or ISIN."

### Decisions
1. ISIN fast-path added in fin (`app/resources/nse_listings.py` +
   `app/core/security_recognition/service.py`) — 2026-06-05.
2. Name-filter fallback made MANDATORY in cortex codeact system prompt — 2026-06-05.
3. Fallback uses `get_portfolio_holdings` + `python_exec` filter on `security_name`
   (not `get_portfolio_ticker_exposure`, which requires a confirmed UUID) — 2026-06-05.
4. ISIN detection: regex `^[A-Z]{2}[A-Z0-9]{10}$` (2 letters + 10 alphanumeric) — 2026-06-05.

## Exploration Results

### Resolution order in `SecurityRecognitionService.recognize()` (fin)

`fin/app/core/security_recognition/service.py:355`

Current order:
1. NSE symbol fast-path — `_batch_lookup_nse_symbols()` → SQL on `nse_equity_listing JOIN etf_mf_security_master`; returns score=1.0 on hit.
2. Vector search (Pinecone, `mpnet-multilingual`, threshold=0.3) — all remaining names.

Missing: ISIN fast-path between steps 1 and 2.

### ISIN lookup table

`fin/app/resources/nse_listings.py` — NSE symbol fast-path lives here.
`etf_mf_security_master` has an `isin` column (join key in the NSE query).
A direct ISIN lookup just needs: `SELECT isin, ticker, name, type FROM etf_mf_security_master WHERE isin = ANY($1)`.

### NSE fast-path gate and ISIN implication

`service.py:361` — NSE fast-path is gated: `if "STOCK" in request.security_types`.
`schemas.py:78-90` — default `security_types` includes all 10 types, so "STOCK" is always present when the caller omits the filter. When the caller explicitly passes `["MF"]` or `["AIF"]`, NSE fast-path is skipped entirely.

**ISIN fast-path must NOT share this gate.** ISINs span every security type — a MF ISIN (`INE040A01034`), AIF ISIN, stock ISIN are all valid. If the ISIN fast-path were gated on `"STOCK" in security_types`, it would silently miss any ISIN for a non-stock security. The ISIN path must run unconditionally before both NSE and vector search.

### Embedding failure bug (confirmed)

`service.py:366-374` — when `_get_embeddings` raises (model-service down), the
exception handler returns empty results **even if `nse_map` already has valid hits**.
This caused the session failures (dev1 model-service was down; ETERNAL had an NSE
hit but it was discarded). Fix: return `nse_map` + ISIN hits before attempting
embeddings.

### Contradicting instructions in cortex system prompt

`cortex/app/workflows/client_diagnostics/codeact.py:432-436` — "MAY fall back"
`cortex/app/workflows/client_diagnostics/codeact.py:457-459` — "surface via final_answer instead of guessing"

Second line wins over the first. Need to: change "MAY" → "MUST", remove the
contradicting line, add a concrete 3-step fallback procedure.

### Holdings column for name filter

`fin/app/core/client_diagnostics/service.py:325` — column is `security_name`.
Pattern: `holdings[holdings['security_name'].str.contains(term, case=False, na=False)]`

### Log redaction of security names (new finding — dev2, 2026-06-05)

Debugged thread `91935cba`, run `2884bfa0`, query "does yagnik has exposure to hdfc bank?".
Confirmed via git blame (`e764aca6`, 2026-06-01):

**Root cause of cortex log showing hash:**
- `fin_client.py` calls `log_event("tool.call", metadata={"body": {"queries": [{"name": "hdfc bank"}]}})`
- `log_event()` → `redact_event(payload)` → `_redact_dict()` finds `"name"` key in metadata → hashes to `sha256:f43d0727cfb6bf30`
- Cortex log shows: `queries[0].name = sha256:f43d0727cfb6bf30` ← **log-only, not the real request**

**`HDFCBANK` confirmed in dev DB:**
- `SELECT ... FROM nse_equity_listing JOIN etf_mf_security_master ... WHERE UPPER(nse.symbol) = 'HDFCBANK'` → 1 row, `ticker=07bf1cf8-aa7b-4189-98a4-4a2602776e55`
- NSE fast-path SHOULD resolve "hdfc bank" if fin receives the plaintext

**Remaining open question:** fin's own log shows `input_name=sha256:f43d0727cfb6bf30` from `service.py:logger.info("Security recognised", input_name=query.name, ...)`. Fin has no redaction layer. This needs live HTTP traffic inspection to confirm whether fin receives the hash or plaintext — could not be resolved from static code reading. If fin receives plaintext "hdfc bank", the `candidate_count=19` Pinecone hits would be for the right embedding and the NSE fast-path should have fired first. If fin receives the hash, NSE fails and Pinecone hits are garbage.

**score_threshold:** `0.3` (default, `RECOGNITION_SCORE_THRESHOLD` not set in fin `.env`).

### Confirmed test results (local fin + model-service running)

| Input | Current result | Expected |
|---|---|---|
| `"Eternal"` | MATCH Eternal Ltd. score=1.0 | ✅ (NSE fast-path) |
| `"HDFCBANK"` | MATCH HDFC Bank score=1.0 | ✅ (NSE fast-path) |
| `"INE040A01034"` (HDFC Bank ISIN) | Tata Nifty500 MF score=0.68 | ❌ wrong |
| `"INE002A01018"` (Reliance ISIN) | ICICI Pru MF score=0.664 | ❌ wrong |
| `"INE1NXX01015"` | Nxt-Infra Trust score=0.695 | ❌ wrong |
| `"hdfc stock"` | NDA Securities score=0.712 | ❌ wrong |

### Out of scope
- Fixing vector-search false positives (score threshold / re-indexing).
- Fixing `get_portfolio_ticker_exposure` to accept ISINs directly.

## Stack

```
fin/isin-fast-path         ← implement first (fin repo)
      ↑
fin/embedding-failure-fix  ← return fast-path hits even when embedding fails
      ↑
cortex/name-filter-fallback ← implement after fin is tested (cortex repo)
```

| Layer | What it does | Depends on | Reviewable question | Status |
|-------|-------------|------------|---------------------|--------|
| `fin/isin-fast-path` | Adds `fetch_securities_by_isin` + `_batch_lookup_isins` + ISIN detection | — | Does ISIN lookup return correct ticker + type for STOCK, MF, AIF? | done |
| `fin/embedding-failure-fix` | Returns NSE + ISIN hits before attempting embeddings | isin-fast-path | Are fast-path hits surfaced even when model-service is down? | done |
| `cortex/name-filter-fallback` | Strengthens system prompt: MUST fallback, 3-step procedure | — | Does agent call holdings + filter security_name instead of giving up? | done |
| `cortex/remove-redaction` | Delete `redact.py` + `redaction_policy.py`, drop `redact_event()` call from `events.py` | — | Do cortex logs now show plaintext security names in `queries[].name`? | done |

## Plan

### fin/isin-fast-path

- [x] **Step 1 — Add `is_isin()` + `IsinMatch` + `fetch_securities_by_isin()`** `fin/app/resources/nse_listings.py`
  - Add `_ISIN_RE = re.compile(r"^[A-Z]{2}[A-Z0-9]{10}$")`
  - Add `is_isin(text) -> bool`
  - Add `IsinMatch` dataclass (isin, ticker, name, security_type)
  - Add `fetch_securities_by_isin(connector, isins)` — SQL: `SELECT isin, ticker, name, type FROM etf_mf_security_master WHERE isin = ANY($1)`

- [x] **Step 2 — Add `_batch_lookup_isins()` + wire into `recognize()`** `fin/app/core/security_recognition/service.py`
  - Add `_batch_lookup_isins()` using `fetch_securities_by_isin`; returns `dict[str, SecurityMatchResult]` keyed by ISIN
  - In `recognize()`: detect ISIN inputs with `is_isin()` **before** both the NSE fast-path and the embedding block; run `_batch_lookup_isins()` for those; return hits immediately (score=1.0)
  - **ISIN fast-path must NOT be gated on `"STOCK" in security_types`** — unlike the NSE path (which checks `if "STOCK" in request.security_types` at `service.py:361`), ISINs span all security types (STOCK, MF, AIF, PMS, etc.). Gating on STOCK would silently miss a MF or AIF ISIN. Run unconditionally.
  - Import `is_isin`, `fetch_securities_by_isin`, `IsinMatch` from resources

### fin/embedding-failure-fix

- [x] **Step 3 — Return fast-path hits before embedding block** `fin/app/core/security_recognition/service.py`
  - Collect ISIN + NSE hits for all queries upfront
  - On embedding failure, return the fast-path hits (score=1.0) for matched queries and empty results for unmatched, instead of returning empty for everything

### cortex/name-filter-fallback

- [x] **Step 4 — Strengthen fallback instruction** `cortex/app/workflows/client_diagnostics/codeact.py`
  - Change `"MAY then fall back"` → `"MUST fall back"`
  - Remove the contradicting line at 457-459
  - Add 3-step procedure: `get_portfolio_holdings` → `python_exec` filter on `security_name` → `final_answer` with disclaimer

### cortex/remove-name-from-hash-fields

- [x] **Step 5 — Remove entire `redact.py` + `redaction_policy.py` mechanism** `cortex/app/observability/`
  - Delete `redact.py` and `redaction_policy.py`
  - Remove `redact_event(payload)` call from `events.py:186`
  - Remove the `from app.observability.redact import redact_event` import at `events.py:158`
  - No other changes needed — the rest of `log_event()` stays intact
  - Origin: commit `e764aca6` (2026-06-01); the redaction was added alongside canonical logging but is not needed

## Open questions

1. When ISIN resolution succeeds (returns UUID), should the agent use `get_portfolio_ticker_exposure` with that UUID, or still use the name-filter fallback? -> ISIN resolution returns a ticker UUID, so agent SHOULD use `get_portfolio_ticker_exposure` — same flow as NSE symbol match. Name-filter fallback is only for when ALL resolution paths (ISIN, NSE, vector) return null.
2. Should the ISIN fast-path respect `security_types` filter or always run regardless of type? -> Run regardless — ISIN uniquely identifies a security across all types. Confirmed: NSE fast-path is gated on `"STOCK" in security_types` (`service.py:361`); ISIN path must not share this gate or it silently misses MF/AIF/PMS ISINs.
3. For the name-filter fallback in cortex: should the agent still attempt a name-filter even when the user explicitly gave an ISIN that didn't resolve? -> No — if an ISIN was given and didn't resolve, it's likely not in the system; name-filter would be misleading. Fallback only when user gave a display name / partial name.

## Confirmed findings
- ⚠️ Embedding failure bug: fast-path hits discarded when model-service is down (`service.py:366-374`). This was root cause of Eternal failure in session, not a data gap.
- ⚠️ ISIN vector matches are consistently wrong (random MFs scoring 0.64–0.70) — embedding a raw ISIN string produces a semantically meaningless vector.
- NSE fast-path is reliable (score=1.0) for symbols that exist in `nse_equity_listing`.

### Live run observations (local env, request `5e42ca6c`, 2026-06-04)

Two additional failure modes observed in a live local run against thread `86dfcba2`:

**1. `org_slug` resolution broken in local env — config bug**
`app/services/org_lookup.py` calls `GET {LEDGER_API_BASE_URL}/api/v1/organizations/<org_id>`.
Cortex local env has `LEDGER_API_BASE_URL=http://localhost:8005` (no path prefix).
But ledger's local `.env` sets `ROUTE_PREFIX=/ledger`, so all routes are served at
`http://localhost:8005/ledger/api/v1/...`. Cortex calls `/api/v1/organizations/...`
→ Fiber returns "Cannot GET" 404.
**Fix**: set `LEDGER_API_BASE_URL=http://localhost:8005/ledger` in
`cortex/system_configs/.env` and `cortex/system_configs/.env.local`.
Same root cause for `find_entity` failures — `GET /api/v1/clients/match` also 404
because of the missing `/ledger` prefix.
Not part of this task — tracked here for visibility.

**2. `find_entity` returns 0 matches locally (previous run `f5f2e434`)**
Cortex calls ledger `GET /api/v1/clients/match?name=Aashka+Yagnik+Family...` → 404.
Local ledger doesn't have this endpoint. Entity scope resolution fails completely —
the agent can't ground "Aashka Yagnik Family" to an entity UUID. This is a local
ledger config gap, not a cortex bug.

**3. Agent gave up after recognition without answering the exposure question**
In run `6870adc3` (request `5e42ca6c`): `recognize_securities` returned 19 candidates
(likely matched HDFC Bank). Instead of calling `get_portfolio_ticker_exposure` with
the resolved UUID, the agent ran `python_exec` with status `"Summarising the match"` —
checked whether the ticker resolved and registered a `hdfc_bank_match_check` table —
then called `final_answer` without ever fetching portfolio data. The exposure question
was never answered.
Root cause: the "summarise the match" python_exec step produced a result the agent
treated as the final deliverable. This is the same class of problem as the name-filter
fallback issue — model following a plausible-looking intermediate step to a premature
`final_answer`. Out of scope for this task but related pattern.

## Testing plan
- **ISIN fast-path**: POST to fin `/api/recognition/search` with `INE040A01034` → must return HDFC Bank ticker, score=1.0, correct security_type.
- **Embedding failure**: kill model-service, POST `ETERNAL` → must still return Eternal Ltd. from NSE fast-path.
- **Name-filter fallback**: send "hdfc stock" to cortex dev2 → agent must call `get_portfolio_holdings` + filter, not give up.
- **Regression**: send "HDFCBANK" → still resolves via NSE fast-path, no fallback triggered.
- **Redaction removal**: after deleting `redact.py`, send "hdfc bank" query → cortex `tool.call` log must show `queries[0].name = hdfc bank` (plaintext, not sha256 hash).

## Rollout plan
- fin changes deploy to dev2 first; validate ISIN resolution with test ISINs.
- cortex system prompt change is config-only; rollback = revert the string edit.

## Review
_(fill at end)_
