// Internal disposable-app check: native ESLint addons stay in this child process.
import assert from "node:assert/strict";
import { cp, rm, writeFile } from "node:fs/promises";
import { createRequire } from "node:module";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = fileURLToPath(new URL("../", import.meta.url));
const app = process.cwd();
const require = createRequire(path.join(app, "package.json"));
const { ESLint } = require("eslint");
const eslint = new ESLint({ cwd: app });
const check = async (code, file) => (await eslint.lintText(code, { filePath: path.join(app, file) }))[0];
const oversized = Array.from({ length: 351 }, (_, i) => `export const value${i} = ${i};`).join("\n");
const cases = [
  ...["src/oversized.ts", "src/index.ts", "src/components/index.tsx", "src/types.ts", "src/constants.ts"].map(file => [oversized, file, "quality/max-lines"]),
  ["export const value: any = 1;", "src/typed.ts", "@typescript-eslint/no-explicit-any"],
  ['export default function Page() { return <a href="/">Home</a>; }', "src/app/page.tsx", "@next/next/no-html-link-for-pages"],
  ['console.log("probe");', "src/app/page.tsx", "quality/no-direct-console"],
  ['import { getDb as loadDb } from "@/db"; export const GET = loadDb;', "src/app/api/probe/route.ts", "quality/no-direct-data-access"],
  ["export const remove = (db, table) => db.delete(table);", "src/features/probe/repository.ts", "drizzle/enforce-delete-with-where"],
  ["export const update = (db, table) => db.update(table).set({ name: 'x' });", "src/features/probe/repository.ts", "drizzle/enforce-update-with-where"],
];
for (const [code, file, rule] of cases) {
  assert((await check(code, file)).messages.some(message => message.ruleId === rule && message.severity === 2), `${rule} not enforced at ${file}`);
}
for (const [code, file] of [
  ["export default function Home() { return <main>Ready</main>; }", "src/app/page.tsx"],
  ['import { getDb } from "@/db"; export const read = () => getDb();', "src/features/probe/repository.ts"],
  ["export const remove = (db, table, condition) => db.delete(table).where(condition);", "src/features/probe/repository.ts"],
  ["export const update = (db, table, condition) => db.update(table).set({ name: 'x' }).where(condition);", "src/features/probe/repository.ts"],
  ["export const remove = (map: Map<string, string>) => map.delete('key');", "src/lib/map.ts"],
]) assert.equal((await check(code, file)).errorCount, 0, file);
for (const file of ["src/app/page.tsx", "app/page.tsx", "components/widget.tsx"]) {
  assert.equal((await eslint.calculateConfigForFile(path.join(app, file))).rules["quality/max-lines"][0], 2);
}
for (const declaration of ["export type Value", "export interface Value"]) {
  const types = Array.from({ length: 351 }, (_, i) => `${declaration}${i} ${declaration.includes("type") ? "=" : ""} { value: string };`).join("\n");
  assert(!(await check(types, "src/public-types.ts")).messages.some(message => message.ruleId === "quality/max-lines"));
  assert((await check(types + "\nexport const runtime = initialize();", "src/types.ts")).messages.some(message => message.ruleId === "quality/max-lines"));
}
await cp(path.join(root, "templates/eslint/eslint.config.mjs.example"), path.join(app, "eslint.advanced.mjs"));
const advanced = new ESLint({ cwd: app, overrideConfigFile: path.join(app, "eslint.advanced.mjs") });
for (const name of ["order.test.ts", "order.spec.ts", "order.e2e-spec.ts", "order-spec.ts", "order-test.js", "order.spec.mts", "order.test.cts", "__tests__/helper.ts"]) {
  const file = path.join(app, "src", name);
  const config = await advanced.calculateConfigForFile(file);
  assert.equal(config.rules["quality/max-lines"][0], 1, name);
  for (const rule of ["max-statements", "max-lines-per-function", "max-nested-callbacks", "import-x/no-restricted-paths", "import-x-debt/no-restricted-paths"]) {
    assert.equal(config.rules[rule][0], 0, `${name}: ${rule}`);
  }
  assert((await advanced.lintText(oversized, { filePath: file }))[0].messages.some(message => message.ruleId === "quality/max-lines" && message.severity === 1), name);
}
assert.equal((await advanced.calculateConfigForFile(path.join(app, "src/order-specification.ts"))).rules["quality/max-lines"][0], 2);
await rm(path.join(app, "eslint.advanced.mjs"));
console.log("PASS content-based barrel detection and consistent test classification in advanced ESLint");
// Resolve the lightweight profile from the fixture so imports use its dependencies.
await cp(path.join(root, "templates/eslint/next.config.mjs.example"), path.join(app, "eslint.light.mjs"));
const localLight = new ESLint({ cwd: app, overrideConfigFile: path.join(app, "eslint.light.mjs") });
assert.equal((await localLight.lintText("export const ready = true;", { filePath: path.join(app, "src/light.ts") }))[0].errorCount, 0);
await rm(path.join(app, "eslint.light.mjs"));

await cp(path.join(root, "templates/eslint/eslint.typed.config.mjs.example"), path.join(app, "eslint.advanced-typed.mjs"));
const advancedTyped = new ESLint({ cwd: app, overrideConfigFile: path.join(app, "eslint.advanced-typed.mjs") });
await cp(path.join(root, "templates/eslint/next.typed.config.mjs.example"), path.join(app, "eslint.typed.config.mjs"));
const typed = new ESLint({ cwd: app, overrideConfigFile: path.join(app, "eslint.typed.config.mjs") });
const probe = path.join(app, "src/async-probe.ts");
// Project service requires a real file included by tsconfig.json.
await writeFile(probe, "export {};\n");
try {
  const legacy = (await advancedTyped.lintText("export async function legacy() { await 1; }", { filePath: probe }))[0];
  assert(legacy.messages.some(message => message.ruleId === "@typescript-eslint/await-thenable" && message.severity === 1), "Advanced typed profile must retain its migration warnings");
  for (const [code, rule] of [
    ["Promise.resolve(1);", "@typescript-eslint/no-floating-promises"],
    ["export const callback: () => void = async () => {};", "@typescript-eslint/no-misused-promises"],
  ]) {
    const result = (await typed.lintText(code, { filePath: probe }))[0];
    assert(result.messages.some(message => message.ruleId === rule && message.severity === 2), `${rule} must block async bugs`);
  }
  const safe = (await typed.lintText("export async function safe() { await Promise.resolve(1); }", { filePath: probe }))[0];
  assert.equal(safe.errorCount, 0, JSON.stringify(safe.messages));
  console.log("PASS focused typed lint rejects floating promises and async void callbacks; awaited promises pass");
} finally {
  await rm(probe, { force: true });
  await rm(path.join(app, "eslint.advanced-typed.mjs"), { force: true });
}
