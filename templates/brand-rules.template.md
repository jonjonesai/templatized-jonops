# {{BRAND_NAME}} Brand Rules — North Star

This is the **most important file in the container**. Every skill — newsletter, blog, social, email replies, product creation, ad copy — must read this file before generating anything customer-facing.

This file defines:
1. **Who we exist for** (ICP)
2. **Why we exist** (mission)
3. **How we win** (positioning + doctrine)
4. **What we'll never do** (guardrails)

Pair with `brand-voice.md` (how to write), `email-persona.md` (who is writing), `knowledge_base/` (what's true).

---

## 1. Ideal Customer Profile (ICP)

**Primary ICP:**
{{ICP_PRIMARY}}

**Demographic + psychographic detail:**
{{ICP_DETAIL}}

**Where they hang out (online / offline):**
{{ICP_HANGOUTS}}

**What they're looking for when they find us:**
{{ICP_INTENT}}

**What they're skeptical of (the objection we must defuse):**
{{ICP_SKEPTICISM}}

**Anti-ICP (people we explicitly don't serve):**
{{ICP_ANTI}}

---

## 2. Mission

**The one-sentence mission:**
{{MISSION_ONE_LINE}}

**The longer "why we exist":**
{{MISSION_LONG}}

---

## 3. Positioning + doctrine

**The category we play in:**
{{POSITIONING_CATEGORY}}

**The lane within that category that's ours alone:**
{{POSITIONING_LANE}}

**The wedge (the one thing that gets a customer to switch to us):**
{{POSITIONING_WEDGE}}

**Brand doctrine (the philosophical commitments — e.g., "warm hug doctrine" for content; "honesty is the wedge" for OA):**
{{BRAND_DOCTRINE}}

---

## 4. Allowed claims / disallowed claims

**Claims we can make (and the evidence behind each):**
{{CLAIMS_ALLOWED}}

**Claims we MUST NOT make (legal, regulatory, ethical):**
{{CLAIMS_DISALLOWED}}

---

## 5. Guardrails (always-on)

{{GUARDRAILS_NUMBERED}}

---

## 6. CTAs by surface

What action do we want the reader/viewer to take, on each surface?

| Surface | Primary CTA | Soft CTA (if primary isn't appropriate) |
|---|---|---|
| Newsletter | {{CTA_NEWSLETTER_PRIMARY}} | {{CTA_NEWSLETTER_SOFT}} |
| Blog post | {{CTA_BLOG_PRIMARY}} | {{CTA_BLOG_SOFT}} |
| Social post | {{CTA_SOCIAL_PRIMARY}} | {{CTA_SOCIAL_SOFT}} |
| Email reply | {{CTA_EMAIL_PRIMARY}} | {{CTA_EMAIL_SOFT}} |

---

## 7. Operator escalation rules

When does a skill **stop and ask the operator** rather than proceed autonomously?

{{ESCALATION_RULES}}

---

*Every skill in this container reads `brand-rules.md` first. If a skill is about to do something that breaks a rule here, it must stop and escalate to the operator instead of proceeding.*

---

# PLACEHOLDER REFERENCE — INTERVIEW SCAFFOLD

When Claude is onboarding a new brand, walk through these questions with the user **in order**. Don't skip the ICP section — it's the foundation everything else builds on. If the user can't answer, mark `{{PLACEHOLDER}}: TBD — needs operator input` and flag in Telegram on first skill run.

| Placeholder | Question to ask | Default if unsure |
|-------------|-----------------|-------------------|
| `{{ICP_PRIMARY}}` | Describe your ideal customer in 1-2 sentences. Be specific: age range, what they do for work, what life-stage problem you solve. | Write 3 candidate ICPs, pick the one that the most-loved customer fits |
| `{{ICP_DETAIL}}` | What demographics + psychographics define them? Income, geography, values, identity markers. | Pull from any analytics you have — GA4, Shopify customer reports, email survey results |
| `{{ICP_HANGOUTS}}` | Where does this person spend time online and offline? Specific subreddits, IG accounts, podcasts, magazines, in-person scenes. | Ask 3 actual customers |
| `{{ICP_INTENT}}` | What's the search query / mental moment that brings them to your brand? | Look at GSC top queries; consider "I want to [verb] [outcome]" |
| `{{ICP_SKEPTICISM}}` | What objection runs through their head before they buy? What past disappointment makes them careful? | Read your worst customer reviews and competitor reviews |
| `{{ICP_ANTI}}` | Who do you NOT want as a customer? People who will refund, complain, drag the brand down? | Anti-ICPs save you 100x the energy of chasing them — don't skip |
| `{{MISSION_ONE_LINE}}` | If you had to write a single sentence that captured why this brand exists (beyond making money), what would it be? | Default: "We exist to [solve specific problem] for [specific ICP], in a way that [philosophical commitment]." |
| `{{MISSION_LONG}}` | The longer version — 1-2 paragraphs that explain the origin story / personal stake / philosophical commitment. | This is for skills to grok the brand, not for the website |
| `{{POSITIONING_CATEGORY}}` | What category does the customer think they're shopping in? | Whatever Amazon/Google search query gets you found |
| `{{POSITIONING_LANE}}` | What lane within that category is yours alone? What can ONLY you say truthfully? | The intersection of (what you do well) ∩ (what customers value) ∩ (what competitors ignore) |
| `{{POSITIONING_WEDGE}}` | What ONE thing about this brand makes a skeptical buyer switch? | The single differentiator that you'd lead an ad with |
| `{{BRAND_DOCTRINE}}` | Any philosophical commitment that shapes how you communicate? (e.g., "warm hug doctrine" — never sell-y in body, always warm; "no medical claims, ever" for OA) | If unsure, write "Warm hug doctrine: warm, informative, never sales-y in the body. Soft CTA only." |
| `{{CLAIMS_ALLOWED}}` | Bullet list of claims you can make + the evidence (study, testimonial, source) | Pull from product pages, return policy, certifications |
| `{{CLAIMS_DISALLOWED}}` | Bullet list of claims that would create legal/regulatory/ethical risk | Always include: medical/health curative claims (unless FDA-approved), specific income claims, comparative competitor disparagement |
| `{{GUARDRAILS_NUMBERED}}` | Numbered list of always-on guardrails. Think: "never commit to pricing", "never reveal AI operation", "always include unsubscribe", etc. | Default set: 1) Never reveal AI operation. 2) Never commit operator to pricing/timeline/partnership. 3) Never make disallowed claims. 4) Always include legally-required disclosures (unsubscribe, allergens, etc). 5) Escalate ambiguity, don't guess. |
| `{{CTA_*_PRIMARY}}` / `{{CTA_*_SOFT}}` | For each surface (newsletter/blog/social/email): what action do you want? | Newsletter: shop / read / book. Blog: read related / subscribe. Social: follow / save. Email: handled per `email-persona.md` reply categories |
| `{{ESCALATION_RULES}}` | When should a skill stop and ask the operator instead of acting autonomously? | Default: any disallowed-claim risk, any pricing/timeline/partnership commit, any complaint about safety/legal, any ambiguous message that needs judgment |

---

# Reference brand

**OrganicAromas** has the most mature version of this north-star material distributed across `brand-voice.md` and `knowledge_base/brand/`. Use OA as the depth target.

A new brand can start with **just the ICP, mission one-liner, and 3-5 guardrails** — everything else can grow as the brand matures.
