# Phase 3: Full-Stack Core - Research

**Researched:** 2026-03-26 (updated re-research pass)
**Domain:** FastAPI REST endpoints + Next.js 16 App Router frontend + Sleeper projections API
**Confidence:** HIGH (backend patterns, engine contract, DB schema), MEDIUM (Sleeper projections endpoint, Next.js 16 specifics)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Search Interaction**
- Live autocomplete after 2+ characters typed — queries player DB on each keystroke
- Each result shows: player name + position + team (e.g., "Justin Jefferson — WR, MIN")
- Max 5 autocomplete suggestions shown
- Selecting a result navigates to `/player/[id]` — no inline card rendering
- If no players match: show "No players found" message in the dropdown (not silent)

**Page Structure**
- Two routes only: `/` (home) and `/player/[id]` (player detail)
- Home page: centered search bar, minimal — no featured players, no clutter
- Player page: player name/team/position header, then recommendation card below
- Search bar persists in the nav/header on all pages — user can search another player without returning home
- Verdict is the hero element on the card — big, bold, color-coded at the top; reasoning and signals below

**Frontend Styling**
- Framework: Next.js (locked from Phase 1)
- Styling: Tailwind CSS
- Components: shadcn/ui or raw Tailwind — Claude's discretion
- Mode: Dark mode only
- Theme: Philadelphia Eagles — midnight green `#004C54`, black/near-black background, silver `#A5ACAF` accents
- Verdict colors: START = green, SIT = red, FLEX = yellow/amber (contrast-safe on dark bg)

**Projected Points**
- Fetch weekly projections from Sleeper API in Phase 3
- Add `projected_points` fetch to `src/fantasy/fetch/sleeper.py`
- Pass fetched value into `score_player()` as `signals.projected_points`

**Scoring Format Selector**
- Present on the recommendation card (not global/persistent)
- Changing format updates verdict + projected points without a page reload (client-side state)
- Default: PPR

**Data Freshness Timestamp**
- Source: `Player.updated_at` column (already in DB, set on upsert)
- Display: human-readable relative time (e.g., "Updated 45 minutes ago")

### Claude's Discretion
- Exact card component layout and spacing
- Whether to use shadcn/ui vs raw Tailwind components
- API pagination/limit behavior for search endpoint
- Loading and error state design
- Exact Tailwind class values

### Deferred Ideas (OUT OF SCOPE)
- Roster upload + full lineup recommendation
- Community platform (user accounts, feeds, comments, reactions)
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SRCH-01 | User can search for any NFL player by name and see autocomplete suggestions | FastAPI `GET /search?q=` with SQLAlchemy LIKE query; Next.js client component with 2-char debounce pattern |
| SRCH-02 | User can select a player from search results and view their recommendation page | Next.js `router.push('/player/[id]')` on selection; FastAPI `GET /player/{id}` endpoint returning Recommendation |
| RECD-04 | User can see the player's injury/practice status (Q/D/Out) on the recommendation page | `Player.injury_status` and `Player.practice_participation` already in DB; API serializes both fields |
| RECD-05 | User can see usage trends (snap %, target share/carry share L3-4W) on the recommendation page | `Player.week1_snap_pct` through `week4_snap_pct`, `week1_target_share`, `week1_carry_share` already in DB |
| DATA-02 | Each recommendation card shows a data freshness timestamp | `Player.updated_at` serialized as ISO string; frontend converts to relative time via `Date.now()` diff |
</phase_requirements>

---

## Summary

Phase 3 wires together three concerns: (1) FastAPI routes that serve search and player-recommendation data from the existing SQLite DB, (2) a Next.js frontend with two routes and a persistent search bar, and (3) fetching Sleeper weekly projections so `projected_points` flows into `score_player()`.

The backend is straightforward: two routes on the existing `main.py` stub (currently just a `def main(): print(...)` placeholder — must be replaced with a FastAPI app), both querying the `Player` + `Matchup` tables via the established SQLAlchemy session factory. uvicorn is NOT currently installed — it must be added via `uv add "uvicorn[standard]"`. The search route uses a SQLite `ilike` query on `full_name`. The player-detail route joins Player to Matchup, builds the appropriate signal dataclass, calls `score_player()`, and returns a serialized response. CORS must be enabled for local development so Next.js (port 3000) can hit FastAPI (port 8000).

The frontend uses Next.js 16 App Router. The critical version-specific requirement: **`params` in dynamic route pages must be awaited asynchronously** — `const { id } = await params` (not `params.id`). This is a hard breaking change in Next.js 16 (was introduced in v15, synchronous compatibility removed in v16). Tailwind CSS v4 (now stable at 4.2.2) uses CSS-first configuration — no `tailwind.config.ts` file; instead `@import "tailwindcss"` in globals.css and `@theme` directive for custom tokens. The UI-SPEC.md document (`.planning/phases/03-full-stack-core/03-UI-SPEC.md`) is the authoritative visual and component contract for implementation — it defines exact component structure, colors, copy, spacing, accessibility requirements, and interaction states. All frontend implementation must follow that spec.

