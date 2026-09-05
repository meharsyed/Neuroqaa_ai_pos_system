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
    "no-restricted-syntax": [
      "error",
      {
        selector: "Literal[value=/\\b(slate|gray|zinc|neutral|stone|emerald|cyan|sky|indigo|violet|purple|rose|pink|fuchsia|lime)-[0-9]{2,3}\\b/]",
        message: "Use a design token. See docs/UI_UX_REVAMP_SPEC.md §3.",
      },
    ],
  },
};
