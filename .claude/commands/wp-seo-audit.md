# WordPress SEO Audit Skill (WooCommerce + WP Rocket)

Performs a comprehensive SEO audit on a WordPress/WooCommerce site with WP Rocket caching.

## Usage

```
/wp-seo-audit <URL>
```

**Example:**
```
/wp-seo-audit https://myshop.com
```

---

## Audit Checklist

When invoked, run the following checks against the target URL `$ARGUMENTS`.

### 1. On-Page SEO (Meta Tags)

Fetch the HTML of the target URL and check for:

- `<title>` tag: present, unique, 50–60 characters
- `<meta name="description">`: present, 120–160 characters
- `<meta name="robots">`: must NOT contain `noindex` or `nofollow` on public pages
- Open Graph tags: `og:title`, `og:description`, `og:image`, `og:url`
- Twitter Card tags: `twitter:card`, `twitter:title`, `twitter:description`
- Canonical `<link rel="canonical">`: present and pointing to the correct URL
- `<html lang="...">`: present and set to the site language

Use `curl -s -L -A "Mozilla/5.0" <URL>` to fetch the HTML, then parse with `grep` or `python3`.

**Example commands:**
```bash
HTML=$(curl -s -L -A "Mozilla/5.0" "$URL")
echo "$HTML" | grep -i '<title>'
echo "$HTML" | grep -i 'meta name="description"'
echo "$HTML" | grep -i 'rel="canonical"'
echo "$HTML" | grep -i 'og:title\|og:description\|og:image'
echo "$HTML" | grep -i 'robots'
```

---

### 2. Heading Structure

- One and only one `<h1>` on each page
- Logical hierarchy: H1 > H2 > H3 (no skipping levels)
- H1 contains the primary keyword

```bash
echo "$HTML" | grep -oi '<h[1-6][^>]*>.*</h[1-6]>' | head -20
```

---

### 3. Image SEO

- All `<img>` tags have a non-empty `alt` attribute
- Image filenames are descriptive (no `img001.jpg`)
- Images are served in modern format (WebP preferred)

```bash
echo "$HTML" | grep -oi '<img [^>]*>' | grep -v 'alt="[^"]\+' | wc -l
```

Report the count of images missing `alt` text.

---

### 4. WP Rocket Cache Headers

Check HTTP response headers to verify WP Rocket is active and caching correctly:

```bash
HEADERS=$(curl -s -I -L -A "Mozilla/5.0" "$URL")
echo "$HEADERS"
```

Look for:
- `X-Cache: HIT` or `X-WP-CF-Super-Cache` — confirms cache is served
- `Cache-Control: max-age=...` — caching duration
- `Vary: Accept-Encoding` — compression negotiation
- `Content-Encoding: gzip` or `br` — GZIP/Brotli compression active
- `X-Rocket-Nginx-Serving-Static` — static file served by Nginx (if applicable)
- Absence of `X-Cache: MISS` on repeated requests (indicates cache warming needed)

**Expected headers when WP Rocket is working:**
```
Cache-Control: max-age=31536000
Content-Encoding: gzip
X-Cache: HIT
```

---

### 5. robots.txt

```bash
curl -s "$BASE_URL/robots.txt"
```

Check:
- File is accessible (HTTP 200)
- Contains `Sitemap:` directive pointing to sitemap
- Does NOT block critical paths (`/wp-content/`, `/wp-includes/` should NOT be disallowed for assets)
- Blocks admin paths: `Disallow: /wp-admin/`

---

### 6. XML Sitemap

```bash
curl -s "$BASE_URL/sitemap.xml" | head -50
curl -s "$BASE_URL/sitemap_index.xml" | head -50
```

Check:
- Sitemap is accessible (HTTP 200)
- Contains product URLs (WooCommerce) and page URLs
- Is referenced in robots.txt
- No `noindex` pages are included in the sitemap
- Last modified dates are recent

For WooCommerce, verify presence of product/category sitemaps:
- `/product-sitemap.xml`
- `/product-category-sitemap.xml`

---

### 7. Structured Data / Schema Markup

```bash
echo "$HTML" | python3 -c "
import sys, json, re
html = sys.stdin.read()
schemas = re.findall(r'<script[^>]*type=[\"'\''']application/ld\+json[\"'\''][^>]*>(.*?)</script>', html, re.DOTALL)
for s in schemas:
    try:
        data = json.loads(s)
        print(json.dumps(data, indent=2))
    except:
        print('Invalid JSON-LD:', s[:100])
"
```

Expected schema types:
- **Home page**: `Organization`, `WebSite` (with `SearchAction` for sitelinks searchbox)
- **Product pages** (WooCommerce): `Product` with `offers`, `aggregateRating`, `brand`
- **Category pages**: `BreadcrumbList`
- **Blog posts**: `Article` or `BlogPosting`