**Primary recommendation:** Build two FastAPI routes (replacing `main.py` stub), add uvicorn, one Next.js 16 client search component, one server-rendered player page with async params and a client island for format switching; use `use-debounce` library for the 300ms keystroke delay; render the Recommendation dataclass fields directly with no transformation layer; follow UI-SPEC.md precisely.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| fastapi | 0.135.1 (already installed) | REST API framework | Already in pyproject.toml; locked from Phase 1 |
| uvicorn | latest (NOT YET INSTALLED) | ASGI server for FastAPI | Required to run FastAPI; must add via `uv add "uvicorn[standard]"` |
| sqlalchemy | 2.0.48 (already installed) | ORM + session for DB queries | Already in use across Phase 1/2 codebase |
| next | **16.2.1** (to install) | App Router, RSC, dynamic routes | Locked from Phase 1 decision; **latest stable as of March 2026** |
| tailwindcss | **4.2.2** (to install) | Utility-first CSS | Locked from Phase 1/CONTEXT.md; **v4 is now stable** |
| typescript | 5.x | Type safety on frontend | Standard for Next.js projects |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| use-debounce | 10.1.0 | Debounce search input in React | Prevents per-keystroke API calls; 300ms delay |
| lucide-react | latest | Icon library | As specified in UI-SPEC.md |
| @types/node, @types/react | latest | TypeScript definitions | Required for Next.js TS projects |

### shadcn/ui Decision (Claude's Discretion)
Recommendation: use **raw Tailwind** for this project. The UI-SPEC.md confirms this decision: "Tool: none — raw Tailwind CSS." shadcn/ui adds value for large component libraries, but this app has only two pages and the card has a fixed structure. `next-themes` is **not needed** since dark mode is enforced by setting `className="dark"` directly on the `<html>` element in `layout.tsx` — no toggle required.

### Tailwind v4 Configuration (IMPORTANT — breaking vs v3)
Tailwind v4 is a CSS-first configuration. There is NO `tailwind.config.ts`/`tailwind.config.js` file. Instead:
- Import: `@import "tailwindcss";` in `globals.css`
- Custom tokens (Eagles colors): `@theme` directive in CSS, not a JS config object
- `darkMode` config: Not needed — Tailwind v4 uses `dark:` variant with `@variant dark (...)` or the class strategy automatically
- Automatic content detection: No `content` array needed; Tailwind v4 detects template files automatically

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| use-debounce | lodash.debounce + useCallback | lodash adds weight; use-debounce is purpose-built and typed |
| raw Tailwind | shadcn/ui | shadcn adds value at scale; unnecessary for 2-page app |
| CORSMiddleware | Next.js API route proxy | Proxy adds a hop; CORS is simpler for localhost dev |
| next-themes | `className="dark"` on html | next-themes needed only for toggleable dark mode; forced-dark is one static class |

### Installation

Backend (uvicorn not yet installed):
```bash
uv add "uvicorn[standard]"
```

Frontend (new Next.js project in `frontend/` subdirectory):
```bash
cd /Users/chetankonathala/Desktop/fantasy-football
npx create-next-app@latest frontend --typescript --tailwind --eslint --app --src-dir --import-alias "@/*"
cd frontend
npm install use-debounce lucide-react
```

**Version verification (run before starting):**
```bash
npm view next version         # confirms 16.2.1
npm view use-debounce version # confirms 10.1.0
npm view tailwindcss version  # confirms 4.2.2
```

---

## Architecture Patterns

### Recommended Project Structure

```
fantasy-football/
├── main.py                    # FastAPI app — Phase 3 REPLACES the current stub
├── src/fantasy/
│   ├── fetch/
│   │   └── sleeper.py         # extend: add fetch_projected_points()
│   ├── db/
│   │   ├── base.py            # session factory (already exists)
│   │   └── models.py          # Player + Matchup (already exists)
│   └── engine.py              # score_player() (already exists)
└── frontend/                  # New Next.js app
    └── src/
        ├── app/
        │   ├── layout.tsx         # root layout — dark mode class, nav with SearchBar
        │   ├── globals.css        # Tailwind v4 @import + @theme with Eagles colors
        │   ├── page.tsx           # home: centered search bar only
        │   └── player/
        │       └── [id]/
        │           └── page.tsx   # player detail — server component, ASYNC params
        └── components/
            ├── SearchBar.tsx      # "use client" — input + dropdown
            ├── RecommendationCard.tsx  # "use client" — format selector + card body
            └── FreshnessStamp.tsx # pure component — relative time display
```

