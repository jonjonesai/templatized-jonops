---
name: wordpress-kadence
description: >
  Operate a WordPress site running the Kadence theme + Kadence Blocks +
  WooCommerce through the Mega Kadence Bridge plugin's REST API. Use when
  building or editing a Kadence WordPress site by voice or chat, especially
  for print-on-demand merch stores in the MEGA ecosystem. Covers theme
  settings (theme_mods), global palette, custom CSS, pages and posts, the
  homepage, menus, WooCommerce products and categories, header/footer
  configuration, snapshot rollback, and the verify-then-report change loop.
  Triggers on: WordPress, Kadence, Kadence Blocks, mega-kadence-bridge,
  claude-bot, MEGA store, POD store, print-on-demand, set up my store,
  build my store, theme mod, palette, header layout, custom CSS, hide page
  title, WooCommerce product, set homepage, change brand color.
---

# WordPress + Kadence Skill (Mega Kadence Bridge edition)

You operate a WordPress site through the **Mega Kadence Bridge** plugin — a
private, authenticated REST API exposed at
`/wp-json/mega-kadence-bridge/v1/`. Authentication is HTTP Basic Auth as a
dedicated `claude-bot` user using a WordPress Application Password. Every
write is snapshotted and reversible.

You do not use SSH. You do not use WP-CLI. The bridge is the entire surface.
The only things outside the bridge are plugin installation, server config,
and PHP file edits — and you ask the user before reaching for any of those.

You verify your own work with an external HTTP request after every change.
You never tell the user "I changed it, please refresh and check" — you check.

---

## Bootstrap

### Read credentials from `.env`

Two patterns are supported, depending on whether the project hosts one
WordPress site or many:

**Single-site (a fresh student install):**
```
BRIDGE_URL=https://yoursite.com/wp-json/mega-kadence-bridge/v1
BRIDGE_USER=claude-bot
BRIDGE_PASS="xxxx xxxx xxxx xxxx xxxx xxxx"
SITE_URL=https://yoursite.com
```

**Multi-site (e.g. SecondBrain, agencies):**
```
BRIDGE_<SITE>_URL=...
BRIDGE_<SITE>_USER=claude-bot
BRIDGE_<SITE>_PASS="xxxx xxxx xxxx xxxx xxxx xxxx"
BRIDGE_<SITE>_SITE=https://...
```

`<SITE>` is an uppercase slug like `MEGA`, `MYSITE`. Pick the one the user
named (or default to `WP_DEFAULT_SITE` if set) and bind to short names for
the session:

```bash
export BRIDGE_URL="$BRIDGE_MEGA_URL"
export BRIDGE_AUTH="$BRIDGE_MEGA_USER:$BRIDGE_MEGA_PASS"
export SITE_URL="$BRIDGE_MEGA_SITE"
```

Application Passwords contain spaces. They MUST be double-quoted in `.env`
because `.env` is bash-sourced. Do not strip the spaces — they're part of
the password.

### Verify the bridge is alive

```bash
curl -s -u "$BRIDGE_AUTH" "$BRIDGE_URL/info" | jq
```

Expected: site name, theme name, WP version, PHP version, and the flags
`kadence_pro_active`, `kadence_blocks_pro`, `woocommerce_active`.

- **401 Unauthorized** — the App Password is wrong, or `.htaccess` isn't
  passing the `Authorization` header. The bridge's activator patches
  `.htaccess` automatically, so a 401 usually means the password was
  regenerated and `.env` is stale.
- **404 Not Found** — the plugin isn't installed or activated.
- **403 Forbidden** — `claude-bot` exists but lost admin role. Check the
  user in WP admin.

### Snapshot starting state before making changes

```bash
mkdir -p .session
curl -s -u "$BRIDGE_AUTH" "$BRIDGE_URL/info"     > .session/info.json
curl -s -u "$BRIDGE_AUTH" "$BRIDGE_URL/settings" > .session/kadence-settings.json
curl -s -u "$BRIDGE_AUTH" "$BRIDGE_URL/render?url=/" > .session/home.json
curl -s -u "$BRIDGE_AUTH" "$BRIDGE_URL/history?limit=10" > .session/history.json
```

