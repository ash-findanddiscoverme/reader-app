# AGENTS.md

## Cursor Cloud specific instructions

**Product:** JustRead — a single Next.js 16 app (App Router) that extracts and renders web articles in a distraction-free reading view. No database, no external services, no Docker.

**Key services:**

| Service | Command | Port |
|---------|---------|------|
| Next.js Dev Server | `npm run dev` | 3000 |

**Scripts:** See `package.json` for `dev`, `build`, `start`, `lint`.

**Non-obvious notes:**

- `linkedom` and `@mozilla/readability` are required runtime dependencies used by `lib/extractor.ts` but were missing from `package.json`. They were installed via `npm install linkedom @mozilla/readability`. If they go missing, reinstall them.
- The API route at `app/api/extract/route.ts` declares `export const runtime = 'edge'`. In the Next.js dev server this still works with Node-based packages like `linkedom`, but be aware of this if you see edge-runtime errors in production builds.
- ESLint has 3 pre-existing errors (two `@typescript-eslint/no-explicit-any` in `page.tsx` and `route.ts`, one `@typescript-eslint/no-require-imports` in `tailwind.config.ts`). These are not blocking.
- The app requires internet access at runtime to fetch external article URLs.
