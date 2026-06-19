// Flat config for ESLint 9 + Next.js 16.
//
// eslint-config-next@16 ships a native flat config, so we import it directly
// (`eslint-config-next/core-web-vitals`). Consuming it through the legacy
// `FlatCompat.extends("next/core-web-vitals")` path crashes under ESLint 9
// ("Converting circular structure to JSON … 'react'"), which is why the old
// .eslintrc.json + ESLINT_USE_FLAT_CONFIG=false setup broke CI.
import nextCoreWebVitals from "eslint-config-next/core-web-vitals";

const eslintConfig = [
  ...nextCoreWebVitals,
  {
    rules: {
      "@next/next/no-img-element": "warn",
      "import/order": [
        "warn",
        {
          groups: ["builtin", "external", "internal", "parent", "sibling", "index"],
          "newlines-between": "always",
          alphabetize: { order: "asc" },
        },
      ],
    },
  },
  {
    // Test files run under Vitest with globals enabled.
    files: ["**/*.test.ts", "**/*.test.tsx"],
    languageOptions: {
      globals: {
        vi: "readonly",
        vitest: "readonly",
        describe: "readonly",
        it: "readonly",
        expect: "readonly",
        beforeEach: "readonly",
        afterEach: "readonly",
      },
    },
  },
  {
    // Playwright e2e specs/fixtures are not React; the react-hooks rules
    // misfire on Playwright's `use` fixture and similar APIs.
    files: ["e2e/**"],
    rules: {
      "react-hooks/rules-of-hooks": "off",
      "react-hooks/set-state-in-effect": "off",
      "react-hooks/immutability": "off",
    },
  },
];

export default eslintConfig;
