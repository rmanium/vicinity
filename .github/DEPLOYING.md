# Deploying the theme

Merging to `main` deploys. Nobody uploads theme files by hand.

## What happens on a merge

The **Deploy theme** workflow (`.github/workflows/deploy.yml`) runs
`.github/scripts/deploy.py deploy`:

1. Pulls the live theme and works out the release. Theme-editor work on the live
   theme (homepage sections, settings, header/footer, editor-made templates) is
   kept; code from git replaces the old code. If the same file changed in both
   places and can't be merged, the deploy stops and nothing changes in the store.
2. Duplicates the live theme as **`Vicinity release <date> <time> <commit>`** and
   uploads the release onto the copy. Duplicating keeps the French theme
   translations, which a freshly uploaded theme would lose.
3. Opens the home page, `/fr`, a collection, a product, the cart and search on the
   copy through its preview link. Any error, or a page not rendered by the new
   theme, stops the deploy before customers see anything.
4. Publishes the copy and repeats the checks on the live site. If they fail, it
   switches straight back to the previous theme.
5. Tags the commit (`release-…`) and commits anything it took from the live theme
   back to `main`, so git matches what customers see.
6. Keeps the 5 newest releases (live included) and deletes older
   `Vicinity release …` themes. Themes with other names are never touched.

Pull requests get **Theme Check** and a **deploy plan** that lists exactly what a
merge would ship.

## Rolling back

Both ways take effect immediately:

- **GitHub:** Actions → **Roll back theme** → Run workflow. With no input it
  publishes the theme that was live before the current release.
- **Shopify admin:** Online Store → Themes → the previous `Vicinity release …`
  (or "Vicinity 2.0") → Publish.

Theme-editor changes made on the release you roll back from stay on that theme;
they don't move to the one you switch to.

## Rules for the team

- Keep using the theme editor on the live theme as usual. Deploys keep that work.
- Don't edit code in the admin code editor. Change code in git and merge.
- Don't edit the `vicinity/main` theme. It is connected to GitHub, so Shopify
  commits its theme-editor changes to `main`, and the next deploy ships them.
  Disconnecting it from GitHub (Themes → `vicinity/main` → ⋯) removes the risk.
- Preview a release before it goes live from the link the workflow prints, or by
  running the workflow script with `--stage-only` locally.

## Setup (once)

1. In Shopify admin install the **Theme Access** app (by Shopify) and create a
   password for the person who maintains deploys. It arrives by email.
2. In GitHub: Settings → Secrets and variables → Actions → New repository secret,
   name `SHOPIFY_CLI_THEME_TOKEN`, value: that password.

`BOOTSTRAP_BASE_SHA` in the workflows is the commit the original "Vicinity 2.0"
theme was built from. It is only used while that theme is live.
