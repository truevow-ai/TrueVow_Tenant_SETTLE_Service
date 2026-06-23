# Scraping Tooling & Human-Emulation Research (Open-Source)

**Date:** 2026-06-23
**Purpose:** Decide which open-source tools to integrate *before* running the FL/CA data acquisition plan.
**Companion docs:** `DATA_ACQUISITION_STRATEGY_FL_CA.md` (what to scrape), `REMAINING_GAPS.md` (deferred items), `docs/architecture/SETTLE_DATA_SCRAPING_SPEC.md` (architecture).

---

## TL;DR (the decision)

1. **Most of our volume needs *zero* human emulation.** Tier 1 sources (CourtListener API, FJC IDB, RECAP, MoreLaw) are structured APIs / bulk data. We just need polite HTTP + an API key + rate limiting.
2. **Use an "escalation ladder":** always reach for the cheapest tool that works, and only escalate to a stealth browser for sites that actually fight back.
3. **Replace the hand-rolled stealth** (current `scrape-casemine-stealth.py` manually patches `navigator.webdriver`, hard-codes 6 user-agents) with a **maintained library**, because anti-bot vendors update faster than hand-rolled evasions.
4. **Start Tier 1 now** (no emulation needed) in parallel with building one shared fetcher module for the harder Tier 2/3/5 sources.

---

## The Escalation Ladder

| Level | Tool (open-source) | When to use | Cost | Speed |
|---|---|---|---|---|
| **L0 — Plain HTTP** | `httpx` (already a dependency) | APIs and static HTML pages | $0 | Fast (100s/min) |
| **L1 — TLS/fingerprint impersonation** | `curl_cffi` (bindings to `curl-impersonate`) | Site blocks plain HTTP on TLS/JA3 fingerprint but doesn't need JavaScript | $0 | Fast |
| **L2 — Stealth browser** | `Playwright` (already used) + **`patchright`** (drop-in patched Playwright); fallbacks: **`Camoufox`** (anti-fingerprint Firefox) or **`nodriver`** | JavaScript-heavy pages or sites that fingerprint the browser | $0 | Slow (1–2 pages/min with human pacing) |
| **L3 — Challenge solver** | **FlareSolverr** (Docker sidecar, uses a real browser) | Cloudflare "Just a moment…" interstitials | $0 | Slow |
| **CAPTCHA wall** | *No reliable OSS solver* | — | — | Deprioritize / skip the source |

**Rule:** never run a browser when an API or static fetch works. Browsers are ~50–100x slower and far more fragile.

### Supporting libraries (cross-cutting)
- **`browserforge`** — generates *consistent* browser fingerprints + matching headers. Replaces the manual 6-user-agent list (a mismatched UA/fingerprint is itself a detection signal).
- **`beautifulsoup4`** / `selectolax` — HTML parsing (already used).
- **Human pacing & checkpointing** — already implemented well in `ANTI_BLOCKING_STRATEGIES.md` (randomized 25–40s delays, longer breaks every 5/10 items, context refresh, incremental saves). Keep this; just centralize it.
- **Proxies** — residential/rotating proxies are paid and **out of the ~$5–10 budget**. Strategy: rely on conservative pacing + stealth; only consider proxies if a high-value source blocks by IP. Not adopting now.

---

## Per-Source Mapping (tied to the acquisition strategy)

| Source (tier) | Level needed | Human emulation? | Notes |
|---|---|---|---|
| CourtListener API v4 — FJC IDB / search / RECAP (1a–1c) | **L0** | No | REST API. Free key = 5,000 req/hr. Just rate-limit + paginate. |
| FJC IDB bulk CSV (2d) | **L0** | No | Plain file download. |
| MoreLaw national verdict search (2b) | **L0 → L1** | No | Static HTML; try L0, escalate to L1 if TLS-blocked. |
| ExaSearch discovery (2c) | **L0** | No | Paid API call (~$0.01/query). |
| News / PR Newswire / blogs (4a–4d) | **L0** | No | Static articles. |
| Plaintiff firm "case results" pages (Tier 3) | **L0 → L1/L3** | Rarely | Mostly static marketing pages; a few sit behind Cloudflare → L1 or L3. |
| TopVerdict retry (1d) | **L2** | Yes | Previously failed → needs stealth browser. |
| JuryVerdictAlert previews (2a) | **L2** | Yes | JS-rendered preview cards. Public preview data only. |
| Casemine (existing scraper) | **L2** | Yes | Already stealth; migrate from hand-rolled to `patchright`. |
| County court portals — Miami-Dade ASP.NET, LA Court (Tier 5) | **L2 (+ session/viewstate)**; some **CAPTCHA** | Yes | Hardest. Some have CAPTCHA → likely defer/skip per budget. |
| Google Scholar (4b) | CAPTCHA wall | — | **Avoid** — aggressive blocking. Use ExaSearch instead. |

**Implication:** ~80% of the projected FL+CA volume comes from L0/L1 sources that need **no human emulation**.

---

## Recommended Architecture

Add **one shared fetcher module** (mirroring the existing `insurance_carriers_intelligence/cis_common.py` pattern) so every `cds_*` scraper reuses the ladder instead of re-implementing stealth:

```
settle_data_scraping_factory/
  _common/
    fetcher.py        # fetch(url, level="L0"|"L1"|"L2"|"L3", **opts) -> html/json
    pacing.py         # randomized human delays, checkpointing (lift from ANTI_BLOCKING_STRATEGIES)
    fingerprints.py   # browserforge wrapper (UA + matching headers/viewport)
  court_dockets_records/
    cds_courtlistener.py   # uses fetcher L0
    cds_fjc_idb.py         # uses fetcher L0
    cds_morelaw.py         # uses fetcher L0/L1
    cds_juryverdictalert.py# uses fetcher L2 (patchright)
```

- Keep scraping dependencies **out of the API service image** (the Dockerfile / `.dockerignore` already exclude `settle_data_scraping_factory/`). Put them in a separate `requirements-scraping.txt`.
- Every record keeps **source tagging** and goes through the existing pipeline: anonymizer → injury classifier → anomaly detector → reputation scoring → admin review.

### Suggested `requirements-scraping.txt`
```
httpx
curl_cffi
playwright
patchright
camoufox            # optional, for tough fingerprinting
browserforge
beautifulsoup4
```
(FlareSolverr runs as a Docker container, not a pip package.)

---

## Legal & Ethical Guardrails (reinforce existing spec)

- **Prefer official APIs / bulk data** (CourtListener, FJC) over scraping wherever possible.
- **Public / preview data only.** No PII, no sealed records, no privileged content (already in the scraping spec).
- **Respect `robots.txt` and ToS;** conservative rate limits; identify gracefully.
- Case names used only for **deduplication**, never stored in `settle_contributions`.

---

## Recommendation

**Adopt the escalation ladder and start Tier 1 (L0) immediately** — CourtListener + FJC need no emulation and deliver the bulk of the target (CA target by Week 2, FL by Week 4). In parallel, build the shared `_common/fetcher.py` with L1 (`curl_cffi`) and L2 (`patchright`) so TopVerdict/JuryVerdictAlert/Casemine are ready when we reach Tier 2. Defer L3/CAPTCHA sources (court portals, Google Scholar) unless Tier 1–3 fall short of targets.
