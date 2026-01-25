#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, re, shutil, pathlib, sys


# =============================================================================
# PATHS & CONTENT ROOTS
# =============================================================================

VAULT = "/Users/jaehyeonlee/Library/Mobile Documents/iCloud~md~obsidian/Documents/j-h-web"
DEST  = "/Users/jaehyeonlee/web/j-h"

SRC_CONTENT_ROOTS = ["about", "contact", "glossary", "method", "shop", "thought", "works"]
ROOT_SECTIONS = set(s.lower() for s in SRC_CONTENT_ROOTS)

SECTIONS = [
    "",
    "allarchive",
    "about", "contact", "glossary", "method", "shop", "thought", "works",
    "works/project", "works/workshop", "works/workshop-practice",
]


# =============================================================================
# SECTION TITLES (I18N)
# =============================================================================

TITLES_EN = {
    "": "home",
    "allarchive": "all archive",
    "about": "about",
    "contact": "contact",
    "glossary": "glossary",
    "method": "methodology",
    "shop": "shop",
    "thought": "thought",
    "works": "works",
    "works/project": "project",
    "works/workshop": "workshop",
    "works/workshop-practice": "workshop practice",
}

TITLES_KR = {
    "": "홈",
    "allarchive": "모든 아카이브",
    "about": "이 웹에 대하여",
    "contact": "연락처",
    "glossary": "참조",
    "method": "방법",
    "shop": "구매",
    "thought": "생각",
    "works": "작업들",
    "works/project": "프로젝트",
    "works/workshop": "워크샵",
    "works/workshop-practice": "워크샵 실천",
}


# =============================================================================
# SECTION TEMPLATES
# =============================================================================

SECTION_TEMPLATES = {
    "allarchive":     "allarchive.html",
    "works":          "section/works.html",
    "shop":           "section/shop.html",
    "glossary":       "allarchive.html",
    "method":         "allarchive.html",
    "thought":        "allarchive.html",
}


# =============================================================================
# FRONT MATTER KEY GROUPS
# =============================================================================

FILE_URL_KEYS = {"thumbnail", "image", "poster"}
KEEP_TOPLEVEL = {"title", "date", "template", "draft", "weight", "slug", "taxonomies"}
NUMERIC_KEYS = {"doc_no", "date_year"}


# =============================================================================
# REGEX DEFINITIONS
# =============================================================================

MD_RE = re.compile(r"\.md$", re.IGNORECASE)

IMG_LINK_RE = re.compile(
    r'!\[([^\]]*)\]\('
    r'\s*([^)"]+?)\s*'
    r'(?:\"([^\"]*)\")?'
    r'\)'
)

LINK_RE = re.compile(
    r'\[([^\]]*)\]\('
    r'\s*([^)]+?)\s*'
    r'\)'
)

DISABLED_LINK_RE = re.compile(r'\[([^\]]+)\]\(\s*#disabled\s*\)')

FM_TOML_RE = re.compile(r'^\s*\+{3}\s*\n(.*?)\n\+{3}\s*', re.S)
FM_YAML_RE = re.compile(r'^\s*-{3}\s*\n(.*?)\n-{3}\s*', re.S)

DATE_FLEX_RE = re.compile(
    r'^\s*(?P<y>\d{4})(?:[.\-\/\s]*(?P<m>\d{1,2})(?:[.\-\/\s]*(?P<d>\d{1,2}))?)?\s*$'
)

WIKILINK_GLOBAL_RE = re.compile(r'\[\[\s*([^\]|]+?)(?:\|([^\]]+))?\s*\]\]')
WIKILINK_ONE_RE    = re.compile(r'^\[\[\s*([^\]|]+?)(?:\|([^\]]+))?\s*\]\]$')

KEYVAL_LINE_TOML = re.compile(r'^\s*([A-Za-z0-9_\-]+)\s*=\s*(.+?)\s*$')
KEYVAL_LINE_YAML = re.compile(r'^\s*([A-Za-z0-9_\-]+)\s*:\s*(.+?)\s*$')

FOOTNOTE_DEF_RE = re.compile(
    r'^\[\^([^\]]+)\]:\s*(.+)$',
    re.M
)

URL_RE = re.compile(r'(?<!\]\()(https?://[^\s<>"\']+)')