### Pattern 1: FastAPI App (replacing main.py stub)
**What:** The current `main.py` is a `def main(): print(...)` stub — it must be replaced entirely with a FastAPI application
**When to use:** This is Wave 1 of Phase 3 execution

```python
# Source: FastAPI official docs + SQLAlchemy 2.0 select() pattern
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from src.fantasy.db.base import get_session_factory
from src.fantasy.db.models import Player, Matchup
from src.fantasy.engine import score_player, SkillSignals, KickerSignals, DSTSignals, ScoringFormat

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

SessionLocal = get_session_factory()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

### Pattern 2: FastAPI Search Route (SRCH-01)
**What:** Case-insensitive LIKE query on `Player.full_name`, limited to 5 results
**When to use:** Every autocomplete keystroke after the frontend debounce fires

```python
# Source: FastAPI official docs + SQLAlchemy 2.0 ilike() pattern
@app.get("/search")
def search_players(q: str, db: Session = Depends(get_db)):
    if len(q) < 2:
        return []
    results = (
        db.query(Player)
        .filter(Player.full_name.ilike(f"%{q}%"))
        .limit(5)
        .all()
    )
    return [
        {"id": p.id, "full_name": p.full_name, "position": p.position, "team": p.team}
        for p in results
    ]
```

### Pattern 3: FastAPI Player-Detail Route (SRCH-02, RECD-04, RECD-05, DATA-02)
**What:** Fetches Player + Matchup, builds the correct signal type, calls `score_player()`, returns full recommendation + card signals
**When to use:** When frontend lands on `/player/[id]`

```python
# Source: engine.py contract (frozen post-Phase 2)
@app.get("/player/{player_id}")
def get_player_recommendation(
    player_id: int,
    format: str = "ppr",
    db: Session = Depends(get_db),
):
    player = db.query(Player).filter(Player.id == player_id).first()
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")

    matchup_rank = None
    if player.matchup_id:
        matchup = db.query(Matchup).filter(Matchup.id == player.matchup_id).first()
        if matchup:
            matchup_rank = matchup.opponent_rank

    scoring_format = ScoringFormat(format)

    skill_positions = {"QB", "RB", "WR", "TE"}
    if player.position in skill_positions:
        signals = SkillSignals(
            position=player.position,
            matchup_rank=matchup_rank,
            injury_status=player.injury_status or None,  # convert "" to None
            snap_pct_l4w=[
                player.week1_snap_pct, player.week2_snap_pct,
                player.week3_snap_pct, player.week4_snap_pct,
            ],
            usage_share_l4w=[
                player.week1_target_share or player.week1_carry_share,
                player.week2_target_share or player.week2_carry_share,
                player.week3_target_share or player.week3_carry_share,
                player.week4_target_share or player.week4_carry_share,
            ],
            projected_points=None,  # Phase 3: wire in after fetch_projected_points()
        )
    elif player.position == "K":
        signals = KickerSignals(matchup_rank=matchup_rank)
    else:  # DST
        signals = DSTSignals(opponent_offense_rank=matchup_rank)

    rec = score_player(signals, scoring_format)

    return {
        # Recommendation fields
        "verdict": rec.verdict.value,
        "score": rec.score,
        "reasons": rec.reasons,
        "low_confidence": rec.low_confidence,
        "scoring_format": rec.scoring_format.value,
        # Card signals (RECD-04, RECD-05)
        "injury_status": player.injury_status,
        "practice_participation": player.practice_participation,
        "snap_pct_l4w": [player.week1_snap_pct, player.week2_snap_pct,
                         player.week3_snap_pct, player.week4_snap_pct],
        "target_share_l4w": [player.week1_target_share, player.week2_target_share,
                              player.week3_target_share, player.week4_target_share],
        "carry_share_l4w": [player.week1_carry_share, player.week2_carry_share,
                             player.week3_carry_share, player.week4_carry_share],
        # DATA-02
        "updated_at": player.updated_at.isoformat(),
        # Player identity
        "full_name": player.full_name,
        "position": player.position,
        "team": player.team,
    }
```

### Pattern 4: Sleeper Projected Points Fetch
**What:** Undocumented but widely-used Sleeper endpoint for weekly projections. Returns `pts_ppr`, `pts_half_ppr`, `pts_std` per player keyed by `player_id` (Sleeper ID).
**When to use:** Called from `src/fantasy/fetch/sleeper.py` during data refresh

```python
# Source: GitHub discussions on undocumented Sleeper endpoints
# Endpoint: https://api.sleeper.com/projections/nfl/{season}/{week}?season_type=regular
# NOTE: base domain is api.sleeper.com (not api.sleeper.app/v1)

SLEEPER_PROJECTIONS_URL = "https://api.sleeper.com/projections/nfl/{season}/{week}"

