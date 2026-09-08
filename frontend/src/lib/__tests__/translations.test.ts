import { describe, expect, it } from "vitest";

import { translations } from "../translations";

/**
 * English and Urdu must carry the same keys.
 *
 * `t()` falls back to the key itself when a translation is missing, so a gap
 * in the Urdu dictionary does not throw — it renders the literal string
 * "bills.title" on the screen, in front of a customer. Nothing catches that
 * except a person switching language and reading every page, which is exactly
 * the kind of check that does not happen.
 */

function flatten(obj: unknown, prefix = ""): string[] {
  if (obj === null || typeof obj !== "object") return [prefix];
  return Object.entries(obj as Record<string, unknown>).flatMap(([k, v]) =>
    flatten(v, prefix ? `${prefix}.${k}` : k)
  );
}

const en = flatten(translations.en).sort();
const ur = flatten(translations.ur).sort();

describe("the Urdu dictionary keeps up with the English one", () => {
  it("has every English key", () => {
    const missing = en.filter((k) => !ur.includes(k));
    expect(
      missing,
      `These would render as raw keys in Urdu:\n  ${missing.join("\n  ")}`
    ).toEqual([]);
  });

  it("has no keys English does not", () => {
    const extra = ur.filter((k) => !en.includes(k));
    expect(extra, `Dead Urdu keys:\n  ${extra.join("\n  ")}`).toEqual([]);
  });

  it("has no blank translations", () => {
    const blanks = flatten(translations.ur).filter((path) => {
      const value = path.split(".").reduce<unknown>(
        (acc, k) => (acc as Record<string, unknown>)?.[k],
        translations.ur
      );
      return typeof value === "string" && value.trim() === "";
    });
    expect(blanks).toEqual([]);
  });

  it("keeps the {placeholders} identical in both languages", () => {
    const placeholders = (s: string) => (s.match(/\{[a-zA-Z0-9_]+\}/g) ?? []).sort();
    const wrong: string[] = [];
    for (const path of en) {
      const get = (dict: unknown) =>
        path.split(".").reduce<unknown>((acc, k) => (acc as Record<string, unknown>)?.[k], dict);
      const e = get(translations.en);
      const u = get(translations.ur);
      if (typeof e === "string" && typeof u === "string") {
        const pe = placeholders(e).join(",");
        const pu = placeholders(u).join(",");
        // A dropped {pct} or {code} leaves a sentence with a hole in it.
        if (pe !== pu) wrong.push(`${path}: en[${pe}] vs ur[${pu}]`);
      }
    }
    expect(wrong, wrong.join("\n")).toEqual([]);
  });
});
