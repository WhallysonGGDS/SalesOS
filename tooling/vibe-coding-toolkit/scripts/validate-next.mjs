import assert from "node:assert/strict";
import { execFileSync, execSync, spawn } from "node:child_process";
import { once } from "node:events";
import { cp, mkdir, mkdtemp, readFile, readdir, readlink, rm, writeFile } from "node:fs/promises";
import { createRequire } from "node:module";
import { createServer } from "node:net";
import { tmpdir } from "node:os";
import path from "node:path";
import { setTimeout as delay } from "node:timers/promises";
import { fileURLToPath } from "node:url";

assert.equal(Number(process.versions.node.split(".")[0]), 24, "Run with Node.js 24");
const root = fileURLToPath(new URL("../", import.meta.url));
const temporary = await mkdtemp(path.join(tmpdir(), "toolkit-next-"));
const app = path.join(temporary, "starter");
const env = { ...process.env, DISABLE_TELEMETRY: "1", NEXT_TELEMETRY_DISABLED: "1", GRAPHIFY_NO_AUTO_REFRESH: "1" };
if (process.platform === "win32") {
  // Skills clones Next's full repository; its fixture paths exceed Windows' default limit.
  const count = Number(env.GIT_CONFIG_COUNT || 0);
  assert(Number.isSafeInteger(count) && count >= 0, "Invalid inherited GIT_CONFIG_COUNT");
  env[`GIT_CONFIG_KEY_${count}`] = "core.longpaths";
  env[`GIT_CONFIG_VALUE_${count}`] = "true";
  env.GIT_CONFIG_COUNT = String(count + 1);
  assert.equal(execFileSync("git", ["config", "--get", "core.longpaths"], { env, encoding: "utf8" }).trim(), "true");
}
// Prove that validation does not depend on the caller's database credentials.
for (const key of ["DATABASE_URL", "DATABASE_URL_UNPOOLED", "LOG_LEVEL"]) delete env[key];
const expectedSkills = [
  "deploy-to-vercel", "differential-review", "find-skills", "gh-fix-ci",
  "next-bundle-optimizer", "next-dev-loop", "shadcn", "supabase-postgres-best-practices", "vercel-cli-with-tokens",
  "vercel-composition-patterns", "vercel-optimize", "vercel-react-best-practices",
  "vercel-react-view-transitions", "web-design-guidelines", "writing-guidelines",
];

function run(command, cwd = app) {
  execSync(command, { cwd, env, stdio: "inherit", timeout: 600_000 });
}

async function copyNext(directory = "") {
  const source = path.join(root, "templates/next", directory);
  for (const entry of await readdir(source, { withFileTypes: true })) {
    const relative = path.join(directory, entry.name);
    if (entry.isDirectory()) await copyNext(relative);
    else {
      const destination = entry.name === ".env.example" ? relative : relative.replace(/\.example$/, "");
      await mkdir(path.dirname(path.join(app, destination)), { recursive: true });
      await cp(path.join(source, entry.name), path.join(app, destination));
    }
  }
}

async function checkDocs() {
  const sources = path.join(root, "templates/project-docs");
  const manifest = JSON.parse(await readFile(path.join(sources, "manifest.json"), "utf8"));
  assert.deepEqual(Object.keys(manifest).sort(), [
    "AGENTS.md", "CLAUDE.md", "PRODUCT.md", "README.md", "docs/architecture.md",
    "docs/design.md", "docs/onboarding.md", "docs/quality.md", "docs/setup.md",
  ]);
  const frameworkInstructions = await readFile(path.join(app, "AGENTS.md"), "utf8");
  assert(frameworkInstructions.trim(), "Expected create-next-app framework instructions");
  const defaults = await readFile(path.join(root, "docs/06-project-defaults.md"), "utf8");
  for (const [destination, source] of Object.entries(manifest)) {
    assert(defaults.includes(destination), `Missing documented destination: ${destination}`);
    await mkdir(path.dirname(path.join(app, destination)), { recursive: true });
    if (destination === "AGENTS.md") {
      await writeFile(path.join(app, destination), frameworkInstructions + "\n\n" + await readFile(path.join(sources, source), "utf8"));
    } else {
      await cp(path.join(sources, source), path.join(app, destination));
    }
  }
  const mergedInstructions = await readFile(path.join(app, "AGENTS.md"), "utf8");
  assert(mergedInstructions.startsWith(frameworkInstructions), "Toolkit must preserve the scaffold AGENTS.md verbatim");
  assert(mergedInstructions.includes(await readFile(path.join(sources, manifest["AGENTS.md"]), "utf8")), "Toolkit instructions must also be present");
  assert.equal((await readFile(path.join(app, "CLAUDE.md"), "utf8")).trim(), "@AGENTS.md");
  // Document templates contain destination-relative links, not toolkit-relative links.
  for (const destination of Object.keys(manifest)) {
    const text = await readFile(path.join(app, destination), "utf8");
    for (const match of text.matchAll(/\]\(([^)]+)\)/g)) {
      if (!/^(https?:|#)/.test(match[1])) await readFile(path.resolve(app, path.dirname(destination), match[1]));
    }
  }
}