def fetch_projected_points(season: int, week: int) -> dict[str, dict]:
    """Fetch weekly projections from Sleeper.

    Returns dict keyed by sleeper_player_id with projection objects.
    Each object contains: pts_ppr, pts_half_ppr, pts_std (float or None).

    NOTE: This endpoint is undocumented. It may be blocked or deprecated.
    Callers should handle HTTP errors gracefully and fall back to None.
    """
    try:
        url = SLEEPER_PROJECTIONS_URL.format(season=season, week=week)
        resp = requests.get(url, params={"season_type": "regular"}, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return {}

def extract_projected_points(projections: dict, sleeper_id: str, scoring_format: str) -> float | None:
    """Extract pts_ppr/pts_half_ppr/pts_std for a player from projections dict.

    scoring_format: "ppr" | "half_ppr" | "standard"
    Returns float or None if player not found or value is None.
    """
    player_proj = projections.get(sleeper_id)
    if not player_proj:
        return None
    field_map = {"ppr": "pts_ppr", "half_ppr": "pts_half_ppr", "standard": "pts_std"}
    return player_proj.get(field_map.get(scoring_format, "pts_ppr"))
```

### Pattern 5: Next.js 16 Dynamic Route (CRITICAL — Async Params)
**What:** In Next.js 16, `params` is a Promise and MUST be awaited. Synchronous `params.id` access was removed.
**When to use:** `frontend/src/app/player/[id]/page.tsx`

```typescript
// Source: Next.js 16 upgrade guide — https://nextjs.org/docs/app/guides/upgrading/version-16
// CORRECT for Next.js 16:
export default async function PlayerPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;  // MUST await — sync access removed in Next.js 16
  const data = await fetch(`http://localhost:8000/player/${id}?format=ppr`).then(r => r.json());
  return <RecommendationCard playerId={id} initialData={data} />;
}

// WRONG (will fail on Next.js 16 — was valid in Next.js 14):
// export default async function PlayerPage({ params }: { params: { id: string } }) {
//   const data = await fetch(`http://localhost:8000/player/${params.id}...`);
// }
```

### Pattern 6: Tailwind v4 CSS Configuration
**What:** Tailwind v4 uses CSS-first configuration. No `tailwind.config.ts` needed.
**When to use:** `frontend/src/app/globals.css`

```css
/* Source: Tailwind CSS v4 docs — https://tailwindcss.com/blog/tailwindcss-v4 */
@import "tailwindcss";

@theme {
  --color-eagles-green: #004C54;
  --color-eagles-silver: #A5ACAF;
  --color-bg-primary: #0A0A0A;
  --color-bg-secondary: #111827;
}
```

Dark mode on `<html>` element (forced, no toggle):
```tsx
// frontend/src/app/layout.tsx
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body>{children}</body>
    </html>
  );
}
```

### Pattern 7: Next.js Search Component (Client)
**What:** `"use client"` component with debounced fetch to `/search?q=`
**When to use:** Embedded in root layout so it persists across all pages

```typescript
// Source: Next.js docs + use-debounce library pattern
"use client";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useDebounce } from "use-debounce";

export function SearchBar() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<PlayerResult[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [debouncedQuery] = useDebounce(query, 300);
  const router = useRouter();

  useEffect(() => {
    if (debouncedQuery.length < 2) { setResults([]); return; }
    setIsLoading(true);
    fetch(`http://localhost:8000/search?q=${encodeURIComponent(debouncedQuery)}`)
      .then(r => r.json())
      .then(data => { setResults(data); setIsLoading(false); })
      .catch(() => { setResults([]); setIsLoading(false); });
  }, [debouncedQuery]);

  // ... render following UI-SPEC.md component spec
}
```

### Pattern 8: Scoring Format Selector (Client Island)
**What:** `useState` for format; on change, refetch from API with `?format=` param; no page reload
**When to use:** Embedded inside the player detail page as a client component

```typescript
// Pattern: client island within server-rendered page
"use client";
import { useState, useEffect } from "react";

const FORMATS = ["ppr", "half_ppr", "standard"] as const;
type Format = typeof FORMATS[number];