# =============================================================================
# BASIC FILE UTILITIES
# =============================================================================

def read_file(p):
    with open(p, "r", encoding="utf-8") as f:
        return f.read()

def write_file(p, s):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write(s)

def is_subsection(section_rel: str) -> bool:
    return "/" in section_rel if section_rel else False


# =============================================================================
# MEDIA PATH HANDLING
# =============================================================================

def to_web_media_path(doc_parent_rel: str, media_rel: str) -> str:
    s = (media_rel or "").strip()
    if not s:
        return s

    if s.startswith(("http://", "https://", "data:")):
        return s

    if s.startswith("/media/"):
        out = s
        if doc_parent_rel:
            out = out.replace(f"/media/{doc_parent_rel}/media/", f"/media/{doc_parent_rel}/")
        return out

    idx = s.find("media/")
    if idx != -1:
        s = s[idx:]

    if s.startswith("media/"):
        rel = s[len("media/"):]
        base = f"/media/{doc_parent_rel}/" if doc_parent_rel else "/media/"
        return os.path.join(base, rel).replace("\\", "/").replace("//", "/")

    return media_rel


def rewrite_media_paths(doc_rel_dir: str, text: str) -> str:
    def repl_img(m):
        alt, mrel, title = m.group(1) or "", m.group(2) or "", m.group(3) or ""
        abs_src = to_web_media_path(doc_rel_dir, mrel)
        return f'![{alt}]({abs_src} "{title}")' if title else f'![{alt}]({abs_src})'

    def repl_link(m):
        label, mrel = m.group(1), m.group(2)
        return f'[{label}]({to_web_media_path(doc_rel_dir, mrel)})'

    text = IMG_LINK_RE.sub(repl_img, text)
    text = LINK_RE.sub(repl_link, text)
    return text


def copy_media_folder(src_doc_dir: str, doc_parent_rel: str):
    media_src = os.path.join(src_doc_dir, "media")
    if not os.path.isdir(media_src):
        return

    dest_media_dir = os.path.join(DEST, "static", "media", doc_parent_rel)

    if os.path.isdir(dest_media_dir):
        shutil.rmtree(dest_media_dir)

    os.makedirs(dest_media_dir, exist_ok=True)

    for root, dirs, files in os.walk(media_src):
        rel = os.path.relpath(root, media_src)
        for d in dirs:
            os.makedirs(os.path.join(dest_media_dir, rel, d), exist_ok=True)
        for f in files:
            sp = os.path.join(root, f)
            dp = os.path.join(dest_media_dir, rel, f)
            os.makedirs(os.path.dirname(dp), exist_ok=True)
            shutil.copy2(sp, dp)


# =============================================================================
# FRONT MATTER PARSING & DATE NORMALIZATION
# =============================================================================

def split_front_matter(text: str):
    m = FM_TOML_RE.match(text)
    if m:
        return ("toml", m.group(1), text[m.end():])
    m = FM_YAML_RE.match(text)
    if m:
        return ("yaml", m.group(1), text[m.end():])
    return (None, "", text)

def assemble_front_matter(kind: str, head: str, body: str) -> str:
    if kind == "toml":
        return "+++\n" + head.strip("\n") + "\n+++\n" + body
    if kind == "yaml":
        return "---\n" + head.strip("\n") + "\n---\n" + body
    return body

def _norm_date_any(s: str) -> str | None:
    m = DATE_FLEX_RE.search(str(s))
    if not m:
        return None
    y = int(m.group('y')); mth = m.group('m'); day = m.group('d')
    if mth is None:
        mm, dd = 1, 1
    else:
        mm = int(mth)
        if not (1 <= mm <= 12): return None
        if day is None:
            dd = 1
        else:
            dd = int(day)
            if not (1 <= dd <= 31): return None
    return f"{y:04d}-{mm:02d}-{dd:02d}"

