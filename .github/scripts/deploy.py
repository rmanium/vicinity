#!/usr/bin/env python3
"""Blue-green deploys of the Vicinity Mart theme to Shopify.

Every deploy duplicates the live theme as "Vicinity release <UTC date> <time>
<sha>", uploads the release onto that copy, checks it through a preview link,
publishes it and checks the live site. The theme that was live stays in the
store untouched, so rolling back is publishing it again: run the Rollback
workflow, or press Publish on it under Online Store > Themes.

Duplicating (rather than uploading into a fresh theme) matters: Shopify keeps
translations of theme content (e.g. the French announcement bar) per theme,
and only a duplicate carries them over.

The live theme also holds the team's theme-editor work (settings_data.json,
JSON templates, header/footer groups) that never passes through git, so each
deploy three-way merges every theme file:

  base  the commit the live theme was built from (the sha in its name)
  git   the commit being deployed
  live  what is on the live theme right now

A file changed on one side only takes that side. A file changed on both
sides is merged key by key (JSON) or line by line (git merge-file); if it
still clashes the deploy stops before touching the store. Whatever the
release takes from live is committed back to git, so git keeps up with what
customers see.

Usage:
  deploy.py deploy [--dry-run | --stage-only]
  deploy.py rollback [--theme-id ID]
"""

import argparse
import datetime
import http.cookiejar
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

STORE = os.environ.get('SHOPIFY_FLAG_STORE', 'vicinity-mart.myshopify.com')
STOREFRONT = os.environ.get('STOREFRONT_URL', 'https://vicinitymart.com').rstrip('/')
SHOPIFY = os.environ.get('SHOPIFY_BIN', 'shopify')
# Commit the original "Vicinity 2.0" theme matches; used while it is live.
BOOTSTRAP_BASE_SHA = os.environ.get('BOOTSTRAP_BASE_SHA', '')
KEEP_RELEASES = int(os.environ.get('KEEP_RELEASES', '5'))
SMOKE_PATHS = [p for p in os.environ.get('SMOKE_PATHS', '/,/fr,/collections/all,/cart,/search?q=rice').split(',') if p]

RELEASE_PREFIX = 'Vicinity release '
RELEASE_NAME = re.compile(r'^Vicinity release \d{4}-\d{2}-\d{2} \d{4} ([0-9a-f]{7,40})$')
THEME_DIRS = ('assets', 'blocks', 'config', 'layout', 'locales', 'sections', 'snippets', 'templates')
REPO = Path(__file__).resolve().parents[2]
MISSING = object()


class Clash(Exception):
    pass


class SmokeFailure(Exception):
    pass


def log(message=''):
    print(message, flush=True)


def fail(message):
    log(f'::error::{message}' if os.environ.get('GITHUB_ACTIONS') else f'ERROR: {message}')
    sys.exit(1)


# --- command helpers --------------------------------------------------------

def run(cmd, binary=False, check=True, cwd=REPO):
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=not binary)
    if check and result.returncode != 0:
        out = result.stdout if not binary else result.stdout.decode(errors='replace')
        err = result.stderr if not binary else result.stderr.decode(errors='replace')
        fail(f'`{" ".join(map(str, cmd))}` failed:\n{out}\n{err}')
    return result


def git(*args, binary=False, check=True):
    return run(['git', *args], binary=binary, check=check).stdout


def shopify(*args):
    return run([SHOPIFY, 'theme', *args, '--store', STORE]).stdout


def json_output(text):
    start = min((i for i in (text.find('['), text.find('{')) if i >= 0), default=-1)
    if start < 0:
        fail(f'Expected JSON from the Shopify CLI, got:\n{text}')
    return json.loads(text[start:])


def list_themes():
    return json_output(shopify('list', '--json'))


def live_theme(themes):
    live = [t for t in themes if t['role'] == 'live']
    if len(live) != 1:
        fail(f'Expected exactly one live theme, found {len(live)}.')
    return live[0]