This gives you a known-good baseline for diffs and rollback if something
goes wrong.

---

## The 6-question student intake

When working with a new student building their first store, ask these
questions one at a time, waiting for each answer. Full script in
`INTAKE.md`. Summary:

1. **Store name** — appears in browser tab, footer, SEO titles.
2. **Niche** — be specific. *"funny golden retriever shirts"*, not *"pets"*.
3. **Style** — light or dark? Dark suits streetwear, gaming, edgy. Light
   suits pets, baby, home, food.
4. **Primary brand color** — hex, color name, or *"I don't know"* (then
   default to `#1B4F8A` navy for light, `#FF5500` orange for dark).
5. **Logo** — upload PNG with transparent bg, or skip for text logo.
6. **Hero image** — upload, or skip for gradient placeholder.

After answers → execute the deploy sequence below. Do not ask permission
between steps. Tell the student what you're doing as you do it.

---

## Deploy sequence (POD store from scratch)

Each numbered step is one or more bridge calls. After every step, capture
the `snapshot_id` from the response into a local note so a single thing can
be rolled back without reverting everything.

| # | Step | Endpoint(s) |
|---|---|---|
| 1 | Apply palette | `POST /option/kadence_global_palette` (workaround — see palette gotcha) |
| 2 | Set core theme_mods | `POST /theme-mods/batch` |
| 3 | Apply Kadence Pro POD preset (if Pro active) | `POST /kadence-pro/preset/pod` |
| 4 | Add custom CSS (the small subset) | `POST /css` |
| 5 | Upload logo | `POST /media/upload-from-url` |
| 6 | Set logo as `custom_logo` | `POST /theme-mod/custom_logo` + `/theme-mod/logo_width` |
| 7 | Upload hero image | `POST /media/upload-from-url` |
| 8 | Create homepage | `POST /pages/ensure` (block markup from `POD-HOMEPAGE-TEMPLATE.md`) |
| 9 | Set as front page | `POST /option/show_on_front` + `POST /option/page_on_front` |
| 10 | Create About page | `POST /pages/ensure` |
| 11 | Create primary menu | `POST /menus/create` + `POST /menus/{id}/items` |
| 12 | Configure WooCommerce | `POST /woo/settings` |
| 13 | Flush all caches | `POST /cache/flush` |
| 14 | Verify externally | `curl -A "Mozilla/5.0" $SITE_URL` + grep |

Do not skip step 14. *Verified* is the only acceptable terminal state.

---

## API reference

Every endpoint with the body shape the bridge actually accepts. (Verified
against the v1.0.1 source, not the README.) Auth header is always
`-u claude-bot:<app password>` — written below as `-u "$BRIDGE_AUTH"`.

### Core

#### `GET /info`
Site, theme, WP version, PHP version, capability flags.

#### `GET /render?url=/path`
Returns `{url, status, html}`. The bridge fetches its own URL with a
cache-busting query param. **This still hits LiteSpeed page cache** if the
cache key ignores query strings — re-verify with an external curl. Always.

#### `POST /cache/flush`
No body. Flushes WP object cache + LiteSpeed (API and hook) + WP Super Cache
+ W3TC + WP Fastest Cache + Autoptimize + Cache Enabler + all transients.
Run after every write.

#### `GET /plugins`
Lists active and inactive plugins.

### Theme settings

#### `GET /theme-mod/{key}` / `POST /theme-mod/{key}`
POST body: `{"value": <anything>}`. Snapshots on POST.

```bash
curl -s -X POST -u "$BRIDGE_AUTH" \
  -H "Content-Type: application/json" \
  -d '{"value": {"layout":"left-logo","itemsLayout":"left-logo","desktop":"contained","tablet":"","mobile":""}}' \
  "$BRIDGE_URL/theme-mod/header_main_layout"
```

#### `POST /theme-mods/batch`
Body: `{"mods": {"key1": value1, "key2": value2, ...}}`. The body must be
wrapped in `mods` — flat will reject. Single snapshot covers all keys, but
batch rollback is **not** supported, so prefer `/theme-mod/{key}` for
anything you might want to roll back individually.

