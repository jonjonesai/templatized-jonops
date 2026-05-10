# {{BRAND_NAME}} Knowledge Base

This is a **pointer index**, not a static encyclopedia. Real facts live in WordPress, WooCommerce, Airtable, and on the live site — fetch them when needed instead of caching them here. Use this file to know **where to look**.

The agent reads this before drafting any customer-facing piece (email, blog, social, newsletter). The email-checker skill specifically reads this so replies cite real facts, not hallucinated ones.

---

## Where canonical facts live

### Products & inventory
- **WooCommerce REST:** `{{WP_URL}}/wp-json/wc/v3/products` — current catalog, stock, pricing
- **Specific product lookup:** `{{WP_URL}}/wp-json/wc/v3/products?search=KEYWORD` or `?slug=PRODUCT_SLUG`
- **Product categories:** {{WP_PRODUCT_CATEGORIES}}
- **Default new product status:** {{WC_DEFAULT_PRODUCT_STATUS}}

### Orders & customer history
- **Order lookup by email:** `{{WP_URL}}/wp-json/wc/v3/orders?customer=EMAIL` (auth required)
- **Order status meanings:** processing, on-hold, completed, cancelled, refunded
- **Shipping policy:** {{SHIPPING_POLICY_LOCATION}}

### Site content (FAQs, About, Policies)
- **About page:** {{ABOUT_PAGE_URL}}
- **FAQ / Help:** {{FAQ_PAGE_URL}}
- **Shipping policy page:** {{SHIPPING_POLICY_URL}}
- **Returns / refunds page:** {{RETURNS_POLICY_URL}}
- **Privacy / terms:** {{PRIVACY_TERMS_URL}}
- **Search any page:** `{{WP_URL}}/wp-json/wp/v2/pages?search=KEYWORD`
- **Search any post:** `{{WP_URL}}/wp-json/wp/v2/posts?search=KEYWORD`

### Brand assets
- **Brand voice:** `brand-voice.md` (this project root)
- **Email persona:** `email-persona.md` (this project root)
- **Brand book / additional docs:** {{BRAND_BOOK_LOCATION}}

### Airtable (operational data)
- **Base ID:** stored in `.env` as `AIRTABLE_BASE_ID`
- **Most relevant tables for customer-facing context:**
{{AIRTABLE_RELEVANT_TABLES}}

### Past customer feedback / patterns
{{CUSTOMER_FEEDBACK_LOCATION}}

---

## Things only this brand knows (non-discoverable facts)

These don't live in any API — they live here. Keep this section short. Add a line whenever the agent gets a question it can't answer from the live sources above.

{{BRAND_SPECIFIC_FACTS}}

---

## Frequently asked, factually answered

When a question comes up repeatedly, codify the answer here so the agent doesn't have to re-research. Keep each entry under 3 lines; link out for depth.

{{BRAND_FAQ_PAIRS}}

---

## Claim boundaries (what we can / can't say)

These are the legal, regulatory, or brand-promise boundaries on what we say to customers.

{{BRAND_CLAIM_BOUNDARIES}}

---

## How to use this file

**Before any customer-facing draft:**
1. Read this file in full.
2. Identify which canonical source has the fact you need.
3. Fetch it live (WP REST, WC REST, Airtable). Don't trust your memory.
4. If a fact isn't in any live source AND isn't in "Things only this brand knows," ask the operator before stating it.

**When to update this file:**
- A new product line launches → update product categories
- A policy URL changes → update the link
- The agent gets a question it couldn't answer cleanly → add it to "Frequently asked"
- A new claim boundary is set (legal, regulatory, brand) → add it

---

# PLACEHOLDER REFERENCE

The `/init` wizard fills these from your earlier answers. If you're populating manually:

| Placeholder | Description | Example |
|-------------|-------------|---------|
| `{{BRAND_NAME}}` | Your brand name | "Custom Creative" |
| `{{WP_URL}}` | Your WordPress site URL | "https://customcreative.store" |
| `{{WP_PRODUCT_CATEGORIES}}` | Comma-separated product categories with WooCommerce IDs | "T-Shirts (329), Hoodies (330), Hip-Hop (265)" |
| `{{WC_DEFAULT_PRODUCT_STATUS}}` | Default for new products | "draft" or "publish" |
| `{{SHIPPING_POLICY_LOCATION}}` | Where the agent can look up shipping rules | "FAQ page → 'shipping' section" or specific URL |
| `{{ABOUT_PAGE_URL}}` | Public About page | "https://customcreative.store/about" |
| `{{FAQ_PAGE_URL}}` | FAQ page URL | "https://customcreative.store/faq" |
| `{{SHIPPING_POLICY_URL}}` | Shipping policy page | "https://customcreative.store/shipping" |
| `{{RETURNS_POLICY_URL}}` | Returns / refunds page | "https://customcreative.store/returns" |
| `{{PRIVACY_TERMS_URL}}` | Privacy / terms page | "https://customcreative.store/privacy" |
| `{{BRAND_BOOK_LOCATION}}` | Where additional brand docs live (or "none") | "brand/brand-book.txt" or "knowledge_base/brand/" or "none yet" |
| `{{AIRTABLE_RELEVANT_TABLES}}` | Bullet list of Airtable tables that have customer-relevant info | See example below |
| `{{CUSTOMER_FEEDBACK_LOCATION}}` | Where past customer feedback lives | "Asana 'Customer Feedback' project" or "none yet" |
| `{{BRAND_SPECIFIC_FACTS}}` | Facts that only this brand knows — short bulleted list | See example below |
| `{{BRAND_FAQ_PAIRS}}` | Q/A pairs for common questions | See example below |
| `{{BRAND_CLAIM_BOUNDARIES}}` | What this brand legally / brand-policy can or cannot say | See example below |

## Example: Airtable Relevant Tables

```markdown
- **Keywords** (`AIRTABLE_KEYWORDS_TABLE`) — content roadmap, what we're publishing about
- **Published Posts** (`AIRTABLE_PUBLISHED_POSTS_TABLE`) — link to past blog posts when answering questions
- **Market Intelligence** (`AIRTABLE_MARKET_INTEL_TABLE`) — competitive context if needed
```

## Example: Brand-Specific Facts

```markdown
- We've been hand-blending in Bali since 1989.
- Our refill program has saved 2,245 bottles from landfill in 2025 alone.
- Our wild-illipe butter comes via Forestwise (Kalimantan).
- Founder is Ria Templer, daughter of Melanie Templer (founder).
- We are the original — many copycats now exist; we are not affiliated with any.
```

## Example: FAQ Pairs

```markdown
**Q: Are your essential oils tested?**
A: Yes. Every oil is GC-MS tested for purity and adulterants. Test reports available on request.

**Q: Do your diffusers work without water?**
A: Yes — they use Bernoulli's Principle to nebulize pure essential oil directly. No water, no heat.

**Q: Where do you ship?**
A: US + worldwide via DHL Express. See shipping page for current rates.
```

## Example: Claim Boundaries

```markdown
- **Never claim oils cure, treat, diagnose, or prevent any disease.** Use "many find," "creates an atmosphere of," "supports a sense of."
- **Never quote a price** in customer email — direct to product pages.
- **Trademark discipline:** always say "Nebulizing Diffuser®" with ® on first mention.
- **No comp-stay / press-comp commitments** without operator approval.
- **No "organic" claims** unless the product is certified organic — list which SKUs are.
```