Validate the extracted JSON-LD at: https://validator.schema.org/

---

### 8. Page Speed & Core Web Vitals

Use the PageSpeed Insights API (no key needed for basic checks):

```bash
curl -s "https://www.googleapis.com/pagespeedonline/v5/runPagespeed?url=$(python3 -c 'import urllib.parse,sys; print(urllib.parse.quote(sys.argv[1]))' "$URL")&strategy=mobile" | python3 -c "
import sys, json
data = json.load(sys.stdin)
cats = data.get('lighthouseResult', {}).get('categories', {})
audits = data.get('lighthouseResult', {}).get('audits', {})
print('=== Lighthouse Scores ===')
for k, v in cats.items():
    print(f'{k}: {round(v[\"score\"]*100)}/100')
print()
print('=== Core Web Vitals ===')
for metric in ['first-contentful-paint','largest-contentful-paint','total-blocking-time','cumulative-layout-shift','speed-index']:
    a = audits.get(metric, {})
    print(f'{a.get(\"title\",metric)}: {a.get(\"displayValue\",\"N/A\")} ({a.get(\"score\",\"?\")})')
"
```

**Target scores for WP Rocket optimized sites:**
| Metric | Target |
|--------|--------|
| Performance | ≥ 90 |
| LCP | < 2.5s |
| FID/TBT | < 200ms |
| CLS | < 0.1 |
| FCP | < 1.8s |

---

### 9. WooCommerce-Specific SEO Checks

For product pages, additionally check:

```bash
PRODUCT_URL="$BASE_URL/shop"  # Adjust to actual product URL
PROD_HTML=$(curl -s -L -A "Mozilla/5.0" "$PRODUCT_URL")
```

- **Product title**: present in `<h1>` and `og:title`
- **Price**: visible in page (not hidden behind JS)
- **Breadcrumbs**: present (`<nav class="woocommerce-breadcrumb">` or equivalent)
- **Product description**: present and not empty
- **Add-to-cart button**: present (not blocked by caching)
- **Product schema**: contains `@type: Product` with `price`, `availability`, `sku`

---

### 10. Internal Linking & Crawlability

```bash
echo "$HTML" | grep -oi 'href="[^"]*"' | grep -v 'http' | sort -u | head -30
```

Check:
- Internal links use relative or absolute same-domain URLs
- No broken internal links (HTTP 404/500)
- No `nofollow` on important internal links
- Pagination uses `<link rel="next">` / `<link rel="prev">` or `?page=N` pattern

---

### 11. WP Rocket Minification & Deferral

Inspect the HTML source for signs of WP Rocket optimization:

```bash
# Check for minified CSS/JS filenames
echo "$HTML" | grep -oi 'src="[^"]*\.min\.\(js\|css\)\|/cache/min/[^"]*"' | head -10

# Check for deferred/async scripts
echo "$HTML" | grep -oi '<script[^>]*defer\|<script[^>]*async' | wc -l

# Check for lazy-loaded images
echo "$HTML" | grep -oi 'loading="lazy"\|data-lazy-src' | wc -l
```

Expected signs when WP Rocket is active:
- CSS/JS files served from `/wp-content/cache/min/`
- External scripts have `defer` or `async` attributes
- Images below the fold have `loading="lazy"`

---

## Output Format

Produce a structured audit report with this format:

```
============================================================
  WordPress SEO Audit Report
  URL: <URL>
  Date: <date>
============================================================

[PASS] Meta title: "My Shop - Best Products Online" (42 chars)
[PASS] Meta description: present (148 chars)
[WARN] Canonical: missing on homepage
[FAIL] robots.txt: blocks /wp-content/ (breaks WP Rocket assets)

[PASS] WP Rocket: Cache-Control max-age detected
[PASS] WP Rocket: GZIP compression active
[FAIL] WP Rocket: X-Cache: MISS on second request (caching not working)

[PASS] Sitemap: accessible at /sitemap_index.xml
[PASS] Sitemap: product-sitemap.xml found
[WARN] Sitemap: not referenced in robots.txt

[PASS] Schema: Product schema found with price and availability
[WARN] Schema: aggregateRating missing (add customer reviews)

[PASS] Images: all 12 images have alt text
[WARN] Performance: LCP 3.2s (target < 2.5s)
[FAIL] Performance: CLS 0.25 (target < 0.1)

============================================================
  Summary: 8 PASS | 3 WARN | 2 FAIL
  Priority fixes:
  1. Fix CLS issues (likely caused by images without dimensions)
  2. Fix robots.txt to unblock WP Rocket cache assets
  3. Add canonical tag to homepage
============================================================
```

Use `[PASS]` (green), `[WARN]` (yellow), `[FAIL]` (red) indicators.
Always end with a prioritized list of fixes.