```bash
curl -s -X POST -u "$BRIDGE_AUTH" \
  -H "Content-Type: application/json" \
  -d '{"mods": {
    "buttons_background": {"color":"palette1","hover":"palette2"},
    "buttons_color": {"color":"palette9","hover":"palette9"},
    "buttons_border_radius": {"size": {"desktop": 4}, "unit": {"desktop": "px"}},
    "header_sticky": true,
    "scroll_up": true,
    "product_archive_columns": 3
  }}' \
  "$BRIDGE_URL/theme-mods/batch"
```

#### `GET /option/{key}` / `POST /option/{key}`
POST body: `{"value": <anything>}`. Use for `siteurl`, `blogname`,
`show_on_front`, `page_on_front`, `woocommerce_*` options, and (per the
palette gotcha) `kadence_global_palette`.

#### `GET /palette` / `POST /palette` ⚠️ GOTCHA
`POST /palette` is currently broken. It accepts an array and stores it as a
PHP array, but Kadence's frontend reads the option and `json_decode`s it —
expecting a JSON-encoded **string**. The result: your palette write
succeeds silently and Kadence reads nothing. (Filed against the bridge
plugin; until fixed, use the workaround below.)

**Workaround — use `/option/kadence_global_palette` with a stringified value:**

```bash
PALETTE_JSON=$(jq -nc \
  --arg p1 "$PRIMARY" \
  --arg p2 "$ACCENT" \
  --arg p3 "$HEADING" \
  --arg p4 "$BODY" \
  --arg p5 "$MUTED" \
  --arg p6 "$BORDER" \
  --arg p7 "$SURFACE" \
  --arg p8 "$BG" \
  --arg p9 "#FFFFFF" \
  '{
    active: "palette",
    palette: [
      {slug:"palette1", color:$p1, name:"Primary CTA"},
      {slug:"palette2", color:$p2, name:"CTA Hover"},
      {slug:"palette3", color:$p3, name:"Headings"},
      {slug:"palette4", color:$p4, name:"Body Text"},
      {slug:"palette5", color:$p5, name:"Muted Text"},
      {slug:"palette6", color:$p6, name:"Borders"},
      {slug:"palette7", color:$p7, name:"Light Surface"},
      {slug:"palette8", color:$p8, name:"Page Background"},
      {slug:"palette9", color:$p9, name:"Pure White"}
    ]
  }')

# Send the JSON-encoded string as the option value
curl -s -X POST -u "$BRIDGE_AUTH" \
  -H "Content-Type: application/json" \
  -d "$(jq -nc --arg v "$PALETTE_JSON" '{value: $v}')" \
  "$BRIDGE_URL/option/kadence_global_palette"
```

Pre-canned palettes (light, dark, brand-color overrides) live in `POD-PALETTES.md`.

#### `GET /css` / `POST /css`
POST body: `{"css": "...", "append": false}`. Uses
`wp_update_custom_css_post()` — the WordPress core custom CSS surface, not
the dead `kadence_custom_css` option. With `append: true`, the new CSS is
concatenated onto existing custom CSS separated by two newlines.

#### `GET /settings`
Dumps every Kadence-prefixed theme_mod (header_, footer_, content_, base_,
heading_, buttons_, site_, page_, post_, product_, mobile_, transparent_,
cart_, ajax_, archive_, search_, sidebar_, boxed_, dropdown_, scroll_,
comments_, nav_, custom_, logo_, breadcrumb_) plus
`kadence_global_palette` and `kadence_pro_theme_config`. Use this to get
oriented on a site you don't know.

#### `GET /settings/all`
Every theme_mod. Large. Use sparingly.

### Content

#### `GET /posts`
Filters: `type` (default `post`), `status` (default `any`), `per_page`
(default 20), `page`, `orderby`, `order`, `search`.

#### `GET /posts/{id}` / `POST /posts/{id}`
POST body: `{title, content, excerpt, status, meta: {key: value}}`. All
optional; only what's provided is updated. Each meta key is snapshotted
individually for granular rollback.

