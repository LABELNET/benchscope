#!/usr/bin/env node
// 检查 zh.js / en.js 是否存在重复键，以及两文件键集合是否一致。
// 仅依赖 Node 内置模块。
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const i18nDir = path.resolve(__dirname, '..', 'src', 'i18n');
const files = {
  zh: path.join(i18nDir, 'zh.js'),
  en: path.join(i18nDir, 'en.js'),
};

// 简单正则提取顶层键：行首两个空格 + 标识符 + 冒号
const KEY_RE = /^ {2}([A-Za-z_$][\w$]*):/;

function extractKeys(file) {
  const src = fs.readFileSync(file, 'utf8');
  const lines = src.split('\n');
  const seen = new Map(); // key -> [lineNumbers]
  for (let i = 0; i < lines.length; i++) {
    const m = lines[i].match(KEY_RE);
    if (m) {
      const key = m[1];
      if (!seen.has(key)) seen.set(key, []);
      seen.get(key).push(i + 1);
    }
  }
  return seen;
}

let failed = false;

const keysByFile = {};
for (const [name, file] of Object.entries(files)) {
  const seen = extractKeys(file);
  keysByFile[name] = seen;
  const dups = [...seen.entries()].filter(([, lines]) => lines.length > 1);
  if (dups.length > 0) {
    failed = true;
    console.error(`[${name}] duplicate keys found in ${path.relative(i18nDir, file)}:`);
    for (const [key, lines] of dups) {
      console.error(`  ${key}: lines ${lines.join(', ')}`);
    }
  }
}

// 比对键集合
const zhKeys = new Set(keysByFile.zh.keys());
const enKeys = new Set(keysByFile.en.keys());
const onlyZh = [...zhKeys].filter((k) => !enKeys.has(k));
const onlyEn = [...enKeys].filter((k) => !zhKeys.has(k));
if (onlyZh.length > 0) {
  failed = true;
  console.error(`[zh] keys missing in en.js: ${onlyZh.join(', ')}`);
}
if (onlyEn.length > 0) {
  failed = true;
  console.error(`[en] keys missing in zh.js: ${onlyEn.join(', ')}`);
}

if (failed) {
  process.exit(1);
}

console.log('OK, no duplicate keys, zh/en keys match');