export function RecommendationCard({ playerId, initialData }: { playerId: string; initialData: RecommendationResponse }) {
  const [format, setFormat] = useState<Format>("ppr");
  const [rec, setRec] = useState<RecommendationResponse>(initialData);
  const [isLoading, setIsLoading] = useState(false);

  // Skip initial fetch since initialData is PPR
  const isFirstRender = useRef(true);
  useEffect(() => {
    if (isFirstRender.current) { isFirstRender.current = false; return; }
    setIsLoading(true);
    fetch(`http://localhost:8000/player/${playerId}?format=${format}`)
      .then(r => r.json())
      .then(data => { setRec(data); setIsLoading(false); })
      .catch(() => setIsLoading(false));
  }, [playerId, format]);

  // render following UI-SPEC.md
}
```

### Pattern 9: Data Freshness Timestamp
**What:** Convert ISO `updated_at` string to relative time without a library
**When to use:** Bottom of recommendation card (DATA-02)

```typescript
// Source: standard JS Date arithmetic — no library needed
function relativeTime(isoString: string): string {
  const diff = Date.now() - new Date(isoString).getTime();
  const seconds = Math.floor(diff / 1000);
  if (seconds < 60) return "Updated just now";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `Updated ${minutes} minute${minutes !== 1 ? "s" : ""} ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `Updated ${hours} hour${hours !== 1 ? "s" : ""} ago`;
  return `Updated ${Math.floor(hours / 24)} day(s) ago`;
}
```

### Anti-Patterns to Avoid

- **Synchronous `params` access in Next.js 16:** `params.id` without await is a hard runtime error. Always type `params` as `Promise<{ id: string }>` and await it.
- **Using tailwind.config.ts for custom colors in v4:** Tailwind v4 uses `@theme` directive in CSS. A `tailwind.config.ts` file is not needed and may conflict.
- **Importing SQLAlchemy inside engine.py:** `engine.py` has zero SQLAlchemy imports by design (enforced in Phase 2). The FastAPI route is responsible for DB queries and signal construction.
- **Joining on player name strings:** The codebase enforces canonical ID joins (`nflverse_id`). The search route returns `Player.id` (PK integer) as the navigation target, never the player name.
- **Global scoring format state:** The format selector is card-scoped, not a global context. Different tabs can show different formats without interference.
- **Calling `fetch_sleeper_players()` per request:** The Sleeper all-players endpoint is ~5MB. Projected points must be fetched similarly — once per refresh cycle in `scripts/refresh.py`, not on every API request.
- **Forgetting `?format=` when format changes:** The scoring format must round-trip to the backend because `score_player()` is the authoritative scorer. The frontend cannot re-score locally.
- **Not installing uvicorn:** The current `pyproject.toml` does not include uvicorn. Running `python main.py` or `uvicorn main:app` will fail without it.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Input debouncing | `setTimeout` in `onChange` + manual cleanup | `use-debounce` hook | Race conditions between cleanup and state updates; library handles this correctly |
| Relative timestamps | Full date formatting library | 5-line JS function (see Pattern 9) | No library needed for this simple case |
| CSS dark mode toggle | Custom JS class toggler | `className="dark"` on `<html>` in layout.tsx | Dark-only app needs no toggle logic at all |
| SQLAlchemy LIKE search | Regex filtering in Python | `Player.full_name.ilike(f"%{q}%")` | SQLite handles this efficiently with the existing index |
| Re-scoring on frontend | Client-side score calculation | `?format=` query param + server round-trip | `score_player()` is the authoritative scorer; frontend cannot replicate all edge cases |

**Key insight:** The most dangerous hand-roll risk is re-implementing scoring logic on the frontend. The `?format=` query param pattern is intentional — always round-trip to `score_player()` rather than trying to adjust the score client-side.

---

## Common Pitfalls

### Pitfall 1: Next.js 16 Async Params (Breaking Change)
**What goes wrong:** Player page crashes with a runtime error because `params.id` is accessed synchronously.
**Why it happens:** Next.js 16 fully removed synchronous access to `params` (transitional compatibility existed in Next.js 15; removed in 16). `params` is now always a `Promise`.
**How to avoid:** Always type params as `Promise<{ id: string }>` and `await params` before accessing `id`. Use the `PageProps` helper type: `export default async function PlayerPage({ params }: PageProps<'/player/[id]'>)`.
**Warning signs:** Next.js build fails, or runtime error "params is not iterable" / accessing undefined.

### Pitfall 2: Tailwind v4 Config File Mismatch
**What goes wrong:** Adding a `tailwind.config.ts` with Eagles colors does nothing or conflicts with v4's CSS-first approach.
**Why it happens:** Tailwind v4 moved configuration entirely into CSS via `@theme`. JS config files have limited scope in v4.
**How to avoid:** Put custom tokens in `globals.css` using `@theme { --color-eagles-green: #004C54; }`. Reference as `text-[#004C54]` or define a utility class — the `bg-eagles-green` shorthand requires `@theme` not a JS config.
**Warning signs:** Custom colors not applied; or `create-next-app` generates a `tailwind.config.ts` which you must adapt or replace with a `@theme` block.

### Pitfall 3: uvicorn Not Installed
**What goes wrong:** `uvicorn main:app --reload` fails with "ModuleNotFoundError: No module named 'uvicorn'".
**Why it happens:** `pyproject.toml` lists `fastapi` but not `uvicorn`. FastAPI ships with `anyio` but not uvicorn.
**How to avoid:** Run `uv add "uvicorn[standard]"` as the first backend task in Wave 0.
**Warning signs:** Import error when trying to start the dev server.

### Pitfall 4: `injury_status` Empty String vs None
**What goes wrong:** `Player.injury_status` is stored as `""` (empty string) for healthy players per `extract_player_data()` normalization. Engine expects `None` to mean healthy.
**Why it happens:** Sleeper returns `null` for healthy players; the normalize layer converts it to `""` to avoid NULL in DB.
**How to avoid:** In the FastAPI route, when constructing `SkillSignals`, pass `injury_status=player.injury_status or None` to convert empty string back to `None`.
**Warning signs:** Healthy players showing unexpected SIT verdicts or Questionable penalty.

### Pitfall 5: `usage_share_l4w` Position Mismatch
**What goes wrong:** WR/TE should use `target_share`; RB should use `carry_share`; QB should pass all `None`. Mixing these produces wrong scores.
**Why it happens:** The Player model stores all three share types as separate columns. The route must select the right columns per position.
**How to avoid:** Use position-gated logic: `if position in ("WR", "TE"): use target_share columns; elif position == "RB": use carry_share columns; else (QB): pass [None, None, None, None]`. The `or` shortcut `week1_target_share or week1_carry_share` only works if exactly one is non-None per player — verify this assumption holds in the actual DB.
**Warning signs:** QB snap-only scoring starts including carry share values; RB scores look like wide receiver target rates.

### Pitfall 6: Sleeper Projections Endpoint Unreliability
**What goes wrong:** `https://api.sleeper.com/projections/nfl/{season}/{week}` is undocumented and unofficial. It may return 404 during offseason, return empty objects for some players, or be blocked.
**Why it happens:** Sleeper sources projections from third-party providers (SportsRadar, RotoWire). The endpoint is not part of the public API contract.
**How to avoid:** Wrap `fetch_projected_points()` in a try/except; return `{}` on any error (not raise); `SkillSignals.projected_points=None` is valid — the engine redistributes weight gracefully (see `_redistribute()` in engine.py).
**Warning signs:** `score_player()` returns valid recommendations even without projected_points — if they are suspiciously uniform, projections may be silently failing.

### Pitfall 7: CORS Blocking the Search Request
**What goes wrong:** Browser blocks the fetch from `localhost:3000` to `localhost:8000` with a CORS error in the console.
**Why it happens:** Different ports = different origins from the browser's perspective.
**How to avoid:** Add `CORSMiddleware` to FastAPI with `allow_origins=["http://localhost:3000"]` before any route definitions. For production, update to the actual deployed frontend URL.
**Warning signs:** Network tab shows a CORS preflight failure (OPTIONS request returning 400/405).

### Pitfall 8: Server Component Fetching vs Client Fetching (Format Selector)
**What goes wrong:** Format change triggers full page navigation instead of in-place update, or the page flickers entirely.
**Why it happens:** App Router mixes server/client components. The initial page load needs the default recommendation (server), but format changes need client-side refetch.
**How to avoid:** Make the player page a server component that fetches the initial data (PPR default) and passes it as `initialData` prop to `<RecommendationCard>` (a `"use client"` component). The card handles format-change refetches independently using `useRef` to skip the first `useEffect` run.
**Warning signs:** Format selector triggers full page navigation instead of in-place update.

---

## Code Examples

### FastAPI CORS + Dependency Injection Setup
```python
# Source: FastAPI official docs — https://fastapi.tiangolo.com/tutorial/cors/
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)
```

### SQLAlchemy LIKE Search (case-insensitive)
```python
# Source: SQLAlchemy 2.0 docs — ilike() for case-insensitive LIKE
db.query(Player).filter(Player.full_name.ilike(f"%{q}%")).limit(5).all()
```

### Next.js 16 App Router Dynamic Route (Async Params)
```
frontend/src/app/player/[id]/page.tsx
```
```typescript
// Source: Next.js 16 upgrade guide — async params required
export default async function PlayerPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const data = await fetch(`http://localhost:8000/player/${id}?format=ppr`).then(r => r.json());
  return <RecommendationCard playerId={id} initialData={data} />;
}
```

### Tailwind v4 CSS-First Config with Eagles Theme
```css
/* Source: Tailwind CSS v4 docs — https://tailwindcss.com/blog/tailwindcss-v4 */
/* frontend/src/app/globals.css */
@import "tailwindcss";