def sanitize_front_matter_text(text: str) -> tuple[str, bool]:
    changed = False
    kind, head, body = split_front_matter(text)
    if not kind:
        return text, False

    if kind == "toml":
        m_date = re.search(r'^\s*date\s*=\s*(.+?)\s*$', head, re.M)
        if m_date:
            n = _norm_date_any(m_date.group(1))
            head2 = re.sub(r'^\s*date\s*=\s*.+?$', f'date = {n}' if n else '', head, flags=re.M)
            if head2 != head: head = head2; changed = True
        else:
            m_sort = re.search(r'^\s*date_sort\s*=\s*(.+?)\s*$', head, re.M)
            if m_sort:
                n = _norm_date_any(m_sort.group(1))
                if n: head = head.rstrip("\n") + f"\ndate = {n}\n"; changed = True

    elif kind == "yaml":
        head2 = re.sub(r'^\s*date\s*=\s*(.+?)\s*$', r'date: \1', head, flags=re.M)
        if head2 != head: head = head2; changed = True
        m_date = re.search(r'^\s*date\s*:\s*(.+?)\s*$', head, re.M)
        if m_date:
            n = _norm_date_any(m_date.group(1))
            head2 = re.sub(r'^\s*date\s*:\s*.+?$', f'date: {n}' if n else '', head, flags=re.M)
            if head2 != head: head = head2; changed = True
        else:
            m_sort = re.search(r'^\s*date_sort\s*:\s*(.+?)\s*$', head, re.M)
            if m_sort:
                n = _norm_date_any(m_sort.group(1))
                if n: head = head.rstrip("\n") + f"\ndate: {n}\n"; changed = True

    return assemble_front_matter(kind, head, body), changed

def ensure_normalized_date(text: str) -> str:
    new_t, _ = sanitize_front_matter_text(text)
    return new_t


# =============================================================================
# WIKILINK & PATH RESOLUTION
# =============================================================================

def _is_vault_abs(path: str) -> bool:
    if not path: return False
    head = path.split("/", 1)[0].lower()
    return head in ROOT_SECTIONS

def _split_lang_and_ext(last: str):
    lang = None
    name = last
    if name.endswith(".md"): name = name[:-3]
    if name.endswith(".kr"):
        name = name[:-3]
        lang = "kr"
    return name, lang

def _slugify_segment(name: str) -> str:
    return name.strip().replace(" ", "-").lower()

def _vault_path_to_site_href(raw_path: str, doc_parent_rel: str) -> str:
    raw_path = (raw_path or "").strip()
    if not raw_path:
        return "/"
    if raw_path.startswith("/"):
        vault_rel = raw_path.lstrip("/")
    elif _is_vault_abs(raw_path):
        vault_rel = raw_path
    else:
        p = pathlib.PurePosixPath(doc_parent_rel) / raw_path
        parts = []
        for part in str(p).split('/'):
            if part in ("", "."): continue
            if part == "..":
                if parts: parts.pop()
                continue
            parts.append(part)
        vault_rel = "/".join(parts)

    parts = [seg for seg in vault_rel.split("/") if seg]
    if not parts: return "/"
    base, lang = _split_lang_and_ext(parts[-1])
    parts[-1] = _slugify_segment(base)
    prefix = "/kr" if lang == "kr" else ""
    href = prefix + "/" + "/".join(parts) + "/"
    return href.replace("//", "/")

def rewrite_wikilinks_in_body(kind: str, head: str, body: str, doc_parent_rel: str):
    def repl(m):
        path = (m.group(1) or "").strip()
        label = (m.group(2) or "").strip()
        href = _vault_path_to_site_href(path, doc_parent_rel)
        if not label:
            label = href.strip("/").split("/")[-1] or href
        return f'[{label}]({href})'
    return head, WIKILINK_GLOBAL_RE.sub(repl, body)


# =============================================================================
# FOOTNOTE EXTRACTION (FOR META)
# =============================================================================

def rewrite_footnotes_in_body(body: str, doc_parent_rel: str) -> str:
    def repl(m):
        note_id = m.group(1).strip()
        raw_text = m.group(2).strip()

        text = WIKILINK_GLOBAL_RE.sub(
            lambda mm: f"[{mm.group(2) or mm.group(1)}]"
                       f"({_vault_path_to_site_href(mm.group(1), doc_parent_rel)})",
            raw_text
        )

        def repl_url(mm):
            url = mm.group(1)
            label = _strip_url_scheme(url)
            return f"[{label}]({url})"

        text = URL_RE.sub(repl_url, text)

        return f"[^{note_id}]: {text}"

    return FOOTNOTE_DEF_RE.sub(repl, body)