async function checkSkills() {
  // Windows junctions can store absolute targets; copies keep checked-in skills portable.
  const copy = process.platform === "win32" ? " --copy" : "";
  run("npx --yes skills@latest add vercel-labs/agent-skills --skill vercel-react-best-practices vercel-composition-patterns web-design-guidelines writing-guidelines vercel-react-view-transitions vercel-optimize deploy-to-vercel vercel-cli-with-tokens --agent codex claude-code --yes" + copy);
  run("npx --yes skills@latest add vercel-labs/skills --skill find-skills --agent codex claude-code --yes" + copy);
  // This disposable fixture selects optional skills to verify packaging, not a product's defaults.
  run("npx --yes skills@latest add https://github.com/vercel/next.js/tree/canary/skills/next-dev-loop --skill next-dev-loop --agent codex claude-code --yes" + copy);
  run("npx --yes skills@latest add https://github.com/vercel/next.js/tree/canary/skills/next-bundle-optimizer --skill next-bundle-optimizer --agent codex claude-code --yes" + copy);
  run("npx --yes skills@latest add supabase/agent-skills --skill supabase-postgres-best-practices --agent codex claude-code --yes" + copy);
  run("npx --yes skills@latest add https://github.com/openai/skills/tree/main/skills/.curated/gh-fix-ci --skill gh-fix-ci --agent codex claude-code --yes" + copy);
  run("npx --yes skills@latest add https://github.com/trailofbits/skills/tree/main/plugins/differential-review --skill differential-review --agent codex claude-code --yes" + copy);
  run("npx --yes skills@latest add shadcn/ui --skill shadcn --agent codex claude-code --yes" + copy);
  assert.deepEqual((await readdir(path.join(app, ".agents/skills"))).sort(), expectedSkills);
  const lock = JSON.parse(await readFile(path.join(app, "skills-lock.json"), "utf8"));
  assert.deepEqual(Object.keys(lock.skills).sort(), expectedSkills);
  for (const name of expectedSkills) {
    const canonical = await readFile(path.join(app, ".agents/skills", name, "SKILL.md"), "utf8");
    assert(canonical.includes(`name: ${name}`) || canonical.includes(`name: "${name}"`), `Missing skill name: ${name}`);
    assert.equal(await readFile(path.join(app, ".claude/skills", name, "SKILL.md"), "utf8"), canonical);
    if (process.platform !== "win32") assert(!path.isAbsolute(await readlink(path.join(app, ".claude/skills", name))));
  }
}

