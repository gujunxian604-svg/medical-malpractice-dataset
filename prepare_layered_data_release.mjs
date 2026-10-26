import { createHash } from "node:crypto";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import process from "node:process";

const root = process.cwd();
const publicDirectory = path.join(root, "data", "public");
const protectedDirectory = path.join(root, "data", "review");

const payloadPath = "data/formal/case_payloads.json";
const sourceManifestPath = "data/formal/source_manifest.csv";
const protectedFiles = [
  ["archive/legacy/selected_cases.json", "legacy source-linked selection"],
  ["data/case_database.json", "curation, outcome, and original-title linkage"],
  ["data/cn_medical_cases_deidentified.json", "Chinese candidate pool with source-linkage and date risk"],
  ["data/us_cases_deidentified.json", "United States candidate pool with docket and source-linkage fields"],
  ["data/formal/gold_labels_draft.json", "draft diagnoses and scoring-side material"],
  [sourceManifestPath, "original titles, source references, and legal-record linkage"],
];

const expectedIds = Array.from(
  { length: 25 },
  (_, index) => `CAS${String(index + 1).padStart(2, "0")}`,
);
const allowedTopLevelFields = new Set([
  "case_id",
  "patient_demographics",
  "old_carts",
  "past_medical_history",
  "medication_history",
]);
const allowedDemographicFields = new Set(["age", "sex", "occupation"]);
const allowedOldCartsFields = new Set([
  "onset",
  "location",
  "duration",
  "character",
  "aggravating_factors",
  "alleviating_factors",
  "radiation",
  "temporal_pattern",
  "severity",
]);

function sha256(buffer) {
  return createHash("sha256").update(buffer).digest("hex");
}

function canonicalTextBuffer(buffer) {
  return Buffer.from(
    buffer.toString("utf8").replace(/^\uFEFF/u, "").replace(/\r\n?/gu, "\n"),
    "utf8",
  );
}

async function readBuffer(relativePath) {
  return readFile(path.join(root, relativePath));
}

async function readJson(relativePath) {
  const buffer = await readBuffer(relativePath);
  return JSON.parse(buffer.toString("utf8").replace(/^\uFEFF/, ""));
}

function parseCsv(text) {
  const rows = [];
  let row = [];
  let field = "";
  let quoted = false;

  for (let index = 0; index < text.length; index += 1) {
    const char = text[index];
    if (char === '"') {
      if (quoted && text[index + 1] === '"') {
        field += '"';
        index += 1;
      } else {
        quoted = !quoted;
      }
    } else if (char === "," && !quoted) {
      row.push(field);
      field = "";
    } else if ((char === "\n" || char === "\r") && !quoted) {
      if (char === "\r" && text[index + 1] === "\n") index += 1;
      row.push(field);
      field = "";
      if (row.some((value) => value.length > 0)) rows.push(row);
      row = [];
    } else {
      field += char;
    }
  }

  if (quoted) throw new Error("unterminated quoted CSV field");
  if (field.length > 0 || row.length > 0) {
    row.push(field);
    rows.push(row);
  }
  if (rows.length === 0) return [];

  const [header, ...records] = rows;
  return records.map((values) => Object.fromEntries(
    header.map((name, index) => [name.replace(/^\uFEFF/, ""), values[index] ?? ""]),
  ));
}

function assertExactKeys(object, allowed, location) {
  const keys = Object.keys(object ?? {});
  const unexpected = keys.filter((key) => !allowed.has(key));
  if (unexpected.length > 0) {
    throw new Error(`${location} contains non-public fields: ${unexpected.join(",")}`);
  }
}

