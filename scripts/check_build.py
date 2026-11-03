#!/usr/bin/env python3
"""Verify generated local assets and links for GitHub Pages deployment."""
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

OUT = Path(__file__).resolve().parents[1] / 'dist'

class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        attr = 'href' if tag in {'a', 'link'} else 'src' if tag in {'img', 'script'} else None
        if attr and attrs.get(attr):
            self.links.append((tag, attrs[attr]))

errors = []
html_files = sorted(OUT.rglob('*.html'))
if not html_files:
    raise SystemExit('No generated HTML files')
for page in html_files:
    parser = Links()
    parser.feed(page.read_text(encoding='utf-8'))
    for tag, raw in parser.links:
        u = urlsplit(raw)
        if u.scheme or u.netloc or raw.startswith(('#', 'mailto:', 'tel:')):
            continue
        if raw.startswith('/'):
            errors.append(f'{page.relative_to(OUT)}: root-absolute path: {raw}')
            continue
        target = (page.parent / unquote(u.path)).resolve() if u.path else page
        if not target.is_relative_to(OUT.resolve()):
            errors.append(f'{page.relative_to(OUT)}: escapes output: {raw}')
            continue
        if target.is_dir():
            target /= 'index.html'
        if not target.is_file():
            errors.append(f'{page.relative_to(OUT)}: missing {tag} target: {raw}')
for required in ['index.html', 'assets/site.css', 'assets/logo.svg', 'assets/network.svg', 'sitemap.xml', 'feed.xml', '.nojekyll']:
    if not (OUT / required).is_file():
        errors.append(f'Missing required output: {required}')
if errors:
    raise SystemExit('Build validation failed:\n' + '\n'.join(errors))
print(f'Validated {len(html_files)} HTML pages, all local asset/page/download links and required artifacts.')