def publish(theme):
    log(f'Publishing {theme["name"]} (#{theme["id"]})...')
    shopify('publish', '--theme', str(theme['id']), '--force')


# --- three-way merge --------------------------------------------------------

def parse_json(data):
    text = data.decode('utf-8-sig')
    text = re.sub(r'\A\s*/\*.*?\*/', '', text, flags=re.S)  # Shopify's "auto-generated" banner
    return json.loads(text)


def same(path, a, b):
    if a is None or b is None:
        return a is b
    if a == b:
        return True
    if path.endswith('.json'):
        try:
            return parse_json(a) == parse_json(b)
        except ValueError:
            return False
    return a.replace(b'\r\n', b'\n') == b.replace(b'\r\n', b'\n')


def merge_values(base, ours, theirs, where):
    if ours == theirs:
        return ours
    if ours == base:
        return theirs
    if theirs == base:
        return ours
    if isinstance(ours, dict) and isinstance(theirs, dict):
        base = base if isinstance(base, dict) else {}
        merged = {}
        for key in list(ours) + [k for k in theirs if k not in ours]:
            value = merge_values(base.get(key, MISSING), ours.get(key, MISSING), theirs.get(key, MISSING), f'{where}.{key}')
            if value is not MISSING:
                merged[key] = value
        return merged
    raise Clash(where)


def merge_both_sides(path, base, ours, theirs):
    """Merge a file changed in git and on live. Returns bytes or raises Clash."""
    if ours is None or theirs is None:
        raise Clash(f'{path}: deleted on one side, changed on the other')
    if path.endswith('.json'):
        try:
            merged = merge_values(parse_json(base) if base is not None else MISSING,
                                  parse_json(ours), parse_json(theirs), path)
        except ValueError as error:
            raise Clash(f'{path}: not valid JSON ({error})')
        return (json.dumps(merged, indent=2, ensure_ascii=False) + '\n').encode()
    if b'\0' in ours or b'\0' in theirs:
        raise Clash(f'{path}: binary file changed on both sides')
    with tempfile.TemporaryDirectory() as tmp:
        files = []
        for name, data in (('ours', ours), ('base', base or b''), ('theirs', theirs)):
            file = Path(tmp) / name
            file.write_bytes(data)
            files.append(str(file))
        result = run(['git', 'merge-file', '-p', *files], binary=True, check=False)
    if result.returncode != 0:
        raise Clash(f'{path}: overlapping edits')
    return result.stdout


def plan(base, live_dir):
    """Work out the release: which files must differ from the deployed commit."""
    base_files = set(git('ls-tree', '-r', '--name-only', base, '--', *THEME_DIRS).splitlines())
    head_files = set(git('ls-files', '--', *THEME_DIRS).splitlines())
    live_files = {p.relative_to(live_dir).as_posix()
                  for d in THEME_DIRS if (live_dir / d).is_dir()
                  for p in (live_dir / d).rglob('*') if p.is_file()}

    overrides = {}  # path -> bytes, or None to delete; applied on top of the commit
    report = {'from_git': [], 'from_live': [], 'merged': [], 'clashes': []}
    for path in sorted(base_files | head_files | live_files):
        b = git('show', f'{base}:{path}', binary=True) if path in base_files else None
        o = (REPO / path).read_bytes() if path in head_files else None
        t = (live_dir / path).read_bytes() if path in live_files else None

        if same(path, o, t):
            continue
        if same(path, o, b):
            overrides[path] = t
            report['from_live'].append(path)
        elif same(path, t, b):
            report['from_git'].append(path)
        else:
            try:
                overrides[path] = merge_both_sides(path, b, o, t)
                report['merged'].append(path)
            except Clash as clash:
                report['clashes'].append(str(clash))
    return overrides, report