async function checkSql() {
  run("npm run db:generate"); // Empty schema and no DATABASE_URL must work.
  const schemaFile = path.join(app, "src/db/schema/index.ts");
  const original = await readFile(schemaFile, "utf8");
  try {
    await writeFile(schemaFile, 'import { integer, pgTable, text } from "drizzle-orm/pg-core";\nexport const probe = pgTable("toolkit_probe", { id: integer().primaryKey(), label: text().notNull() });\n');
    run("npm run db:generate");
    const sqlFiles = (await readdir(path.join(app, "drizzle"))).filter(file => file.endsWith(".sql"));
    assert.equal(sqlFiles.length, 1);
    assert((await readFile(path.join(app, "drizzle", sqlFiles[0]), "utf8")).includes('CREATE TABLE "toolkit_probe"'));
    await writeFile(path.join(app, "toolkit-sql-smoke.mjs"), `
import assert from "node:assert/strict";
import { PGlite } from "@electric-sql/pglite";
import { drizzle } from "drizzle-orm/pglite";
import { migrate } from "drizzle-orm/pglite/migrator";
import { sql } from "drizzle-orm";
const client = new PGlite();
const db = drizzle(client);
try {
  await migrate(db, { migrationsFolder: "./drizzle" });
  await migrate(db, { migrationsFolder: "./drizzle" });
  await db.execute(sql\x60insert into toolkit_probe (id, label) values (1, \${"committed"})\x60);
  assert.deepEqual((await db.execute(sql\x60select id, label from toolkit_probe where id = 1\x60)).rows, [{ id: 1, label: "committed" }]);
  await assert.rejects(db.transaction(async tx => {
    await tx.execute(sql\x60update toolkit_probe set label = \${"rollback"} where id = 1\x60);
    throw new Error("rollback-probe");
  }), /rollback-probe/);
  assert.equal((await db.execute(sql\x60select label from toolkit_probe where id = 1\x60)).rows[0].label, "committed");
  await db.execute(sql\x60update toolkit_probe set label = \${"updated"} where id = 1\x60);
  assert.equal((await db.execute(sql\x60select label from toolkit_probe where id = 1\x60)).rows[0].label, "updated");
  await db.execute(sql\x60delete from toolkit_probe where id = 1\x60);
  assert.equal((await db.execute(sql\x60select id from toolkit_probe\x60)).rows.length, 0);
  console.log("PASS generated migrations, reapplication, PostgreSQL CRUD and transaction rollback (PGlite)");
} finally { await client.close(); }
`);
    run("node toolkit-sql-smoke.mjs");
  } finally {
    await writeFile(schemaFile, original);
    await rm(path.join(app, "drizzle"), { recursive: true, force: true });
    await rm(path.join(app, "toolkit-sql-smoke.mjs"), { force: true });
  }
}

async function checkCleanTypecheck() {
  const routeDirectory = path.join(app, "src/app/api/typecheck-probe");
  await mkdir(routeDirectory, { recursive: true });
  try {
    await writeFile(path.join(routeDirectory, "route.ts"), "export function GET(_request: number) { return Response.json({ ok: true }); }\n");
    await rm(path.join(app, ".next"), { recursive: true, force: true });
    await rm(path.join(app, "tsconfig.tsbuildinfo"), { force: true });
    let rejected = false;
    try { execSync("npm run typecheck", { cwd: app, env, encoding: "utf8", stdio: "pipe", timeout: 120_000 }); }
    catch (error) {
      assert.equal(error.status, 2);
      assert.match(error.stdout + error.stderr, /typecheck-probe/);
      assert.match(error.stdout + error.stderr, /RouteHandlerConfig/);
      rejected = true;
    }
    assert(rejected, "Clean typecheck must reject invalid route signatures without a prior build");
  } finally { await rm(routeDirectory, { recursive: true, force: true }); }
  await rm(path.join(app, ".next"), { recursive: true, force: true });
  await rm(path.join(app, "tsconfig.tsbuildinfo"), { force: true });
  run("npm run typecheck");
  console.log("PASS clean typecheck generates route types and rejects invalid route handlers before build");
}

async function checkServerBoundary() {
  const page = path.join(app, "src/app/page.tsx");
  const original = await readFile(page, "utf8");
  try {
    await writeFile(page, '"use client";\nimport { getDatabaseUrl } from "@/lib/env";\nexport default function Page() { return <main>{getDatabaseUrl()}</main>; }\n');
    let rejected = false;
    try { execSync("npm run build", { cwd: app, env, encoding: "utf8", stdio: "pipe", timeout: 120_000 }); }
    catch (error) {
      assert.equal(error.status, 1);
      assert.match(error.stdout + error.stderr, /server-only/);
      rejected = true;
    }
    assert(rejected, "Next must reject server environment imports in Client Components");
    console.log("PASS Next compiler enforces the server-only boundary");
  } finally { await writeFile(page, original); }
}

function checkAudit() {
  run("npm audit --omit=dev");
  let output;
  try { output = execSync("npm audit --json", { cwd: app, env, encoding: "utf8", timeout: 120_000, stdio: ["ignore", "pipe", "inherit"] }); }
  catch (error) {
    assert.equal(error.status, 1, "Unexpected audit failure");
    output = error.stdout;
  }
  const audit = JSON.parse(output);
  assert(!audit.error && audit.metadata?.vulnerabilities, "Audit did not return a vulnerability report");
  const advisories = Object.values(audit.vulnerabilities).flatMap(item => item.via.filter(value => typeof value === "object").map(value => value.url));
  console.log("Full audit (including development):", JSON.stringify({ counts: audit.metadata.vulnerabilities, advisories: [...new Set(advisories)] }));
}

