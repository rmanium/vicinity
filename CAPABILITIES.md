# Live theme capabilities → Trade

Inventory of what the live **Warehouse** theme (`vicinity/main`) actually does,
mapped against **Trade 16.0.0**. Tick what you want and I'll build it.

Nothing here is implemented yet — the branch is currently stock Trade plus
brand colours, fonts, tracking tags, the Persian webfont and `robots.txt`.

## A. Native in Trade — drop-in, low risk

Configuration only. No custom code, nothing that can break layout.

| # | Capability | How it's done in Trade |
| --- | --- | --- |
| A1 | Mega menu | `header` → `menu_type_desktop: mega` (links only — no images) |
| A2 | Sticky header | `header` → `sticky_header_type` |
| A3 | Country + language selectors | header / footer settings |
| A4 | Announcement bar, rotating | `announcement-bar` blocks + `auto_rotate` |
| A5 | Predictive search | `predictive-search` + `predictive_search_enabled` |
| A6 | Cart as page / drawer / notification | `cart_type` (live theme uses page) |
| A7 | Cart notes | `show_cart_note` |
| A8 | Pickup / store availability | `pickup-availability` |
| A9 | Product recommendations | `related-products` |
| A10 | Quick add / quick buy | `quick_add` on product grids |
| A11 | Colour swatches | `variant_picker` → `swatch_shape` |
| A12 | Sale + sold-out badges | `badges` settings (already mapped to brand red) |
| A13 | Star ratings on cards | `show_rating` — needs Judge.me, which you have |
| A14 | Newsletter | `newsletter` section + footer newsletter |
| A15 | Blog posts ("Vicinity Voice") | `featured-blog` |
| A16 | FAQ accordions | `collapsible-content` |
| A17 | Category tiles | `collection-list` or `multicolumn` |
| A18 | Hero / slideshow | `image-banner`, `slideshow` |
| A19 | Delivery-window columns | `multicolumn` |
| A20 | Rich text / catering CTA | `rich-text` |
| A21 | Video | `video` |
| A22 | Featured collection / product | `featured-collection`, `featured-product` |
| A23 | Contact form | `contact-form` |
| A24 | Payment icons | footer `payment_enable` |
| A25 | Custom Liquid escape hatch | `custom-liquid` |
| A26 | App blocks (Judge.me, Fether, Trust Badges) | `apps` + `@app` blocks |
| A27 | Logo list | `multicolumn` |
| A28 | Image with text / multirow | `image-with-text`, `multirow` |

## B. Needs custom work — no Trade equivalent

Each is a real build. Worth deciding case by case.

| # | Capability | Effort | Note |
| --- | --- | --- | --- |
| B1 | Free-shipping progress bar ($55) | Medium | Custom snippet in cart + drawer |
| B2 | Scheduled promo popup | Medium | Trade's `popups` settings only style built-in dialogs — there is no marketing popup section. App may be cheaper |
| B3 | Exit-intent popup | Medium | Same as above |
| B4 | Recently viewed products | Medium | Custom section, localStorage-driven |
| B5 | Mobile-specific hero image | Small | Custom section, or art-directed CSS |
| B6 | Phone + email in header | Small | Or put them in the announcement bar (free) |
| B7 | Mega menu images | Medium | Trade's mega menu is links only |
| B8 | Survey modal | Medium | Old one used jQuery + dead `ga()`; would be rebuilt |
| B9 | Map section | Small | Or embed via `custom-liquid` |
| B10 | Promotion list / countdown | Medium | Or an app |
| B11 | Team page | Small | `multicolumn` gets ~90% there |
| B12 | LinkedIn link | Small | No field in Trade; footer text block works |

## C. Content to re-port (was built, now parked)

Already written and validated on `backup/vicinity-2026-full-port`.
Reusable as-is once the pipeline is proven.

| # | Item | Detail |
| --- | --- | --- |
| C1 | Homepage | 11 sections: hero, delivery windows, category tiles, café banner, Judge.me ×2, blog, catering |
| C2 | Product page | Judge.me + Trust Badges + Fether app blocks |
| C3 | FAQ page | 11 Q&As in 4 groups |
| C4 | Contact page | Store info + form |
| C5 | 13 category landing pages | persian-food, pantry, bakery, beverages, … |
| C6 | Collection templates | brand / brands / all-collections2 |
| C7 | Header + footer | Announcement bar, mega menu, footer blocks |
| C8 | page.surprise | VCafé redemption card |

## D. New in Trade, not in Warehouse

Free if you want them — Trade is Shopify's B2B theme.

| # | Capability |
| --- | --- |
| D1 | Quick order list (`quick-order-list`) |
| D2 | Bulk quick order list (`bulk-quick-order-list`) — volume pricing, quantity rules |
| D3 | Cart drawer with free-gift / collection upsell slot |
| D4 | Reveal-on-scroll + hover animations |
| D5 | Native colour/image swatches on collection filters |

## Deploy note

A theme swap **cannot** ship through the Shopify GitHub integration: it never
overwrites `config/settings_data.json`, and it never deletes removed files.
Use `shopify theme push` (a true sync) to a clean theme instead.