def extract_footnotes_for_meta(body: str, doc_parent_rel: str) -> list[dict]:
    notes = []
    for m in FOOTNOTE_DEF_RE.finditer(body):
        note_id = m.group(1).strip()
        raw_text = m.group(2).strip()

        # 1) 내부 위키링크 처리
        text = WIKILINK_GLOBAL_RE.sub(
            lambda mm: f"[{mm.group(2) or mm.group(1)}]"
                       f"({_vault_path_to_site_href(mm.group(1), doc_parent_rel)})",
            raw_text
        )

        # 2) 외부 URL 처리 (https:// → 표시용 scheme 제거)
        def repl_url(mm):
            url = mm.group(1)
            label = _strip_url_scheme(url)
            return f"[{label}]({url})"

        text = URL_RE.sub(repl_url, text)

        notes.append({
            "id": note_id,
            "text": text,
        })

    return notes




# =============================================================================
# CUSTOM META → EXTRA
# =============================================================================

def _strip_quotes(s: str) -> str:
    s = s.strip()
    if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
        return s[1:-1]
    return s

def _strip_url_scheme(url: str) -> str:
    return re.sub(r'^https?://', '', url)

def _yaml_quote(s: str) -> str:
    s = (s or "").strip()
    if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
        return s

    s = s.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{s}"'

def _extract_yaml_block_list(head: str, key: str):
    lines = head.splitlines()
    values = []
    out = []

    i = 0
    while i < len(lines):
        ln = lines[i]
        if re.match(rf'^\s*{re.escape(key)}\s*:\s*$', ln):
            i += 1
            while i < len(lines):
                m = re.match(r'^\s*-\s*(.+)\s*$', lines[i])
                if not m:
                    break
                values.append(_strip_quotes(m.group(1)))
                i += 1
            continue
        out.append(ln)
        i += 1

    return values, "\n".join(out)

