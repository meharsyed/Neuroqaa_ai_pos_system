module.exports = {
  root: true,
  env: { browser: true, es2020: true },
  extends: [
    "eslint:recommended",
    "plugin:@typescript-eslint/recommended",
    "plugin:react-hooks/recommended",
  ],
  ignorePatterns: ["dist", ".eslintrc.cjs"],
  parser: "@typescript-eslint/parser",
  plugins: ["react-refresh"],
  rules: {
    "react-refresh/only-export-components": ["warn", { allowConstantExport: true }],
    "@typescript-eslint/no-unused-vars": ["error", { argsIgnorePattern: "^_" }],

    // Raw Tailwind palette classes break dark mode, because only the tokens in
    // src/index.css have values for both themes.
    //
    // The previous version of this rule listed slate, gray, zinc, neutral,
    // stone, emerald, cyan, sky, indigo, violet, purple, rose, pink, fuchsia
    // and lime — and omitted red, orange, amber, yellow and blue, which were
    // 100% of the actual violations. It passed CI for months while the problem
    // it was written to stop kept happening.
    //
    // `green` and `teal` are deliberately NOT listed: tailwind.config.js
    // redefines those two ramps to point at this project's brand CSS
    // variables, so `text-teal-600` IS a token here.
    //
    // Use instead: text-success / bg-success-bg, warning, destructive, info,
    // the n-* neutral ramp, or bg-background / text-muted-foreground.
    "no-restricted-syntax": [
      "error",
      {
        selector:
          "Literal[value=/\\b(red|orange|amber|yellow|lime|blue|indigo|violet|purple|fuchsia|pink|rose|slate|gray|zinc|neutral|stone|emerald|cyan|sky)-[0-9]{2,3}\\b/]",
        message:
          "Raw Tailwind palette class — it has no dark-mode value. Use a design token " +
          "(success / warning / destructive / info / n-*) or the brand ramps green-* / teal-*. " +
          "See docs/UI_UX_REVAMP_SPEC.md §3.",
      },
      {
        // The same string built by interpolation slips past the Literal rule.
        selector:
          "TemplateElement[value.raw=/\\b(red|orange|amber|yellow|lime|blue|indigo|violet|purple|fuchsia|pink|rose|slate|gray|zinc|neutral|stone|emerald|cyan|sky)-[0-9]{2,3}\\b/]",
        message:
          "Raw Tailwind palette class in a template literal — it has no dark-mode value. " +
          "Use a design token. See docs/UI_UX_REVAMP_SPEC.md §3.",
      },
    ],
  },
};