@theme {
  --color-eagles-green: #004C54;
  --color-eagles-silver: #A5ACAF;
}
```

### Dark Mode Forced (No Toggle)
```tsx
/* frontend/src/app/layout.tsx */
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="bg-[#0A0A0A] text-[#F9FAFB]">{children}</body>
    </html>
  );
}
```

---

## Canonical References (Must Read Before Implementing)

The following files are the authoritative contracts for Phase 3 implementation. All planners and implementers must read these before writing code:

| File | What It Governs |
|------|----------------|
| `src/fantasy/engine.py` | `Recommendation` dataclass (frozen shape), `score_player()` signature, all signal types |
| `src/fantasy/db/models.py` | `Player` and `Matchup` ORM columns; all 12 usage stat columns, `updated_at`, injury fields |
| `src/fantasy/db/base.py` | `get_session_factory()` — use for FastAPI `Depends()` injection |
| `src/fantasy/fetch/sleeper.py` | Existing Sleeper client; `injury_status or ""` normalization (root cause of Pitfall 4) |
| `.planning/phases/03-full-stack-core/03-UI-SPEC.md` | **Complete visual and component contract** — exact component structure, colors, copy, spacing, accessibility, interaction states |
| `.planning/phases/03-full-stack-core/03-VALIDATION.md` | Per-task validation map, test commands, Wave 0 gaps |

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Next.js Pages Router | App Router with RSC | Next.js 13+ (stable 14) | Server components reduce client JS; dynamic routes use file-based `[id]` segments |
| `getServerSideProps` | `async` server component with `fetch()` | Next.js 13+ | Simpler data fetching pattern; no special export needed |
| Synchronous `params` access | Async `await params` | **Next.js 16 (breaking)** | All dynamic route `params` are Promises; must await |
| Tailwind v3 `tailwind.config.js` | Tailwind v4 CSS-first `@theme` | **Tailwind v4 stable (2025)** | No JS config file; tokens in CSS; automatic content detection |
| `next-themes` for dark mode | `className="dark"` static | n/a for forced-dark apps | No library needed when dark mode is unconditional |
| Manual CORS handling | `CORSMiddleware` | FastAPI 0.90+ | Built-in middleware, no custom decorator needed |

**Deprecated/outdated (corrections to prior research):**
- "Use Tailwind v3.4.x — v4 is in RC": **WRONG as of March 2026.** Tailwind v4.2.2 is the stable `latest` tag. Use v4.
- "Use Next.js 15.x": **Outdated.** Next.js 16.2.1 is the stable `latest` tag. Use 16. Critical breaking change: async params.
- "`next-themes` needed for dark mode enforcement": Only needed if dark mode is toggleable. For forced dark mode, `className="dark"` on `<html>` is sufficient.

---

## Open Questions

1. **Sleeper projected points endpoint availability during offseason / early week**
   - What we know: The endpoint `https://api.sleeper.com/projections/nfl/{season}/{week}` exists and returns `pts_ppr/pts_half_ppr/pts_std` per player
   - What's unclear: Whether projections are available early in the week (Monday/Tuesday before Sunday games) or only Thursday+ when lines are set
   - Recommendation: Implement with graceful fallback (`{}`); log when projections are unavailable; test during active season only

