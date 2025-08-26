import re, pathlib

ROOT = pathlib.Path("/Users/jaehyeonlee/Desktop/j-h/_staging").resolve()

# 스테이징 내 .md 인덱스 (절대경로 -> ROOT 기준 상대경로)
md_index = {p.resolve(): p.resolve().relative_to(ROOT).as_posix()
            for p in ROOT.rglob("*.md")}

# 이미지 제외, http/https/@/mailto/# 시작 제외, []와() 사이 여백/<> 허용
link_re = re.compile(
    r'(?<!\!)'          # not image
    r'\[([^\]]+)\]'     # [label]
    r'\s*\(\s*'         # spaces OK
    r'<?'               # optional '<'
    r'((?!https?://)(?!@/)(?!mailto:)(?!#)[^)>\s]+)'  # target
    r'>?'               # optional '>'
    r'\s*\)'            # spaces OK
)

changed_files = 0
total_converted = 0

def pick_candidate(base: pathlib.Path, is_kr: bool):
    """파일/디렉토리/확장자 유무 상관없이 실제 md를 찾아 반환 (leaf bundle 지원)"""
    cands = [
        base,
        base.with_suffix(".kr.md" if is_kr else ".md"),
        base / ("index.kr.md" if is_kr else "index.md"),
        base.with_suffix(".md" if is_kr else ".kr.md"),
        base / ("index.md" if is_kr else "index.kr.md"),
    ]
    for c in cands:
        rc = c.resolve()
        if rc in md_index:
            return rc
    return None

for path in ROOT.rglob("*.md"):
    text = path.read_text(encoding="utf-8")
    orig = text
    is_kr = path.name.endswith(".kr.md")

    def repl(m):
        global total_converted
        label, raw = m.group(1), m.group(2).strip()

        # 앵커 분리
        base_str, sep, anchor = raw.partition("#")

        # 1) 절대경로(/로 시작)면 ROOT 기준
        if base_str.startswith("/"):
            bases = [(ROOT / base_str.lstrip("/"))]
        else:
            # 2) 상대경로(현재 파일 기준) 먼저 시도
            base_rel = (path.parent / base_str)
            # 3) 실패 대비 루트 기준도 폴백으로 시도 (posts/... 처럼 루트 상대 링크)
            base_abs = (ROOT / base_str)
            bases = [base_rel, base_abs]

        picked = None
        for b in bases:
            picked = pick_candidate(b, is_kr)
            if picked:
                break
        if not picked:
            return m.group(0)  # 변환 불가 → 원문 유지

        rel = md_index[picked]
        total_converted += 1
        return f"[{label}](@/{rel}{('#'+anchor) if sep else ''})"

    text = link_re.sub(repl, text)
    if text != orig:
        path.write_text(text, encoding="utf-8")
        changed_files += 1

print(f"[fix_links] files_changed={changed_files}, links_converted={total_converted}")
