# Security Recognition: ISIN fast-path + name-filter fallback

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