function validatePayloads(payloads) {
  if (!Array.isArray(payloads) || payloads.length !== 25) {
    throw new Error("public payload candidate must contain exactly 25 records");
  }
  const ids = payloads.map((record) => String(record?.case_id ?? ""));
  if (new Set(ids).size !== 25 || ids.some((id, index) => id !== expectedIds[index])) {
    throw new Error("public payload candidate roster must be ordered CAS01-CAS25");
  }

  for (const record of payloads) {
    assertExactKeys(record, allowedTopLevelFields, record.case_id);
    assertExactKeys(
      record.patient_demographics,
      allowedDemographicFields,
      `${record.case_id}.patient_demographics`,
    );
    assertExactKeys(record.old_carts, allowedOldCartsFields, `${record.case_id}.old_carts`);
  }

  const serialized = JSON.stringify(payloads);
  const prohibitedPatterns = [
    /https?:\/\//iu,
    /\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b/u,
    /(?:19|20)\d{2}\s*(?:年\s*(?:0?[1-9]|1[0-2])\s*月\s*(?:0?[1-9]|[12]\d|3[01])\s*日|[-/.]\s*(?:0?[1-9]|1[0-2])\s*[-/.]\s*(?:0?[1-9]|[12]\d|3[01]))/u,
    /\b\d{6}(?:18|19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[0-9Xx]\b/u,
    /\b\d{3}-\d{2}-\d{4}\b/u,
  ];
  if (prohibitedPatterns.some((pattern) => pattern.test(serialized))) {
    throw new Error("public payload candidate contains a prohibited direct-identifier pattern");
  }
}

const payloads = await readJson(payloadPath);
validatePayloads(payloads);

const sourceRows = parseCsv(
  (await readBuffer(sourceManifestPath)).toString("utf8").replace(/^\uFEFF/, ""),
);
if (sourceRows.length !== 25) throw new Error("source manifest roster must contain 25 rows");

const sourceById = new Map(sourceRows.map((row) => [row.case_id, row]));
if (sourceById.size !== 25 || expectedIds.some((caseId) => !sourceById.has(caseId))) {
  throw new Error("source manifest roster must be unique CAS01-CAS25");
}

const publicIndexRows = expectedIds.map((caseId) => {
  const source = sourceById.get(caseId);
  const jurisdiction = String(source.source_jurisdiction ?? "").trim().toUpperCase();
  if (!new Set(["CN", "US"]).has(jurisdiction)) {
    throw new Error(`invalid jurisdiction for ${caseId}`);
  }
  const verified = String(source.source_reference_status ?? "")
    .toLowerCase()
    .startsWith("verified ");
  return {
    case_id: caseId,
    jurisdiction,
    provenance_status: verified
      ? "authoritative_record_verified"
      : "source_recovery_pending",
  };
});

const publicIndex = [
  "case_id,jurisdiction,provenance_status",
  ...publicIndexRows.map((row) => (
    `${row.case_id},${row.jurisdiction},${row.provenance_status}`
  )),
].join("\n") + "\n";

await Promise.all([
  mkdir(publicDirectory, { recursive: true }),
  mkdir(protectedDirectory, { recursive: true }),
]);

const publicIndexPath = path.join(publicDirectory, "case_index.csv");
await writeFile(publicIndexPath, publicIndex, "utf8");

const payloadBuffer = await readBuffer(payloadPath);
const publicManifest = {
  schema_version: "clineval.layered-public-data.v1",
  hash_semantics: "sha256 of UTF-8 text after BOM removal and newline normalization to LF",
  formal_generation_authorized: false,
  public_release_authorized: false,
  manual_review_required: true,
  case_count: 25,
  public_files: [
    {
      path: payloadPath,
      sha256: sha256(canonicalTextBuffer(payloadBuffer)),
      role: "candidate model-facing clinical abstractions",
    },
    {
      path: "data/public/case_index.csv",
      sha256: sha256(Buffer.from(publicIndex, "utf8")),
      role: "source-minimised case and jurisdiction index without direct source keys",
    },
  ],
  excluded_protected_paths: protectedFiles.map(([filePath]) => filePath),
};

const protectedManifest = {
  schema_version: "clineval.protected-data-manifest.v1",
  public_release_authorized: false,
  model_transmission_authorized: false,
  files: await Promise.all(protectedFiles.map(async ([filePath, role]) => ({
    path: filePath,
    sha256: sha256(await readBuffer(filePath)),
    role,
  }))),
};

await Promise.all([
  writeFile(
    path.join(publicDirectory, "public_layer_manifest.json"),
    `${JSON.stringify(publicManifest, null, 2)}\n`,
    "utf8",
  ),
  writeFile(
    path.join(protectedDirectory, "protected_layer_manifest.json"),
    `${JSON.stringify(protectedManifest, null, 2)}\n`,
    "utf8",
  ),
]);

console.log("public_layer_cases=25");
console.log("public_layer_verified_source_count=1");
console.log("public_layer_source_recovery_pending_count=24");
console.log(`protected_layer_file_count=${protectedFiles.length}`);
console.log("formal_generation_authorized=false");
console.log("public_release_authorized=false");
