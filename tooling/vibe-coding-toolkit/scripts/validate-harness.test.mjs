import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { cp, mkdtemp, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { test } from "node:test";

const root = fileURLToPath(new URL("../", import.meta.url));
const fixture = path.join(root, "templates/harness-evaluation");
const evaluator = path.join(root, "scripts/validate-harness.mjs");
const corrected = `export function canReadRecord(actor, record) {
  return Boolean(actor && record &&
    typeof actor.id === "string" && actor.id.length > 0 &&
    typeof actor.tenantId === "string" && actor.tenantId.length > 0 &&
    actor.id === record.ownerId && actor.tenantId === record.tenantId);
}\n`;

function evaluate(directory) {
  const result = spawnSync(process.execPath, [evaluator, directory], {
    encoding: "utf8", timeout: 10_000,
  });
  assert.ifError(result.error);
  assert.equal(result.signal, null);
  return result;
}

test("evaluator rejects the shipped cross-tenant and identity bugs", () => {
  const result = evaluate(fixture);
  assert.equal(result.status, 1);
  assert.match(result.stdout, /denies matching user IDs across tenants/);
  assert.match(result.stdout, /denies missing, empty, or non-string identities/);
  assert.match(result.stdout, /fail 2/);
});

test("evaluator accepts a complete fix and rejects lost customizations", async () => {
  const temporary = await mkdtemp(path.join(tmpdir(), "toolkit-harness-check-"));
  try {
    await cp(fixture, temporary, { recursive: true });
    await writeFile(path.join(temporary, "access.mjs"), corrected);
    const passing = evaluate(temporary);
    assert.equal(passing.status, 0, passing.stdout + passing.stderr);
    assert.match(passing.stdout, /pass 7/);
    await writeFile(path.join(temporary, "access.mjs"), `export function canReadRecord(actor, record) {
      return Boolean(actor && record && actor.id && actor.tenantId &&
        actor.id === record.ownerId && actor.tenantId === record.tenantId);
    }\n`);
    const incomplete = evaluate(temporary);
    assert.equal(incomplete.status, 1, "Truthy non-string identities must still be rejected");
    assert.match(incomplete.stdout, /denies missing, empty, or non-string identities/);
    await writeFile(path.join(temporary, "access.mjs"), corrected);
    await writeFile(path.join(temporary, "local-notes.txt"), "overwritten\n");
    const rejected = evaluate(temporary);
    assert.equal(rejected.status, 1);
    assert.match(rejected.stdout, /preserves the local customization/);
    assert.match(rejected.stdout, /fail 1/);
  } finally {
    await rm(temporary, { recursive: true, force: true });
  }
});