def print_report(report):
    labels = {
        'from_git': 'Changed in git (shipping now)',
        'from_live': 'Changed on the live theme only (kept, and synced back to git)',
        'merged': 'Changed in both places, merged',
        'clashes': 'Changed in both places, could not merge',
    }
    for key, label in labels.items():
        if report[key]:
            log(f'{label}:')
            for item in report[key]:
                log(f'  {item}')


# --- release steps ----------------------------------------------------------

def base_commit(live):
    match = RELEASE_NAME.match(live['name'])
    sha = match.group(1) if match else BOOTSTRAP_BASE_SHA
    if not sha:
        fail(f'Live theme "{live["name"]}" was not made by this pipeline and BOOTSTRAP_BASE_SHA is not set, '
             'so there is no base to merge the theme-editor changes against.')
    full = git('rev-parse', '--verify', '--quiet', f'{sha}^{{commit}}', check=False).strip()
    if not full:
        fail(f'Commit {sha} (what the live theme was built from) is not in this checkout. '
             'Fetch the full history and tags.')
    return full


def commit_sync(overrides, live):
    """Write what the release takes from live into git; returns the release commit."""
    if not overrides:
        return git('rev-parse', 'HEAD').strip()
    for path, data in overrides.items():
        file = REPO / path
        if data is None:
            git('rm', '--quiet', '--', path)
        else:
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_bytes(data)
            git('add', '--', path)
    git('commit', '--quiet', '-m',
        f'chore: sync theme editor changes from "{live["name"]}" [skip ci]\n\n'
        'Picked up by the deploy workflow so git matches the release it published.')
    return git('rev-parse', 'HEAD').strip()


def export_tree(commit, target):
    target.mkdir(parents=True)
    archive = run(['git', 'archive', '--format=tar', commit, '--', *THEME_DIRS], binary=True).stdout
    extract = subprocess.run(['tar', '-x', '-C', str(target)], input=archive, capture_output=True)
    if extract.returncode != 0:
        fail(f'Could not unpack the release: {extract.stderr.decode(errors="replace")}')


def wait_until_ready(theme_id, timeout=600):
    deadline = time.time() + timeout
    while time.time() < deadline:
        theme = next((t for t in list_themes() if t['id'] == theme_id), None)
        if theme and not theme.get('processing'):
            return
        time.sleep(10)
    fail(f'Theme #{theme_id} was still processing after {timeout // 60} minutes.')


def stage(name, live, release_dir):
    """Duplicate the live theme and make the copy match the release."""
    log(f'Duplicating the live theme as "{name}"...')
    theme = json_output(shopify('duplicate', '--theme', str(live['id']), '--name', name, '--force', '--json'))['theme']
    wait_until_ready(theme['id'])
    # A full push mirrors the release: only changed files are uploaded, and files
    # the release no longer has are removed from the copy.
    log('Uploading the release onto the copy (Theme Check must pass)...')
    run([SHOPIFY, 'theme', 'push', '--store', STORE, '--theme', str(theme['id']),
         '--strict', '--path', str(release_dir)])
    log(f'Staged #{theme["id"]}. Preview: {STOREFRONT}/?preview_theme_id={theme["id"]}')
    return theme


def tag_release(commit, name, theme, previous):
    stamp = name.removeprefix(RELEASE_PREFIX).rsplit(' ', 1)[0].replace('-', '').replace(' ', '-')
    tag = f'release-{stamp}-{commit[:7]}'
    git('tag', '-a', tag, commit, '-m',
        f'{name}\n\ntheme_id={theme["id"]}\nprevious_theme_id={previous["id"]}\nprevious_theme_name={previous["name"]}')
    git('push', '--quiet', 'origin', f'refs/tags/{tag}')
    return tag


