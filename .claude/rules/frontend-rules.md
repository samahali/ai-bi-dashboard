# React Frontend Development Rules

You are a Senior React Engineer.

## General

- Use React 19.
- Use Vite.
- Use JavaScript unless TypeScript is explicitly requested.
- Follow clean architecture.
- Follow DRY, KISS and SOLID principles.
- Write production-ready, maintainable code.
- Keep components reusable and modular.

## Folder Structure

Organize the project into:

src/
├── assets/
├── components/
├── pages/
├── hooks/
├── services/
├── context/
├── layouts/
├── routes/
├── utils/
├── constants/
├── styles/

Every folder should have a clear responsibility.

## Components

- Use Functional Components only.
- Never use Class Components.
- Keep components small and focused.
- One component = one responsibility.
- Move reusable UI into shared components.
- Avoid duplicated code.

## Hooks

- Use React Hooks.
- Extract reusable logic into custom hooks.
- Never call hooks conditionally.
- Follow React Hooks rules.

## State Management

- Use Context API for lightweight global state.
- Do not introduce global state unless necessary.
- Keep local state local.

## API Layer

- Never call APIs directly inside components.
- Keep all API requests inside services/.
- Use Axios.
- Centralize API configuration.
- Handle request errors consistently.

## Routing

- Use React Router.
- Keep routes inside routes/.
- Lazy load pages when appropriate.

## Styling

- Keep styling consistent.
- Prefer CSS Modules or Tailwind (depending on the project).
- Avoid inline styles except for dynamic values.
- Reuse common styles.

## Performance

- Use React.memo only when beneficial.
- Use useMemo and useCallback only when necessary.
- Lazy load heavy components.
- Avoid unnecessary re-renders.

## Forms

- Validate all user inputs.
- Display meaningful validation messages.
- Disable submit while processing.

## Error Handling

- Handle loading states.
- Handle empty states.
- Handle API errors gracefully.
- Never leave the user without feedback.

## Security

Follow OWASP Frontend Security Best Practices.

- Never trust client-side validation.
- Escape untrusted content.
- Never use dangerouslySetInnerHTML unless explicitly required.
- Never store secrets in the frontend.
- Read API URLs from environment variables.
- Sanitize user-generated content where appropriate.

## Imports

- Sort imports using ESLint + import/order.
- Remove unused imports.
- Import order:

1. React
2. Third-party libraries
3. Internal modules
4. Relative imports
5. Styles

Leave one blank line between groups.

## Code Style

- Follow ESLint.
- Follow Prettier formatting.
- Use meaningful variable names.
- Use descriptive component names.
- Prefer early returns.
- Avoid nested conditions when possible.
- Keep functions small.

## Naming

Components:
PascalCase

Example:
SalesChart.jsx

Hooks:
camelCase with "use"

Example:
useSales.js

Utilities:
camelCase

Constants:
UPPER_SNAKE_CASE

## Accessibility

- Use semantic HTML.
- Add alt text to images.
- Use proper button elements.
- Use labels for form inputs.
- Ensure keyboard accessibility.

## Project Rules

- Never modify API contracts unless requested.
- Never duplicate business logic.
- Keep UI separate from business logic.
- Create reusable components whenever possible.
- Keep pages clean by extracting complex UI into components.

## Before Generating Code

Always ensure the generated code:

- Passes ESLint.
- Passes Prettier.
- Contains no unused imports.
- Contains no unused variables.
- Follows React best practices.
- Is production-ready.

If creating a new feature:

- Reuse existing components before creating new ones.
- Do not duplicate code.
- Maintain the existing project architecture.
- Keep files focused and under 300 lines when possible.
- If a component becomes too large, split it into smaller components.