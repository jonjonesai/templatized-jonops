---
skill: init-business
version: 1.0.0
cadence: manual
trigger: user-invoked (/init)
airtable_reads: []
airtable_writes: []
external_apis: []
active: true
notes: "Onboarding wizard. Run once to configure JonOps for a new business. Generates CLAUDE.md, email-persona.md, brand-voice.md, knowledge-base.md, and MEMORY.md from templates."
---

# Init Business Skill — Onboarding Wizard

## What This Skill Does (Plain English)
This skill guides a new user through setting up JonOps for their small business. It asks ~15-20 questions about their business, brand, integrations, and preferences, then automatically generates the configuration files needed to run the agent. After running this skill, the user just needs to set their API keys and they're ready to deploy.

**Run this skill once when first setting up JonOps.**

---

## How to Run

The user invokes this skill by running:
```bash
claude /init
```

Or by asking Claude to "initialize JonOps for my business" or "set up the marketing agent."

---

## Prerequisites

Before running this skill, the user should:
1. Have cloned the templatized-jonops repository
2. Be in the project directory
3. Have a basic understanding of what JonOps does (covered in README.md)

**No API keys are required to run this wizard.** API keys are configured in `.env` after the wizard completes.

---

## Wizard Flow

### Welcome Message

Start with:

```
═══════════════════════════════════════════════════════════════════════════════
🚀 JonOps Initialization Wizard
═══════════════════════════════════════════════════════════════════════════════

Welcome! I'm going to help you configure JonOps for your business.

JonOps is an autonomous marketing agent that handles:
• Blog content creation (SEO-optimized posts)
• Social media posting and engagement
• Email inbox management
• Newsletter campaigns
• Lead generation and outreach
• Market intelligence and keyword research

This wizard will ask you about your business, brand voice, and which features
you want to enable. At the end, I'll generate your configuration files.

This takes about 10-15 minutes. Ready? Let's go!
═══════════════════════════════════════════════════════════════════════════════
```

### Section 1: Business Basics

Ask these questions one at a time. Validate responses before moving on.

**Q1: Business Name**
```
What's the name of your business?
Example: "Sweet Delights Bakery" or "Thompson & Associates Law"
```

**Q2: Website URL**
```
What's your website URL?
Example: https://sweetdelightsbakery.com
```
Validate: Must start with http:// or https://

**Q3: Business Description**
```
In 1-2 sentences, what does your business do? Who do you serve?
Example: "We're a family-owned bakery specializing in artisan sourdough and custom wedding cakes. We serve the greater Portland area."
```

**Q4: Business Type**
```
Which best describes your business?

1. Product-based (you sell physical products)
2. Service-based (you provide services)
3. Content/Media (blog, news, entertainment site)
4. Hybrid (products + services + content)

Enter 1-4:
```

**Q5: Industry/Niche**
```
What industry or niche is your business in?
Examples: bakery, landscaping, legal services, astrology, fitness, accounting, real estate
```

---

### Section 2: Operator Info

**Q6: Your Name**
```
What's your name? (This is used for internal references only)
```

**Q7: Your Role**
```
What's your role? (e.g., Owner, Founder, Marketing Manager)
```

**Q8: Your Location**
```
Where are you located? (City, Country)
Example: Austin, Texas or Bali, Indonesia
```

**Q9: Timezone**
```
What timezone should the agent use for scheduling?

Common options:
1. US Eastern (America/New_York)
2. US Central (America/Chicago)
3. US Mountain (America/Denver)
4. US Pacific (America/Los_Angeles)
5. UK (Europe/London)
6. Central Europe (Europe/Paris)
7. Australia Eastern (Australia/Sydney)
8. Asia/Singapore
9. Asia/Jakarta (WITA)
10. Other (I'll specify)

Enter 1-10:
```
If "Other": ask for IANA timezone string (e.g., "Pacific/Auckland")

---

### Section 3: Brand Voice

**Q10: Target Audience**
```
Who is your ideal customer? Be specific about demographics and interests.
Example: "Women 25-45 interested in home baking and artisan bread"
Example: "Small business owners who need estate planning and contracts"
```

**Q11: Brand Personality**
```
How would you describe your brand's personality? Choose up to 3:

1. Professional / Authoritative
2. Friendly / Approachable
3. Playful / Fun
4. Warm / Caring
5. Bold / Edgy
6. Sophisticated / Elegant
7. Down-to-earth / Practical
8. Inspiring / Motivational

Enter your choices (e.g., "2, 4, 7"):
```