def push_sync_commit(release_commit, deployed_from, tag):
    if release_commit == deployed_from:
        return
    pushed = run(['git', 'push', '--quiet', 'origin', f'{release_commit}:refs/heads/main'], check=False)
    if pushed.returncode == 0:
        log('Pushed the sync commit to main.')
        return
    branch = f'sync/{tag}'
    git('push', '--quiet', 'origin', f'{release_commit}:refs/heads/{branch}')
    log(f'main moved during the deploy, so the sync commit is on branch {branch}.')
    if os.environ.get('GH_TOKEN'):
        run(['gh', 'pr', 'create', '--base', 'main', '--head', branch,
             '--title', f'Sync theme editor changes from {tag}',
             '--body', 'The deploy workflow took these files from the live theme. Merge to keep git in step.'],
            check=False)


def prune(keep):
    """Delete old release themes, keeping the newest `keep` (live included)."""
    themes = list_themes()
    releases = sorted((t for t in themes if RELEASE_NAME.match(t['name']) and t['role'] != 'live'),
                      key=lambda t: t['name'], reverse=True)
    for theme in releases[max(keep - 1, 0):]:
        log(f'Removing old release {theme["name"]} (#{theme["id"]})')
        shopify('delete', '--theme', str(theme['id']), '--force')


# --- smoke tests ------------------------------------------------------------

def fetch(opener, url):
    request = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Vicinity deploy check)'})
    try:
        with opener.open(request, timeout=30) as response:
            return response.status, response.read().decode('utf-8', errors='replace')
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode('utf-8', errors='replace')
    except (urllib.error.URLError, TimeoutError) as error:
        return 0, str(error)


def smoke(theme_id, preview, attempts=6):
    """Load key pages and confirm they render with this theme and without Liquid errors."""
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    paths = list(SMOKE_PATHS)
    status, body = fetch(opener, f'{STOREFRONT}/products.json?limit=1')
    try:
        products = json.loads(body).get('products') or [] if status == 200 else []
    except ValueError:
        products = []
    if products:
        paths.append(f'/products/{products[0]["handle"]}')

    problems = []
    for path in paths:
        for attempt in range(attempts):
            joiner = '&' if '?' in path else '?'
            extra = f'preview_theme_id={theme_id}' if preview else f'deploy_check={int(time.time())}'
            status, body = fetch(opener, f'{STOREFRONT}{path}{joiner}{extra}')
            rendered_by = re.search(r'Shopify\.theme = \{[^}]*"id":(\d+)', body)
            problem = None
            if status != 200:
                problem = f'HTTP {status}'
            elif 'Liquid error' in body or 'Liquid syntax error' in body:
                problem = 'Liquid error on the page'
            elif not rendered_by or rendered_by.group(1) != str(theme_id):
                problem = f'rendered by theme {rendered_by.group(1) if rendered_by else "?"}, expected {theme_id}'
            # Retry rate limits, server errors and the live cache catching up.
            if problem and attempt < attempts - 1 and (status in (0, 429) or status >= 500 or 'rendered by' in problem):
                time.sleep(10)
                continue
            break
        log(f'  {"FAIL" if problem else "ok  "} {path}{": " + problem if problem else ""}')
        if problem:
            problems.append(f'{path}: {problem}')
    if problems:
        raise SmokeFailure('; '.join(problems))


# --- commands ---------------------------------------------------------------

