// Flat ESLint config (ESLint 8.21+/9 standard) for the Vite + React 18 +
// TypeScript frontend. Kept intentionally unopinionated: catches real bugs
// (unused vars, hook dependency issues, unreachable code) without imposing a
// new style on an already-consistent codebase.
import js from '@eslint/js'
import tseslint from '@typescript-eslint/eslint-plugin'
import tsParser from '@typescript-eslint/parser'
import importPlugin from 'eslint-plugin-import'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import globals from 'globals'

export default [
  { ignores: ['dist', 'node_modules'] },
  js.configs.recommended,
  {
    files: ['**/*.{ts,tsx}'],
    languageOptions: {
      parser: tsParser,
      parserOptions: {
        ecmaVersion: 'latest',
        sourceType: 'module',
        ecmaFeatures: { jsx: true },
      },
      globals: {
        ...globals.browser,
      },
    },
    plugins: {
      '@typescript-eslint': tseslint,
      import: importPlugin,
      'react-hooks': reactHooks,
      'react-refresh': reactRefresh,
    },
    rules: {
      ...tseslint.configs.recommended.rules,
      ...reactHooks.configs.recommended.rules,
      // TypeScript's own compiler (tsc --noEmit) already catches genuine
      // undefined-reference errors; no-undef doesn't understand TS type
      // positions (e.g. `React.ReactNode`, ambient ES2022 built-ins) and
      // produces false positives on them.
      'no-undef': 'off',
      'no-unused-vars': 'off',
      '@typescript-eslint/no-unused-vars': ['warn', { argsIgnorePattern: '^_' }],
      '@typescript-eslint/no-explicit-any': 'off',
      'react-refresh/only-export-components': [
        'warn',
        { allowConstantExport: true },
      ],
      // React, then third-party, then internal (@/ alias), then relative,
      // then styles — one blank line between groups, per frontend-rules.md.
      'import/order': [
        'warn',
        {
          groups: [
            'builtin',
            'external',
            'internal',
            ['parent', 'sibling', 'index'],
            'object',
            'type',
          ],
          pathGroups: [
            { pattern: 'react', group: 'builtin', position: 'before' },
            { pattern: '@/**', group: 'internal' },
            { pattern: '**/*.css', group: 'index', position: 'after' },
          ],
          pathGroupsExcludedImportTypes: ['react'],
          'newlines-between': 'always',
        },
      ],
    },
    settings: {
      // Plain node resolver: import/order only needs to classify each
      // import path into a group via `pathGroups` below, not fully resolve
      // the module — no need for eslint-import-resolver-typescript, whose
      // peer deps (@typescript-eslint/utils ^8.x) conflict with this
      // project's pinned @typescript-eslint ^7.x line.
      'import/resolver': {
        node: { extensions: ['.js', '.jsx', '.ts', '.tsx'] },
      },
    },
  },
]