**Q12: Brand Voice Bullets**
```
Give me 3-5 bullet points that describe how your brand communicates.
Think about: tone, language style, what you'd never say, signature phrases.

Example for a bakery:
• Warm and inviting — like a friend sharing recipes over coffee
• Uses sensory language — describes textures, aromas, flavors
• Encouraging to beginners — "You can do this!" energy
• Never pretentious or overly technical
• Occasionally uses food emojis (🥖🍞) in social content

Type your bullet points (press Enter twice when done):
```

---

### Section 4: Content & WordPress

**Q13: WordPress Setup**
```
Does your website use WordPress?

1. Yes — WordPress with self-hosted or managed hosting
2. No — I use a different platform (Shopify, Squarespace, etc.)
3. I don't have a website yet

Enter 1-3:
```

If Yes to WordPress:

**Q13a: WordPress Categories**
```
What are your main blog/content categories?
List them separated by commas.
Example: Recipes, Baking Tips, Product News, Behind the Scenes
```

**Q13b: WooCommerce**
```
Do you have WooCommerce (online store) installed?

1. Yes — I sell products through my WordPress site
2. No — My site is content-only or I use a different store platform

Enter 1-2:
```

**Q14: Daily Content Format**
```
JonOps can publish short daily content to keep your blog active. What format works best?

1. Quick Tips — Short tips related to your expertise (150-300 words)
2. Educational Facts — Interesting facts about your industry (200-400 words)
3. Seasonal Reminders — Timely reminders for your audience (200-400 words)
4. Themed Days — Rotating content (Tip Tuesday, FAQ Friday, etc.)
5. Daily Horoscope — Full zodiac readings (astrology niche only)
6. Custom — I'll describe my own format
7. Skip — I don't want daily content

Enter 1-7:
```

If Custom, ask:
```
Describe your custom daily content format:
```

---

### Section 5: Marketing & Competitors

**Q15: Competitors**
```
List 3-5 competitor websites (domains only).
JonOps uses these for market intelligence and keyword research.

Example: competitorbakery.com, anotherbakery.com, breadblog.net
```

**Q16: Seed Keywords**
```
List 5-10 keywords related to your business.
These seed the keyword research engine.

Example for a bakery: sourdough bread, artisan bakery, bread recipes, cake decorating, baking tips
Example for a lawyer: estate planning, small business lawyer, contracts attorney, will preparation
```

**Q17: Target Communities**
```
Where does your audience hang out online? List relevant subreddits, forums, or communities.

Example: r/Baking, r/Breadit, r/cakedecorating
Example: r/legaladvice, r/smallbusiness, r/Entrepreneur

(Leave blank if unsure — JonOps can suggest communities based on your niche)
```

---

### Section 6: Email Persona

JonOps can draft email replies on your behalf using a consistent persona.

**Q18: Email Persona Name**
```
What name should the agent use when drafting email replies?
This can be your name, a team member, or a brand persona.

Example: "Sarah" or "The Sweet Delights Team" or "Rebecca Moore"
```

**Q19: Email Persona Role**
```
What's this persona's role? (shown in email signatures)
Example: "Founder & Head Baker" or "Customer Support" or "Lead Astrologer"
```

**Q20: Email Sign-off**
```
How should emails be signed off?
Example: "Warmly, Sarah — Sweet Delights Bakery"
Example: "Best regards, Thompson & Associates"
```

---

### Section 7: Integrations

**Q21: Which integrations will you use?**
```
Select all that apply:

1. Asana — Task management and workflow tracking (recommended)
2. Sendy — Self-hosted email newsletter
3. Metricool — Social media scheduling
4. Instantly — Email outreach campaigns
5. Telegram — Operator notifications (recommended)

Enter your choices (e.g., "1, 5"):
```

For each selected integration, note that they'll need to provide credentials in `.env`.

**Q22: Social Platforms**
```
Which social media platforms does your business use?

1. Instagram
2. Facebook
3. Twitter/X
4. Pinterest
5. LinkedIn
6. TikTok

Enter your choices (e.g., "1, 2, 4"):
```

---

### Section 8: Schedule Preferences

**Q23: Schedule Confirmation**
```
JonOps runs on a preset daily schedule optimized for most businesses.
Here's the default schedule (times shown in your timezone):

• 07:00 — Daily content post
• 09:00 — Blog writer (long-form SEO content)
• 10:00 — Social media research
• 11:00 — Email inbox check (morning)
• 12:00 — Social media posting
• 14:00 — Lead finder
• 16:00 — Social engagement monitoring
• 18:00 — Outreach campaigns
• 21:00 — Email inbox check (evening)
• 22:00 — Daily summary and task check

Would you like to:
1. Keep the default schedule (recommended)
2. Adjust specific times
3. Disable certain skills

Enter 1-3:
```

If "Adjust" or "Disable", walk through changes. Otherwise, keep defaults.

---

### Section 9: Review & Generate

