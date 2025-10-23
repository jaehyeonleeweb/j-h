#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, re, shutil, pathlib, sys

# === 경로 설정 (필요 시 수정) ===
VAULT = "/Users/jaehyeonlee/Library/Mobile Documents/iCloud~md~obsidian/Documents/j-h-web"
DEST  = "/Users/jaehyeonlee/web/j-h"

# Vault에서 가져올 섹션 루트 (보관함 최상위 폴더들)
SRC_CONTENT_ROOTS = ["about", "contact", "glossary", "method", "shop", "thought", "works"]
ROOT_SECTIONS = set(s.lower() for s in SRC_CONTENT_ROOTS)

# 목적지에 항상 있어야 하는 섹션(없으면 자동 생성)
SECTIONS = [
    "",  # 홈
    "about", "contact", "glossary", "method", "shop", "thought", "works",
    "works/project", "works/workshop", "works/workshop-practice",
]

# 🔤 영문/한국어 섹션 타이틀
TITLES_EN = {
    "": "all archive", "about": "about", "contact": "contact",
    "glossary": "glossary", "method": "methodology", "shop": "shop",
    "thought": "thought", "works": "works",
    "works/project": "project", "works/workshop": "workshop",
    "works/workshop-practice": "workshop practice",
}
TITLES_KR = {
    "": "아카이브", "about": "소개", "contact": "연락처",
    "glossary": "참조", "method": "방법론", "shop": "구매",
    "thought": "생각", "works": "작업",
    "works/project": "프로젝트", "works/workshop": "워크샵",
    "works/workshop-practice": "워크샵 실천",
}

# 섹션별 템플릿 매핑
SECTION_TEMPLATES = {
    "":               "section.html",        # all archive (리스트)
    "works":          "section/works.html",  # 썸네일 그리드
    "shop":           "section/shop.html",   # 썸네일 그리드
    "glossary":       "section.html",
    "method":         "section.html",
    "thought":        "section.html",
    # 하위 섹션들은 transparent 규칙으로 처리
}

# 파일 경로(미디어)로 간주할 커스텀 키
FILE_URL_KEYS = {"thumbnail", "image", "poster"}

# ---------- 정규식 ----------
MD_RE = re.compile(r"\.md$", re.IGNORECASE)
IMG_LINK_RE = re.compile(r'!\[([^\]]*)\]\((?:\s*)(media/[^)]+)(?:\s*)\)')
LINK_RE     = re.compile(r'\[([^\]]*)\]\((?:\s*)(media/[^)]+)(?:\s*)\)')

FM_TOML_RE = re.compile(r'^\s*\+{3}\s*\n(.*?)\n\+{3}\s*', re.S)
FM_YAML_RE = re.compile(r'^\s*-{3}\s*\n(.*?)\n-{3}\s*', re.S)

DATE_FLEX_RE = re.compile(r'^\s*(?P<y>\d{4})(?:[.\-\/\s]*(?P<m>\d{1,2})(?:[.\-\/\s]*(?P<d>\d{1,2}))?)?\s*$')

# Obsidian [[path|label]]
WIKILINK_GLOBAL_RE = re.compile(r'\[\[\s*([^\]|]+?)(?:\|([^\]]+))?\s*\]\]')
WIKILINK_ONE_RE    = re.compile(r'^\[\[\s*([^\]|]+?)(?:\|([^\]]+))?\s*\]\]$')

KEYVAL_LINE_TOML = re.compile(r'^\s*([A-Za-z0-9_\-]+)\s*=\s*(.+?)\s*$')
KEYVAL_LINE_YAML = re.compile(r'^\s*([A-Za-z0-9_\-]+)\s*:\s*(.+?)\s*$')

# 상위에 유지할 프론트매터 키
KEEP_TOPLEVEL = {"title", "date", "template", "draft", "weight", "slug", "taxonomies"}

# ---------- 유틸 ----------
def read_file(p):
    with open(p, "r", encoding="utf-8") as f:
        return f.read()

def write_file(p, s):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write(s)

def is_subsection(section_rel: str) -> bool:
    # 예: 'works/project' 같은 하위 섹션만 True
    return "/" in section_rel if section_rel else False