def move_custom_fields_into_extra(text: str, doc_parent_rel: str, footnotes: list[dict]) -> str:
    kind, head, body = split_front_matter(text)
    if not kind:
        return text

    def handle_link_value(raw: str):
        raw0 = _strip_quotes(raw)
        m_w = WIKILINK_ONE_RE.match(raw0)
        if m_w:
            path = (m_w.group(1) or "").strip()
            label = (m_w.group(2) or "").strip()
        else:
            path = raw0
            label = ""
        href = _vault_path_to_site_href(path, doc_parent_rel)
        if not label:
            label = href.strip("/").split("/")[-1] or href
        return href, label

    def label_from_wikilink_or_text(raw: str) -> str:
        raw0 = _strip_quotes(raw)
        m_w = WIKILINK_ONE_RE.match(raw0)
        if m_w and m_w.group(2):
            return m_w.group(2).strip()
        return raw0

    def media_href_from_value(raw: str) -> str:
        raw0 = _strip_quotes(raw).strip()
        if not raw0:
            return raw0

        m_any = re.search(r'\[\[\s*([^\]|]+)', raw0)
        candidate = (m_any.group(1).strip() if m_any else raw0)

        if candidate.startswith("/media/"):
            out = candidate
            if doc_parent_rel:
                out = out.replace(f"/media/{doc_parent_rel}/media/", f"/media/{doc_parent_rel}/")
            return out

        idx = candidate.find("media/")
        if idx != -1:
            return to_web_media_path(doc_parent_rel, candidate[idx:])

        return candidate

    if kind == "toml":
        lines = head.splitlines()
        keep_lines, moved = [], {}

        for ln in lines:
            m2 = KEYVAL_LINE_TOML.match(ln)
            if not m2:
                keep_lines.append(ln)
                continue

            k, v = m2.group(1), m2.group(2)
            k_low = k.lower()

            if k_low in KEEP_TOPLEVEL:
                keep_lines.append(ln)
                continue

            if k_low in NUMERIC_KEYS:
                raw0 = _strip_quotes(v).strip()
                try:
                    val = str(int(raw0)) if raw0 else "0"
                except ValueError:
                    mnum = re.search(r"\d+", raw0)
                    val = mnum.group(0) if mnum else "0"
                moved[k] = val
                continue

            if k_low == "link":
                href, label = handle_link_value(v)

                moved.setdefault("link", []).append({
                    "href": href,
                    "label": label,
                })


            elif k_low in FILE_URL_KEYS:
                moved[k] = f'"{media_href_from_value(v)}"'
            else:
                label = label_from_wikilink_or_text(v)
                moved[k] = f'"{label}"' if not label.startswith('"') else label

        head2 = "\n".join([l for l in keep_lines if l.strip() != ""])
        if re.search(r'^\s*\[extra\]\s*$', head2, re.M):
            head2 = re.sub(
                r'(\[extra\][^\[]*)',
                lambda mm: mm.group(1) + "".join([f'\n{k} = {moved[k]}' for k in moved]),
                head2, flags=re.S
            )
        elif moved:
            head2 = (head2 + "\n\n[extra]\n" + "\n".join(f"{k} = {moved[k]}" for k in moved)).strip("\n")

        return assemble_front_matter(kind, head2, body)

    if kind == "yaml":
        md_items, head = _extract_yaml_block_list(head, "meta_description")

        def rewrite_md_item(s: str) -> str:
            s = WIKILINK_GLOBAL_RE.sub(
                lambda m: f"[{m.group(2) or m.group(1)}]"
                        f"({_vault_path_to_site_href(m.group(1), doc_parent_rel)})",
                s
            )

            def repl_url(m):
                url = m.group(1)
                label = _strip_url_scheme(url)
                return f"[{label}]({url})"

            s = URL_RE.sub(repl_url, s)

            return s


        moved = {}
        if md_items:
            moved["meta_description"] = [rewrite_md_item(s) for s in md_items]

        if footnotes:
            moved["notes"] = footnotes

        lines = head.splitlines()
        keep_lines = []

        for ln in lines:
            m2 = KEYVAL_LINE_YAML.match(ln)
            if not m2:
                keep_lines.append(ln)
                continue

            k, v = m2.group(1), m2.group(2)
            k_low = k.lower()

            if k_low == "meta_description":
                continue

            if k_low in KEEP_TOPLEVEL:
                keep_lines.append(ln)
                continue

            if k_low in NUMERIC_KEYS:
                raw0 = _strip_quotes(v).strip()
                try:
                    val = str(int(raw0)) if raw0 else "0"
                except ValueError:
                    mnum = re.search(r"\d+", raw0)
                    val = mnum.group(0) if mnum else "0"
                moved[k] = val
                continue

            if k_low == "link":
                href, label = handle_link_value(v)
                moved.setdefault("link", []).append({
                    "href": href,
                    "label": label,
                })


            elif k_low in FILE_URL_KEYS:
                moved[k] = f'"{media_href_from_value(v)}"'

            else:
                label = label_from_wikilink_or_text(v)
                moved[k] = f'"{label}"' if not label.startswith('"') else label


        head2 = "\n".join([l for l in keep_lines if l.strip() != ""])

        def _emit_yaml_extra_lines(moved_dict: dict) -> list[str]:
            lines = []
            for k, v in moved_dict.items():
                if k == "link":
                    lines.append("  link:")
                    for item in v:
                        if not isinstance(item, dict):
                            continue

                        href_q  = _yaml_quote(item.get("href", ""))
                        label_q = _yaml_quote(item.get("label", ""))
                        lines.append(f"    - href: {href_q}")
                        lines.append(f"      label: {label_q}")

                elif k == "notes":
                    lines.append("  notes:")
                    for item in v:
                        note_id = _yaml_quote(item.get("id", ""))
                        note_text = _yaml_quote(item.get("text", ""))
                        lines.append(f"    - id: {note_id}")
                        lines.append(f"      text: {note_text}")

                else:
                    if isinstance(v, list):
                        lines.append(f"  {k}:")
                        for item in v:
                            lines.append(f"    - {_yaml_quote(item)}")
                    else:
                        lines.append(f"  {k}: {_yaml_quote(v)}")

            return lines


        extra_lines = _emit_yaml_extra_lines(moved)

        if re.search(r'^\s*extra\s*:\s*$', head2, re.M):
            head2 = re.sub(
                r'(^\s*extra\s*:\s*$)',
                lambda mm: mm.group(1) + "\n" + "\n".join(extra_lines),
                head2,
                count=1,
                flags=re.M
            )
        elif moved:
            head2 = (head2.rstrip("\n") + "\nextra:\n" + "\n".join(extra_lines)).strip("\n")

        return assemble_front_matter(kind, head2, body)

    return text


