#!/usr/bin/env node
/**
 * Open-source release audit: secrets, PII, internal references and file sizes.
 *
 *   node scripts/oss-audit.mjs                  # files that would ship (tracked + untracked, not ignored)
 *   node scripts/oss-audit.mjs --history        # also every added line in `git log -p --all`
 *   node scripts/oss-audit.mjs --json out.json  # machine-readable findings
 *   node scripts/oss-audit.mjs --fail-on high   # only fail on high (default: low = any finding)
 *   node scripts/oss-audit.mjs --max-mb 5       # size threshold (default 5 MB)
 *
 * Matched values are never printed: findings carry file:line, rule and severity only.
 * Suppress a reviewed false positive with `oss-audit:allow` on the same line.
 * Exit code: 0 clean, 1 findings at or above --fail-on, 2 usage or git error.
 */
import { spawn, spawnSync } from "node:child_process";
import { createHmac } from "node:crypto";
import { readFileSync, statSync, writeFileSync } from "node:fs";
import { userInfo } from "node:os";
import { createInterface } from "node:readline";
import { gunzipSync } from "node:zlib";

const args = process.argv.slice(2);
const opt = (name, fallback) => {
  const i = args.indexOf(name);
  return i >= 0 && args[i + 1] ? args[i + 1] : fallback;
};
const HISTORY = args.includes("--history");
const JSON_OUT = opt("--json", null);
const FAIL_ON = opt("--fail-on", "low");
const MAX_BYTES = Number(opt("--max-mb", "5")) * 1024 * 1024;
const RANK = { low: 1, medium: 2, high: 3 };
if (!RANK[FAIL_ON]) {
  console.error(`--fail-on must be low, medium or high`);
  process.exit(2);
}

