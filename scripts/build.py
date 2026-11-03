#!/usr/bin/env python3
"""AISS GitHub Pages builder. Folder == page, nested folder == section."""
from __future__ import annotations
import datetime as dt
import email.utils
import html
import json
import os
from pathlib import Path
import re
import shutil
from urllib.parse import unquote, quote, urlsplit
import xml.etree.ElementTree as ET
import mistune
import yaml

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / 'content'
OUT = ROOT / 'dist'
CONFIG = json.loads((ROOT / 'site.json').read_text(encoding='utf-8'))
BASE = os.environ.get('SITE_URL', CONFIG['site_url']).rstrip('/')
if not BASE.startswith('https://'):
    raise ValueError('SITE_URL must start with https://')
render_md = mistune.create_markdown(plugins=['table', 'strikethrough', 'url'])


def esc(text):
    return html.escape(str(text), quote=True)


def read_md(path):
    raw = path.read_text(encoding='utf-8')
    if raw.startswith('---\n'):
        front, delim, body = raw[4:].partition('\n---\n')
        if not delim:
            raise ValueError(f'Unclosed front matter: {path}')
        metadata = yaml.safe_load(front) or {}
        if not isinstance(metadata, dict):
            raise ValueError(f'Expected YAML object: {path}')
        return metadata, body.strip()
    return {}, raw.strip()


def content_directories(parent):
    """Only immediately nested directories with index.md create sections/pages."""
    output = []
    for directory in parent.iterdir():
        if not directory.is_dir() or directory.name.startswith(('.', '_')) or directory.name == 'files':
            continue
        index = directory / 'index.md'
        if not index.is_file():
            raise ValueError(f'Missing index.md: {directory}')
        meta, body = read_md(index)
        if meta.get('draft') is True:
            continue
        meta['title'] = str(meta.get('title') or directory.name.replace('-', ' ').title())
        meta['_body'] = body
        meta['_directory'] = directory
        meta['_slug'] = directory.name
        output.append(meta)
    return sorted(output, key=lambda m: (int(m.get('order', 100)), m['title'].lower()))


pages = content_directories(CONTENT)
if not pages or pages[0]['_slug'] != 'home':
    raise ValueError('Required: content/home/index.md with order: 0')
all_sections = {page['_slug']: content_directories(page['_directory']) for page in pages}
page_routes = {page['_slug']: ('/' if page['_slug'] == 'home' else '/' + page['_slug'] + '/') for page in pages}


def nav_html(route):
    return ''.join(f'<a href="{esc(page_routes[p["_slug"]])}"{(" aria-current=\"page\"" if page_routes[p["_slug"]] == route else "")}>{esc(p["title"])}</a>' for p in pages)


# Small inline SVGs, accessible labels supplied outside SVG. No icon-font dependency.
ICONS = {
    'github': '<path d="M9 19c-4.3 1.4-4.3-2.5-6-3m12 6v-3.9a3.4 3.4 0 0 0-1-2.7c3.4-.4 7-1.7 7-7.5a5.8 5.8 0 0 0-1.5-4 5.4 5.4 0 0 0-.1-4S18.2-.4 15 2.5a14 14 0 0 0-7 0C4.8-.4 3.6 0 3.6 0a5.4 5.4 0 0 0-.1 4A5.8 5.8 0 0 0 2 8c0 5.8 3.6 7.1 7 7.5a3.4 3.4 0 0 0-1 2.7V22"/>',
    'linkedin': '<rect x="2" y="9" width="4" height="13"/><circle cx="4" cy="4" r="2"/><path d="M11 22V9h4v2c1-1.9 6-3.1 7 2v9h-4v-8c0-2.7-3-2.5-3 0v8z"/>',
    'youtube': '<rect x="2" y="5" width="20" height="14" rx="4"/><path d="m10 9 6 3-6 3z"/>',
    'x': '<path d="m3 3 18 18M21 3 3 21M7 3l11 18"/>',
    'scholar': '<path d="m2 9 10-6 10 6-10 6zM6 12v5c3.5 3 8.5 3 12 0v-5M22 9v8"/>',
    'email': '<rect x="2" y="5" width="20" height="14" rx="2"/><path d="m3 7 9 7 9-7"/>',
}


def social_html():
    result = []
    for name, url in CONFIG.get('social', {}).items():
        if name not in ICONS:
            raise ValueError(f'Unknown social icon: {name}')
        icon = f'<svg aria-hidden="true" viewBox="0 0 24 24" width="19" height="19" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">{ICONS[name]}</svg>'
        label = 'Google Scholar' if name == 'scholar' else name.capitalize()
        # Empty links intentionally do NOT generate fake/clickable anchors.
        if url:
            if not str(url).startswith(('https://', 'mailto:')):
                raise ValueError(f'Invalid social URL for {name}')
            result.append(f'<a href="{esc(url)}" aria-label="{esc(label)}" title="{esc(label)}" rel="me noopener noreferrer">{icon}</a>')
        else:
            result.append(f'<span class="social-unset" title="{esc(label)} link coming soon" aria-label="{esc(label)} link not yet configured">{icon}</span>')
    return ''.join(result)