# =============================================================================
# IMAGE BLOCKS (MULTI-IMAGE SET, :::images ... :::)
# =============================================================================


IMG_BLOCK_RE = re.compile(
    r':::\s*images\s*\n(?P<body>.*?)\n:::',
    re.S
)

def transform_image_blocks(doc_rel_dir: str, text: str) -> str:
    def repl(m):
        body = m.group("body").strip("\n")

        lines = [ln.strip() for ln in body.splitlines() if ln.strip()]
        imgs = []
        caption = None

        for ln in lines:
            # caption 문법
            if ln.lower().startswith("caption:"):
                caption = ln.split(":", 1)[1].strip()
                continue

            # markdown image
            mi = IMG_LINK_RE.match(ln)
            if not mi:
                continue

            alt = (mi.group(1) or "").strip()
            src = (mi.group(2) or "").strip()

            src_abs = to_web_media_path(doc_rel_dir, src)
            imgs.append((alt, src_abs))

        # 이미지가 하나도 없으면 원문 유지
        if not imgs:
            return m.group(0)

        html = []
        html.append('<figure class="img-set">')

        html.append('  <div class="img-set__images">')
        for alt, src_abs in imgs:
            html.append(f'    <img src="{src_abs}" alt="{alt}">')
        html.append('  </div>')

        if caption:
            html.append(f'  <figcaption>{caption}</figcaption>')

        html.append('</figure>')

        return "\n".join(html)

    return IMG_BLOCK_RE.sub(repl, text)




# =============================================================================
# IMAGE DIRECTIVES (SINGLE IMAGE VIA MARKDOWN TITLE)
# =============================================================================

def _parse_img_title_directives(title: str) -> dict:
    out = {}
    if not title:
        return out

    tokens = [t.strip() for t in title.split(';') if t.strip()]
    for raw in tokens:
        if '=' in raw:
            k, v = raw.split('=', 1)
            out[k.strip().lower()] = v.strip()
        elif ':' in raw:
            k, v = raw.split(':', 1)
            out[k.strip().lower()] = v.strip()
        else:
            out[raw.lower()] = True
    return out

def transform_markdown_images_with_directives(doc_rel_dir: str, text: str) -> str:
    def repl(m):
        alt, src, title = (m.group(1) or "").strip(), (m.group(2) or "").strip(), (m.group(3) or "").strip()
        src_abs = to_web_media_path(doc_rel_dir, src)
        opts = _parse_img_title_directives(title)
        if not opts:
            return f'![{alt}]({src_abs})'

        classes, style, data_attr = [], "", ""
        if 'full' in opts: classes.append('img--full')

        fixed = opts.get('fixed') or opts.get('max')
        if fixed:
            classes.append('img--fixed')
            try:
                style += f'max-width:{int(str(fixed).replace("px",""))}px;'
            except:
                pass

        fig = [f'<figure class="{" ".join(classes)}" style="{style}"{data_attr}>',
               f'  <img src="{src_abs}" alt="{alt}">']
        if 'caption' in opts and opts['caption']:
            fig.append(f'  <figcaption>{opts["caption"]}</figcaption>')
        fig.append('</figure>')
        return "\n".join(fig)

    return IMG_LINK_RE.sub(repl, text)

def transform_disabled_links(text: str) -> str:
    return DISABLED_LINK_RE.sub(
        r'<a class="is-disabled" aria-disabled="true">\1</a>',
        text
    )


# =============================================================================
# SECTION INDEX GENERATION
# =============================================================================