# ---------- 미디어 경로 재작성 ----------
def to_web_media_path(doc_parent_rel: str, media_rel: str) -> str:
    """
    media_rel이 'media/...' 또는 '/media/...'일 때
    웹 기준 경로로 변환.
    예:
      doc_parent_rel = 'works/project'
      media_rel = 'media/thumbnail/th_pr-001.webp'
      -> '/media/works/project/thumbnail/th_pr-001.webp'
    """
    media_rel = (media_rel or "").strip().lstrip("/")
    # 이미 사이트 절대경로면 바로 정규화 후 반환
    if media_rel.startswith("media/") is False and media_rel.startswith("/media/"):
        out = media_rel
        # 중복된 '/media/<parent>/media/' 패턴 정리
        if doc_parent_rel:
            out = out.replace(f"/media/{doc_parent_rel}/media/", f"/media/{doc_parent_rel}/")
        return out
    # 'media/...' 상대 경로 → 사이트 절대경로
    if media_rel.startswith("media/"):
        media_rel = media_rel[len("media/"):]  # 'thumbnail/th_pr-001.webp'
    base = f"/media/{doc_parent_rel}/" if doc_parent_rel else "/media/"
    path = os.path.join(base, media_rel).replace("\\", "/")
    return path.replace("//", "/")

def rewrite_media_paths(doc_rel_dir: str, text: str) -> str:
    def repl_img(m):
        alt, mrel = m.group(1), m.group(2)
        return f'![{alt}]({to_web_media_path(doc_rel_dir, mrel)})'
    text = IMG_LINK_RE.sub(repl_img, text)

    def repl_link(m):
        label, mrel = m.group(1), m.group(2)
        return f'[{label}]({to_web_media_path(doc_rel_dir, mrel)})'
    text = LINK_RE.sub(repl_link, text)
    return text

def copy_media_folder(src_doc_dir: str, doc_parent_rel: str):
    media_src = os.path.join(src_doc_dir, "media")
    if not os.path.isdir(media_src):
        return
    dest_media_dir = os.path.join(DEST, "static", "media", doc_parent_rel)
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

# ---------- 프론트매터 ----------
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

# ---------- 날짜 정규화 ----------
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

def pre_sanitize_content():
    content_root = pathlib.Path(DEST) / "content"
    if not content_root.exists():
        return
    fixed = 0
    for p in content_root.rglob("*.md"):
        t = read_file(p)
        new_t, changed = sanitize_front_matter_text(t)
        if changed:
            write_file(str(p), new_t)
            fixed += 1
            print(f"FIXED {p}")
    if fixed:
        print(f"[sanitize] fixed {fixed} file(s).")

def ensure_normalized_date(text: str) -> str:
    new_t, _ = sanitize_front_matter_text(text)
    return new_t

# ---------- 위키링크/경로 ----------
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
    href = href.replace("//", "/")
    return href

def rewrite_wikilinks_in_body(kind: str, head: str, body: str, doc_parent_rel: str):
    def repl(m):
        path = (m.group(1) or "").strip()
        label = (m.group(2) or "").strip()
        href = _vault_path_to_site_href(path, doc_parent_rel)
        if not label:
            label = href.strip("/").split("/")[-1] or href
        return f'[{label}]({href})'
    return head, WIKILINK_GLOBAL_RE.sub(repl, body)

# ---------- 커스텀 메타 → extra 이동 ----------
def _strip_quotes(s: str) -> str:
    s = s.strip()
    if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
        return s[1:-1]
    return s

