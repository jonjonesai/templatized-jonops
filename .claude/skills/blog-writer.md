---
skill: blog-writer
version: 1.0.0
cadence: daily 00:00
trigger: cron
airtable_reads: [Keywords, Content Calendar, Research]
airtable_writes: [Keywords, Content Calendar, Published Posts, Generated Images]
external_apis: [wordpress, rankmath, firecrawl, replicate, tinify, dataforseo, asana]
active: true
notes: "Daily SEO blog post pipeline. Picks keyword from queue, researches, writes, publishes."
---

# Blog Writer Skill

## What This Skill Does (Plain English)
This skill writes and publishes a full SEO-optimized blog post from start to finish. It picks the next keyword from a queue, researches what competitors wrote about it, writes a 2,500-3,500 word article with AI-generated images, product CTAs (if applicable), and newsletter signup forms, then publishes it live on WordPress with all SEO metadata set.

**Example outputs by business type:**
- **Bakery:** "Sourdough Starter Guide: Everything Beginners Need to Know" with 7 custom baking images
- **Landscaper:** "Spring Lawn Care in Zone 7: Your Complete Checklist" with seasonal imagery
- **Lawyer:** "Estate Planning Basics: 5 Documents Every Adult Needs" with professional graphics
- **E-commerce:** "Best Gifts for [Niche]: 2026 Buyer's Guide" with product photography

---

> **Version:** 1.1.0 | **Last Updated:** 2026-04-05
> **Author:** JonOps Agent System
>
> This is the master reference for writing SEO-optimized blog posts.
> Any Claude agent with access to this file should be able to execute the full
> blog writing pipeline from keyword selection to published draft — with zero
> additional context needed.
>
> **Note:** Business-specific settings (brand voice, categories, products) are defined in CLAUDE.md.

---

## 0. Step 0: Refresh-Queue Pre-Check (gsc-ga4-sweep handoff)

