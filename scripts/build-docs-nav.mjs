#!/usr/bin/env node
/**
 * Generates docs/docs.json, the Mintlify site configuration, from the documentation tree, and keeps
 * the section-index.md aliases the site needs. Zero dependencies.
 *
 * The filesystem is the source: a page added under docs/ appears in the published navigation without
 * anyone editing a config file. Hand-maintained navigation is how a docs site silently stops matching
 * the repository it came from.
 *
 * Two Mintlify behaviours shape this (both established on a running site, not by reading about them):
 *
 *   1. It will not serve a page named README: it treats README.md as a repository readme, redirects a
 *      directory to it, and then 404s. It does serve a page named index. So each directory holding a
 *      README.md gets a generated section-index.md copy beside it, and the navigation points there.
 *      The README stays the file people edit; the copy is a build artifact, checked byte for byte in
 *      CI. A symlink works under `mint dev` but not in Mintlify's cloud build.
 *   2. It serves pages without the .md extension, so the ../section/page.md links that GitHub follows
 *      would 404. One redirect per page fixes that, the README URLs included.
 *
 * Usage: node scripts/build-docs-nav.mjs           write docs.json and the aliases
 *        node scripts/build-docs-nav.mjs --check   fail if either is stale or missing
 */
import { readFileSync, readdirSync, statSync, existsSync, writeFileSync } from 'node:fs';
import { join, relative, resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const DOCS = join(ROOT, 'docs');
const OUT = join(DOCS, 'docs.json');
const SKIP = new Set(['assets', 'node_modules']);
const CHECK = process.argv.includes('--check');

// The order of the groups is the order of the directories: the prefixes fix the reading order.
const LABELS = {
  '': 'Start here',
  '00-start': 'Getting started',
  '10-talking': 'Talking to Troi',
  '20-console': 'The console',
  '30-views': 'The views',
  '40-abilities': 'What Troi can do',
  '50-safety': 'Safety',
  '60-memory': 'Memory and data',
  '70-reference': 'Reference',
};
// Directories on the Reference tab; everything else is the guide.
const REFERENCE = new Set(['70-reference']);
const label = (d) => LABELS[d] ?? d.replace(/^\d+-/, '').replace(/-/g, ' ').replace(/^./, (c) => c.toUpperCase());

function walk(dir, out = []) {
  for (const entry of readdirSync(dir).sort()) {
    const p = join(dir, entry);
    if (entry === 'section-index.md') continue; // a generated copy of README.md, not a page
    if (statSync(p).isDirectory()) { if (!SKIP.has(entry)) walk(p, out); }
    else if (entry.endsWith('.md')) out.push(p);
  }
  return out;
}

const problems = [];
let created = 0;

/** A directory's README.md needs a section-index.md copy beside it: Mintlify will not serve README. */
function ensureAlias(dir) {
  const readme = join(DOCS, dir, 'README.md');
  const alias = join(DOCS, dir, 'section-index.md');
  const want = readFileSync(readme, 'utf8');
  if (existsSync(alias) && readFileSync(alias, 'utf8') === want) return;
  if (CHECK) { problems.push(`stale or missing: docs/${dir ? dir + '/' : ''}section-index.md (copy of README.md)`); return; }
  writeFileSync(alias, want);
  created++;
}

/** The page's own order, when its front matter says so (`order: 2`); README first, then by order, then by name. */
function order(file) {
  const head = readFileSync(file, 'utf8').slice(0, 600);
  const m = head.match(/^order:\s*(\d+)\s*$/m);
  return m ? Number(m[1]) : 1000;
}

const groups = new Map();
const entries = [];
for (const file of walk(DOCS)) {
  const rel = relative(DOCS, file).split('\\').join('/');
  const dir = rel.includes('/') ? rel.slice(0, rel.lastIndexOf('/')) : '';
  const base = rel.replace(/\.md$/, '');
  const isReadme = base === 'README' || base.endsWith('/README');
  if (isReadme) ensureAlias(dir);
  const nav = isReadme ? (dir ? `${dir}/section-index` : 'section-index') : base;
  if (!groups.has(dir)) groups.set(dir, []);
  groups.get(dir).push({ nav, isReadme, order: isReadme ? -1 : order(file) });
  entries.push({ base, nav, isReadme, dir });
}

const ordered = [...groups.entries()]
  .sort(([a], [b]) => (a === '' ? -1 : b === '' ? 1 : a.localeCompare(b)))
  .map(([dir, pages]) => ({
    dir,
    group: label(dir),
    pages: pages
      .sort((a, b) => a.order - b.order || a.nav.localeCompare(b.nav))
      .map((p) => p.nav),
  }));

const redirects = [];
for (const e of entries.sort((a, b) => a.base.localeCompare(b.base))) {
  if (e.isReadme) {
    // The directory URL and both README URLs point at the generated page: Mintlify redirects a
    // directory to its README on its own and then cannot serve it, so these are explicit.
    const target = `/${e.nav}`;
    if (e.dir) redirects.push({ source: `/${e.dir}`, destination: target });
    else redirects.push({ source: '/', destination: target });
    redirects.push({ source: `/${e.base}`, destination: target });
    redirects.push({ source: `/${e.base}.md`, destination: target });
  } else {
    redirects.push({ source: `/${e.nav}.md`, destination: `/${e.nav}` });
  }
}

const guide = ordered.filter((g) => !REFERENCE.has(g.dir)).map(({ group, pages }) => ({ group, pages }));
const reference = ordered.filter((g) => REFERENCE.has(g.dir)).map(({ group, pages }) => ({ group, pages }));

const config = {
  $schema: 'https://mintlify.com/docs.json',
  theme: 'mint',
  name: 'Troi of Silo One',
  // The site description for search engines and AI indexing. Kept here rather than in the Mintlify
  // dashboard: dashboard edits commit to docs.json, which this script regenerates, so they would be lost.
  description:
    'Troi of Silo One is a chief of staff that lives on your Mac: it listens, sees when you ask, ' +
    'does the work, keeps its memory in a vault you own, and never deletes anything of yours.',
  // The brand: the silo's blue-violet, with its lighter and darker ends (brand/make_logo.py).
  colors: { primary: '#5B5CEB', light: '#8C95F7', dark: '#3527B8' },
  logo: {
    light: '/assets/logo/lockup-light.svg',
    dark: '/assets/logo/lockup-dark.svg',
    href: '/',
  },
  favicon: '/assets/logo/favicon.svg',
  // The console is dark first (space behind every page); the site follows the reader's system.
  appearance: { default: 'system' },
  // The author's site and the repository, from the navbar and the footer.
  navbar: {
    links: [{ label: 'Author', href: 'https://ayesigapaul.vercel.app/' }],
    primary: { type: 'github', href: 'https://github.com/Silo-One-Ug/troi-of-silo-one' },
  },
  footer: {
    socials: {
      website: 'https://ayesigapaul.vercel.app/',
      github: 'https://github.com/Silo-One-Ug/troi-of-silo-one',
    },
  },
  navigation: {
    tabs: [
      { tab: 'Guide', groups: guide },
      ...(reference.length ? [{ tab: 'Reference', groups: reference }] : []),
    ],
  },
  redirects,
};
const json = JSON.stringify(config, null, 2) + '\n';
const pages = ordered.reduce((n, g) => n + g.pages.length, 0);

if (CHECK) {
  if (!existsSync(OUT) || readFileSync(OUT, 'utf8') !== json) problems.push('docs/docs.json does not match the documentation tree');
  if (problems.length) {
    console.error(`\n${problems.length} problem(s) with the published site configuration:\n`);
    for (const p of problems) console.error(`  ✗ ${p}`);
    console.error('\nRegenerate with: node scripts/build-docs-nav.mjs\n');
    process.exit(1);
  }
  console.log(`Checked ${pages} page(s) across ${ordered.length} group(s), and every section index alias.`);
  console.log('docs/docs.json matches the documentation tree.');
} else {
  writeFileSync(OUT, json);
  console.log(`Wrote docs/docs.json: ${pages} page(s), ${ordered.length} group(s), ${redirects.length} redirect(s).`);
  console.log(`${created} index copy/copies written.`);
}
