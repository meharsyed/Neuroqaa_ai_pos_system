import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

/**
 * The access token is held in memory and attached by an axios interceptor, so
 * anything that reaches an API endpoint by plain browser navigation arrives
 * with no Authorization header and gets a 401 — the user sees DRF's
 * browsable-API error page instead of their document.
 *
 * This shipped: the quotation Print button was an <a href="/api/…/pdf/">.
 * It is the kind of mistake that looks completely correct in review, so it is
 * pinned here rather than remembered.
 */

const SRC = join(__dirname, "..", "..");

function sourceFiles(dir: string, found: string[] = []): string[] {
  for (const entry of readdirSync(dir)) {
    if (entry === "node_modules" || entry === "__tests__" || entry === "test") continue;
    const full = join(dir, entry);
    if (statSync(full).isDirectory()) sourceFiles(full, found);
    else if (/\.(ts|tsx)$/.test(entry)) found.push(full);
  }
  return found;
}

describe("nothing navigates straight at the API", () => {
  const files = sourceFiles(SRC);

  it("finds source files to check", () => {
    expect(files.length).toBeGreaterThan(30);
  });

  it("has no href pointing at /api/", () => {
    const offenders: string[] = [];
    for (const file of files) {
      const text = readFileSync(file, "utf8");
      text.split("\n").forEach((line, i) => {
        // href="/api/..." or href={`/api/...`} or href={somethingApiUrl(...)}
        if (/href\s*=\s*[{"'`][^}"'`]*\/api\//.test(line)) {
          offenders.push(`${file.replace(SRC, "src")}:${i + 1}  ${line.trim()}`);
        }
      });
    }
    expect(
      offenders,
      "Fetch it through apiClient (see lib/pdf.ts openApiPdf) — a plain link " +
        "carries no Authorization header and returns 401:\n" + offenders.join("\n"),
    ).toEqual([]);
  });

  it("has no window.open aimed at /api/", () => {
    const offenders: string[] = [];
    for (const file of files) {
      const text = readFileSync(file, "utf8");
      text.split("\n").forEach((line, i) => {
        if (/window\.open\(\s*[`"']?[^)]*\/api\//.test(line)) {
          offenders.push(`${file.replace(SRC, "src")}:${i + 1}  ${line.trim()}`);
        }
      });
    }
    expect(offenders, offenders.join("\n")).toEqual([]);
  });
});