async function checkHttp() {
  const probe = createServer();
  await new Promise(resolve => probe.listen(0, "127.0.0.1", resolve));
  const port = probe.address().port;
  await new Promise(resolve => probe.close(resolve));
  const server = spawn(process.execPath, [path.join(app, "node_modules/next/dist/bin/next"), "start", "--hostname", "127.0.0.1", "--port", String(port)], { cwd: app, env, stdio: "inherit" });
  const exited = once(server, "exit");
  try {
    let response;
    for (let attempt = 0; attempt < 60 && !response; attempt++) {
      assert.equal(server.exitCode, null, "Next server exited before becoming ready");
      try { response = await fetch(`http://127.0.0.1:${port}/`, { signal: AbortSignal.timeout(1_000) }); }
      catch { await delay(250); }
    }
    assert(response, "Next server did not become ready");
    assert.equal(response.status, 200);
    assert((await response.text()).includes("<main"));
  } finally {
    if (server.exitCode === null) server.kill("SIGTERM");
    await exited;
  }
}

try {
  run('npx --yes create-next-app@latest starter --typescript --tailwind --eslint --app --src-dir --import-alias "@/*" --use-npm --disable-git --no-react-compiler --no-cache-components --no-agent-feedback --yes', temporary);
  const packageFile = path.join(app, "package.json");
  const require = createRequire(packageFile);
  const nextVersion = require("next/package.json").version;
  assert(/^\d+\.\d+\.\d+$/.test(nextVersion));
  const eslintMajor = require("eslint/package.json").version.split(".")[0];
  assert(/^\d+$/.test(eslintMajor));
  run("npm install drizzle-orm pg server-only zod pino clsx tailwind-merge");
  run(`npm install -D @types/node@24 drizzle-kit @types/pg @next/env@${nextVersion} vitest eslint-plugin-drizzle @electric-sql/pglite @eslint/js@${eslintMajor} typescript-eslint eslint-plugin-import-x eslint-import-resolver-typescript`);
  assert.equal(require("@next/env/package.json").version, nextVersion);
  await copyNext();
  await cp(path.join(root, "templates/eslint/eslint-rules"), path.join(app, "eslint-rules"), { recursive: true });
  await mkdir(path.join(app, "scripts"));
  await cp(path.join(root, "templates/eslint/verify.mjs"), path.join(app, "scripts/verify-quality-rules.mjs"));
  await cp(path.join(root, "templates/eslint/next-app.config.mjs.example"), path.join(app, "eslint.config.mjs"));
  await cp(path.join(root, "templates/project/.graphifyignore.example"), path.join(app, ".graphifyignore"));
  const packageJson = JSON.parse(await readFile(packageFile, "utf8"));
  Object.assign(packageJson.scripts, {
    lint: "eslint .", typecheck: "next typegen && tsc --noEmit",
    "lint:typed": "eslint --config eslint.typed.config.mjs .",
    "lint:rules": "node scripts/verify-quality-rules.mjs ./eslint-rules/index.cjs",
    test: "vitest run", "test:watch": "vitest",
    "db:generate": "drizzle-kit generate", "db:migrate": "drizzle-kit migrate",
    check: "npm run lint && npm run typecheck && npm run lint:typed && npm run lint:rules && npm test && npm run build",
  });
  await writeFile(packageFile, JSON.stringify(packageJson, null, 2) + "\n");
  await checkDocs();
  await checkSkills();
  // Windows locks loaded native addons; the child must exit before removing its dependencies.
  execFileSync(process.execPath, [path.join(root, "scripts/check-eslint.mjs")], { cwd: app, env, stdio: "inherit", timeout: 120_000 });
  await checkSql();
  await checkCleanTypecheck();
  await checkServerBoundary();
  run("npm run check");
  checkAudit();
  await checkHttp();
  const lock = JSON.parse(await readFile(path.join(app, "package-lock.json"), "utf8"));
  const versions = Object.fromEntries(["next", "react", "drizzle-orm", "drizzle-kit", "pg", "zod", "pino", "vitest"].map(name => [name, lock.packages[`node_modules/${name}`].version]));
  assert(Object.values(versions).every(version => /^\d+\.\d+\.\d+$/.test(version)), "Expected stable releases");
  console.log("Validated versions:", JSON.stringify(versions));
} finally {
  await rm(temporary, { recursive: true, force: true });
}

console.log(`PASS ${process.platform}: documentation contracts, Next/Drizzle templates, quality guards, tests, SQL, build, audit, HTTP and ${expectedSkills.length} selected local skills`);