#### `POST /posts/create`
Body: `{title, content, excerpt, status, type, parent, slug, featured_image_id, meta}`.
`status` defaults to `draft`, `type` defaults to `post`. For pages, prefer
`/pages/ensure` instead — it's idempotent.

#### `GET /posts/find?slug=mypage&type=page`
Idempotency helper. Returns post info if found, 404 if not. Use this
**before** creating to avoid duplicates.

#### `POST /pages/ensure`
Body: `{slug, title, content, excerpt, status, meta}`. Returns
`{id, url, edit_url, created: true|false}`. The right tool for any page
that's part of the deploy sequence — running it twice is safe.

#### `GET /menus`
All nav menus + their items + the assigned theme locations.

#### `POST /menus/create`
Body: `{name, location}`. The optional `location` (e.g. `primary`) assigns
the new menu via `nav_menu_locations`.

#### `POST /menus/{id}/items`
Body: `{title, url, type, object, object_id, parent}`.
- Custom URL: `{title, url, type: "custom"}`
- Page link: `{title, type: "post_type", object: "page", object_id: <page_id>}`
- Sub-item: add `parent: <parent_item_id>`

### Media

#### `POST /media/upload-from-url`
Body: `{url, title, alt, attach_to}`. Sideloads the remote image into the
WP media library. Returns `{id, url}`. Use the returned `id` for:
- `/posts/{id}` body field `featured_image_id`
- `/woo/products/create` body field `image_id`
- `/theme-mod/custom_logo` body value

#### `GET /media`
Filters: `per_page`, `page`, `mime_type`.

### Kadence

#### `GET /blocks`
Discovery. Every Kadence block registered, with its attribute keys and
supports object. Use to confirm a block name + attributes before
generating block markup.

#### `GET /kadence-pro/config` / `POST /kadence-pro/config`
POST body: `{config: {module_name: bool, ...}}`. Modules:
`conditional_headers`, `elements`, `adv_pages`, `header_addons`, `mega_menu`,
`woocommerce_addons`, `scripts`, `infinite`, `localgravatars`,
`archive_meta`, `dark_mode`. Merged onto existing config (not replaced).

#### `POST /kadence-pro/preset/pod`
One-shot. Enables `header_addons + mega_menu + elements + conditional_headers + woocommerce_addons + scripts`,
disables `dark_mode + infinite`. Use on POD store deploys when Kadence Pro
is active.

#### `GET /header`
Snapshot of the 26 header-related theme_mods. Useful for "show me what the
header looks like right now."

#### `GET /footer`
Snapshot of the 17 footer-related theme_mods.

### WooCommerce (only registered when WC is active)

#### `GET /woo/status`
`{woocommerce_active, kadence_woo_addons, woocommerce_version, currency, currency_symbol, product_count}`.

#### `GET /woo/settings` / `POST /woo/settings`
POST body: `{settings: {key: value, ...}}`. Keys with `woocommerce_`
prefix go to options; everything else goes to theme_mods (via the same
single endpoint). Useful keys:
- `woocommerce_currency`: `"USD"`
- `woocommerce_default_country`: `"US:CA"`
- `product_archive_columns`: `3`
- `product_archive_default_view`: `"grid"`
- `product_archive_image_hover_switch`: `"fade"`
- `cart_pop_show_on_add`: `true` *(Kadence Pro)*
- `product_sticky_add_to_cart`: `true` *(Kadence Pro)*

#### `GET /woo/products`
Filters: `status`, `per_page`, `page`, `category` (slug).

#### `POST /woo/products/create`
Body: `{name, status, description, short_description, regular_price, sale_price, sku, stock_quantity, image_id, categories: [name|id...]}`.
Creates a `WC_Product_Simple`. Variable products (size variants on a
t-shirt, e.g.) need a separate post-create step to set variation meta —
flagged as a future bridge enhancement.

#### `GET /woo/products/{id}` / `POST /woo/products/{id}`
Same body shape as create.

#### `GET /woo/categories` / `POST /woo/categories/create`
Create body: `{name, slug, parent, description}`.

#### `GET /woo/orders`
Filters: `status`, `per_page`, `page`.

