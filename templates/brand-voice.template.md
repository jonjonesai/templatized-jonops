# {{BRAND_NAME}} Brand Voice

Pair this with `email-persona.md` ({{EMAIL_PERSONA_NAME}} — {{EMAIL_PERSONA_ROLE}}), `brand-rules.md` (north star + ICP + doctrine), and `knowledge_base/` if present.

This file is the **authoritative voice document** for any customer-facing writing — emails, blog posts, newsletter, social, ad copy. Skills read this file before drafting; if a sentence breaks a rule here, rewrite it.

---

## Brand essence

**What we are:** {{BRAND_ESSENCE_WHAT_WE_ARE}}

**What we are NOT:** {{BRAND_ESSENCE_WHAT_WE_ARE_NOT}}

**Tagline energy:** *{{BRAND_TAGLINE}}*

---

## Voice in one paragraph

{{VOICE_PARAGRAPH}}

---

## Six core voice attributes

| Attribute | What it means | Example |
|---|---|---|
| **{{VOICE_ATTR_1}}** | {{VOICE_ATTR_1_MEANING}} | "{{VOICE_ATTR_1_EXAMPLE}}" |
| **{{VOICE_ATTR_2}}** | {{VOICE_ATTR_2_MEANING}} | "{{VOICE_ATTR_2_EXAMPLE}}" |
| **{{VOICE_ATTR_3}}** | {{VOICE_ATTR_3_MEANING}} | "{{VOICE_ATTR_3_EXAMPLE}}" |
| **{{VOICE_ATTR_4}}** | {{VOICE_ATTR_4_MEANING}} | "{{VOICE_ATTR_4_EXAMPLE}}" |
| **{{VOICE_ATTR_5}}** | {{VOICE_ATTR_5_MEANING}} | "{{VOICE_ATTR_5_EXAMPLE}}" |
| **{{VOICE_ATTR_6}}** | {{VOICE_ATTR_6_MEANING}} | "{{VOICE_ATTR_6_EXAMPLE}}" |

---

## Tone by context

| Context | Tone | Example |
|---|---|---|
| Email reply (customer) | {{TONE_EMAIL_CUSTOMER}} | "{{TONE_EMAIL_CUSTOMER_EXAMPLE}}" |
| Email reply (B2B/partnership) | {{TONE_EMAIL_B2B}} | "{{TONE_EMAIL_B2B_EXAMPLE}}" |
| Blog post | {{TONE_BLOG}} | {{TONE_BLOG_EXAMPLE}} |
| Newsletter | {{TONE_NEWSLETTER}} | {{TONE_NEWSLETTER_EXAMPLE}} |
| Social caption | {{TONE_SOCIAL}} | "{{TONE_SOCIAL_EXAMPLE}}" |

---

## Hard rules (always)

{{HARD_RULES_NUMBERED}}

---

## Banned phrases

{{BANNED_PHRASES_LIST}}

---

## Quick-reference phrases ({{EMAIL_PERSONA_NAME}}'s voice)

**Would say:**
{{WOULD_SAY_EXAMPLES}}

**Would NEVER say:**
{{WOULD_NEVER_SAY_EXAMPLES}}

---

## Vocabulary palette (optional — only if domain is sensory/specialized)

{{VOCABULARY_PALETTE}}

---

## Surface rules

- **Sentence case** in headings, CTAs (or specify otherwise: {{HEADING_CASE_RULE}})
- **Oxford comma:** {{OXFORD_COMMA_RULE}}
- **Exclamation marks:** {{EXCLAMATION_RULE}}
- **Em dashes:** {{EM_DASH_RULE}}
- **English variant:** {{ENGLISH_VARIANT}}

---

*Read this file + `email-persona.md` + `brand-rules.md` (+ relevant `knowledge_base/` material) before any customer-facing draft. The voice is the brand's fingerprint — protect it.*

---

# PLACEHOLDER REFERENCE — INTERVIEW SCAFFOLD

The `/init` wizard (or Claude during brand onboarding) fills these in by interviewing the user. **If the user says "I don't know yet," default per the heuristic in the right column.**

