// _scripts/templater/new_bundle.js
// 폴더 + index.md/index.kr.md + content.md/content.kr.md 생성 + 프런트매터 자동 채우기
module.exports = async (tp) => {
  const categories = ["note", "reference"];
  const cat = await tp.system.suggester(categories, categories, true) || "note";
  const titleEn = await tp.system.prompt("English title (for URL/slug)") || "Untitled";
  const titleKr = await tp.system.prompt("Korean title (optional)") || "";
  const docnum  = await tp.system.prompt("Doc number (optional)") || "";
  const author  = await tp.system.prompt("Author (optional)", "JH") || "";
  const today   = tp.date.now("YYYY-MM-DD");

  // 슬러그(영문 제목 기준)
  const slug = titleEn.normalize("NFKD")
    .replace(/[^\w\s-]/g, "")
    .trim().toLowerCase()
    .replace(/\s+/g, "-");

  // 폴더 경로 (vault 기준 상대 경로)
  const folder = `posts/${cat}/${today}-${slug}`;
  try { await app.vault.createFolder(folder); } catch (_) {}

  // 공통 프런트매터 (Zola용 YAML)
  const front = (title) => `---
title: ${title}
date: ${today}
template: post.html
extra:
  category: ${cat}
${docnum ? `  doc_number: "${docnum}"\n` : ""}${author ? `  author: "${author}"\n` : ""}---
`;

  // 파일 생성
  await app.vault.create(`${folder}/index.md`, front(titleEn) + "\n");
  await app.vault.create(`${folder}/index.kr.md`, front(titleKr || titleEn) + "\n");

  // 참고용 본문 파일(옵시디언에서 쪼개쓰고 싶을 때)
  const partHeader = "---\nis_partial: true\n---\n\n";
  await app.vault.create(`${folder}/content.md`, partHeader);
  await app.vault.create(`${folder}/content.kr.md`, partHeader);

  // 이미지 넣을 자리 안내 노트
  try { await app.vault.create(`${folder}/README.txt`, "Drop images into this folder.\nUse ![](./image.jpg) from index.*.md\n"); } catch (_) {}

  new Notice(`Created bundle: ${folder}`);
  const file = app.vault.getAbstractFileByPath(`${folder}/index.md`);
  if (file) await app.workspace.getLeaf(true).openFile(file);
};