def shell(title, description, route, content):
    canonical = BASE + route
    schema = json.dumps({'@context': 'https://schema.org', '@type': 'WebPage', 'name': title, 'description': description, 'url': canonical, 'isPartOf': {'@type': 'WebSite', 'name': CONFIG['full_name'], 'url': BASE}}, ensure_ascii=False).replace('<', '\\u003c')
    year = dt.date.today().year
    nav = nav_html(route)
    document = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="theme-color" content="#0c3250"><title>{esc(title)} | AISS Lab</title><meta name="description" content="{esc(description)}"><link rel="canonical" href="{esc(canonical)}"><meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(description)}"><meta property="og:url" content="{esc(canonical)}"><link rel="icon" href="/assets/logo.svg" type="image/svg+xml"><link rel="alternate" href="/feed.xml" type="application/rss+xml" title="AISS updates"><link rel="stylesheet" href="/assets/site.css"><script type="application/ld+json">{schema}</script></head><body><a class="skip" href="#main">Skip to content</a><header class="site-header"><div class="container header-inner"><a href="/" class="brand" aria-label="AISS homepage"><img src="/assets/logo.svg" width="54" height="54" alt=""><span><strong>AISS</strong><small>AI Safety and Security</small></span></a><details class="mobile-nav"><summary aria-label="Open navigation">Menu <span aria-hidden="true">☰</span></summary><nav aria-label="Mobile navigation">{nav}</nav></details><nav class="desktop-nav" aria-label="Primary navigation">{nav}</nav></div></header><main id="main">{content}</main><footer class="footer"><div class="container footer-inner"><div class="footer-brand"><img src="/assets/logo.svg" alt="" width="36" height="36"><span><strong>AISS Research Lab</strong><small>Research on safe, secure and responsible AI.</small></span></div><div class="foot-links"><a href="/">Home</a><a href="/publications/">Publications</a><a href="/feed.xml">RSS</a></div><div class="social-links" aria-label="Social media profiles">{social_html()}</div><p class="copyright">© {year} AI Safety and Security. Built from Markdown.</p></div></footer></body></html>'''
    return document


# Attachments belong to their page or section: content/<page>/<section>/files/.
# Files never generate extra navigation links or sections.
DOWNLOAD_EXTENSIONS = {
    '.pdf', '.zip', '.csv', '.tsv', '.json', '.txt', '.xml', '.md',
    '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.odt', '.ods', '.odp',
    '.png', '.jpg', '.jpeg', '.webp', '.gif', '.svg', '.bib', '.ris',
    '.py', '.ipynb', '.r', '.tex', '.mp4', '.mp3', '.wav', '.gz', '.7z'
}


def resource_url(directory, path):
    """Resolve Markdown files/... links to a predictable public download path."""
    parsed = urlsplit(html.unescape(path))
    if not parsed.path.startswith('files/'):
        return None
    if parsed.query or parsed.fragment:
        raise ValueError(f'File links cannot include queries/fragments: {path}')
    relative = Path(unquote(parsed.path))
    if (relative.is_absolute() or '..' in relative.parts or
            any(part.startswith('.') for part in relative.parts) or
            len(relative.parts) < 2):
        raise ValueError(f'Unsafe file link: {path}')
    actual = directory / relative
    if not actual.is_file() or actual.is_symlink():
        raise FileNotFoundError(f'Missing downloadable file: {actual}')
    if actual.suffix.lower() not in DOWNLOAD_EXTENSIONS:
        raise ValueError(f'Unsupported attachment format: {actual}')
    public = Path('downloads') / directory.relative_to(CONTENT) / relative
    return '/' + '/'.join(quote(part) for part in public.parts)


def render_content(entry):
    """Render Markdown and fix only local files/ links, leaving other links intact."""
    result = render_md(entry['_body'])
    directory = entry['_directory']

    def anchor_replace(match):
        address = match.group(2)
        public_url = resource_url(directory, address)
        if public_url is None:
            return match.group(0)
        return match.group(1) + esc(public_url) + match.group(3) + ' class="file-download" download'

    def image_replace(match):
        public_url = resource_url(directory, match.group(2))
        if public_url is None:
            return match.group(0)
        return match.group(1) + esc(public_url) + match.group(3)

    result = re.sub(r'(<a\b[^>]*?\bhref=")([^"]+)("[^>]*?)>',
                    lambda m: anchor_replace(m) + '>', result)
    result = re.sub(r'(<img\b[^>]*?\bsrc=")([^"]+)("[^>]*?)>',
                    lambda m: image_replace(m) + '>', result)
    return result