**Summary**
```
═══════════════════════════════════════════════════════════════════════════════
📋 Configuration Summary
═══════════════════════════════════════════════════════════════════════════════

BUSINESS
  Name: [BUSINESS_NAME]
  URL: [BUSINESS_URL]
  Type: [BUSINESS_TYPE]
  Industry: [INDUSTRY]

OPERATOR
  Name: [OPERATOR_NAME]
  Role: [OPERATOR_ROLE]
  Location: [LOCATION]
  Timezone: [TIMEZONE]

BRAND VOICE
  Target Audience: [TARGET_AUDIENCE]
  Personality: [PERSONALITY_TRAITS]
  Voice Guidelines: [VOICE_BULLETS]

CONTENT
  WordPress: [YES/NO]
  Categories: [CATEGORIES]
  WooCommerce: [YES/NO]
  Daily Format: [DAILY_FORMAT]

MARKETING
  Competitors: [COMPETITOR_LIST]
  Seed Keywords: [KEYWORDS]
  Communities: [COMMUNITIES]
  Social Platforms: [PLATFORMS]

EMAIL PERSONA
  Name: [PERSONA_NAME]
  Role: [PERSONA_ROLE]
  Sign-off: [SIGNOFF]

INTEGRATIONS
  Enabled: [INTEGRATION_LIST]

═══════════════════════════════════════════════════════════════════════════════

Does this look correct?
1. Yes — Generate my configuration files
2. No — Let me make changes

Enter 1-2:
```

If changes needed, allow editing specific sections.

---

## File Generation

Once confirmed, generate the following files:

### 1. CLAUDE.md

Read `templates/CLAUDE.template.md` and replace all `{{PLACEHOLDERS}}` with user responses.

Key replacements:
- `{{BRAND_NAME}}` → Business Name
- `{{BRAND_URL}}` → Website URL
- `{{BRAND_DESCRIPTION}}` → Business Description
- `{{BUSINESS_TYPE}}` → Business Type
- `{{INDUSTRY}}` → Industry
- `{{OPERATOR_NAME}}` → Operator Name
- `{{OPERATOR_ROLE}}` → Operator Role
- `{{OPERATOR_LOCATION}}` → Location
- `{{TIMEZONE}}` → Timezone
- `{{TARGET_AUDIENCE}}` → Target Audience
- `{{BRAND_PERSONALITY}}` → Personality traits
- `{{BRAND_VOICE_BULLETS}}` → Voice guidelines
- `{{HAS_WORDPRESS}}` → yes/no
- `{{WP_CATEGORIES}}` → Categories JSON array
- `{{HAS_WOOCOMMERCE}}` → yes/no
- `{{DAILY_CONTENT_FORMAT}}` → Daily format selection
- `{{COMPETITORS}}` → Competitor list
- `{{NICHE_KEYWORDS}}` → Seed keywords
- `{{TARGET_COMMUNITIES}}` → Subreddits/communities
- `{{SOCIAL_PLATFORMS}}` → Platform list
- `{{EMAIL_PERSONA_NAME}}` → Persona name
- `{{EMAIL_PERSONA_ROLE}}` → Persona role
- `{{EMAIL_SIGNOFF}}` → Sign-off
- `{{INTEGRATIONS}}` → Enabled integrations

Write the populated file to `CLAUDE.md` in the project root.

### 2. email-persona.md

Read `templates/email-persona.template.md` and populate:
- `{{PERSONA_NAME}}` → Persona name
- `{{PERSONA_ROLE}}` → Persona role
- `{{BUSINESS_NAME}}` → Business name
- `{{BRAND_VOICE_BULLETS}}` → Voice guidelines
- `{{EMAIL_SIGNOFF}}` → Sign-off
- `{{INDUSTRY}}` → Industry

Write to `email-persona.md` in the project root.

### 3. brand-voice.md

