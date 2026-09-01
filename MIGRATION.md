# Warehouse → Trade migration (`feature/vicinity-2026`)

Vicinity Mart has moved off **Warehouse 2.3.1** (Maestrooo, paid, Vintage-era)
onto **Trade 16.0.0** (Shopify, free, Online Store 2.0).

## Base: genuine Trade 16.0.0 ✅

The base is real Trade source, pulled from the store:

```
shopify theme pull --store=vicinity-mart.myshopify.com --theme=193517289766
```

Trade turns out to be a **Dawn sibling**: comparing Trade 16.0.0 against
[Dawn 16.0.0](https://github.com/Shopify/dawn) (both released 2026-08-10), every file in
`assets/`, `snippets/`, `layout/` and all 48 `sections/*.liquid` is **byte-identical**.
They differ only in:

- `config/settings_schema.json` — theme name, and Trade drops Dawn's `customer_account_menu`
- `config/settings_data.json` — Trade's own preset (warm neutrals, DM Sans / Jost)
- `sections/{header,footer}-group.json` and the 12 default `templates/*.json` — default content
- `locales/*` — Trade-specific schema strings

Practically: **Trade is Dawn with a different paint job.** Anything written against Dawn's
section API works unchanged here, and the theme could be re-based onto Dawn or another
Dawn-family theme with no template rework.

## The Vicinity layer (re-apply after any base swap)

| File | Purpose |
| --- | --- |
| `config/settings_data.json` | Brand colours, Ubuntu type, logo, favicon, cart + social settings |
| `sections/header-group.json` | Announcement bar + header |
| `sections/footer-group.json` | Footer blocks (about / quick links / contact) |
| `templates/index.json` | Homepage |
| `templates/product.json` | Product page incl. Judge.me, Trust Badges, Fether app blocks |
| `templates/page.faq.json` | 11 Q&As across 4 groups |
| `templates/page.contact.json` | Store info + contact form |
| `templates/page.*.json` (13) | Category landing pages |
| `templates/robots.txt.liquid` | Custom robots rule (`Disallow: /*.atom`) |
| `snippets/vicinity-head.liquid` | GA4, Meta Pixel, Google site verification |
| `snippets/vicinity-body-end.liquid` | HubSpot |
| `assets/vicinity-custom.css` | Samim Persian webfont + `.persian-text` |
| `assets/Samim.{woff2,woff,ttf}` | Persian webfont files |
| `layout/theme.liquid` | 3 injection lines (see `grep -n vicinity layout/theme.liquid`) |

## Brand mapping

Warehouse used flat colour settings; Trade uses **colour schemes**.

| Scheme | Background | Text | Button | Used for |
| --- | --- | --- | --- | --- |
| `scheme-1` | `#ffffff` | `#121251` | `#ed1c24` | Default page |
| `scheme-2` | `#f6f6f8` | `#121251` | `#ed1c24` | Cards, soft bands |
| `scheme-3` | `#121251` | `#ffffff` | `#ed1c24` | Footer, newsletter, banner overlays |
| `scheme-4` | `#ed1c24` | `#ffffff` | `#ffffff` | Announcement bar, sale badges |
| `scheme-5` | `#ebebf1` | `#121251` | `#121251` | Muted, sold-out badges |

Type: `ubuntu_n7` headings / `ubuntu_n5` body, `body_scale: 106` (≈17px, matching Warehouse).

## Apps

Decision: **keep Judge.me, Fether Frequently Bought, SEOWill Trust Badges, and the product labels.**

| App | Status |
| --- | --- |
| Judge.me Reviews | ✅ Ported — review widget on `product.json`, featured carousel + medals on `index.json` |
| Fether Frequently Bought | ✅ Ported — upsell widget and related-products widget on `product.json` |
| SEOWill Trust Badges | ✅ Ported — star-rating block on `product.json` |
| BSS Product Labels | ⚠️ Needs app embed (see below) |
| SCM / Secomapp Product Labels | ⚠️ Needs app embed — **and was already broken** (see below) |
| HubSpot | ✅ Ported via `snippets/vicinity-body-end.liquid` |

### Why the label apps could not be copied across

Their Warehouse code is theme-coupled and cannot be lifted as-is:

- **BSS** hardcoded `storeId 23301` plus CSS targeting `.homepage-slideshow .slick-slide` —
  Warehouse's Slick carousel, which does not exist in Trade.
- **SCM** reads `settings.scm_pl_piregex`, `settings.scm_pl_lppath` and friends. Those settings
  appear **nowhere in Warehouse's own `settings_schema.json`** — so this app's code was already
  dead on the live site. Worth confirming whether the app is still subscribed at all before
  spending time on it.

Both vendors ship **app embeds** for Online Store 2.0, which is the supported path:

> Shopify admin → Online Store → Themes → (Trade) → Customize → **App embeds** → toggle on.

App embeds are stored in `config/settings_data.json` under `current.blocks` and will appear in
this branch automatically once enabled, so no manual file editing is needed.

## Deliberately dropped

| Dropped | Why |
| --- | --- |
| GemPages + PageFly templates/assets (~15 files) | Confirmed drop — affected pages fall back to the default page template, so body content still renders and only the builder layouts are lost |
| `layout/theme.dmr-backup-*.liquid` (4) | Stale app-generated backups from Aug 2022 |
| `templates/customers/*` (7) | Trade uses Shopify's new customer accounts |
| `page.team.json` | Placeholder content only (`john@test.com`) |
| `page.products-2`, `page.special-offers` | All collection blocks empty/disabled |
| `page.all-products` custom-liquid block | Placeholder ("Write or copy/paste Liquid code") |
| Placeholder homepage sections | Empty `apps` sections, "Slide title / Tell your story" slideshows |
| jQuery 1.9.1 + Slick carousel | Trade sections are dependency-free |
| `assets/custom.js` | Used dead `ga()` (Universal Analytics), jQuery, and a survey modal |
| `snippets/tiny-script-control.liquid` | Deferred `content_for_header` — unsafe and unnecessary |

## Known gaps

1. **Mobile hero image** — Warehouse's slideshow had a separate `mobile_image`; Trade has no mobile variant.
2. **Recently viewed products** — no Trade equivalent.
3. **Hero CTAs** — original banners linked the whole image with no button label; Trade needs a
   labelled button, so "Shop all groceries" / "Order café & ready meals" were added.
4. **"Delivery made simple"** had a shipping-policy link but a blank button label, so it never
   rendered a button on the live site. Ported faithfully as a heading only.
5. **Free-shipping threshold ($55)** — Warehouse had a progress bar; Trade has none.
6. **LinkedIn** — Trade has no LinkedIn social field.
7. **Header phone/email** — unsupported in Trade's header; phone moved to the announcement bar.
8. **Mega menu images** — Warehouse's mega menu had image blocks; Trade's is links only.
9. **Popups** — Warehouse's scheduled promo + exit-intent popups have no Trade equivalent.

## Still to do

- [ ] Enable BSS / SCM label app embeds on the new theme (and confirm SCM is still needed)
- [ ] Rebuild the two popups (scheduled promo + exit intent)
- [ ] Verify GA4 / Meta Pixel aren't double-firing via Customer Events
- [ ] Confirm `main-menu-1` and `home-footer` menu handles still exist
- [ ] Preview and QA, then publish

## Preview

```
shopify theme dev --store=vicinity-mart.myshopify.com
```

The branch is also connected to theme `vicinity/feature/vicinity-2026` (#193517519142)
via the Shopify GitHub integration, so pushing this branch deploys to that unpublished theme.
