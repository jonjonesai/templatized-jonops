# Brand Onboarding — Activation Sequence

This doc is for the operator (or Claude) bringing up a NEW templatized-jonops container for the first time. It captures the correct skill activation order discovered during the **olylife pilot (2026-05-16)** — a 33-skill brand onboarding done end-to-end in one session.

> **TL;DR.** Skills have dependencies. Activating a downstream skill before its upstream is firing wastes cycles and produces empty queues. Onboard in **dependency tiers** — Tier 0 (true sources) → Tier 4 (consumers).

---

## The Golden Rule

**Activate upstream skills first. Manually fire them once to seed their queues. THEN activate the downstream skills.**

Otherwise: `social-poster-2` runs daily on an empty research queue, `blog-writer` runs on an empty keyword queue, etc. The agent skips gracefully but you get no production work for days.

---

## Pre-flight (before any skill activates)

Container is booted, all skills are `active: false`, scheduler is ticking, telegram-daemon connects. (If this isn't true, see `MIGRATION.md` Phase 1-4.)

Verify:
```bash
ssh jonops-vps 'docker exec jonops-<brand> bash -c "(set -a; . /opt/jonops/projects/<brand>/.env 2>&1 1>/dev/null); echo exit=$?"'
```
Exit `0` = `.env` is shell-safe (no unquoted-spaces values — see Gotcha #1).

---

## Activation Tiers

### Tier 0 — True sources (no upstream)

Activate these first. They produce data the rest of the system consumes.

| Skill | Cadence | What it seeds | First-fire required? |
|---|---|---|---|
| `daily-watchdog` | daily 23:30 | nothing — pure observability | optional (smoke test) |
| `daily-contribution` | daily 07:00 | today's blog post (used by SP1) | yes, to verify content pipeline |
| `market-intelligence` | weekly Mon 02:30 | Market Intelligence table (used by all Tier 1) | **YES — required** |
| `asana-check` | daily 22:00 | reads operator inbox, no upstream | optional |
| `sendy-sync` | daily 06:00 | syncs to ESP, no upstream | optional |
| `email-checker` | daily 11:00 + 21:00 | drafts replies, no upstream | **blocked on Gmail OAuth** — see Gotcha #3 |

After activating + first-firing market-intelligence, the Market Intelligence table will have one record. **Verify before moving to Tier 1:**

```bash
curl -s "https://api.airtable.com/v0/${AIRTABLE_BASE_ID}/${AIRTABLE_MARKET_INTEL_TABLE}?maxRecords=1" \
  -H "Authorization: Bearer ${AIRTABLE_API_KEY}" | jq '.records | length'
```

Expect `1` (or more).

### Tier 1 — Consumes Tier 0

| Skill | Reads | Writes | Notes |
|---|---|---|---|
| `keyword-researcher` | Market Intelligence | Keywords queue | Weekly Mon 08:00 |
| `social-poster-1` | latest published blog | Metricool drafts | Daily 09:00 — needs at least one blog already published |
| `content-researcher` | Market Intelligence | Research table | Per-keyword deep-dive |
| `b2b-outreach-query-researcher` | Market Intelligence | B2B Queries | (skip if not doing B2B) |
| `link-outreach-query-researcher` | Market Intelligence | Outreach Queries | Weekly |

Activate, then manually fire `keyword-researcher` to populate the Keywords queue. **Verify before Tier 2:**

```bash
curl -s "https://api.airtable.com/v0/${AIRTABLE_BASE_ID}/${AIRTABLE_KEYWORDS_TABLE}?filterByFormula=Status%3D'Queued'&maxRecords=5" \
  -H "Authorization: Bearer ${AIRTABLE_API_KEY}" | jq '.records | length'
```

Expect ≥1.

### Tier 2 — Consumes Tier 1

| Skill | Reads | Writes |
|---|---|---|
| `blog-writer` | Keywords queue | Published Posts, WordPress |
| `b2b-outreach-lead-finder` | B2B Queries queue | B2B Leads |
| `link-outreach-lead-finder` | Outreach Queries queue | Outreach Leads |
| `newsletter-researcher` | Published Posts (week) | Newsletter Queue |

Manually fire `blog-writer` once to verify the SEO content pipeline produces a real post.

### Tier 3 — Consumes Tier 2

| Skill | Reads | Writes |
|---|---|---|
| `social-poster-2` | Social Mining Drafts | Metricool drafts |
| `social-researcher` | Market Intelligence + Reddit/web | Social Mining Queue |
| `newsletter-writer` | Newsletter Queue | Sendy campaign sent |
| `email-verifier` | unverified Leads | verified Leads |

### Tier 4 — Engagement / outbound (final layer)

| Skill | Reads | Sends |
|---|---|---|
| `social-engager` | Social Mining Log | Reddit/social replies (manual approval until Phase 2) |
| `b2b-outreach-conductor` | B2B Leads (verified) | Instantly campaigns |
| `link-outreach-conductor` | Outreach Leads (verified) | Email outreach |

### Special: Google-dependent skills (OAuth-gated)

| Skill | Required OAuth |
|---|---|
| `email-checker` | Gmail (gmail.modify, gmail.compose) |
| `gsc-ga4-sweep` | GSC (webmasters.readonly) + GA4 (analytics.readonly) |

**Per the canonical Google OAuth doctrine: ONE `GOOGLE_REFRESH_TOKEN` covers Gmail + GSC + GA4.** If `GOOGLE_*` env vars are `REPL...` placeholders (10-char), wire OAuth before activating any of these.

---

## Lessons from the olylife pilot (gotchas to expect)

### Gotcha #1 — `.env` values with unquoted spaces break bash-source

Docker-compose's env_file parser handles spaces fine. But many skills (especially the `wordpress-kadence` skill) bash-source the `.env` directly — and bash chokes on `KEY=value with spaces`, throwing `command not found` for each whitespace-separated word.

**Fix:** wrap any value containing spaces in double quotes. WP Application Passwords (`Cj4w Ndw6 ...`), multi-word `AIRTABLE_BASE_NAME`, `SENDY_BRAND_NAME` are the usual culprits. Use the `envfix.py` helper pattern from olylife onboarding.

### Gotcha #2 — `cron-dispatcher.sh --slot HH:MM` only handles daily slots

`--slot 02:30` looks up the current day's weekly key (e.g. `saturday_02:30`). If the weekly skill is keyed `monday_02:30`, you can't fire it on a Saturday via `--slot`.

**Workaround:** bypass the dispatcher and invoke claude directly with the production pattern:
```bash
docker exec jonops-<brand> bash -c "
cd /home/agent/project
SKILL=/home/agent/project/.claude/skills/<skill-name>.md
INSTRUCTION='Read the skill file at \$SKILL and execute the COMPLETE pipeline. Follow every step. Do not skip steps. Do not ask for confirmation — execute autonomously.'
claude --print --dangerously-skip-permissions -p \"\$INSTRUCTION\" < /dev/null
"
```

### Gotcha #3 — Google OAuth must be wired *before* Gmail/GSC/GA4 skills

If `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` / `GOOGLE_REFRESH_TOKEN` are placeholders, `email-checker` and `gsc-ga4-sweep` skip gracefully with `SKILL_RESULT: skip` — but they NEVER produce work. Wire OAuth as part of pre-flight, not as a follow-up.

### Gotcha #4 — `TODO_JON` markers in CLAUDE.md

The `init-business` wizard leaves placeholders (`COMPETITORS`, `NICHE_KEYWORDS`, `TARGET_COMMUNITIES`, `HERO_PRODUCT_*`, etc.). Some are blockers, some are not.

**Blockers (fill before activating):**
- `COMPETITORS` — required by `market-intelligence`
- `NICHE_KEYWORDS` — seeds `keyword-researcher`
- `WP_CATEGORIES` — used by `blog-writer`

**Soft (fill iteratively):**
- `TARGET_COMMUNITIES` — used by `social-researcher` (Tier 3)
- `HERO_PRODUCT_*` — used by `blog-writer` for CTA blocks

### Gotcha #5 — Cost-watch the first market-intelligence run

First fire: ~$0.07 (4 DataForSEO + 4 Firecrawl). With more competitors, scales linearly. Set `COMPETITORS` to a tight 3-5 domain list to keep first-run cost <$0.15.

---

## Pilot run reference

| Brand | First boot | Tier-0 firing order | Notes |
|---|---|---|---|
| **olylife** | 2026-05-16 | watchdog → daily-contribution → market-intelligence | Educational SEO lane wide open (no competitor produces educational content). Documented gotchas #1, #2, #3, #5. |

When onboarding a new brand, append a row here.

---

## Quick-reference activation script

The `Educate-before-activate` doctrine (Jon's standing rule): walk the operator through what each skill does BEFORE flipping `active: false → true`. Don't auto-activate skills via batch script.

That said, the *order* of operator-confirmed activations should follow this doc.
