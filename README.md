# AISS Lab website

A static academic research-group website inspired by PreCog's clear research-focused presentation. All page text and sections are managed through folders and Markdown. GitHub Actions generates and publishes the HTML. No database, server, CMS or JavaScript build system is required.

## The only content rule

```
content/
├── home/                       ← Home link in navigation, URL /
│   ├── index.md                ← Homepage metadata
│   ├── 10-intro/
│   │   └── index.md            ← First homepage section, hero and about
│   ├── 20-research/
│   │   └── index.md            ← Second section
│   ├── 30-news/
│   │   └── index.md            ← Shows latest items from content/news/
│   ├── 40-publications/
│   │   └── index.md            ← Shows selected items from content/publications/
│   └── 50-join/
│       └── index.md            ← Final homepage section
├── publications/               ← Publications link, URL /publications/
│   ├── index.md                ← Page heading / introduction
│   ├── animal-bias/
│   │   └── index.md            ← Publication section on Publications page
│   └── .../
├── projects/                   ← Projects link, URL /projects/
│   ├── index.md
│   └── research-themes/
│       └── index.md            ← Section on Projects page
├── news/                       ← News link, URL /news/
│   ├── index.md
│   └── 2026-10-research-grant/
│       └── index.md            ← News section on News page
├── people/
├── teaching/
├── blog/
├── datasets/
├── brainstorm/
└── openings/
```

**Every immediate subdirectory of `content/` with an `index.md` automatically becomes a navigation link and a page.** `content/home/` is the homepage and always appears first. `title` and `order` in each category's `index.md` determine navigation text and order. There is no separate navigation configuration.

**Every directory exactly one level deeper automatically becomes a section on its parent page.** That section is placed after the page introduction and before the common footer. An `index.md` file inside each section folder supplies its title, order and body. No section registration or Python edits are needed. The directory name is its HTML section anchor, e.g. `/projects/#research-themes`. Nested folders deeper than that are not interpreted as pages or sections, and should not be used for content.

The builder rejects category or section folders that lack `index.md`, instead of silently dropping them. This avoids confusing missing navigation links.

## Editing a page

Edit `content/people/index.md` to change the People page intro. To add a section, create `content/people/new-section/index.md`:

```md
---
title: New section
order: 20
summary: Optional short description
---

Write your section here using normal **Markdown**.
```

To add a nav page, create `content/resources/index.md`:

```md
---
title: Resources
order: 75
summary: Reading lists and shared resources
---

Resources maintained by the group.
```

It becomes `/resources/` and appears automatically in the navigation. Set `draft: true` in front matter to exclude a page or section from the build. The `order` field sets display position (lower first, default 100). On a page with publication or news entries, `sort_date: YYYY-MM-DD` allows dated entries to sort newest first when their `order` values match.

## Download files without editing the build scripts

Any navigation page or section can offer downloads. Create a `files/` directory **beside the relevant `index.md`** and place the document there. `files/` is reserved for attachments and never becomes a navigation item or page section.

```text
content/
  datasets/
    index.md                       # Datasets page
    files/                         # Optional attachments for the page intro
      dataset-catalogue.pdf
    resources/                     # Resources section on Datasets page
      index.md
      files/                       # Attachments for this section
        dataset-v1.csv
        paper.pdf
        source-code.zip
```

Link in the **Markdown next to the file** using the standard relative syntax:

```md
[Download catalogue](files/dataset-catalogue.pdf)
[Download CSV dataset](files/dataset-v1.csv)
[Download paper (PDF)](files/paper.pdf)
[Download source code](files/source-code.zip)
```

Each link is resolved relative to its own `index.md`. The builder checks that the file exists; a missing file stops the build with a useful error instead of deploying a broken link. Links are rewritten as absolute download URLs so they work correctly even for the homepage. Files are copied to `dist/downloads/` preserving the full content path. Example: `content/datasets/resources/files/dataset-v1.csv` is deployed to `/downloads/datasets/resources/files/dataset-v1.csv`. A browser download is requested through the HTML `download` attribute (browser behaviour can vary).

The supported extensions are common documents (`pdf`, `docx`, `pptx`, `xlsx`), data (`csv`, `tsv`, `json`), archives (`zip`, `7z`, `gz`), text/code (`txt`, `md`, `ipynb`, `py`, `bib`) and image/audio/video files. Nested paths like `files/releases/2026/data.csv` work. Do not use symlinks. Avoid uploading private, copyrighted or large files that should not be publicly distributed. GitHub Pages has publishing limits; host very large datasets on Zenodo or another repository and link to them via a normal HTTPS URL instead.

An actual working example is provided under `content/datasets/resources/files/README-example.txt` and linked from that section's Markdown. It is a demonstration, not a research dataset. Remove or replace it before public launch.