// Large files that are reviewed and intentionally tracked (see RELEASE_CHECKLIST.md, "Size").
const ALLOW_LARGE = [/^models\/keel-[23]\/onnx\/model_quantized\.onnx$/];
// This scanner's own rule table would match itself.
const SKIP_PATHS = [/^scripts\/oss-audit\.mjs$/, /^node_modules\//];

// Keel's local bearer is HMAC-derived from a built-in default secret, so the default token is
// computable by anyone with the source. Flag any literal copy of it (and of a KEEL_SECRET-derived one).
const keelTokens = new Set();
for (const secret of ["keel-local-decider", process.env.KEEL_SECRET?.trim()].filter(Boolean)) {
  keelTokens.add(createHmac("sha256", secret).update("keel-local-decider-v1").digest("base64url").slice(0, 40));
}

const localUsers = new Set(
  [userInfo().username, process.env.USERNAME, process.env.USER]
    .filter((u) => u && u.length >= 4 && !/^(user|admin|runner|root|node)$/i.test(u))
    .map((u) => u.toLowerCase()),
);
const escapeRe = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

const EMAIL_OK =
  /(@users\.noreply\.github\.com|@example\.(com|org|net)|\.(invalid|example|test|localhost)$|@(contoso|fabrikam|northwindtraders|adventure-works)\.com$|noreply@|@[\w.-]*\.(png|jpe?g|svg|webp|gif)$|^git@)/i;

// Deliberately fake secrets inside eval cases and data generators (Keel must learn to stop on
// them). Reviewed by hand: reported as low, never silently dropped, because provider-shaped
// values (AWS key ids, PEM headers) can still trip GitHub push protection.
const FIXTURES = [
  /^src\/lib\/decider\/eval[\w-]*\.ts$/,
  /^training\/keel\/(gen_|families)\w*\.py$/,
  /^artifacts\/parity\/blind\//,
];
const FIXTURE_RULES = new Set(["aws-key", "private-key", "bearer-literal", "conn-string", "secret-assignment", "email", "jwt", "openai-key", "github-token"]);
const PATH_USER_OK = /^(public|default|default user|all users|you|your-?name|username|<[^>]+>|%username%|\$env:username|\$\{?user(name)?\}?|runner|runneradmin|user|me|name|example)$/i;

/** @type {{id:string, severity:"low"|"medium"|"high", type:string, re:RegExp, check?:(m:RegExpExecArray, line:string)=>boolean}[]} */
const RULES = [
  { id: "private-key", severity: "high", type: "private key block", re: /-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP )?PRIVATE KEY-----/g },
  { id: "aws-key", severity: "high", type: "AWS access key id", re: /\b(?:AKIA|ASIA)[0-9A-Z]{16}\b/g, check: (m) => !m[0].endsWith("EXAMPLE") },
  { id: "github-token", severity: "high", type: "GitHub token", re: /\b(?:gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{60,})\b/g },
  { id: "openai-key", severity: "high", type: "OpenAI/Anthropic-style API key", re: /\bsk-(?:proj-|ant-|or-v1-)?[A-Za-z0-9_-]{32,}\b/g },
  { id: "slack-token", severity: "high", type: "Slack token", re: /\bxox[abprs]-[A-Za-z0-9-]{10,}\b/g },
  { id: "google-key", severity: "high", type: "Google API key", re: /\bAIza[0-9A-Za-z_-]{35}\b/g },
  { id: "hf-token", severity: "high", type: "Hugging Face token", re: /\bhf_[A-Za-z0-9]{30,}\b/g },
  { id: "azure-key", severity: "high", type: "Azure storage/service key or SAS", re: /(?:AccountKey=[A-Za-z0-9+/=]{20,}|SharedAccessSignature=|[?&]sig=[A-Za-z0-9%+/=]{30,})/g },
  { id: "jwt", severity: "high", type: "JSON Web Token", re: /\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}/g },
  {
    id: "conn-string",
    severity: "high",
    type: "connection string with credentials",
    re: /\b[a-z][a-z0-9+.-]{1,20}:\/\/([^\s:/@'"`]+):([^\s@/'"`]{3,})@[\w.-]+/gi,
    check: (m) => !/^(\$\{?|<|\*+$|x+$|pass(word)?$|secret$|changeme$|postgres$)/i.test(m[2]) && !/^(user|username|<)/i.test(m[1]),
  },
  {
    id: "keel-default-bearer",
    severity: "high",
    type: "literal Keel bearer (HMAC of the built-in default secret)",
    re: keelTokens.size ? new RegExp([...keelTokens].map(escapeRe).join("|"), "g") : /$^/g,
  },
  {
    id: "bearer-literal",
    severity: "high",
    type: "literal bearer token",
    re: /\bBearer\s+([A-Za-z0-9_\-.=+/]{20,})/g,
    check: (m) => !keelTokens.has(m[1]) && !/^(\$|\{|<|x{6,}|\*{3,}|YOUR|REPLACE|TOKEN)/i.test(m[1]),
  },
  {
    id: "secret-assignment",
    severity: "medium",
    type: "hard-coded secret-like assignment",
    re: /\b(?:api[_-]?key|secret|token|passw(?:or)?d|client[_-]?secret)["']?\s*[:=]\s*["']([A-Za-z0-9_\-+/=.]{20,})["']/gi,
    check: (m) => !/^(\$|process\.env|import\.meta|<|x{6,}|your|replace|example)/i.test(m[1]),
  },
  {
    id: "local-user-path",
    severity: "medium",
    type: "local user path",
    re: /(?:\b[A-Za-z]:[\\/]{1,2}Users[\\/]{1,2}|(?<![\w.])\/(?:home|Users)\/)([^\\/\s"'`<>:;,)]+)/g,
    check: (m) => !PATH_USER_OK.test(m[1]),
  },
  {
    id: "internal-host",
    severity: "medium",
    type: "internal Microsoft host or URL",
    re: /\b(?:[\w-]+\.)*(?:corp\.microsoft\.com|redmond\.corp|microsoft\.sharepoint(?:-df)?\.com|[\w-]+-my\.sharepoint\.com|microsoftapc\.sharepoint\.com|dev\.azure\.com\/[\w-]+|([\w-]+)\.visualstudio\.com|packagefeedproxy\.microsoft\.io|eng\.ms|aka\.ms\/[\w-]*internal|msazure\.\w+|teams\.microsoft\.com\/l\/|microsoft\.enterprise\.slack\.com|onebranch\.\w+|osgwiki\.com|[\w-]+\.trafficmanager\.net)\b/gi,
    // code.visualstudio.com and the Marketplace are public.
    check: (m) => !/^(code|marketplace|www)$/i.test(m[1] ?? ""),
  },
  {
    id: "email",
    severity: "medium",
    type: "email address",
    re: /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b/g,
    check: (m) => !EMAIL_OK.test(m[0]) && !/@\d+\.\d+/.test(m[0]),
  },
  {
    id: "local-username",
    severity: "low",
    type: "local machine username",
    re: localUsers.size ? new RegExp(`\\b(?:${[...localUsers].map(escapeRe).join("|")})\\b`, "gi") : /$^/g,
  },
  {
    id: "private-ip",
    severity: "low",
    type: "private network address",
    re: /\b(?:10\.(?:\d{1,3}\.){2}\d{1,3}|192\.168\.\d{1,3}\.\d{1,3}|172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3})\b/g,
  },
];

function scanText(text, where, out) {
  const lines = text.split(/\r?\n/);
  for (let i = 0; i < lines.length; i++) scanLine(lines[i], where.path, i + 1, where.extra, out);
}

function scanLine(line, path, lineNo, extra, out) {
  if (line.length > 20000) line = line.slice(0, 20000);
  if (line.includes("oss-audit:allow")) return;
  for (const rule of RULES) {
    rule.re.lastIndex = 0;
    let m;
    const seen = new Set();
    while ((m = rule.re.exec(line))) {
      if (m[0] === "") break;
      if (rule.check && !rule.check(m, line)) continue;
      if (seen.has(rule.id)) continue;
      seen.add(rule.id);
      const fixture = FIXTURE_RULES.has(rule.id) && FIXTURES.some((re) => re.test(path));
      out.push({
        rule: rule.id,
        severity: fixture ? "low" : rule.severity,
        type: fixture ? `${rule.type}; synthetic eval/training fixture` : rule.type,
        path,
        line: lineNo,
        ...extra,
      });
    }
  }
}

const isBinary = (buf) => buf.subarray(0, 8000).includes(0);

/** Minimal ustar reader so tracked tarballs are scanned too. */
function* tarEntries(buf) {
  let off = 0;
  while (off + 512 <= buf.length) {
    const name = buf.toString("utf8", off, off + 100).replace(/\0.*$/s, "");
    if (!name) break;
    const prefix = buf.toString("utf8", off + 345, off + 500).replace(/\0.*$/s, "");
    const size = parseInt(buf.toString("utf8", off + 124, off + 136).replace(/\0.*$/s, "").trim() || "0", 8);
    const type = String.fromCharCode(buf[off + 156] || 48);
    const start = off + 512;
    if (type === "0" || type === "\0") yield { name: prefix ? `${prefix}/${name}` : name, data: buf.subarray(start, start + size) };
    off = start + Math.ceil(size / 512) * 512;
  }
}

function git(argv) {
  const r = spawnSync("git", argv, { encoding: "buffer", maxBuffer: 1 << 30 });
  if (r.status !== 0) {
    console.error(`git ${argv.join(" ")} failed: ${r.stderr?.toString() ?? ""}`);
    process.exit(2);
  }
  return r.stdout;
}

const findings = [];
const sizes = [];

// 1. Working tree: everything that would ship.
const tracked = new Set(git(["ls-files", "-z"]).toString("utf8").split("\0").filter(Boolean));
const files = git(["ls-files", "-z", "-co", "--exclude-standard"]).toString("utf8").split("\0").filter(Boolean);
for (const path of [...new Set(files)]) {
  if (SKIP_PATHS.some((re) => re.test(path))) continue;
  let st;
  try {
    st = statSync(path);
  } catch {
    continue; // deleted in the working tree
  }
  if (!st.isFile()) continue;
  const status = tracked.has(path) ? "tracked" : "untracked";
  if (st.size > MAX_BYTES) {
    const allowed = ALLOW_LARGE.some((re) => re.test(path));
    sizes.push({ path, bytes: st.size, status, allowed });
    if (!allowed) findings.push({ rule: "large-file", severity: "medium", type: `file over ${MAX_BYTES / 1048576} MB (${status})`, path, line: 0 });
    if (st.size > 64 * 1024 * 1024) continue;
  }
  const buf = readFileSync(path);
  if (/\.(tar\.gz|tgz)$/i.test(path)) {
    try {
      for (const entry of tarEntries(gunzipSync(buf))) {
        if (!isBinary(entry.data)) scanText(entry.data.toString("utf8"), { path: `${path}!${entry.name}`, extra: { source: "tree" } }, findings);
      }
    } catch {
      findings.push({ rule: "unreadable-archive", severity: "low", type: "archive could not be inspected", path, line: 0 });
    }
    continue;
  }
  if (isBinary(buf)) continue;
  scanText(buf.toString("utf8"), { path, extra: { source: "tree" } }, findings);
}

// 2. History: every added line of every commit reachable from any ref.
async function scanHistory() {
  const child = spawn("git", ["log", "-p", "--all", "--no-color", "--no-ext-diff", "-U0", "--format=@@COMMIT %H"], { stdio: ["ignore", "pipe", "inherit"] });
  const rl = createInterface({ input: child.stdout, crlfDelay: Infinity });
  const found = [];
  let commit = "";
  let path = "";
  let lineNo = 0;
  for await (const raw of rl) {
    if (raw.startsWith("@@COMMIT ")) {
      commit = raw.slice(9, 21);
      continue;
    }
    if (raw.startsWith("+++ ")) {
      path = raw.startsWith("+++ b/") ? raw.slice(6) : "";
      continue;
    }
    if (raw.startsWith("@@ ")) {
      const m = /\+(\d+)/.exec(raw);
      lineNo = m ? Number(m[1]) : 0;
      continue;
    }
    if (!path || SKIP_PATHS.some((re) => re.test(path))) continue;
    if (raw.startsWith("+")) {
      scanLine(raw.slice(1), path, lineNo, { source: "history", commit }, found);
      lineNo++;
    }
  }
  await new Promise((resolve) => child.on("close", resolve));
  // Report each (rule, path, line) once, at the oldest commit that introduced it (git log is newest-first).
  const unique = new Map();
  for (const f of found) unique.set(`${f.rule}|${f.path}|${f.line}`, f);
  return [...unique.values()];
}
if (HISTORY) findings.push(...(await scanHistory()));

// Report.
const bySev = { high: 0, medium: 0, low: 0 };
for (const f of findings) bySev[f.severity]++;
findings.sort((a, b) => RANK[b.severity] - RANK[a.severity] || a.path.localeCompare(b.path) || a.line - b.line);
for (const f of findings) {
  const loc = f.line ? `${f.path}:${f.line}` : f.path;
  const src = f.source === "history" ? ` [history ${f.commit}]` : "";
  console.log(`${f.severity.toUpperCase().padEnd(6)} ${f.rule.padEnd(20)} ${loc}${src}  (${f.type})`);
}
if (sizes.length) {
  console.log(`\nFiles over ${MAX_BYTES / 1048576} MB that would ship:`);
  for (const s of sizes) console.log(`  ${(s.bytes / 1048576).toFixed(1).padStart(7)} MB  ${s.status.padEnd(9)} ${s.path}${s.allowed ? "  (allowed)" : ""}`);
}
console.log(`\nscanned ${files.length} files${HISTORY ? " + git history" : ""}: high ${bySev.high}, medium ${bySev.medium}, low ${bySev.low}`);
if (JSON_OUT) writeFileSync(JSON_OUT, JSON.stringify({ generatedAt: new Date().toISOString(), counts: bySev, findings, sizes }, null, 2));
const failing = findings.filter((f) => RANK[f.severity] >= RANK[FAIL_ON]).length;
process.exit(failing ? 1 : 0);