def move_custom_fields_into_extra(text: str, doc_parent_rel: str) -> str:
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
        """
        FILE_URL_KEYS용:
          - 값 어딘가에 [[...]] 가 있으면 내부 경로만 추출
          - '/media/...'로 시작하면 그대로 사용(중복 '/media/<parent>/media/'는 정규화)
          - '...media/...'를 포함하면 그 지점부터를 'media/...'로 간주해 웹 경로로 변환
        """
        raw0 = _strip_quotes(raw).strip()
        if not raw0:
            return raw0

        # 1) 위키링크가 문자열 어딘가에 섞여 있는 경우까지 처리
        m_any = re.search(r'\[\[\s*([^\]|]+)', raw0)
        candidate = (m_any.group(1).strip() if m_any else raw0)

        # 2) 이미 사이트 절대경로인 경우
        if candidate.startswith("/media/"):
            out = candidate
            if doc_parent_rel:
                out = out.replace(f"/media/{doc_parent_rel}/media/", f"/media/{doc_parent_rel}/")
            return out

        # 3) '...media/...' 포함 → 그 지점부터 'media/...'만 추출
        idx = candidate.find("media/")
        if idx != -1:
            media_rel = candidate[idx:]  # 'media/...'
            return to_web_media_path(doc_parent_rel, media_rel)

        # 4) 그 외는 원본 유지(외부 URL 등)
        return candidate

    if kind == "toml":
        lines = head.splitlines()
        keep_lines, moved = [], {}
        for ln in lines:
            m2 = KEYVAL_LINE_TOML.match(ln)
            if not m2:
                keep_lines.append(ln); continue
            k, v = m2.group(1), m2.group(2)
            k_low = k.lower()
            if k_low in KEEP_TOPLEVEL:
                keep_lines.append(ln); continue

            if k_low == "link":
                href, label = handle_link_value(v)
                moved["link"] = f'"{href}"'
                moved["link_label"] = f'"{label}"'
            elif k_low in FILE_URL_KEYS:
                href = media_href_from_value(v)
                moved[k] = f'"{href}"'
            else:
                label = label_from_wikilink_or_text(v)
                if not (label.startswith('"') and label.endswith('"')):
                    label = f'"{label}"'
                moved[k] = label

        head2 = "\n".join([l for l in keep_lines if l.strip() != ""])
        if re.search(r'^\s*\[extra\]\s*$', head2, re.M):
            head2 = re.sub(
                r'(\[extra\][^\[]*)',
                lambda mm: mm.group(1) + "".join([f'\n{k} = {moved[k]}' for k in moved]),
                head2, count=1, flags=re.S
            )
        elif moved:
            extra_lines = ["", "[extra]"] + [f'{k} = {moved[k]}' for k in moved]
            head2 = (head2 + "\n" + "\n".join(extra_lines)).strip("\n")
        return assemble_front_matter(kind, head2, body)

    if kind == "yaml":
        lines = head.splitlines()
        keep_lines, moved = [], {}
        for ln in lines:
            m2 = KEYVAL_LINE_YAML.match(ln)
            if not m2:
                keep_lines.append(ln); continue
            k, v = m2.group(1), m2.group(2)
            k_low = k.lower()
            if k_low in KEEP_TOPLEVEL:
                keep_lines.append(ln); continue

            if k_low == "link":
                href, label = handle_link_value(v)
                moved["link"] = f'"{href}"'
                moved["link_label"] = f'"{label}"'
            elif k_low in FILE_URL_KEYS:
                href = media_href_from_value(v)
                moved[k] = f'"{href}"'
            else:
                label = label_from_wikilink_or_text(v)
                if not (label.startswith('"') and label.endswith('"')):
                    label = f'"{label}"'
                moved[k] = label

        head2 = "\n".join([l for l in keep_lines if l.strip() != ""])
        if re.search(r'^\s*extra\s*:\s*$', head2, re.M):
            head2 = re.sub(
                r'(^\s*extra\s*:\s*$)',
                lambda mm: mm.group(1) + "".join([f'\n  {k}: {moved[k]}' for k in moved]),
                head2, count=1, flags=re.M
            )
        elif moved:
            extra_lines = ["extra:"] + [f'  {k}: {moved[k]}' for k in moved]
            head2 = (head2.rstrip("\n") + "\n" + "\n".join(extra_lines)).strip("\n")
        return assemble_front_matter(kind, head2, body)

    return text

# ---------- 섹션 인덱스 생성/보정 ----------
def ensure_index_for_section(section_rel: str):
    dest_dir = os.path.join(DEST, "content", section_rel) if section_rel else os.path.join(DEST, "content")
    os.makedirs(dest_dir, exist_ok=True)
    en_path = os.path.join(dest_dir, "_index.md")
    kr_path = os.path.join(dest_dir, "_index.kr.md")

    # ─── (1) about/contact는 '리디렉트 전용'으로 강제 생성 ─────────────────
    REDIRECT_SECTIONS = {
        "about":   {"en": "/about/about/",   "kr": "/kr/about/about/"},
        "contact": {"en": "/contact/contact/","kr": "/kr/contact/contact/"},
    }
    if section_rel in REDIRECT_SECTIONS:
        en_redirect = REDIRECT_SECTIONS[section_rel]["en"]
        kr_redirect = REDIRECT_SECTIONS[section_rel]["kr"]

        en_text = f"""+++
title = "{TITLES_EN.get(section_rel, section_rel)}"
redirect_to = "{en_redirect}"
+++ 
"""
        kr_text = f"""+++
title = "{TITLES_KR.get(section_rel, section_rel)}"
redirect_to = "{kr_redirect}"
+++ 
"""

        write_file(en_path, en_text)
        write_file(kr_path, kr_text)
        print(f"CREATE (redirect) _index.* @ {section_rel or '/'}")
        return

    # ─── (2) 그 외 섹션은 기존 로직(템플릿/transparent) 유지 ───────────────
    needs_transparent = is_subsection(section_rel)
    tmpl = SECTION_TEMPLATES.get(section_rel, "section.html")

    if not os.path.exists(en_path):
        title = TITLES_EN.get(section_rel, "archive")
        en_lines = ["+++", f'title = "{title}"', f'template = "{tmpl}"']
        if needs_transparent: en_lines.append("transparent = true")
        en_lines.append('# sort_by = "extra.date_sort"')
        en_lines.append("+++")
        write_file(en_path, "\n".join(en_lines) + "\n")
        print(f"CREATE _index.md @ {section_rel or '/'}")

    if not os.path.exists(kr_path):
        title = TITLES_KR.get(section_rel, "아카이브")
        kr_lines = ["+++", f'title = "{title}"', f'template = "{tmpl}"']
        if needs_transparent: kr_lines.append("transparent = true")
        kr_lines.append('# sort_by = "extra.date_sort"')
        kr_lines.append("+++")
        write_file(kr_path, "\n".join(kr_lines) + "\n")
        print(f"CREATE _index.kr.md @ {section_rel or '/'}")

    def ensure_transparent_flag(path: str):
        if not needs_transparent or not os.path.exists(path): return
        txt = read_file(path)
        if "transparent" in txt: return
        kind, head, body = split_front_matter(txt)
        new_txt = assemble_front_matter(kind, "transparent = true\n" + head.lstrip("\n"), body) if kind else "transparent = true\n" + txt
        write_file(path, new_txt); print(f"PATCH transparent=true → {path}")

    ensure_transparent_flag(en_path); ensure_transparent_flag(kr_path)