Images can also be displayed from the same directory using `![Description](files/diagram.png)` without causing a download. External URLs and site navigation links are left unchanged.

## Homepage sections

Homepage source folders use exactly the same discovery rule, with an optional `layout` value in the section front matter:

- `layout: intro`: large AISS hero followed by the section's Markdown as the lab introduction.
- `layout: research`: `###` headings in the Markdown become research tiles.
- `layout: listing` and `source: news` or `source: publications`: display entries defined in those content folders; `limit: 3` sets homepage count.
- `layout: join`: join/collaboration band.
- No layout or `layout: prose`: ordinary Markdown section.

Section order comes from `order`, not the folder name. Numeric folder prefixes are just convenient visual sorting in GitHub. You can add a new homepage section with any name and `index.md` and it will appear in the correct location.

## News, publications and blog

Each news item, paper or blog item has its own section directory under its parent page. Edit its `index.md` to update content. News and publications render in layouts suited to research information. The homepage's latest news and selected publications reuse those same directories; there is no duplicate content to maintain. Articles in `blog/<article-name>/index.md` appear as sections on the Blog page. This intentionally follows the requested two-level structure rather than generating separate URLs for individual articles.

Publication front matter can have `authors`, `venue`, `paper_url`, `selected` and `sort_date`. News entries can have `date_label`, `sort_date` and `category`.

## Footer and social profiles

The header navigation and footer are generated once by `scripts/build.py` and reused on every page. Social icons currently have **no destinations** and are rendered as non-clickable placeholders, not `href="#"` links.

To activate one, update `site.json`:

```json
"social": {
  "github": "https://github.com/YOUR-ORG",
  "linkedin": "",
  "youtube": "",
  "x": "",
  "scholar": "",
  "email": ""
}
```

Supported icons: GitHub, LinkedIn, YouTube, X, Google Scholar and email. For email use `mailto:contact@example.org`. Empty entries remain visible but non-clickable. Footer branding and standard links are shared on every page.

## Local build

Python 3.12 is recommended.

```sh
python -m pip install -r requirements.txt
python scripts/build.py
python scripts/check_build.py
python -m http.server 8000 --directory dist
```

Visit `http://localhost:8000`. The generated site goes to `dist/` and can be served by any static hosting provider. Python packages are used only during builds.

## Deploy to GitHub Pages

1. Upload all files and folders to the repository root, including `.github/workflows/deploy.yml`.
2. In the repository settings, select **Pages > Build and deployment > GitHub Actions**.
3. Push to `main`, or run **Build and deploy AISS static website** from the Actions tab. The workflow installs Python dependencies, builds Markdown and publishes `dist/`.
4. The included `CNAME` contains `aiss.mohdluqman.com`. Point that subdomain DNS to the GitHub Pages host before using it. The builder generates relative links, so assets and navigation work at a custom domain or the default `username.github.io/repository/` subpath. For a repository subpath, update `site_url` and workflow `SITE_URL` to that full address, and remove `CNAME` unless you use the custom domain.
5. To change the canonical URL, edit `site_url` in `site.json` **and** `SITE_URL` in `.github/workflows/deploy.yml`.

The build creates `sitemap.xml`, `feed.xml`, `robots.txt` and `.nojekyll` automatically. The RSS feed reflects News sections.

## Where files belong

- `content/`: **all editable Markdown**, arranged by page and section.
- `assets/`: the logo, network illustration and shared CSS.
- `site.json`: global site identity, canonical domain and social profile URLs; **not** a page or section list.
- `scripts/build.py`: the automatic builder. Content editors should not need to change it.
- `.github/workflows/deploy.yml`: GitHub Pages automation.
- `dist/`: generated output; rebuild instead of editing it.

This package retains only the verified material available in the earlier project. Sections that do not have confirmed member details, course information, funded roles or released datasets remain editable descriptions rather than fabricated listings.

## Troubleshooting styles or images not loading

The HTML uses relative asset URLs such as `./assets/site.css` on the homepage and `../assets/site.css` on subpages. This works for GitHub Pages project subpaths and custom domain roots. If you previously deployed the old build, rebuild and redeploy the complete `dist/` directory, then perform a hard refresh to clear cached HTML.

Use `python scripts/check_build.py` after building to catch missing stylesheets, images, navigation pages and downloadable files. For local preview, run `python -m http.server 8000 --directory dist` and open `http://localhost:8000/`, rather than opening the HTML file directly.

If a custom domain is configured, confirm that its DNS and GitHub Pages domain setting both match `CNAME`. The URLs in `site.json` and workflow `SITE_URL` must match the actual public address for canonical metadata, RSS and sitemap links.