**Why this step exists:** The `gsc-ga4-sweep` skill (weekly Monday 04:00) identifies pages that are losing rank or hostage on page 2. Rather than flagging them for human review, it queues them in `GSC Opportunities` (Airtable) with `Type=Content-Refresh` + `Status=Queued for Refresh` + a populated `Refresh Brief`. Blog-writer picks the highest-impressions queued refresh BEFORE pulling from the Content Calendar — autonomous loop, no human bottleneck. Quota: **1 refresh per day per brand** (don't dominate normal cadence).

**Run this BEFORE Step 1 (Keyword Selection). If a refresh is processed, skip Steps 1-9 and go straight to Step 10 (post-publish updates).**

### 0.1 Query Airtable for queued refreshes

```bash
RECORDS=$(curl -s -G "https://api.airtable.com/v0/$AIRTABLE_BASE_ID/$AIRTABLE_GSC_OPPORTUNITIES_TABLE" \
  -H "Authorization: Bearer $AIRTABLE_API_KEY" \
  --data-urlencode "filterByFormula=AND({Brand}='$BRAND_NAME',{Status}='Queued for Refresh',{Type}='Content-Refresh')" \
  --data-urlencode "sort[0][field]=Impressions" \
  --data-urlencode "sort[0][direction]=desc" \
  --data-urlencode "maxRecords=1")

REFRESH_RECORD_ID=$(echo "$RECORDS" | python3 -c "import sys,json;d=json.load(sys.stdin);print(d['records'][0]['id'] if d.get('records') else '')")
```

If empty → continue to Step 1 normally. No refresh today.

### 0.2 Snapshot the existing post (mandatory pre-write safety)

```bash
SNAPDIR="/home/agent/project/.claude/data/blog-writer/refresh-snapshots"
mkdir -p "$SNAPDIR"
SNAP="$SNAPDIR/$(date -u +%Y%m%dT%H%M%SZ)-${BRAND_SLUG}-${POST_ID}.md"

# Pull post content + Rank Math meta + featured image ID + categories
curl -s -u "$WP_USERNAME:$WP_PASSWORD" "$WP_URL/wp-json/wp/v2/posts/$POST_ID?context=edit" > "$SNAP.json"

# Pull Rank Math meta
curl -s -u "$WP_USERNAME:$WP_PASSWORD" "$WP_URL/wp-json/rankmath/v1/getMetadata?objectID=$POST_ID&objectType=post" > "$SNAP.rankmath.json" 2>/dev/null

echo "# Refresh snapshot — $BRAND_NAME post $POST_ID" > "$SNAP"
echo "date: $(date -Iseconds)" >> "$SNAP"
echo "trigger: gsc-ga4-sweep refresh queue (record $REFRESH_RECORD_ID)" >> "$SNAP"
```

### 0.3 Read the Refresh Brief

```bash
BRIEF=$(echo "$RECORDS" | python3 -c "import sys,json;print(json.load(sys.stdin)['records'][0]['fields'].get('Refresh Brief',''))")
TARGET_QUERY=$(echo "$RECORDS" | python3 -c "import sys,json;print(json.load(sys.stdin)['records'][0]['fields'].get('Target Query',''))")
PAGE_URL=$(echo "$RECORDS" | python3 -c "import sys,json;print(json.load(sys.stdin)['records'][0]['fields'].get('Page URL',''))")
POST_ID=$(echo "$RECORDS" | python3 -c "import sys,json;print(json.load(sys.stdin)['records'][0]['fields'].get('Post ID',''))")
```

### 0.4 Refresh strategy (chosen by Refresh Brief's "Suggested angle")

| Suggested angle | Action |
|-----------------|--------|
| `rank-drop recovery` | Read existing post, identify what's stale, rewrite with new SERP-current data + 2026 references. Preserve URL, slug, ID, featured image, categories, tags. Update body content to match what's currently winning the SERP. |
| `page-2 → page-1` | Existing post ranks 11-20 with high impressions. Rewrite emphasizing the target query in H1 + intro + sub-headings. Add internal links from related top-ranking posts. Expand thin sections. |
| `expand for related queries` | Existing post owns one query but adjacent ones (top 5 SERP overlap) are uncovered. Add 2-3 new H2 sections covering the related angle. |

In ALL cases:
- Re-run SERP research (Step 2) for the target query.
- Re-write content using the SAME content rules as Steps 4-7 (voice, length, image generation, CTAs, newsletter form).
- PRESERVE: URL, slug, post ID, publication date, original featured image (unless brief says to regenerate), categories, tags, comment thread.
- UPDATE: title, content, Rank Math meta, modified date.

### 0.5 PATCH the post via WP REST

```bash
PAYLOAD=$(jq -n --arg t "$NEW_TITLE" --arg c "$NEW_CONTENT" '{title: $t, content: $c}')
curl -s -X POST -u "$WP_USERNAME:$WP_PASSWORD" -H "Content-Type: application/json" \
  "$WP_URL/wp-json/wp/v2/posts/$POST_ID" -d "$PAYLOAD"

# Update Rank Math meta separately
curl -s -X POST -u "$WP_USERNAME:$WP_PASSWORD" -H "Content-Type: application/json" \
  "$WP_URL/wp-json/rankmath/v1/updateMeta" \
  -d "{\"objectID\":$POST_ID,\"objectType\":\"post\",\"meta\":{\"rank_math_title\":\"$NEW_META_TITLE\",\"rank_math_description\":\"$NEW_META_DESC\",\"rank_math_focus_keyword\":\"$TARGET_QUERY\"}}"
```

### 0.6 Verify on live HTML

```bash
sleep 30
LIVE=$(curl -sL "$PAGE_URL")
if echo "$LIVE" | grep -qF "$NEW_H1"; then
  REFRESH_STATUS="Refreshed"
else
  REFRESH_STATUS="Refresh-Failed"
  # Roll back: PATCH post with snapshotted content + meta
  ORIG_TITLE=$(jq -r '.title.raw' "$SNAP.json")
  ORIG_CONTENT=$(jq -r '.content.raw' "$SNAP.json")
  curl -s -X POST -u "$WP_USERNAME:$WP_PASSWORD" -H "Content-Type: application/json" \
    "$WP_URL/wp-json/wp/v2/posts/$POST_ID" -d "$(jq -n --arg t "$ORIG_TITLE" --arg c "$ORIG_CONTENT" '{title: $t, content: $c}')"
  bash /home/agent/project/telegram-alert.sh "❌ [$BRAND_NAME] blog-writer refresh rolled back on $PAGE_URL — verification failed"
fi
```

### 0.7 Update the Airtable record

```bash
curl -s -X PATCH "https://api.airtable.com/v0/$AIRTABLE_BASE_ID/$AIRTABLE_GSC_OPPORTUNITIES_TABLE/$REFRESH_RECORD_ID" \
  -H "Authorization: Bearer $AIRTABLE_API_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"fields\":{\"Status\":\"$REFRESH_STATUS\",\"Snapshot Path\":\"$SNAP\",\"Refresh Date\":\"$(date -u +%Y-%m-%d)\"}}"
```

### 0.8 Exit (skip Steps 1-9)

If a refresh ran (success or rolled back), this skill is done for the day. Emit:

```
SKILL_RESULT: success | refresh | $TARGET_QUERY | post $POST_ID | $REFRESH_STATUS
```

Do NOT pick a Content Calendar item this run — the brand gets one autonomous SEO action per day, refresh OR new post.

If verification rolled back, the brand still consumed its one daily slot. Telegram fired. Operator will review the snapshot and the rollback.

---

## TABLE OF CONTENTS

0. [Step 0: Refresh-Queue Pre-Check (gsc-ga4-sweep handoff)](#0-step-0-refresh-queue-pre-check-gsc-ga4-sweep-handoff)
1. [Overview & Goals](#1-overview--goals)
2. [Prerequisites & Environment](#2-prerequisites--environment)
3. [Step 1: Keyword Selection](#3-step-1-keyword-selection)
4. [Step 2: SERP Research](#4-step-2-serp-research)
5. [Step 3: Content Outline](#5-step-3-content-outline)
6. [Step 4: Writing the Post](#6-step-4-writing-the-post)
7. [Step 5: Image Generation](#7-step-5-image-generation)
8. [Step 6: Product CTA Insertion](#8-step-6-product-cta-insertion)
9. [Step 7: Newsletter Form Funnels](#9-step-7-newsletter-form-funnels)
10. [Step 8: SEO Optimization (Rank Math)](#10-step-8-seo-optimization-rank-math)
11. [Step 9: WordPress Publishing](#11-step-9-wordpress-publishing)
12. [Step 10: Post-Publish Updates](#12-step-10-post-publish-updates)
13. [Reference: API Endpoints](#13-reference-api-endpoints)
14. [Reference: Product Catalog](#14-reference-product-catalog)
15. [Reference: WordPress Categories](#15-reference-wordpress-categories)
16. [Reference: Airtable Tables](#16-reference-airtable-tables)
17. [Reference: Block Templates](#17-reference-block-templates)
18. [Troubleshooting](#18-troubleshooting)

---

## 1. Overview & Goals

**Mission:** Create the most comprehensive, authoritative, and engaging content for each target keyword — content that is genuinely the best resource on the internet for that topic, designed to rank #1 in Google.

**Content philosophy:**
- **Depth over length** — every paragraph must add value, never pad
- **Relentlessly helpful** — answer every question a reader could have
- **Authoritative but accessible** — expert-level domain knowledge delivered in the brand voice defined in CLAUDE.md
- **SEO-native** — structured for both readers and search engines from the ground up
- **Monetized naturally** — product CTAs (if applicable) and newsletter signups feel like helpful additions, not interruptions

**Per-post deliverables:**
- 2,500–3,500 words across 5–7 H2 sections
- 1 featured image + 1 image per H2 section (6–8 images total)
- 2 product CTAs (1 inline text mention, 1 Kadence block)
- 2 form funnels (1 mid-article via PHP auto-insert, 1 end-of-post in content)
- Full Rank Math SEO (focus keyword, meta title, meta description, slug)
- Internal links to 2+ existing posts on the site
- Airtable + Asana tracking updates

---

## 2. Prerequisites & Environment

### Environment Variables (required)
All values are set in `.env` and injected via Docker. See CLAUDE.md for the full list.
```
WP_URL=<Your WordPress URL>
WP_USERNAME=<WordPress username>
WP_PASSWORD=<WordPress app password>
AIRTABLE_API_KEY=<Airtable personal access token>
AIRTABLE_BASE_ID=<Your Airtable base ID>
DATAFORSEO_LOGIN=<DataForSEO login email>
DATAFORSEO_PASSWORD=<DataForSEO API password>
FIRECRAWL_API_KEY=<Firecrawl API key>
ASANA_API_KEY=<Asana personal access token>
```

### Airtable Tables
| Table | ID | Purpose |
|-------|----|---------|
| Keywords | `$AIRTABLE_KEYWORDS_TABLE` | Target keywords with status tracking |
| Research | `$AIRTABLE_RESEARCH_TABLE` | Scraped competitor content |
| Content Calendar | `$AIRTABLE_CONTENT_TABLE` | Post tracking and scheduling |
| Generated Images | `$AIRTABLE_GENERATED_IMAGES_TABLE` | Image generation records |

### WordPress Resources
**Check CLAUDE.md for your business-specific values:**
| Resource | Where to Find |
|----------|---------------|
| Fluent Form shortcode | CLAUDE.md → Form Funnel IDs |
| Product CTA Block | CLAUDE.md → Product Info (if HAS_PRODUCTS=yes) |
| Primary Categories | CLAUDE.md → WordPress → Primary categories |
| Mid-Article Form | Auto-inserted by PHP Code Snippet after 3rd H2 (if configured) |

### Asana Project
**Check CLAUDE.md → Asana Project Structure for your GIDs:**
| Resource | CLAUDE.md Key |
|----------|---------------|
| Project GID | `{{ASANA_PROJECT_GID}}` |
| Inbox Section | `{{ASANA_INBOX_GID}}` |
| In Progress Section | `{{ASANA_IN_PROGRESS_GID}}` |
| Drafts Section | `{{ASANA_DRAFTS_GID}}` |
| Done Section | `{{ASANA_DONE_GID}}` |

---

## 3. Step 1: Keyword Selection

### Source: Airtable Keywords Table

Query the Keywords table for the next keyword to write about:

```bash
# Get next "Queue" keyword
AIRTABLE_KEY=$(echo "$AIRTABLE_API_KEY" | tr -d '[:space:]')
curl -s --retry 3 --retry-delay 2 "https://api.airtable.com/v0/$AIRTABLE_BASE_ID/$AIRTABLE_KEYWORDS_TABLE" \
  -H "Authorization: Bearer $AIRTABLE_KEY" \
  --data-urlencode "filterByFormula={Status}='Queue'" \
  --data-urlencode "sort[0][field]=Search Volume" \
  --data-urlencode "sort[0][direction]=desc" \
  --data-urlencode "maxRecords=1" \
  -G
```

### Selection Priority
1. Check if a specific keyword was assigned via Asana task
2. Check Airtable Content Calendar for today's scheduled topic
3. Pick the highest-volume "Queue" keyword from the Keywords table
4. If no queued keywords, check Asana Inbox for ad-hoc requests from the operator

### After Selecting
Update the keyword status to "Researching":

```bash
curl -s --retry 3 --retry-delay 2 -X PATCH "https://api.airtable.com/v0/$AIRTABLE_BASE_ID/$AIRTABLE_KEYWORDS_TABLE/$KEYWORD_RECORD_ID" \
  -H "Authorization: Bearer $AIRTABLE_KEY" \
  -H "Content-Type: application/json" \
  -d '{"fields": {"Status": "Researching"}}'
```

Also create a Content Calendar entry with status "Researching":

```bash
curl -s --retry 3 --retry-delay 2 -X POST "https://api.airtable.com/v0/$AIRTABLE_BASE_ID/$AIRTABLE_CONTENT_TABLE" \
  -H "Authorization: Bearer $AIRTABLE_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "fields": {
      "Title": "Working title here",
      "Keyword": "the focus keyword",
      "Status": "Researching",
      "Category": "Category name"
    }
  }'
```

---

## 4. Step 2: SERP Research

### Purpose
Analyze the top-ranking content for this keyword so we can create something definitively better.

### 4a. Get SERP Results via DataForSEO

```bash
curl -s -X POST "https://api.dataforseo.com/v3/serp/google/organic/live/regular" \
  -u "$DATAFORSEO_LOGIN:$DATAFORSEO_PASSWORD" \
  -H "Content-Type: application/json" \
  -d '[{
    "keyword": "YOUR_KEYWORD_HERE",
    "location_code": 2840,
    "language_code": "en",
    "depth": 10
  }]'
```

**Important:** The endpoint is `/live/regular` (NOT just `/live`).

Extract the top 5–7 organic result URLs and titles from the response at:
`result[0].items` where `type == "organic"`

### 4b. Scrape Each Result via Firecrawl

For each top-ranking URL:

```bash
curl -s -X POST "https://api.firecrawl.dev/v1/scrape" \
  -H "Authorization: Bearer $FIRECRAWL_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://competitor-url.com/article",
    "formats": ["markdown"]
  }'
```

The response returns clean markdown at `data.markdown`.

### 4c. Store Research in Airtable

For each scraped result, create a record in the Research table:

```bash
curl -s --retry 3 --retry-delay 2 -X POST "https://api.airtable.com/v0/$AIRTABLE_BASE_ID/$AIRTABLE_RESEARCH_TABLE" \
  -H "Authorization: Bearer $AIRTABLE_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "fields": {
      "Keyword": "the focus keyword",
      "Source URL": "https://competitor-url.com/article",
      "Source Title": "Article Title",
      "Content": "First 10000 chars of scraped markdown...",
      "Summary": "AI-generated 2-3 sentence summary",
      "SERP Position": 1,
      "Date Scraped": "2026-02-21"
    }
  }'
```

### 4d. Analyze the Competition

Before writing, analyze the scraped content to identify:
- **Content gaps** — what are competitors NOT covering that readers would want?
- **Common structure** — how are top articles organized?
- **Unique angles** — what perspective can WLH bring that no one else does?
- **Questions answered** — compile a list of all questions the top articles answer
- **Questions missed** — identify questions readers would have that NO competitor answers
- **Average word count** — aim for 20-50% more than the top result
- **Internal linking opportunities** — which existing WLH posts can we link to?

Update the Content Calendar status to "Writing":

```bash
curl -s --retry 3 --retry-delay 2 -X PATCH "https://api.airtable.com/v0/$AIRTABLE_BASE_ID/$AIRTABLE_CONTENT_TABLE/$CALENDAR_RECORD_ID" \
  -H "Authorization: Bearer $AIRTABLE_KEY" \
  -H "Content-Type: application/json" \
  -d '{"fields": {"Status": "Writing"}}'
```

---

## 5. Step 3: Content Outline

### Structure Template

Every blog post follows this structure:

```
# [Title with Focus Keyword] (H1 — set via WP title, not in content)

[Opening paragraph — hook + focus keyword in first 100 words]
[Brief overview of what the reader will learn]

## [H2 Section 1 — ideally contains focus keyword]
[Image for this section]
[Content: 300-500 words]

## [H2 Section 2]
[Image for this section]
[Content: 300-500 words]

## [H2 Section 3]
[Image for this section]
[Content: 300-500 words]

--- PHP auto-inserts mid-article newsletter signup here ---

## [H2 Section 4]
[Image for this section]
[INLINE PRODUCT CTA — natural text mention with link]
[Content: 300-500 words]

## [H2 Section 5]
[Image for this section]
[Content: 300-500 words]

## [H2 Section 6 — "Frequently Asked Questions" or thematic wrap-up]
[Image for this section]
[Content: FAQ format or summary, 300-500 words]

## [H2 Section 7 — Conclusion / "Final Thoughts"]
[Content: 200-300 words, empowering takeaway]
[KADENCE PRODUCT CTA BLOCK — reusable block ref:5467 with dynamic product]

[END-OF-POST NEWSLETTER SIGNUP — Kadence row with Fluent Form]
```

### Outline Rules
1. Focus keyword MUST appear in: title, first 100 words, at least 2 H2 headings, meta description
2. Each H2 should be a complete, valuable subtopic — not just a transition
3. Use H3 subheadings within sections when they have distinct sub-points
4. Include at least one FAQ-style section (great for featured snippets)
5. Plan internal links to 4+ existing WLH posts (more is better for SEO; Link Whisper plugin is also active)
6. Plan where the inline product mention and Kadence CTA block will go

---

## 6. Step 4: Writing the Post

### Brand Voice (from CLAUDE.md)
**Read CLAUDE.md → Brand Voice for your specific tone guidelines.** Common patterns:
- Matches your brand personality (warm, professional, playful, authoritative, etc.)
- Speaks to your target audience at their level
- Empowering and helpful — content should inspire action
- Conversational or formal based on your brand
- Language and spelling as defined in CLAUDE.md

### Writing Standards
- **Authority:** Demonstrate deep domain expertise — reference specific knowledge, techniques, and insights relevant to your niche
- **Accessibility:** Always explain technical terms in context so your audience can follow
- **Engagement:** Use questions, direct address ("you"), vivid metaphors, and concrete examples
- **Originality:** NEVER copy competitor content. Use research as inspiration, then bring your unique perspective
- **Value density:** Every paragraph must teach, inspire, or help the reader. Zero filler.
- **Transitions:** Each section should flow naturally into the next
- **Active voice:** Prefer active constructions

### Content Format (HTML for WordPress)
Write the post body as clean HTML. Use:
- `<h2>` for main sections (5-7 per post)
- `<h3>` for subsections within H2 blocks
- `<p>` for paragraphs
- `<strong>` for emphasis (not `<b>`)
- `<em>` for astrological terms on first use
- `<ul>` / `<ol>` for lists
- `<blockquote>` for key insights or quotes
- `<a href="...">` for internal and external links

**Do NOT use Gutenberg block comments in the main body text.** The post content is submitted as HTML via the REST API. Only use Gutenberg block syntax for the product CTA block reference and the end-of-post newsletter signup.

### Internal Linking
Link to at least 2 existing posts from your site. To find relevant posts:

```bash
# Search existing posts by keyword
curl -s "$WP_URL/wp-json/wp/v2/posts?search=your+keyword&per_page=5" \
  -u "$WP_USERNAME:$WP_PASSWORD" | python3 -c "
import json, sys
for p in json.load(sys.stdin):
    print(f'{p[\"title\"][\"rendered\"]}: {p[\"link\"]}')
"
```

Use descriptive anchor text (not "click here"). Example:
```html
<p>If you're curious about how sourdough starters work,
check out our <a href="$WP_URL/post-slug/">complete guide
to maintaining your starter</a>.</p>
```

---

## 7. Step 5: Image Generation

### Pipeline: generate-image.sh → Replicate (Flux) → Tinify → WordPress

Every image is generated via the `generate-image.sh` script. This ensures all images are:
- Generated with consistent quality (Flux via Replicate)
- Compressed via Tinify (optimal file size)
- Uploaded directly to the WP media library
- Tracked in the Airtable "Generated Images" table

### 7a. Generate Each Image

For each image (1 featured + 1 per H2), run the generate-image.sh script:

```bash
# Generate image and upload to WordPress
bash /home/agent/project/generate-image.sh \
  "YOUR IMAGE PROMPT HERE" \
  "short-descriptive-title"
```

The script outputs the WordPress media URL on success. Capture this for embedding in the post.

**Aspect ratios:**
The script generates landscape images by default (suitable for blog featured images and section images).

### 7b. Image Prompt Guidelines

Write prompts that are:
- **Specific to the section content** — not generic stock imagery
- **Visually rich** — describe colors, mood, composition, lighting
- **Style-consistent** — check CLAUDE.md → Image Generation Pipeline for your brand's style guidance
- **On-brand** — incorporate your brand colors, themes, and visual identity

**Example prompts by business type:**

**Bakery:**
- Featured: `"Warm inviting photograph of fresh sourdough bread on a rustic wooden cutting board, steam rising, golden crust, artisan bakery atmosphere, natural lighting, no text"`
- Section: `"Close-up of hands kneading bread dough, flour dusted wooden surface, warm kitchen lighting, professional food photography style, no text"`

**Landscaping:**
- Featured: `"Beautiful spring garden with lush green lawn, colorful flower beds, professional landscaping, golden hour lighting, residential setting, no text"`
- Section: `"Gardener's hands planting seedlings in rich dark soil, spring planting, warm natural light, editorial style, no text"`

**Professional Services (lawyer, accountant):**
- Featured: `"Modern minimalist office desk with legal documents, professional atmosphere, clean lines, soft natural lighting, business aesthetic, no text"`
- Section: `"Confident professional reviewing documents at desk, warm office lighting, editorial business photography style, no text"`

### 7c. Upload to WordPress Media Library

The `generate-image.sh` script handles the full pipeline:
1. Generates image via Replicate
2. Compresses via Tinify
3. Uploads to WordPress Media Library
4. Returns the WordPress media URL

**Usage:**
```bash
# The script returns the WP media URL on stdout
WP_IMAGE_URL=$(bash /home/agent/project/generate-image.sh "your prompt" "image-title")
echo "Image URL: $WP_IMAGE_URL"
```

If you need to manually upload an existing image:
```bash
curl -s -X POST "$WP_URL/wp-json/wp/v2/media" \
  -u "$WP_USERNAME:$WP_PASSWORD" \
  -H "Content-Disposition: attachment; filename=\"keyword-slug-section-name.webp\"" \
  -H "Content-Type: image/webp" \
  --data-binary @/tmp/post-image.webp
```

### 7d. Set the Featured Image

When creating/updating the post, set `featured_media` to the featured image's media ID.

### 7e. Insert Section Images in Content

For each H2 section, insert the image immediately after the `<h2>` tag:

```html
<h2>Your Section Heading</h2>
<figure class="wp-block-image size-large">
  <img src="$WP_URL/wp-content/uploads/2026/02/section-image-name.webp"
       alt="focus keyword or descriptive alt text" />
</figure>
<p>Content begins here...</p>
```

**IMPORTANT — SEO Rule:** At least ONE image in the post must have its `alt` attribute set to the exact focus keyword.

---

## 8. Step 6: Product CTA Insertion

> **Note:** This section only applies if `HAS_PRODUCTS=yes` in CLAUDE.md. If your business doesn't sell products, skip this step entirely.

### Goal: 2 product mentions per post — 1 inline text, 1 Kadence block

### 8a. Identify Relevant Product Category

Analyze the blog topic/keyword to determine which product category is most relevant. Check CLAUDE.md → Product Info for your category structure.

### 8b. Find Matching Products

Query WooCommerce for products matching the relevant category:

```bash
# Get products for a specific category
curl -s "$WP_URL/wp-json/wc/v3/products?category=CATEGORY_ID&per_page=20&status=publish" \
  -u "$WP_USERNAME:$WP_PASSWORD"
```

**Check CLAUDE.md → Product Info for:**
- Your WooCommerce category IDs
- Product types available
- Category → content topic mappings

**Example mappings by business type:**
- **Bakery:** Bread recipes → bread-making tools, Cake posts → cake decorating supplies
- **Landscaping:** Spring posts → spring planting supplies, Lawn care → lawn equipment
- **Boutique:** Style guides → featured clothing categories

### 8c. Inline Product Mention (CTA #1)

Place this naturally within the body text of Section 4 or 5. It should feel like a helpful recommendation, not an ad.

**Example by business type:**

*Bakery:*
```html
<p>If you're ready to start your sourdough journey, our
<a href="/product/sourdough-starter-kit/" target="_blank" rel="noopener">Complete Sourdough Starter Kit</a>
has everything you need — including a detailed guide written by our head baker.</p>
```

*Landscaping:*
```html
<p>For Zone 7 gardeners, our
<a href="/product/spring-planting-bundle/" target="_blank" rel="noopener">Spring Planting Bundle</a>
includes all the native perennials mentioned in this guide.</p>
```

**Rules:**
- Link directly to the individual product page
- Use the actual product name as anchor text
- Keep it to 1-2 sentences, woven into the content flow
- Tone: helpful and on-brand (check CLAUDE.md for voice)

### 8d. Kadence Product CTA Block (CTA #2)

Place the block **in the body of the post** — after the 4th or 5th H2 section is ideal. **NEVER place it at the very end** adjacent to the newsletter signup block, as the two CTA blocks will abut awkwardly. There should be at least one full content section between the product CTA and the newsletter signup.

**Option A: Use the synced reusable block (static template):**
```html
<!-- wp:block {"ref":5467} /-->
```

**Option B (PREFERRED): Inline the Kadence markup with dynamic product data:**

Replace the placeholders in this template with actual product data:

```html
<!-- wp:kadence/rowlayout {"uniqueID":"cta_product_POSTID","columns":2,"colLayout":"left-forty","tabletLayout":"row","mobileLayout":"collapse","padding":[30,30,30,30],"bgColor":"#f8f6ff","borderRadius":[12,12,12,12]} -->
<div class="wp-block-kadence-rowlayout alignnone">
<!-- wp:kadence/column {"uniqueID":"cta_col_img_POSTID","id":1} -->
<div class="wp-block-kadence-column inner-column-1"><div class="kt-inside-inner-col">
<!-- wp:image {"sizeSlug":"medium","linkDestination":"custom"} -->
<figure class="wp-block-image size-medium">
  <a href="PRODUCT_URL"><img src="PRODUCT_IMAGE_URL" alt="PRODUCT_NAME" /></a>
</figure>
<!-- /wp:image -->
</div></div>
<!-- /wp:kadence/column -->
<!-- wp:kadence/column {"uniqueID":"cta_col_txt_POSTID","id":2} -->
<div class="wp-block-kadence-column inner-column-2"><div class="kt-inside-inner-col">
<!-- wp:heading {"level":3,"style":{"color":{"text":"#2d1854"}}} -->
<h3 class="wp-block-heading has-text-color" style="color:#2d1854">PRODUCT_TITLE_OR_CTA_HEADLINE</h3>
<!-- /wp:heading -->
<!-- wp:paragraph {"style":{"color":{"text":"#4a3970"}}} -->
<p class="has-text-color" style="color:#4a3970">PRODUCT_DESCRIPTION_OR_CTA_TEXT</p>
<!-- /wp:paragraph -->
<!-- wp:kadence/advancedbtn {"uniqueID":"cta_btn_POSTID"} -->
<div class="wp-block-kadence-advancedbtn kt-btn-wrap-cta_btn_POSTID">
<!-- wp:kadence/singlebtn {"uniqueID":"cta_btn_s_POSTID","text":"BUTTON_TEXT","link":"PRODUCT_URL","color":"#ffffff","background":"#6b21a8","backgroundHover":"#7c3aed","borderRadius":[8,8,8,8],"padding":[12,32,12,32]} -->
<div class="kt-btn-wrap"><a class="kt-button button" href="PRODUCT_URL" style="color:#ffffff;background-color:#6b21a8;border-radius:8px;padding:12px 32px"><span class="kt-btn-inner-text">BUTTON_TEXT</span></a></div>
<!-- /wp:kadence/singlebtn -->
</div>
<!-- /wp:kadence/advancedbtn -->
</div></div>
<!-- /wp:kadence/column -->
</div>
<!-- /wp:kadence/rowlayout -->
```

**Placeholders to replace:**
- `POSTID` → WordPress post ID (for unique block IDs)
- `PRODUCT_URL` → individual product permalink
- `PRODUCT_IMAGE_URL` → product featured image URL (from WooCommerce API `images[0].src`)
- `PRODUCT_NAME` → product name
- `PRODUCT_TITLE_OR_CTA_HEADLINE` → e.g., "Show Off Your Pisces Pride"
- `PRODUCT_DESCRIPTION_OR_CTA_TEXT` → 1-2 sentences about the product
- `BUTTON_TEXT` → rotate between: "Shop Now", "Get Yours", "Grab It Here", "Treat Yourself"

---

## 9. Step 7: Newsletter Form Funnels

### Two placements per post:

### 9a. Mid-Article Signup (Automatic)

This is handled by the PHP Code Snippet installed in WordPress. It automatically inserts a styled newsletter signup block with Fluent Form ID 3 after the 3rd H2 (or 4th if 7+ H2s).

**No action needed from the blog writer** — the PHP filter does this on the frontend.

### 9b. End-of-Post Signup (Manual in Content)

> **Note:** Only include if `USES_FLUENT_FORMS=yes` in CLAUDE.md.

Add this Kadence block at the very end of the post content, after the conclusion. Customize the headline, description, and image to match your brand:

```html
<!-- wp:kadence/rowlayout {"uniqueID":"signup_end_POSTID","columns":2,"colLayout":"left-forty","tabletLayout":"row","mobileLayout":"collapse","padding":[30,30,30,30],"bgColor":"#f0f0f0","borderRadius":[16,16,16,16]} -->
<div class="wp-block-kadence-rowlayout alignnone">
<!-- wp:kadence/column {"uniqueID":"signup_img_POSTID","id":1} -->
<div class="wp-block-kadence-column inner-column-1"><div class="kt-inside-inner-col">
<!-- wp:image {"sizeSlug":"medium"} -->
<figure class="wp-block-image size-medium">
  <img src="NEWSLETTER_IMAGE_URL"
       alt="Join our newsletter community" />
</figure>
<!-- /wp:image -->
</div></div>
<!-- /wp:kadence/column -->
<!-- wp:kadence/column {"uniqueID":"signup_txt_POSTID","id":2} -->
<div class="wp-block-kadence-column inner-column-2"><div class="kt-inside-inner-col">
<!-- wp:heading {"level":3,"style":{"color":{"text":"#1e1b3a"}}} -->
<h3 class="wp-block-heading has-text-color" style="color:#1e1b3a">NEWSLETTER_HEADLINE</h3>
<!-- /wp:heading -->
<!-- wp:paragraph {"style":{"color":{"text":"#4a4568"}}} -->
<p class="has-text-color" style="color:#4a4568">NEWSLETTER_DESCRIPTION</p>
<!-- /wp:paragraph -->
<!-- wp:shortcode -->
[fluentform id="FORM_ID"]
<!-- /wp:shortcode -->
</div></div>
<!-- /wp:kadence/column -->
</div>
<!-- /wp:kadence/rowlayout -->
```

**Replace these placeholders from CLAUDE.md:**
- `NEWSLETTER_IMAGE_URL` — Upload a branded newsletter image to WP Media
- `NEWSLETTER_HEADLINE` — e.g., "Tips Delivered Weekly" or "Join Our Community"
- `NEWSLETTER_DESCRIPTION` — 1-2 sentences about what subscribers get
- `FORM_ID` — From CLAUDE.md → Form Funnel IDs
- `POSTID` — WordPress post ID for unique block IDs

---

## 10. Step 8: SEO Optimization (Rank Math)

### Focus Keyword Checklist

Before publishing, verify ALL of these:

| Requirement | Where |
|-------------|-------|
| Focus keyword in title | Post title (H1) |
| Focus keyword in slug | URL slug |
| Focus keyword in first 100 words | Opening paragraph |
| Focus keyword in meta title | Rank Math meta |
| Focus keyword in meta description | Rank Math meta |
| Focus keyword in at least 2 H2 tags | Section headings |
| Focus keyword as alt text on 1 image | At least one `<img alt="">` |
| Focus keyword density 1-2% | Throughout the content |

### Set Rank Math Meta via API

After creating the WordPress post, set the SEO metadata:

```bash
# Set focus keyword, meta title, and meta description
curl -s -X POST "$WP_URL/wp-json/rankmath/v1/updateMeta" \
  -u "$WP_USERNAME:$WP_PASSWORD" \
  -H "Content-Type: application/json" \
  -d '{
    "objectType": "post",
    "objectID": POST_ID,
    "meta": {
      "rank_math_focus_keyword": "your focus keyword",
      "rank_math_title": "Your SEO Title with Focus Keyword %sep% %sitename%",
      "rank_math_description": "Your 150-160 character meta description containing the focus keyword. Make it compelling and click-worthy."
    }
  }'
```

### Meta Title Format
**Max 60 characters** (including site name). Use Rank Math variables for the separator and site name:

`[Focus Keyword]: [Compelling Promise] %sep% %sitename%`

The `%sep%` and `%sitename%` variables are expanded by Rank Math at render time, so the raw title you set should be ~45-50 chars before the variables.

**Examples by business type:**
- **Bakery:** `Sourdough Starter Guide: Everything Beginners Need %sep% %sitename%`
- **Landscaping:** `Spring Lawn Care Zone 7: Your Complete Checklist %sep% %sitename%`
- **Lawyer:** `Estate Planning Basics: 5 Essential Documents %sep% %sitename%`
- **E-commerce:** `Best Gifts for Bakers: 2026 Buyer's Guide %sep% %sitename%`

### Meta Description Guidelines
- **130-155 characters** (stay under 155 to avoid truncation in Google SERPs)
- Include focus keyword naturally (ideally near the start)
- Include a compelling reason to click
- Use active, engaging language
- End with a hook or question when possible

### Slug Format
- All lowercase, hyphen-separated
- Focus keyword should be prominent
- Remove stop words (the, a, an, is, for, etc.) when they add no value
- Example: `pisces-2026-horoscope-complete-guide`

---

## 11. Step 9: WordPress Publishing

### Create the Post

```bash
curl -s -X POST "$WP_URL/wp-json/wp/v2/posts" \
  -u "$WP_USERNAME:$WP_PASSWORD" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Post Title with Focus Keyword",
    "slug": "focus-keyword-slug",
    "content": "FULL HTML CONTENT HERE",
    "status": "publish",
    "categories": [CATEGORY_ID],
    "tags": [TAG_IDS],
    "featured_media": FEATURED_IMAGE_MEDIA_ID
  }'
```

**CRITICAL RULES:**
1. **Always publish as `"publish"`** — all posts go live immediately
2. **Always set `featured_media`** — never publish without a featured image
3. **Always set `categories`** — default to `171` (The world of Horoscope) if no specific category applies
4. **Always set tags** — create or reuse relevant tags (zodiac sign name, topic, etc.)

### Category Selection Guide

**Every post should have multiple categories.** Always include the primary topic category PLUS any relevant secondary categories.

**Check CLAUDE.md → WordPress → Primary categories for your category structure.**

Best practice: Create a logical category hierarchy that mirrors your content strategy:
- **Primary category** — The main topic area (e.g., "Recipes", "Guides", "News")
- **Secondary categories** — Subtopics or attributes (e.g., "Bread", "Desserts", "Beginner")

**To list existing categories:**
```bash
curl -s "$WP_URL/wp-json/wp/v2/categories?per_page=50" \
  -u "$WP_USERNAME:$WP_PASSWORD" | python3 -c "
import json, sys
for c in json.load(sys.stdin):
    print(f'{c[\"id\"]}: {c[\"name\"]} ({c[\"slug\"]})')
"
```

**To create a new category:**
```bash
curl -s -X POST "$WP_URL/wp-json/wp/v2/categories" \
  -u "$WP_USERNAME:$WP_PASSWORD" \
  -H "Content-Type: application/json" \
  -d '{"name": "Category Name", "slug": "category-slug", "description": "Category description"}'
```

### Tag Creation
```bash
# Create tag
curl -s -X POST "$WP_URL/wp-json/wp/v2/tags" \
  -u "$WP_USERNAME:$WP_PASSWORD" \
  -H "Content-Type: application/json" \
  -d '{"name": "pisces 2026"}'
```

---

## 12. Step 10: Post-Publish Updates

After creating the draft, update all tracking systems:

### 12a. Update Airtable Keyword Status

```bash
curl -s --retry 3 --retry-delay 2 -X PATCH "https://api.airtable.com/v0/$AIRTABLE_BASE_ID/$AIRTABLE_KEYWORDS_TABLE/$KEYWORD_RECORD_ID" \
  -H "Authorization: Bearer $AIRTABLE_KEY" \
  -H "Content-Type: application/json" \
  -d '{"fields": {"Status": "Published", "Date Published": "2026-02-21"}}'
```

### 12b. Update Airtable Content Calendar

```bash
curl -s --retry 3 --retry-delay 2 -X PATCH "https://api.airtable.com/v0/$AIRTABLE_BASE_ID/$AIRTABLE_CONTENT_TABLE/$CALENDAR_RECORD_ID" \
  -H "Authorization: Bearer $AIRTABLE_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "fields": {
      "Status": "Draft",
      "WP Post ID": POST_ID,
      "WP URL": "$WP_URL/slug/",
      "Word Count": WORD_COUNT,
      "Featured Image URL": "image url"
    }
  }'
```

### 12c. Create/Update Asana Task

```bash
# Create task in Drafts section
curl -s -X POST "https://app.asana.com/api/1.0/tasks" \
  -H "Authorization: Bearer $ASANA_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "data": {
      "name": "📝 Blog Draft: Post Title Here",
      "notes": "Focus keyword: XYZ\nWord count: XXXX\nWP Post ID: XXXX\nStatus: Draft — awaiting review\n\nSections: X H2s, X images generated\nProduct CTA: Product Name\nInternal links: 2\n\nCompleted: 2026-02-21",
      "projects": ["1213328321428246"],
      "memberships": [{"project": "1213328321428246", "section": "1213375221698074"}]
    }
  }'
```

### 12d. Log Summary

Print a completion summary:

```
✅ Blog post created successfully
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Title:          [post title]
Focus Keyword:  [keyword]
Word Count:     [count]
WP Post ID:     [id]
Status:         Draft
Images:         [count] generated (featured + sections)
Product CTA:    [product name] (inline + block)
Internal Links: [count]
SEO Score:      Focus keyword set, meta title, meta description
Airtable:       Keywords ✓ | Content Calendar ✓ | Research ✓
Asana:          Task created in Drafts section
```

---

## 13. Reference: API Endpoints

| Service | Endpoint | Auth |
|---------|----------|------|
| WordPress REST | `$WP_URL/wp-json/wp/v2/` | Basic: `$WP_USERNAME:$WP_PASSWORD` |
| WooCommerce | `$WP_URL/wp-json/wc/v3/` | Basic: `$WP_USERNAME:$WP_PASSWORD` |
| Rank Math | `$WP_URL/wp-json/rankmath/v1/updateMeta` | Basic: `$WP_USERNAME:$WP_PASSWORD` |
| Fluent Forms | `$WP_URL/wp-json/fluentform/v1/` | Basic: `$WP_USERNAME:$WP_PASSWORD` |
| Airtable | `https://api.airtable.com/v0/$AIRTABLE_BASE_ID/` | Bearer: `$AIRTABLE_API_KEY` |
| Airtable Meta | `https://api.airtable.com/v0/meta/bases/$AIRTABLE_BASE_ID/tables` | Bearer: `$AIRTABLE_API_KEY` |
| DataForSEO SERP | `https://api.dataforseo.com/v3/serp/google/organic/live/regular` | Basic: `$DATAFORSEO_LOGIN:$DATAFORSEO_PASSWORD` |
| Firecrawl | `https://api.firecrawl.dev/v1/scrape` | Bearer: `$FIRECRAWL_API_KEY` |
| Image Generation | `generate-image.sh` | Uses REPLICATE_API + TINIFY_API from .env |
| Asana | `https://app.asana.com/api/1.0/` | Bearer: `$ASANA_API_KEY` |

**Note on Airtable:** Always strip whitespace from the API key: `AIRTABLE_KEY=$(echo "$AIRTABLE_API_KEY" | tr -d '[:space:]')`

---

## 14. Reference: Product Catalog

> **Note:** This section only applies if `HAS_WOOCOMMERCE=yes` in CLAUDE.md.

### Listing Your WooCommerce Categories

```bash
# List all product categories
curl -s "$WP_URL/wp-json/wc/v3/products/categories?per_page=50" \
  -u "$WP_USERNAME:$WP_PASSWORD" | python3 -c "
import json, sys
for c in json.load(sys.stdin):
    print(f'{c[\"id\"]}: {c[\"name\"]} ({c[\"count\"]} products)')
"
```

### How to Get a Random Product for a Category

```bash
CATEGORY_ID=YOUR_CATEGORY_ID
curl -s "$WP_URL/wp-json/wc/v3/products?category=$CATEGORY_ID&per_page=20&status=publish" \
  -u "$WP_USERNAME:$WP_PASSWORD" | python3 -c "
import json, sys, random
products = json.load(sys.stdin)
if products:
    p = random.choice(products)
    print(f'Name: {p[\"name\"]}')
    print(f'URL: {p[\"permalink\"]}')
    print(f'Image: {p[\"images\"][0][\"src\"] if p[\"images\"] else \"none\"}')
    print(f'Price: {p[\"price\"]}')
else:
    print('No products found in this category')
"
```

**Document your product catalog in CLAUDE.md → Product Info** for easy reference.

---

## 15. Reference: WordPress Categories

**Your categories are business-specific. To list them:**

```bash
curl -s "$WP_URL/wp-json/wp/v2/categories?per_page=50" \
  -u "$WP_USERNAME:$WP_PASSWORD" | python3 -c "
import json, sys
for c in json.load(sys.stdin):
    print(f'{c[\"id\"]}: {c[\"name\"]} ({c[\"slug\"]}) - {c[\"count\"]} posts')
"
```

New categories can be created via the WP REST API as needed (see Step 9).

**Document your primary categories in CLAUDE.md → WordPress → Primary categories.**

---

## 16. Reference: Airtable Tables

### Keywords Table (`$AIRTABLE_KEYWORDS_TABLE`)
| Field | Type |
|-------|------|
| Keyword | singleLineText (primary) |
| Search Volume | number |
| Difficulty | number |
| Intent | singleSelect |
| Status | singleSelect (**Queue** → **Researching** → **Published**) — EXACT values, case-sensitive |
| Date Created | createdTime |
| Date Published | date |
| Notes | multilineText |

### Research Table (`$AIRTABLE_RESEARCH_TABLE`)
| Field | Type |
|-------|------|
| Keyword | singleLineText (primary) |
| Source URL | url |
| Source Title | singleLineText |
| Content | multilineText |
| Summary | multilineText |
| SERP Position | number |
| Date Scraped | date |

### Content Calendar Table (`$AIRTABLE_CONTENT_TABLE`)
| Field | Type |
|-------|------|
| Title | singleLineText (primary) |
| Keyword | singleLineText |
| Status | singleSelect (Queue/Researching/Writing/Draft/Scheduled/Published) |
| WP Post ID | number |
| WP URL | url |
| Publish Date | date |
| Featured Image URL | url |
| Category | singleLineText |
| Word Count | number |
| Notes | multilineText |

### Generated Images Table (`$AIRTABLE_GENERATED_IMAGES_TABLE`)
| Field | Type |
|-------|------|
| Name | singleLineText (primary) |
| Image URL | url |
| Image Model | singleLineText |
| Prompt | multilineText |
| Site | singleLineText |
| Article Title | singleLineText |
| Status | singleSelect |

---

## 17. Reference: Block Templates

### End-of-Post Newsletter Signup Block
See Section 9b for the full Kadence block markup.

### Product CTA Block (Dynamic)
See Section 8d for the full Kadence block markup with placeholder variables.

### Product CTA Block (Synced/Reusable)
```html
<!-- wp:block {"ref":5467} /-->
```

---

## 18. Troubleshooting

### Common Issues

**Airtable 401 error:**
The API key may have trailing whitespace. Always strip it:
```bash
AIRTABLE_KEY=$(echo "$AIRTABLE_API_KEY" | tr -d '[:space:]')
```

**DataForSEO 404:**
Use `/v3/serp/google/organic/live/regular` — NOT `/live` alone.

**Asana 403:**
Use `app.asana.com/api/1.0` — NOT `api.asana.com`.

**generate-image.sh timeout:**
Image generation can take 30-60 seconds. The script handles timeouts internally.

**WordPress image upload fails:**
Ensure `Content-Type` matches the file format. Use `image/webp` for .webp files.

**Rank Math meta not saving:**
The `updateMeta` endpoint returns `{"slug": true}` on success. If it returns an error, verify the post ID exists and the meta key names are correct (they're prefixed with `rank_math_`).

**Product CTA block not rendering:**
If using the reusable block reference (`ref:5467`), Kadence Blocks must be active. If the block was deleted, inline the markup instead (Section 8d Option B).

**Mid-article form not showing:**
Verify the Code Snippet is active in WP Admin > Code Snippets. The snippet only fires on `is_single()` pages with 3+ H2 tags.

---

## 19. Telegram Alert

Before finishing, send a Telegram alert summarizing the result. Use the PROJECT_SLUG from CLAUDE.md:

**On success:**
```bash
bash /home/agent/project/telegram-alert.sh "✅ [PROJECT_SLUG] blog-writer — Published: [Post Title] | WP ID: [id] | [word count] words | [post_url]"
```

**On failure:**
```bash
bash /home/agent/project/telegram-alert.sh "❌ [PROJECT_SLUG] blog-writer — [error details]"
```

**On skip:**
```bash
bash /home/agent/project/telegram-alert.sh "⚠️ [PROJECT_SLUG] blog-writer — [skip reason]"
```

---

## SKILL_RESULT

```
SKILL_RESULT: success | Blog post published: [Post Title] | WP ID: [id] | [word count] words | [post_url]
```

On skip: `SKILL_RESULT: skip | [reason] | no post published`
On fail: `SKILL_RESULT: fail | [error details] | no post published`

---

*End of Blog Writer Skill v1.0.0*