def copy_downloads():
    copied = 0
    for files_dir in CONTENT.rglob('files'):
        if not files_dir.is_dir():
            continue
        owner = files_dir.parent
        if owner != CONTENT and (owner / 'index.md').is_file():
            for file in files_dir.rglob('*'):
                if not file.is_file():
                    continue
                if file.is_symlink() or file.suffix.lower() not in DOWNLOAD_EXTENSIONS:
                    raise ValueError(f'Unsafe or unsupported attachment: {file}')
                destination = OUT / 'downloads' / file.relative_to(CONTENT)
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(file, destination)
                copied += 1
    return copied


def section_id(section):
    return re.sub(r'[^a-z0-9-]+', '-', section['_slug'].lower()).strip('-')


def section_heading(section, link=None):
    heading = f'<h2>{esc(section["title"])}</h2>'
    summary = f'<p>{esc(section["summary"])}</p>' if section.get('summary') else ''
    action = f'<a class="text-link" href="{esc(link)}">View all</a>' if link else ''
    return f'<div class="section-head"><div>{heading}{summary}</div>{action}</div>'


def news_item(n):
    label = str(n.get('date_label') or n.get('sort_date') or '')
    return f'<article class="news-item"><div class="news-date"><time>{esc(label)}</time><span>{esc(n.get("category", "Update"))}</span></div><div><h3>{esc(n["title"])}</h3><div class="news-description">{render_content(n)}</div></div></article>'


def publication_item(p):
    title = esc(p['title'])
    if p.get('paper_url'):
        url = str(p['paper_url'])
        if not url.startswith(('https://', 'http://')):
            raise ValueError(f'Invalid publication URL: {url}')
        title = f'<a href="{esc(url)}" rel="noopener noreferrer">{title}</a>'
    return f'<article class="publication-item"><div class="publication-marker" aria-hidden="true">◆</div><div><h3>{title}</h3><p class="authors">{esc(p.get("authors", ""))}</p><p class="venue">{esc(p.get("venue", ""))}</p>{render_content(p) if p["_body"] else ""}</div></article>'


def order_items(items):
    # Prefer explicitly assigned order, otherwise newest dated entries first.
    return sorted(items, key=lambda x: (int(x.get('order', 100)), -(dt.date.fromisoformat(str(x['sort_date'])).toordinal() if x.get('sort_date') else 0), x['title']))


def listing(section, *, on_home=False):
    source = str(section.get('source') or section['_slug'])
    if source not in all_sections:
        raise ValueError(f'Unknown section source: {source}')
    items = order_items(all_sections[source])
    if on_home:
        if source == 'publications':
            items = [x for x in items if x.get('selected', True)]
        items = items[:int(section.get('limit', 4))]
    renderer = publication_item if source == 'publications' else news_item if source == 'news' else lambda entry: f'<article class="prose"><h3>{esc(entry["title"])}</h3>{render_content(entry)}</article>'
    cls = 'publication-list' if source == 'publications' else 'news-list' if source == 'news' else 'prose'
    return f'<div class="{cls}">{"".join(renderer(x) for x in items) or "<p>No entries published yet.</p>"}</div>'


def home_section(section):
    layout = section.get('layout', 'prose')
    sid = section_id(section)
    if layout == 'intro':
        lead = esc(section.get('summary', ''))
        hero = f'<section class="hero" id="{sid}"><div class="container hero-inner"><div class="hero-copy"><p class="hero-kicker">{esc(section.get("kicker", "AISS Lab"))}</p><h1>{esc(section["title"])}</h1><p class="hero-lead">{lead}</p><div class="hero-actions"><a class="button button-light" href="/publications/">Explore our research</a><a class="quiet-link" href="/people/">Meet the group</a></div></div><img class="hero-illustration" src="/assets/network.svg" alt="Abstract neural network visualization" width="740" height="490"></div></section>'
        about = f'<section class="about-band"><div class="container about-layout"><div class="section-side"><span class="side-line"></span><h2>About AISS</h2></div><div class="prose about-copy">{render_content(section)}</div></div></section>'
        return hero + about
    if layout == 'research':
        cards = []
        for heading, body in re.findall(r'^###\s+(.+?)\n(.*?)(?=^###\s+|\Z)', section['_body'], re.M | re.S):
            cards.append(f'<div class="research-card"><h3>{esc(heading)}</h3>{render_content({**section, '_body': body.strip()})}</div>')
        content = f'<div class="research-grid">{"".join(cards)}</div>' if cards else f'<div class="prose">{render_content(section)}</div>'
        return f'<section class="section soft" id="{sid}"><div class="container">{section_heading(section, "/projects/")}{content}</div></section>'
    if layout == 'join':
        return f'<section class="join-section" id="{sid}"><div class="container join-inner"><div><h2>{esc(section["title"])}</h2><p class="join-lead">{esc(section.get("summary", ""))}</p><div class="join-copy">{render_content(section)}</div></div><a class="button button-light" href="/openings/">Explore opportunities</a></div></section>'
    source = str(section.get('source', ''))
    if layout == 'listing':
        body = listing(section, on_home=True)
        link = page_routes.get(source)
    else:
        body = f'<div class="prose">{render_content(section)}</div>'
        link = None
    return f'<section class="section {"publications-section" if source == "publications" else ""}" id="{sid}"><div class="container">{section_heading(section, link)}{body}</div></section>'