| Placeholder | Question to ask | If user is unsure |
|-------------|-----------------|-------------------|
| `{{BRAND_NAME}}` | What's the brand name as it appears in customer communications? | Use the legal business name |
| `{{BRAND_ESSENCE_WHAT_WE_ARE}}` | In 1-2 sentences, what is this brand *actually*? Be specific — not generic positioning. | Pull from the about page |
| `{{BRAND_ESSENCE_WHAT_WE_ARE_NOT}}` | What does this brand explicitly NOT want to be mistaken for? (e.g., OA: "not a wellness brand riding the essential-oil trend") | Look at competitors and find the lane to disown |
| `{{BRAND_TAGLINE}}` | If you had to capture the brand vibe in 5-9 words, what would it be? | Default to the home-page hero line |
| `{{VOICE_PARAGRAPH}}` | If your brand walked into a room, how would it speak? Write a 3-5 sentence paragraph — concrete, no buzzwords. | See OA `brand-voice.md` "Voice in one paragraph" as the gold-standard reference |
| `{{VOICE_ATTR_1}}` through `{{VOICE_ATTR_6}}` | 6 single-word adjectives that capture this voice. (Warm, Sensory, Knowledgeable, Premium, Solution-focused, Honest is OA's set — yours will differ.) | Start with 3 and add as you discover them |
| `{{VOICE_ATTR_N_MEANING}}` | For each attribute: in 5-15 words, what does it mean in practice? | Skip if not yet defined |
| `{{VOICE_ATTR_N_EXAMPLE}}` | A real sentence from your archive (or one you'd be proud to write) that embodies this attribute | Browse past customer emails / blog posts for the best lines |
| `{{TONE_EMAIL_CUSTOMER}}` etc | For each context (customer email, B2B, blog, newsletter, social): what's the tonal recipe? | Match the customer-email tone to your most-praised support reply |
| `{{HARD_RULES_NUMBERED}}` | Numbered list of inviolable rules. Anything that would embarrass the brand if violated. Examples: trademark discipline, no medical claims, no commit-to-pricing, never break character. | Always include: "Never reveal AI operation. Stay in character as {{EMAIL_PERSONA_NAME}}." |
| `{{BANNED_PHRASES_LIST}}` | Bullet list of phrases this brand never uses. Hyperbole, jargon, dishonest claims, off-brand corporate-speak. | Default ban list: "world-class", "unparalleled", "game-changer", "I'm an AI", "per our policy" |
| `{{WOULD_SAY_EXAMPLES}}` | 4-6 real sentences `{{EMAIL_PERSONA_NAME}}` would naturally say | Grab from past sent emails / drafts |
| `{{WOULD_NEVER_SAY_EXAMPLES}}` | 4-6 phrases that would feel off-brand or AI-like | Include the standard set + brand-specific |
| `{{VOCABULARY_PALETTE}}` | If the brand has a sensory domain (scent, food, music, atmosphere), list 5-10 word groups by category. Otherwise: "N/A — this brand is non-sensory." | Skip if non-sensory |
| `{{HEADING_CASE_RULE}}` | Title Case, Sentence case, or ALL CAPS? | Sentence case (modern default) |
| `{{OXFORD_COMMA_RULE}}` | Always / never / inconsistent | Always (safer) |
| `{{EXCLAMATION_RULE}}` | Liberal / minimal / banned in body copy | Minimal — reserve for genuine emphasis |
| `{{EM_DASH_RULE}}` | Allowed / discouraged / banned (some brands ban em dashes to feel less AI-y) | Allowed unless brand wants to dodge "AI feel" |
| `{{ENGLISH_VARIANT}}` | US, UK, AU, etc. | US English by default |

---

# Reference brand (mature implementation)

**OrganicAromas** — see `jonops-organicaromas:/home/agent/project/brand-voice.md`. Use as the gold standard for depth + specificity. The OA file is what a fully-matured `brand-voice.md` looks like.

A minimum-viable `brand-voice.md` (for a new brand without years of customer data) covers: essence (we are / we are NOT), one-paragraph voice, 3 core attributes, 3 hard rules, 5 banned phrases. Everything else can grow over time.