Read `templates/brand-voice.template.md` and populate the brand-voice placeholders (see template's PLACEHOLDER REFERENCE table). Use the user's earlier wizard answers for what's pre-known (`{{BRAND_NAME}}`, `{{EMAIL_PERSONA_NAME}}`, `{{ENGLISH_VARIANT}}`, etc.); ask any missing voice/tone/banned-phrase questions in a single follow-up batch before writing the file.

Key voice questions to ask if not already collected:
- "What is your brand NOT? (One sentence anchoring against your category — e.g. 'A wellness brand riding the trend' or 'A POD merch farm.')"
- "What's the one wedge that makes your voice different from competitors? (e.g. 'cultural specificity', 'honesty', 'sensory writing')"
- "List 4-6 phrases your brand would never say. (e.g. 'Dear Valued Customer', 'World-class', 'Per our policy')"
- "List 4-6 phrases your brand would naturally say."
- "Any trademark, regulatory, or legal claim discipline rules? (e.g. 'never say cures', 'always use ® on first mention')"
- "Exclamation marks: rare / sparingly / freely?"
- "Em dashes: fine / banned (per brand book)?"
- "Emoji rules: none / light social only / freely?"

Write to `brand-voice.md` in the project root.

### 4. knowledge-base.md

Read `templates/knowledge-base.template.md` and populate the knowledge-base placeholders. Most placeholders auto-fill from the user's earlier wizard answers (URL, product categories, Airtable tables); only ask follow-ups for what isn't yet known.

Key KB questions to ask if not already collected:
- "Where does your shipping policy live? (URL or 'FAQ → shipping section')"
- "What's your About / FAQ / Returns / Privacy URLs?"
- "Any brand-specific facts the agent should know? (Things not on the live site — founding year, sourcing partners, what makes you the original, etc.) — list 3-8 short bullets."
- "Any claim boundaries to enforce? (e.g. 'never claim oils cure', 'never quote price in email', 'no organic claim unless certified')"

Write to `knowledge-base.md` in the project root.

### 5. MEMORY.md

Copy `templates/MEMORY.template.md` to `MEMORY.md` — no replacements needed.

### 6. .env.example Enhancement

Generate a customized `.env.example` with only the env vars needed for their enabled integrations:

```bash
# === JonOps Environment Variables ===
# Generated by /init wizard on [DATE]

# WordPress (required)
WP_URL=[THEIR_URL]
WP_USERNAME=
WP_PASSWORD=

# Airtable (required)
AIRTABLE_API_KEY=
AIRTABLE_BASE_ID=
# [Include all AIRTABLE_*_TABLE vars]

# Replicate (for image generation)
REPLICATE_API=

# Tinify (for image compression)
TINIFY_API=

# [Only include integrations they selected:]

# Asana (if enabled)
ASANA_API_KEY=
ASANA_PROJECT_GID=
ASANA_INBOX_SECTION_GID=
ASANA_TODO_SECTION_GID=
ASANA_DONE_SECTION_GID=

# Sendy (if enabled)
SENDY_URL=
SENDY_API_KEY=
SENDY_LIST_MAIN=
SENDY_FROM_NAME=
SENDY_FROM_EMAIL=
SENDY_REPLY_TO=

# Metricool (if enabled)
METRICOOL_API_TOKEN=
METRICOOL_BLOG_ID=

# Instantly (if enabled)
INSTANTLY_API_KEY=
INSTANTLY_CAMPAIGN_ID=
INSTANTLY_FROM_EMAIL=

# Telegram (if enabled)
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=

# Timezone
TZ_OFFSET_HOURS=[CALCULATED_FROM_TIMEZONE]
```

---

## Completion Message

```
═══════════════════════════════════════════════════════════════════════════════
✅ Configuration Complete!
═══════════════════════════════════════════════════════════════════════════════

I've generated the following files:

  📄 CLAUDE.md — Your agent's identity and configuration
  📄 email-persona.md — Email reply persona (the voice that signs your replies)
  📄 brand-voice.md — Brand-level voice rules (banned phrases, claim discipline, signature vocabulary)
  📄 knowledge-base.md — Pointer index telling the agent where canonical facts live
  📄 MEMORY.md — Agent's learning memory (starts empty)
  📄 .env.example — Environment variables template

NEXT STEPS:

1. Copy .env.example to .env:
   cp .env.example .env

2. Fill in your API keys in .env
   - See SETUP.md for instructions on getting each API key

3. Set up Airtable:
   - Run: python scripts/setup/create-airtable-tables.py
   - This creates the required tables in your Airtable base

4. Start JonOps:
   docker compose up -d

5. Verify it's running:
   python scheduler.py --status

═══════════════════════════════════════════════════════════════════════════════

Need help? Check SETUP.md for detailed instructions, or ask me any questions!
```

---

## Validation Rules

- Business URL must be valid (starts with http/https)
- Email sign-off should not be empty
- At least 1 competitor should be provided
- At least 3 seed keywords should be provided
- Timezone must be a valid IANA timezone string

---

## Error Handling

- If user cancels mid-wizard: Save progress to `.init-progress.json` so they can resume
- If template files are missing: Error and instruct user to re-clone the repo
- If file write fails: Show error and suggest manual creation

---

## SKILL_RESULT

```
SKILL_RESULT: success | JonOps initialized for [BUSINESS_NAME] | Files generated: CLAUDE.md, email-persona.md, brand-voice.md, knowledge-base.md, MEMORY.md, .env.example
```

On cancel: `SKILL_RESULT: skip | User cancelled initialization wizard`
On error: `SKILL_RESULT: fail | [error details]`

---

*Run: Manually via `/init` command*
*Version: 1.0.0*