def normal_page_section(section, category):
    if category == 'news':
        body = news_item(section)
        return f'<section class="page-section" id="{section_id(section)}">{body}</section>'
    if category == 'publications':
        body = publication_item(section)
        return f'<section class="page-section" id="{section_id(section)}">{body}</section>'
    summary = f'<p class="section-summary">{esc(section["summary"])}</p>' if section.get('summary') else ''
    body = render_content(section)
    return f'<section class="page-section" id="{section_id(section)}"><h2>{esc(section["title"])}</h2>{summary}<div class="prose">{body}</div></section>'


def write(route, content):
    path = OUT / route.lstrip('/')
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix == '.html':
        route = '/' if path.parent == OUT else '/' + path.parent.relative_to(OUT).as_posix() + '/'
        prefix = './' if route == '/' else '../'
        content = content.replace('href="/', f'href="{prefix}').replace('src="/', f'src="{prefix}')
    path.write_text(content, encoding='utf-8')


# Remove stale generated pages from prior builds.
if OUT.exists():
    shutil.rmtree(OUT)
OUT.mkdir()

for page in pages:
    slug = page['_slug']
    route = page_routes[slug]
    if slug == 'home':
        body = ''.join(home_section(s) for s in all_sections[slug])
        title = CONFIG['full_name']
    else:
        intro = render_content(page) if page['_body'] else ''
        header = f'<div class="container page-intro"><div class="page-header"><h1>{esc(page["title"])}</h1><p>{esc(page.get("summary", ""))}</p></div><div class="prose page-prose">{intro}</div></div>'
        sections = ''.join(normal_page_section(s, slug) for s in order_items(all_sections[slug]))
        content = f'<div class="container page-content">{sections or "<p>Content will be added here.</p>"}</div>'
        body = header + content
        title = page['title']
    write(route + 'index.html', shell(title, str(page.get('summary') or CONFIG['description'])[:165], route, body))

# Discoverability only for generated pages (no phantom post URLs).
ns = 'http://www.sitemaps.org/schemas/sitemap/0.9'
ET.register_namespace('', ns)
urlset = ET.Element(f'{{{ns}}}urlset')
for route in page_routes.values():
    loc = ET.SubElement(ET.SubElement(urlset, f'{{{ns}}}url'), f'{{{ns}}}loc')
    loc.text = BASE + route
write('/sitemap.xml', ET.tostring(urlset, encoding='unicode', xml_declaration=True))
write('/robots.txt', f'User-agent: *\nAllow: /\nSitemap: {BASE}/sitemap.xml\n')
rss = ET.Element('rss', version='2.0')
channel = ET.SubElement(rss, 'channel')
for tag, value in [('title', 'AISS Lab Updates'), ('link', BASE), ('description', CONFIG['description'])]:
    ET.SubElement(channel, tag).text = value
for n in order_items(all_sections.get('news', [])):
    item = ET.SubElement(channel, 'item')
    for tag, value in [('title', n['title']), ('link', BASE + '/news/#' + section_id(n)), ('guid', BASE + '/news/#' + section_id(n)), ('description', re.sub(r'\s+', ' ', n['_body'])[:250])]:
        ET.SubElement(item, tag).text = value
    if n.get('sort_date'):
        date = dt.date.fromisoformat(str(n['sort_date']))
        ET.SubElement(item, 'pubDate').text = email.utils.format_datetime(dt.datetime.combine(date, dt.time(), dt.timezone.utc))
write('/feed.xml', ET.tostring(rss, encoding='unicode', xml_declaration=True))
download_count = copy_downloads()
shutil.copytree(ROOT / 'assets', OUT / 'assets')
(OUT / '.nojekyll').touch()
if (ROOT / 'CNAME').exists():
    shutil.copy2(ROOT / 'CNAME', OUT / 'CNAME')
print(f'Built {len(pages)} page(s), {sum(map(len, all_sections.values()))} section(s), {len(all_sections.get("news", []))} news entries, {download_count} attachment(s).')
