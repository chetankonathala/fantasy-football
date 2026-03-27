---
phase: 03-full-stack-core
plan: "02"
subsystem: ui
tags: [nextjs, tailwind, react, typescript, search, autocomplete]

# Dependency graph
requires:
  - phase: 03-full-stack-core/03-01
    provides: FastAPI search endpoint at localhost:8000/search, player routing to /player/{id}
provides:
  - Next.js 16 frontend app shell with Eagles dark theme
  - SearchBar autocomplete component with 300ms debounced search
  - Root layout with persistent nav header containing SearchBar
  - Home page with centered heading and search bar
  - Player navigation flow via router.push('/player/{id}')
affects:
  - 03-03-PLAN (player detail page, RecommendationCard — builds into this app shell)
  - 03-04-PLAN (end-to-end integration — builds on this frontend)

# Tech tracking
tech-stack:
  added:
    - next@16.2.1
    - tailwindcss@4.x (CSS-first config via @theme directive)
    - use-debounce (300ms keystroke debounce)
    - lucide-react (icon library)
    - typescript@5.x
    - eslint-config-next
  patterns:
    - Tailwind v4 CSS-first config — @import "tailwindcss" + @theme directive in globals.css, no tailwind.config.ts
    - Client component with useRef for click-outside, useEffect for debounced fetch, keyboard nav state machine
    - Fixed nav header pattern — h-14, pt-14 body offset, SearchBar constrained to w-80

key-files:
  created:
    - frontend/src/app/globals.css
    - frontend/src/app/layout.tsx
    - frontend/src/app/page.tsx
    - frontend/src/components/SearchBar.tsx
    - frontend/package.json
    - frontend/next.config.ts
    - frontend/tsconfig.json
  modified: []

key-decisions:
  - "Tailwind v4 CSS-first config: @theme directive in globals.css, no tailwind.config.ts — matches plan exactly"
  - "SearchBar is a 'use client' component embedded in root layout so it persists across all pages without re-mounting"
  - "Dropdown visibility controlled by isOpen AND (results.length > 0 OR (debouncedQuery >= 2 AND !isLoading)) to correctly show empty state"

patterns-established:
  - "Pattern: Tailwind v4 Eagles theme tokens — --color-eagles-green, --color-bg-primary, --color-bg-secondary etc declared in @theme block"
  - "Pattern: Client search component — useDebounce(query, 300), fetch on debouncedQuery change, keyboard nav with activeIndex state"
  - "Pattern: Fixed nav layout — header fixed top z-40 h-14, body pt-14 offset"

requirements-completed: [SRCH-01]

# Metrics
duration: 8min
completed: 2026-03-27
---

# Phase 3 Plan 02: Next.js Frontend Shell with Eagles Theme and SearchBar Autocomplete Summary

**Next.js 16 app with Tailwind v4 Eagles theme, fixed nav header, and SearchBar autocomplete component wired to the FastAPI search endpoint with 300ms debounce, keyboard nav, and accessibility attributes**

## Performance

- **Duration:** 8 min
- **Started:** 2026-03-27T14:18:56Z
- **Completed:** 2026-03-27T14:26:00Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- Scaffolded Next.js 16 app with Tailwind v4 CSS-first config (Eagles color tokens via @theme directive, no tailwind.config.ts)
- Built root layout with forced dark mode (className="dark"), Inter font, fixed nav header (bg-[#111827], border-[#004C54]), SearchBar slot
- Created home page with centered "Fantasy Advisor" heading, "Start/Sit clarity, instantly." subtitle, and SearchBar
- Implemented full SearchBar component: 300ms debounce, fetch after 2+ chars, keyboard navigation (ArrowUp/Down/Enter/Escape), click-outside-to-close, loading spinner, empty state, router.push to /player/{id}, ARIA attributes (combobox/listbox/option)
- Build passes cleanly with no TypeScript errors

## Task Commits

Each task was committed atomically:

1. **Task 1: Scaffold Next.js app, configure Tailwind v4 Eagles theme, create root layout with nav** - `ab11d81` (feat)
2. **Task 2: Build SearchBar autocomplete component with debounced search, keyboard nav, and routing** - `932acbe` (feat)

## Files Created/Modified
- `frontend/src/app/globals.css` - Tailwind v4 CSS-first config with @theme Eagles color tokens
- `frontend/src/app/layout.tsx` - Root layout: dark mode, Inter font, fixed nav header with SearchBar, pt-14 body offset
- `frontend/src/app/page.tsx` - Home page: centered "Fantasy Advisor" heading, subtitle, SearchBar
- `frontend/src/components/SearchBar.tsx` - Client component: debounced autocomplete, keyboard nav, click-outside, ARIA, loading spinner, empty state
- `frontend/package.json` - Dependencies: next, use-debounce, lucide-react, tailwindcss, typescript
- `frontend/next.config.ts` - Next.js 16 config
- `frontend/tsconfig.json` - TypeScript config with @/* import alias

## Decisions Made
- Tailwind v4 CSS-first config used exactly as specified in plan — @theme directive in globals.css, no tailwind.config.ts
- SearchBar embedded in root layout (not page components) so it persists across all routes without remounting
- Dropdown show condition: isOpen AND (results.length > 0 OR (debouncedQuery.length >= 2 AND !isLoading)) — correctly shows empty state after completed search with no results

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - build succeeded cleanly on first attempt after each task.

## User Setup Required

None - no external service configuration required. Note: SearchBar fetch calls localhost:8000/search which requires the FastAPI backend (03-01) to be running.

## Next Phase Readiness
- App shell complete — Plan 03-03 can build the player detail page and RecommendationCard into this layout
- SearchBar routes to /player/{id} — Plan 03-03 needs to create frontend/src/app/player/[id]/page.tsx
- Eagles theme tokens available globally via @theme for all future components
- No blockers

---
*Phase: 03-full-stack-core*
*Completed: 2026-03-27*