2. **Player.id vs nflverse_id as URL parameter**
   - What we know: The search returns `Player.id` (integer PK); the URL is `/player/[id]`
   - What's unclear: Using the integer PK is simpler but couples frontend URLs to DB row IDs. Using `nflverse_id` is more stable but requires the search endpoint to return it.
   - Recommendation: Use `Player.id` (integer PK) for Phase 3 simplicity. The route `/player/123` is fine for a personal tool. Phase 4 can switch to slug URLs if needed.

3. **`create-next-app` generating tailwind.config.ts for v4**
   - What we know: Tailwind v4 uses CSS-first config; `create-next-app` may still scaffold a `tailwind.config.ts` depending on the template version
   - What's unclear: Whether `npx create-next-app@latest` in March 2026 scaffolds v3 or v4 Tailwind config
   - Recommendation: After scaffolding, check `package.json` for `tailwindcss` version and inspect `globals.css`. If v3 config is generated, replace with `@import "tailwindcss"` + `@theme` block. If v4 is already configured, verify Eagles color tokens are added to the `@theme` block.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.x (already installed) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` (exists) |
| Quick run command | `uv run pytest tests/test_api.py -x -q` |
| Full suite command | `uv run pytest tests/ -v` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SRCH-01 | `/search?q=just` returns array with full_name, position, team | integration | `uv run pytest tests/test_api.py::test_search_returns_autocomplete -x` | ❌ Wave 0 |
| SRCH-01 | `/search?q=x` (1 char) returns empty list | unit | `uv run pytest tests/test_api.py::test_search_min_chars -x` | ❌ Wave 0 |
| SRCH-01 | `/search?q=zzznomatch` returns empty list not 404 | unit | `uv run pytest tests/test_api.py::test_search_no_results -x` | ❌ Wave 0 |
| SRCH-02 | `GET /player/{id}` returns verdict, reasons, injury_status | integration | `uv run pytest tests/test_api.py::test_player_detail_returns_recommendation -x` | ❌ Wave 0 |
| RECD-04 | Player detail includes `injury_status` and `practice_participation` | unit | `uv run pytest tests/test_api.py::test_player_detail_injury_fields -x` | ❌ Wave 0 |
| RECD-05 | Player detail includes `snap_pct_l4w`, `target_share_l4w`, `carry_share_l4w` | unit | `uv run pytest tests/test_api.py::test_player_detail_usage_fields -x` | ❌ Wave 0 |
| DATA-02 | Player detail includes `updated_at` as ISO string | unit | `uv run pytest tests/test_api.py::test_player_detail_updated_at -x` | ❌ Wave 0 |
| SRCH-02 | `GET /player/{id}?format=half_ppr` returns HALF_PPR in response | unit | `uv run pytest tests/test_api.py::test_player_format_selector -x` | ❌ Wave 0 |
| (Sleeper) | `fetch_projected_points()` handles HTTP error and returns `{}` | unit | `uv run pytest tests/test_sleeper.py::test_fetch_projected_points_fallback -x` | ❌ Wave 0 |

**Frontend tests:** Frontend rendering is not covered by the pytest suite. Manual verification of the UI is the acceptance gate — see `03-VALIDATION.md` manual verification checklist.

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_api.py -x -q`
- **Per wave merge:** `uv run pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_api.py` — FastAPI TestClient tests for `/search` and `/player/{id}`; covers SRCH-01, SRCH-02, RECD-04, RECD-05, DATA-02
- [ ] `tests/test_sleeper.py` — extend existing file with `test_fetch_projected_points_fallback` test (mock requests.get to raise HTTPError, assert `{}` returned)
- [ ] uvicorn install: `uv add "uvicorn[standard]"` — must run before any API tests