def cmd_deploy(dry_run, stage_only):
    themes = list_themes()
    live = live_theme(themes)
    base = base_commit(live)
    head = git('rev-parse', 'HEAD').strip()
    log(f'Live theme: {live["name"]} (#{live["id"]}), built from {base[:7]}. Deploying {head[:7]}.')

    with tempfile.TemporaryDirectory() as tmp:
        live_dir = Path(tmp) / 'live'
        live_dir.mkdir()
        log('Pulling the live theme...')
        shopify('pull', '--theme', str(live['id']), '--path', str(live_dir))
        overrides, report = plan(base, live_dir)
        print_report(report)

        if report['clashes']:
            fail('The same files were changed in git and in the theme editor since the last release. '
                 'Pull them from the live theme, reconcile them in git, and merge again. Nothing was deployed.')
        if not report['from_git'] and not report['merged']:
            log('The live theme already has everything in this commit. Nothing to deploy.')
            return
        if dry_run:
            log('Dry run: stopping before anything is uploaded.')
            return

        release_commit = commit_sync(overrides, live)
        stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H%M')
        name = f'{RELEASE_PREFIX}{stamp} {release_commit[:7]}'
        release_dir = Path(tmp) / 'release'
        export_tree(release_commit, release_dir)
        theme = stage(name, live, release_dir)

        log('Checking the new theme through its preview link...')
        try:
            smoke(theme['id'], preview=True)
        except SmokeFailure as error:
            fail(f'The new theme failed its checks, so it was not published ({error}). '
                 f'It is left unpublished as #{theme["id"]} for inspection.')
        if stage_only:
            log('Stage only: the release is ready but not published.')
            return

        tag = tag_release(release_commit, name, theme, live)
        publish(theme)
        log('Checking the live site...')
        try:
            smoke(theme['id'], preview=False)
        except SmokeFailure as error:
            log('The live site failed its checks. Switching back to the previous theme.')
            publish(live)
            fail(f'Rolled back to {live["name"]}: {error}')

        push_sync_commit(release_commit, head, tag)
        prune(KEEP_RELEASES)
        log(f'Live: {name} (#{theme["id"]}). To undo, publish {live["name"]} (#{live["id"]}) '
            'or run the Rollback workflow.')


def previous_theme_for(live):
    """The theme that was live before `live`, from the release tag's notes."""
    for message in git('for-each-ref', 'refs/tags/release-*', '--format=%(contents)%00').split('\0'):
        notes = dict(line.split('=', 1) for line in message.splitlines() if '=' in line)
        if notes.get('theme_id') == str(live['id']) and notes.get('previous_theme_id', '').isdigit():
            return int(notes['previous_theme_id'])
    return None


def cmd_rollback(theme_id):
    themes = list_themes()
    live = live_theme(themes)
    by_id = {t['id']: t for t in themes}
    if theme_id is None:
        theme_id = previous_theme_for(live)
    if theme_id is None:
        older = sorted((t for t in themes if RELEASE_NAME.match(t['name']) and t['role'] != 'live'
                        and t['name'] < live['name']), key=lambda t: t['name'], reverse=True)
        theme_id = older[0]['id'] if older else None
    if theme_id is None or theme_id not in by_id:
        fail('Could not tell which theme to roll back to. Re-run with a theme id.')
    target = by_id[theme_id]
    if target['role'] == 'live':
        fail(f'{target["name"]} is already live.')

    log(f'Live now: {live["name"]} (#{live["id"]}). Rolling back to {target["name"]} (#{target["id"]}).')
    log('Theme-editor changes made since the release are not carried over.')
    publish(target)
    try:
        smoke(target['id'], preview=False)
    except SmokeFailure as error:
        fail(f'Rolled back, but the live checks failed: {error}')
    log(f'Rolled back. {live["name"]} (#{live["id"]}) is still in Themes if you need it again.')


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='command', required=True)
    deploy = sub.add_parser('deploy', help='release HEAD as a new theme and publish it')
    mode = deploy.add_mutually_exclusive_group()
    mode.add_argument('--dry-run', action='store_true', help='plan the merge, upload nothing')
    mode.add_argument('--stage-only', action='store_true', help='build and check the release, do not publish')
    rollback = sub.add_parser('rollback', help='publish the previous release again')
    rollback.add_argument('--theme-id', type=int, help='theme to publish (default: the one live before this)')
    args = parser.parse_args()

    if args.command == 'deploy':
        cmd_deploy(args.dry_run, args.stage_only)
    else:
        cmd_rollback(args.theme_id)


if __name__ == '__main__':
    main()