### History / rollback

#### `GET /history?limit=50`
Most recent first. Each entry: `{id, timestamp, operation, target, previous, new, context}`.

#### `GET /history/{snapshot_id}`
A single snapshot.

#### `POST /rollback/{snapshot_id}`
Reverts the change. **Supported operations:** `theme_mod_set`, `option_set`,
`palette_set`, `css_set`, `post_update`, `kadence_pro_config_set`,
`kadence_pro_preset_pod`. **Not supported:** `theme_mods_batch_set`,
`post_create`, `page_ensure`, `menu_*`, `media_upload`, `product_create`,
`product_update`, `woo_settings_set`. For unsupported
operations, undo by hand — usually by repeating the original call with the
`previous` values from the snapshot.

---

## Kadence internals (read once, return as needed)

Full coverage in `KADENCE-INTERNALS.md`. The seven points to keep loaded:

### 1. Theme mods are PHP arrays, not JSON strings
Kadence reads via `get_theme_mod($key)` and uses `sub_option()` on the raw
PHP value. Storing a JSON string (which `wp theme mod set` does) breaks
Kadence's reader. The bridge stores values correctly via `set_theme_mod()`
— pass arrays as JSON in the request body and the bridge does the right
thing.

### 2. The palette is the one exception
`kadence_global_palette` is the single Kadence option stored as a
JSON-encoded **string**, not a serialized array. See the palette gotcha
above.

### 3. `kadence_custom_css` option is dead
Kadence used to read CSS from `get_option('kadence_custom_css')`. It
doesn't anymore. The correct surface is WordPress core's custom CSS via
`wp_update_custom_css_post()` / `wp_get_custom_css()`. The bridge's `/css`
endpoint uses the right one. Don't hand-edit `kadence_custom_css` — it
will silently do nothing.

### 4. `--global-content-width` constrains "contained" layouts
Kadence's `site-header-row-layout-contained` is constrained by the CSS
variable `--global-content-width`, set from the `content_width` theme_mod.
If unset, "contained" has nothing to constrain to. Set explicitly:

```bash
curl -s -X POST -u "$BRIDGE_AUTH" \
  -H "Content-Type: application/json" \
  -d '{"value": {"size": 1290, "unit": "px"}}' \
  "$BRIDGE_URL/theme-mod/content_width"
```

### 5. Prefer theme_mods over CSS overrides — never `!important`
For 90% of styling, there's a Kadence theme_mod that does it natively.
Find that mod first. CSS overrides — especially with `!important` —
fight Kadence and break on theme updates. Tools, in priority order:

1. `/theme-mods/batch` — for layout, color, typography, sticky, button
   shape, header/footer rows, mobile breakpoints.
2. `/option/{key}` — for site-wide WP options.
3. `/css` — only for the genuine remainder (custom-built selectors,
   home-only hide rules, mobile clamps that no theme_mod expresses).

If you're reaching for `!important`, stop. Find the theme_mod first. If
the theme_mod doesn't exist, write the CSS without `!important` and use
specificity (`.home .selector` instead of `.selector !important`).

### 6. The `/render` endpoint can lie
`/render` does an internal `wp_remote_get` with a cache-buster query
param. LiteSpeed can still serve a cached response if its cache key
ignores query strings. After every change, verify with an external curl
that mimics a real browser:

```bash
curl -s -A "Mozilla/5.0" "$SITE_URL/path/" | grep 'expected-class'
```

If `/render` and external curl disagree, the cache layer is disagreeing
with itself. Flush, wait a moment, re-verify with external curl.

### 7. Header builder slot keys
The 9 desktop slots: `top-left`, `top-center`, `top-right`, `main-left`,
`main-center`, `main-right`, `bottom-left`, `bottom-center`, `bottom-right`.
Items: `logo`, `navigation`, `button`, `social`, `search`, `html`,
`widget`, `cart`, `mobile-trigger`.

The shape Kadence stores in `header_desktop_items`:

```json
{
  "top":    {"left": [], "left_center": [], "center": [], "right_center": [], "right": []},
  "main":   {"left": ["logo"], "left_center": [], "center": [], "right_center": [], "right": ["navigation","cart"]},
  "bottom": {"left": [], "left_center": [], "center": [], "right_center": [], "right": []}
}
```