# ---------- 복사 제외 규칙 ----------
def should_skip_as_section_index(rel_path_from_vault: str) -> bool:
    lower = rel_path_from_vault.lower()
    return (
        lower.endswith("about/index.md") or lower.endswith("about/index.kr.md") or
        lower.endswith("contact/index.md") or lower.endswith("contact/index.kr.md")
    )

# ---------- 목적지 정리 ----------
def clean_destination():
    content_dir = os.path.join(DEST, "content")
    media_dir   = os.path.join(DEST, "static", "media")
    if os.path.isdir(content_dir):
        shutil.rmtree(content_dir); print("CLEAN content/ (removed)")
    os.makedirs(content_dir, exist_ok=True)
    if os.path.isdir(media_dir):
        shutil.rmtree(media_dir); print("CLEAN static/media/ (removed)")

# ---------- 문서 처리 파이프라인 ----------
def process_markdown(src_path: str, rel_path_from_vault: str):
    if should_skip_as_section_index(rel_path_from_vault):
        print(f"SKIP {rel_path_from_vault} (handled by auto _index)")
        return

    text = read_file(src_path)
    doc_parent_rel = str(pathlib.PurePosixPath(rel_path_from_vault).parent)
    if doc_parent_rel == ".": doc_parent_rel = ""

    # 프론트매터/본문 분리
    kind, head, body = split_front_matter(text)

    # 1) media 경로 + 본문 위키링크 변환
    body = rewrite_media_paths(doc_parent_rel, body)
    head, body = rewrite_wikilinks_in_body(kind, head, body, doc_parent_rel)

    # 합치기
    text2 = assemble_front_matter(kind, head, body)

    # 2) 날짜 정규화
    text2 = ensure_normalized_date(text2)

    # 3) 커스텀 메타 extra로 이동 (link→href/label, 파일키→웹경로, 그 외는 라벨)
    text2 = move_custom_fields_into_extra(text2, doc_parent_rel)

    # 4) 목적지로 복사
    dest_rel = rel_path_from_vault
    dest_path = os.path.join(DEST, "content", dest_rel)
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    write_file(dest_path, text2)

    # 5) media 폴더 복사
    copy_media_folder(os.path.dirname(src_path), doc_parent_rel)

    print(f"OK  {rel_path_from_vault} → content/{dest_rel}")

def main():
    # 0) 깨끗한 동기화
    clean_destination()

    # 1) 필수 섹션 인덱스 보장 (+ 템플릿/transparent 규칙 적용)
    for sec in SECTIONS:
        ensure_index_for_section(sec)

    # 2) 섹션/페이지 복사
    for root in SRC_CONTENT_ROOTS:
        src_root = os.path.join(VAULT, root)
        if not os.path.isdir(src_root): continue
        for dirpath, _, filenames in os.walk(src_root):
            for fn in filenames:
                if not MD_RE.search(fn): continue
                if fn.startswith("_index"): continue  # Vault엔 _index 안 만듦
                src_path = os.path.join(dirpath, fn)
                rel = os.path.relpath(src_path, VAULT).replace("\\", "/")
                process_markdown(src_path, rel)

    print("\nDone. Now run: zola serve")

if __name__ == "__main__":
    main()