def ensure_index_for_section(section_rel: str):

    if section_rel == "":
        content_root = os.path.join(DEST, "content")

        en_path = os.path.join(content_root, "_index.md")
        kr_path = os.path.join(content_root, "_index.kr.md")

        text = """+++
title = ""
template = "section.html"
+++
"""

        if not os.path.exists(en_path):
            write_file(en_path, text)
            print("CREATE content/_index.md")

        if not os.path.exists(kr_path):
            write_file(kr_path, text)
            print("CREATE content/_index.kr.md")

        return

    dest_dir = os.path.join(DEST, "content", section_rel)
    os.makedirs(dest_dir, exist_ok=True)
    en_path = os.path.join(dest_dir, "_index.md")
    kr_path = os.path.join(dest_dir, "_index.kr.md")

    REDIRECT_SECTIONS = {
        "about":   {"en": "/about/about/",   "kr": "/kr/about/about/"},
        "contact": {"en": "/contact/contact/","kr": "/kr/contact/contact/"},
    }

    if section_rel in REDIRECT_SECTIONS:
        write_file(en_path, f"""+++
title = "{TITLES_EN.get(section_rel, section_rel)}"
redirect_to = "{REDIRECT_SECTIONS[section_rel]['en']}"
+++ 
""")
        write_file(kr_path, f"""+++
title = "{TITLES_KR.get(section_rel, section_rel)}"
redirect_to = "{REDIRECT_SECTIONS[section_rel]['kr']}"
+++ 
""")
        print(f"CREATE (redirect) _index.* @ {section_rel}")
        return

    needs_transparent = is_subsection(section_rel)
    tmpl = SECTION_TEMPLATES.get(section_rel, "allarchive.html")

    if not os.path.exists(en_path):
        lines = ["+++", f'title = "{TITLES_EN.get(section_rel,"archive")}"', f'template = "{tmpl}"']
        if needs_transparent: lines.append("transparent = true")
        lines += ['# sort_by = "extra.date_sort"', "+++"]
        write_file(en_path, "\n".join(lines) + "\n")

    if not os.path.exists(kr_path):
        lines = ["+++", f'title = "{TITLES_KR.get(section_rel,"아카이브")}"', f'template = "{tmpl}"']
        if needs_transparent: lines.append("transparent = true")
        lines += ['# sort_by = "extra.date_sort"', "+++"]
        write_file(kr_path, "\n".join(lines) + "\n")


# =============================================================================
# DESTINATION CLEANUP & PIPELINE
# =============================================================================

def should_skip_as_section_index(rel_path_from_vault: str) -> bool:
    lower = rel_path_from_vault.lower()
    return (
        lower.endswith("about/index.md") or lower.endswith("about/index.kr.md") or
        lower.endswith("contact/index.md") or lower.endswith("contact/index.kr.md")
    )

def clean_destination():
    content_dir = os.path.join(DEST, "content")
    media_dir   = os.path.join(DEST, "static", "media")
    if os.path.isdir(content_dir):
        shutil.rmtree(content_dir)
    os.makedirs(content_dir, exist_ok=True)
    if os.path.isdir(media_dir):
        shutil.rmtree(media_dir)

def process_markdown(src_path: str, rel_path_from_vault: str):
    if should_skip_as_section_index(rel_path_from_vault):
        return

    text = read_file(src_path)
    doc_parent_rel = str(pathlib.PurePosixPath(rel_path_from_vault).parent)
    if doc_parent_rel == ".": doc_parent_rel = ""

    kind, head, body = split_front_matter(text)
    body = rewrite_media_paths(doc_parent_rel, body)
    head, body = rewrite_wikilinks_in_body(kind, head, body, doc_parent_rel)

    body = rewrite_footnotes_in_body(body, doc_parent_rel)

    body = transform_image_blocks(doc_parent_rel, body)
    body = transform_markdown_images_with_directives(doc_parent_rel, body)
    body = transform_disabled_links(body)

    footnotes = extract_footnotes_for_meta(body, doc_parent_rel)


    text2 = assemble_front_matter(kind, head, body)
    text2 = ensure_normalized_date(text2)
    text2 = move_custom_fields_into_extra(text2, doc_parent_rel, footnotes)

    dest_path = os.path.join(DEST, "content", rel_path_from_vault)
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    write_file(dest_path, text2)
    copy_media_folder(os.path.dirname(src_path), doc_parent_rel)

def main():
    clean_destination()

    for sec in SECTIONS:
        ensure_index_for_section(sec)

    for root in SRC_CONTENT_ROOTS:
        src_root = os.path.join(VAULT, root)
        if not os.path.isdir(src_root):
            continue
        for dirpath, _, filenames in os.walk(src_root):
            for fn in filenames:
                if not MD_RE.search(fn): continue
                if fn.startswith("_index"): continue
                src_path = os.path.join(dirpath, fn)
                rel = os.path.relpath(src_path, VAULT).replace("\\", "/")
                process_markdown(src_path, rel)

    print("\nDone. Now run: zola serve")

if __name__ == "__main__":
    main()