Mobile uses `header_mobile_items` with the same shape plus a `popup` array
for hamburger menu items.

---

## The change workflow — no shortcuts

```
1. READ      Use /render or the relevant GET endpoint. See what's there.
2. PLAN      Identify the exact theme_mod / option / post field to change.
3. CHANGE    POST to the bridge. Capture the snapshot_id from the response.
4. FLUSH     POST /cache/flush.
5. VERIFY    External curl with User-Agent. Grep for the expected change.
6. REPORT    Only tell the user it's done after step 5 confirms it.
```

If step 5 fails, do not report success. Either dig into why (cache layer
not flushed, wrong theme_mod key, expected class isn't where you thought)
or roll back via the snapshot_id and try again.

---

## Common recipes

### Change brand color
Read `POD-PALETTES.md` for the current palette templates, swap the
primary/accent hexes, store via the `/option/kadence_global_palette`
workaround above, flush, verify a button color in the rendered HTML.

### Hide page title on a specific page

```bash
PAGE_ID=$(curl -s -u "$BRIDGE_AUTH" "$BRIDGE_URL/posts/find?slug=about&type=page" | jq -r '.id')

curl -s -X POST -u "$BRIDGE_AUTH" \
  -H "Content-Type: application/json" \
  -d '{"meta": {"_kad_post_title": "hide"}}' \
  "$BRIDGE_URL/posts/$PAGE_ID"

curl -s -X POST -u "$BRIDGE_AUTH" "$BRIDGE_URL/cache/flush"

# Verify (expect 0 matches)
curl -s -A "Mozilla/5.0" "$SITE_URL/about/" | grep -c 'page-hero-section'
```

### Set the site logo

```bash
LOGO_ID=$(curl -s -X POST -u "$BRIDGE_AUTH" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/logo.png", "title": "Logo", "alt": "Brand logo"}' \
  "$BRIDGE_URL/media/upload-from-url" | jq -r '.id')

curl -s -X POST -u "$BRIDGE_AUTH" \
  -H "Content-Type: application/json" \
  -d "{\"value\": $LOGO_ID}" \
  "$BRIDGE_URL/theme-mod/custom_logo"

curl -s -X POST -u "$BRIDGE_AUTH" \
  -H "Content-Type: application/json" \
  -d '{"value": {"size": {"desktop": 220}, "unit": {"desktop": "px"}}}' \
  "$BRIDGE_URL/theme-mod/logo_width"

curl -s -X POST -u "$BRIDGE_AUTH" "$BRIDGE_URL/cache/flush"
```

### Add a product

```bash
IMG_ID=$(curl -s -X POST -u "$BRIDGE_AUTH" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://...", "title": "Mockup", "alt": "Product mockup"}' \
  "$BRIDGE_URL/media/upload-from-url" | jq -r '.id')

curl -s -X POST -u "$BRIDGE_AUTH" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"Funny Cat T-Shirt\",
    \"status\": \"publish\",
    \"description\": \"...\",
    \"regular_price\": \"24.99\",
    \"image_id\": $IMG_ID,
    \"categories\": [\"Apparel\"]
  }" \
  "$BRIDGE_URL/woo/products/create"

curl -s -X POST -u "$BRIDGE_AUTH" "$BRIDGE_URL/cache/flush"
```

### Roll back a change

```bash
# snapshot_id was returned in the change response; if you didn't capture it, look it up:
curl -s -u "$BRIDGE_AUTH" "$BRIDGE_URL/history?limit=20" | jq '.entries[] | {id, timestamp, operation, target}'

curl -s -X POST -u "$BRIDGE_AUTH" "$BRIDGE_URL/rollback/mkb_1700000000_abc12345"
```

### Find recent changes (when the user says "you broke X")

```bash
curl -s -u "$BRIDGE_AUTH" "$BRIDGE_URL/history?limit=20" \
  | jq '.entries[] | {time:.timestamp, op:.operation, target:.target}'
```

---

## What to do when the bridge can't do it (SSH escape hatch)

The bridge covers everything you need for day-to-day site building. A
small set of operations are genuinely outside it:

- Installing / activating / deactivating plugins
- Editing PHP files (theme child, mu-plugins, `wp-config.php`, `functions.php`)
- Database export / import / migration
- File operations outside the WP media library
- Server config (`.htaccess` beyond the auth-passthrough the bridge
  manages, `php.ini`, nginx)
- Recovering when the bridge itself is broken

For these, fall back to SSH + WP-CLI. **Tell the user before you SSH in.**
SSH is the escape hatch, not the default — the user is paying for the
bridge specifically so they don't have to read a terminal log. Announce
the operation in plain English ("I'm going to SSH in and install
WooCommerce") and proceed.

### SSH credentials

The student's SSH details should live in `.env` alongside the bridge creds:

```
SSH_USER=u123456789
SSH_HOST=hostname.hostinger.com
SSH_PORT=65002
SSH_KEY=~/.ssh/id_ed25519
WP_PATH=/home/u123456789/domains/yoursite.com/public_html
```

Set a short alias for the session:

```bash
SSH="ssh -i $SSH_KEY -p $SSH_PORT -o StrictHostKeyChecking=no $SSH_USER@$SSH_HOST"
WP="wp --path=$WP_PATH --allow-root"
```

### Common SSH operations

#### Install a plugin
```bash
$SSH "$WP plugin install kadence-blocks --activate"
$SSH "$WP plugin install woocommerce --activate"
$SSH "$WP plugin install seo-by-rank-math --activate"
$SSH "$WP plugin install litespeed-cache --activate"
```

#### Install Kadence theme
```bash
$SSH "$WP theme install kadence --activate"
```

#### Install Mega Kadence Bridge from GitHub Releases (when WP admin upload isn't an option)
```bash
$SSH "cd $WP_PATH/wp-content/plugins && \
  curl -L -o mega-kadence-bridge.zip https://github.com/jonjonesai/mega-kadence-bridge/releases/latest/download/mega-kadence-bridge.zip && \
  unzip -o mega-kadence-bridge.zip && \
  rm mega-kadence-bridge.zip"
$SSH "$WP plugin activate mega-kadence-bridge"
$SSH "cat $WP_PATH/wp-content/.claude-bridge/credentials.json"   # grab .env block
```

#### Set permalinks (on a fresh install — the bridge can't change these)
```bash
$SSH "$WP rewrite structure '/%postname%/' --hard"
$SSH "$WP rewrite flush --hard"
```

#### Back up before a risky change
```bash
$SSH "$WP db export $WP_PATH/backup-$(date +%Y%m%d-%H%M).sql"
```

#### Disaster recovery — bridge is broken
```bash
# Confirm plugin still loaded
$SSH "$WP plugin list --status=active"

# If activation failed, deactivate from CLI
$SSH "$WP plugin deactivate mega-kadence-bridge"

# Re-enable Application Passwords if Hostinger Tools disabled them
$SSH "$WP option update hostinger_disable_app_passwords '' "
$SSH "$WP plugin activate mega-kadence-bridge"

# Read the regenerated credentials
$SSH "cat $WP_PATH/wp-content/.claude-bridge/credentials.json"
```

#### Enable PHP error display while debugging (turn back off after)
```bash
$SSH "$WP config set WP_DEBUG true --raw"
$SSH "$WP config set WP_DEBUG_LOG true --raw"
$SSH "tail -f $WP_PATH/wp-content/debug.log"
# When done:
$SSH "$WP config set WP_DEBUG false --raw"
```

### Hostinger gotchas

| Issue | Fix |
|---|---|
| WP-CLI not in PATH | Use full path: `/usr/local/bin/wp` |
| Hostinger "Disable Application Passwords" enabled | hPanel → WordPress → Tools → off; bridge auto-handles on activate |
| LiteSpeed not purging | `$SSH "$WP litespeed-purge all"` — separate from bridge `/cache/flush` |
| SSH key auth refused | Hostinger requires Ed25519 or RSA 4096; add public key in panel → SSH Keys |
| Memory limit too low | `$SSH "$WP config set WP_MEMORY_LIMIT 256M"` |
| Max upload too small | Add to `.htaccess`: `php_value upload_max_filesize 64M` and `php_value post_max_size 64M` |

### When NOT to use SSH

- Theme settings, content, palette, CSS, products, menus — use the bridge.
- "It's faster via SSH" — no it isn't, and the bridge gives you snapshots.
- "I want to verify the change" — external `curl -A "Mozilla/5.0" $SITE_URL`,
  not SSH.

The rule: SSH for installs, escape hatches, and recovery. Bridge for
everything else.

---

## Diagnosing problems

In order:

1. **Bridge response says `success: false`** — read the `code` and
   `message`. Most common: `missing_value` (you forgot the `value` wrapper),
   `invalid_palette` (palette gotcha), `not_found` (wrong post ID or
   slug).
2. **Auth or 404** — `curl /info` to confirm the plugin is alive and your
   creds work. If `/info` returns 401, the App Password in `.env` is
   stale — regenerate via wp-admin → Users → claude-bot → Application
   Passwords (or deactivate + reactivate the plugin to auto-regenerate).
3. **Write succeeded but page doesn't look different** — `GET /history?limit=5`
   to confirm the write was recorded. Then external-curl the page and
   grep for what you expected. If the page is unchanged, the cache likely
   didn't flush properly — `POST /cache/flush` again, wait 5 seconds,
   re-curl.
4. **Theme_mod write took, no visible effect** — you set the wrong key.
   `GET /settings` and grep for similar keys. Common confusion:
   `header_main_background` vs `header_main_bg`,
   `buttons_background` vs `button_background`. Kadence is consistent —
   `_main` for the middle header row, `_top`/`_bottom` for the others.
5. **`/css` write doesn't appear** — could be a syntax error rejected by
   `wp_update_custom_css_post()`. Read it back via `GET /css` to confirm
   it stored. If not, your CSS has a parse error.
6. **`/render` and external curl disagree** — page cache mismatch. Flush
   again, wait, prefer the external curl as truth.

---

## Files in this skill directory

- `SKILL.md` (this file) — entry point, loaded by Claude Code's skill system
- `INTAKE.md` — the 6-question student wizard with decision rules
- `KADENCE-INTERNALS.md` — deep gotchas, theme_mod data shapes, Kadence
  reader/writer model
- `POD-HOMEPAGE-TEMPLATE.md` — the 5-section homepage block markup as a
  parameterized template (hero, stats, niche imagery, trust row, CTA)
- `POD-PALETTES.md` — light and dark mode palette tables, plus
  brand-color-driven variants
- `POD-STYLES.css` — the small subset of CSS that genuinely can't be
  expressed as theme_mods, ready to be POSTed via `/css`

When deploying a POD store, fetch the relevant files from this directory,
parameterize them with the student's intake answers, and POST the result
via the bridge. The skill is the opinion layer; the bridge stays primitive.

---

## Operating principles (keep these loaded)

- **No SSH. No WP-CLI. No `!important`. No band-aids.** The bridge does
  what it does; if it can't do something, the answer is to extend the
  bridge or ask the user — not work around with shell access.
- **Verify, don't ask.** Never tell the user "please refresh and check."
  Curl the page yourself and grep for the change.
- **Snapshot every change.** Capture every `snapshot_id` you receive
  during a session into a local note. If something looks wrong later,
  you have a precise rollback target.
- **Theme_mods first, CSS last.** If a Kadence setting expresses what you
  want, use it. CSS only for the genuine remainder.
- **Prefer idempotent endpoints.** `/pages/ensure` over `/posts/create`
  for pages, `/posts/find` before any create, `/option/{key}` GET before
  POST when you don't know the current value.
- **One change at a time when you can.** `/theme-mod/{key}` over batch
  when the change matters and might need rollback. Batch only for related
  groups that succeed-or-fail together.

---

*Skill maintained at github.com/jonjonesai/wordpress-kadence-skill — paired
with the Mega Kadence Bridge plugin at github.com/jonjonesai/mega-kadence-bridge.*
