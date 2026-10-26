import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import { readFile } from "node:fs/promises";
import path from "node:path";
import process from "node:process";

const root = process.cwd();
const protectedPaths = new Set([
  "archive/legacy/selected_cases.json",
  "data/case_database.json",
  "data/cn_medical_cases_deidentified.json",
  "data/us_cases_deidentified.json",
  "data/formal/gold_labels_draft.json",
  "data/formal/source_manifest.csv",
]);
const requiredPublicPaths = new Set([
  "data/formal/case_payloads.json",
  "data/public/case_index.csv",
  "data/public/public_layer_manifest.json",
]);
const findings = [];

function add(code, filePath = null) {
  findings.push({ issue_code: code, path: filePath });
}

function sha256CanonicalText(textValue) {
  const normalized = String(textValue).replace(/^\uFEFF/u, "").replace(/\r\n?/gu, "\n");
  return createHash("sha256").update(normalized, "utf8").digest("hex");
}

async function readText(relativePath) {
  try {
    return await readFile(path.join(root, relativePath), "utf8");
  } catch {
    add("REQUIRED_PUBLIC_FILE_MISSING", relativePath);
    return null;
  }
}

const tracked = new Set(
  execFileSync("git", ["ls-files"], { cwd: root, encoding: "utf8" })
    .split(/\r?\n/u)
    .filter(Boolean)
    .map((filePath) => filePath.replaceAll("\\", "/")),
);

for (const filePath of protectedPaths) {
  if (tracked.has(filePath)) add("PROTECTED_PATH_STILL_TRACKED", filePath);
}
for (const filePath of requiredPublicPaths) {
  if (!tracked.has(filePath)) add("REQUIRED_PUBLIC_PATH_NOT_TRACKED", filePath);
}

const payloadText = await readText("data/formal/case_payloads.json");
const indexText = await readText("data/public/case_index.csv");
const manifestText = await readText("data/public/public_layer_manifest.json");

if (payloadText !== null) {
  let payloads;
  try {
    payloads = JSON.parse(payloadText.replace(/^\uFEFF/, ""));
  } catch {
    add("PUBLIC_PAYLOAD_PARSE_ERROR", "data/formal/case_payloads.json");
  }
  if (!Array.isArray(payloads) || payloads.length !== 25) {
    add("PUBLIC_PAYLOAD_ROSTER_INVALID", "data/formal/case_payloads.json");
  }
  const prohibited = [
    /https?:\/\//iu,
    /\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b/u,
    /(?:19|20)\d{2}\s*(?:年\s*(?:0?[1-9]|1[0-2])\s*月\s*(?:0?[1-9]|[12]\d|3[01])\s*日|[-/.]\s*(?:0?[1-9]|1[0-2])\s*[-/.]\s*(?:0?[1-9]|[12]\d|3[01]))/u,
    /\b\d{6}(?:18|19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[0-9Xx]\b/u,
    /\b\d{3}-\d{2}-\d{4}\b/u,
  ];
  if (prohibited.some((pattern) => pattern.test(payloadText))) {
    add("PUBLIC_PAYLOAD_DIRECT_IDENTIFIER_PATTERN", "data/formal/case_payloads.json");
  }
}

if (indexText !== null) {
  const lines = indexText.trim().split(/\r?\n/u);
  if (lines[0] !== "case_id,jurisdiction,provenance_status" || lines.length !== 26) {
    add("PUBLIC_INDEX_SCHEMA_OR_ROSTER_INVALID", "data/public/case_index.csv");
  }
  if (/(?:original_title|source_url|docket|court|diagnosis|name)/iu.test(indexText)) {
    add("PUBLIC_INDEX_PROHIBITED_FIELD", "data/public/case_index.csv");
  }
}

if (manifestText !== null) {
  try {
    const manifest = JSON.parse(manifestText.replace(/^\uFEFF/, ""));
    const expectedHashSemantics = "sha256 of UTF-8 text after BOM removal and newline normalization to LF";
    if (manifest.formal_generation_authorized !== false
        || manifest.public_release_authorized !== false
        || manifest.manual_review_required !== true) {
      add("PUBLIC_MANIFEST_AUTHORITY_FLAGS_INVALID", "data/public/public_layer_manifest.json");
    }
    if (manifest.hash_semantics !== expectedHashSemantics) {
      add("PUBLIC_MANIFEST_HASH_SEMANTICS_INVALID", "data/public/public_layer_manifest.json");
    }
    const publicFiles = Array.isArray(manifest.public_files) ? manifest.public_files : [];
    const manifestHashByPath = new Map(publicFiles.map((item) => [item?.path, item?.sha256]));
    const expectedHashes = new Map([
      ["data/formal/case_payloads.json", payloadText === null ? null : sha256CanonicalText(payloadText)],
      ["data/public/case_index.csv", indexText === null ? null : sha256CanonicalText(indexText)],
    ]);
    if (publicFiles.length !== expectedHashes.size) {
      add("PUBLIC_MANIFEST_FILE_SET_INVALID", "data/public/public_layer_manifest.json");
    }
    for (const [filePath, expectedHash] of expectedHashes) {
      if (expectedHash !== null && manifestHashByPath.get(filePath) !== expectedHash) {
        add("PUBLIC_MANIFEST_FILE_HASH_MISMATCH", filePath);
      }
    }
  } catch {
    add("PUBLIC_MANIFEST_PARSE_ERROR", "data/public/public_layer_manifest.json");
  }
}

findings.sort((left, right) => left.issue_code.localeCompare(right.issue_code)
  || String(left.path).localeCompare(String(right.path)));
const automatedLayerGatePassed = findings.length === 0;
const report = {
  automated_layer_gate_passed: automatedLayerGatePassed,
  public_release_authorized: false,
  manual_review_required: true,
  tracked_path_count: tracked.size,
  protected_path_count: protectedPaths.size,
  required_public_path_count: requiredPublicPaths.size,
  issues_total: findings.length,
  findings,
};

console.log(JSON.stringify(report, null, 2));
process.exitCode = automatedLayerGatePassed ? 0 : 1;