---

## Sources

### Primary (HIGH confidence)
- `src/fantasy/engine.py` — `Recommendation` dataclass shape (frozen post-Phase 2), `score_player()` signature, all signal types — read directly
- `src/fantasy/db/models.py` — `Player` and `Matchup` ORM columns; confirmed `updated_at`, injury fields, and all 12 usage stat columns — read directly
- `src/fantasy/db/base.py` — `get_session_factory()` pattern for FastAPI `Depends()` injection — read directly
- `src/fantasy/fetch/sleeper.py` — Existing Sleeper client; confirmed `injury_status or ""` normalization (Pitfall 4 root cause) — read directly
- `pyproject.toml` — Confirmed FastAPI 0.135.1 and SQLAlchemy 2.0.48 already installed; uvicorn NOT listed; pytest 9.x available — read directly
- `main.py` — Confirmed current stub is `def main(): print("Hello...")` — must be replaced entirely
- `.planning/phases/03-full-stack-core/03-UI-SPEC.md` — Complete visual contract; confirmed raw Tailwind decision, exact colors, component specs — read directly
- Next.js 16 upgrade guide — https://nextjs.org/docs/app/guides/upgrading/version-16 — async params breaking change confirmed
- FastAPI official docs — https://fastapi.tiangolo.com/tutorial/cors/ + https://fastapi.tiangolo.com/tutorial/sql-databases/

### Secondary (MEDIUM confidence)
- `npm view next dist-tags` output — confirmed 16.2.1 is `latest`; 15.3.9 is `next-15-3` — verified via npm registry
- `npm view tailwindcss dist-tags` output — confirmed 4.2.2 is `latest`; 3.4.19 is `v3-lts` — verified via npm registry
- `npm view use-debounce version` — confirmed 10.1.0 — verified via npm registry
- Tailwind CSS v4 blog — https://tailwindcss.com/blog/tailwindcss-v4 — CSS-first config approach confirmed
- Sleeper projections endpoint `https://api.sleeper.com/projections/nfl/{season}/{week}` — confirmed via multiple GitHub discussions and third-party wrappers; response fields `pts_ppr`, `pts_half_ppr`, `pts_std` reported consistently

### Tertiary (LOW confidence)
- `create-next-app` scaffold behavior for Tailwind v4 — unclear whether it auto-configures v4 or v3 style; verify after scaffolding

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all backend dependencies confirmed in pyproject.toml via direct file read; Next.js 16.2.1 and Tailwind 4.2.2 confirmed via npm registry
- Architecture: HIGH — engine contract is frozen, DB schema is frozen, patterns are standard FastAPI + Next.js App Router; async params confirmed from official Next.js 16 docs
- Pitfalls: HIGH for backend (confirmed from code inspection of normalize.py/engine.py/models.py); HIGH for async params (confirmed from Next.js 16 official upgrade guide); MEDIUM for Tailwind v4 config (CSS-first approach confirmed but exact `create-next-app` scaffolding behavior unverified)
- Sleeper projections: MEDIUM — endpoint exists and is widely used but officially undocumented; fallback to `{}` is mandatory

**Research date:** 2026-03-26
**Valid until:** 2026-04-26 (stable stack; Sleeper endpoint should be re-verified if > 30 days old)
