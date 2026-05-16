# {{BRAND_NAME}} Knowledge Base — Entry Point

The knowledge base is the **fact source-of-truth** for any skill that needs to be accurate about the brand's products, ingredients, mechanisms, history, customer pain points, FAQs, or claims-evidence.

Unlike `brand-voice.md` (how to write) and `brand-rules.md` (what we stand for), the KB is **what's true**.

---

## File vs. directory — pick the maturity level that fits

**Day-1 brand (no KB yet):** This single file is enough. Fill in the sections below as you learn.

**Operating brand:** This file is fine. Add a couple of sibling files (e.g., `knowledge-base-faq.md`, `knowledge-base-products.md`) only when this file gets unwieldy.

**Mature brand (years of customer data, multiple product lines):** Expand to a `knowledge_base/` **directory** with subdirectories per domain. Reference structure (from OrganicAromas):

```
knowledge_base/
├── brand/              # trademark guidelines, voice references, founder story
├── content/            # blog content patterns, evergreen topic library
├── data/               # customer survey data, GA4 reports, GSC snapshots
├── design/             # logo files, color codes, photo style guide
├── email/              # past high-performing email examples, segment definitions
├── leads-strategy/     # B2B target profile, outreach playbooks
├── manuals-and-guides/ # product manuals, how-to-use guides
├── policies/           # returns, shipping, warranty, privacy
├── social/             # platform-specific content libraries
├── tools/              # internal references for skills (API quirks, etc.)
└── wordpress/          # WP schema, custom post types, taxonomy notes
```

When the directory exists, this single file becomes the **index / map** of what lives in each subdirectory.

---

## 1. Products (or services)

{{PRODUCTS_SECTION}}

---

## 2. Mechanism / how it works (the educated buyer's question)

{{MECHANISM_SECTION}}

---

## 3. Common customer questions (FAQ source-of-truth)

{{FAQ_SECTION}}

---

## 4. Customer pain points (what they're trying to solve)

{{PAIN_POINTS}}

---

## 5. Origin story / brand history (for "about us" / founder-voice content)

{{ORIGIN_STORY}}

---

## 6. Evidence library (citations behind allowed claims from `brand-rules.md`)

{{EVIDENCE_LIBRARY}}

---

## 7. Glossary (domain-specific terminology with correct usage)

{{GLOSSARY}}

---

## 8. Operational facts (for skills to query — SKUs, IDs, URLs, integrations)

{{OPERATIONAL_FACTS}}

---

*Skills query this KB **before** drafting any factual claim. If a skill needs a fact that's not in here, it should escalate ("KB gap: I need X to write Y") rather than fabricate.*

---

# PLACEHOLDER REFERENCE — INTERVIEW SCAFFOLD

Walk through these with the user when scaffolding a brand container. **The KB is optional for day-1 brands** — skip what doesn't apply yet and revisit as the brand matures. Track gaps in the brand's `MEMORY.md` so they can be filled in later sessions.

| Section | Question to ask | If user is unsure / gap |
|---|-----------------|--------------------------|
| `{{PRODUCTS_SECTION}}` | List every product/service with: name, SKU/ID, what it is, what makes it different, price range. | Pull from Shopify/WooCommerce/Stripe; flag products with no description |
| `{{MECHANISM_SECTION}}` | How does the product actually work? What's the technical/scientific/craft mechanism? (OA: nebulizing diffusion vs ultrasonic. UT: cold-press extraction. WLH: astrological reading methodology.) | Optional for some brands; critical for any brand selling on the basis of "how it works" |
| `{{FAQ_SECTION}}` | Top 10-20 questions customers ask + the canonical answer. | Pull from support inbox; if no inbox yet, write the questions you'd expect based on the ICP |
| `{{PAIN_POINTS}}` | What pain points does this brand actually solve for the ICP? Be specific — not "feel better" but "the kitchen doesn't smell like wet plastic from the ultrasonic diffuser anymore." | Cross-reference with `brand-rules.md` ICP intent + skepticism sections |
| `{{ORIGIN_STORY}}` | Founder story / why does this brand exist? When was it started? What's the personal stake? | Optional but valuable for newsletter founder-voice content |
| `{{EVIDENCE_LIBRARY}}` | For each "allowed claim" in `brand-rules.md`, the underlying citation/study/testimonial. | Critical for any brand where a customer might ask "how do you know that?" |
| `{{GLOSSARY}}` | Domain-specific terms + their correct usage in this brand's voice. (e.g., OA: "Nebulizing Diffuser®" not "diffuser". WLH: "transit" vs "aspect" vs "house") | If the brand has any specialized vocabulary, define it here so skills don't use it incorrectly |
| `{{OPERATIONAL_FACTS}}` | Things skills need to query: WP base URL, Shopify store ID, Sendy list IDs, Airtable base/table GIDs, social handles. | Most of this is already in `.env`; this section is the **human-readable map** of what lives where |

---

# Maturity ladder — when to graduate from file → directory

Graduate this single file to a `knowledge_base/` directory when **any** of the following are true:
- This file exceeds ~800 lines and topics are starting to bleed into each other
- A subject area (e.g., product manuals, customer surveys) wants its own structured corpus, not a section
- Multiple skills are reading different slices and would benefit from focused per-domain files
- The brand has crossed ~6 months of operating data and "the KB" needs version control per-domain

When you graduate, this file becomes the **index** — list each subdirectory with a one-line description, then keep the section headers above as pointers ("Products — see `knowledge_base/products/`").

---

# Reference brand

**OrganicAromas** runs the full directory model — see `jonops-organicaromas:/home/agent/project/knowledge_base/`. 16 subdirectories, evolved over years. Use as the depth target.

**UtamaSpice** is another mature reference (per Jon's note 2026-05-16: "UtamaSpice or OrganicAromas definitely is" mature enough for full KB).
