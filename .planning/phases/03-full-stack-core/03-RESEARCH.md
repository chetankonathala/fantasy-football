# Phase 3: Full-Stack Core - Research

**Researched:** 2026-03-26
**Domain:** FastAPI REST endpoints + Next.js App Router frontend + Sleeper projections API
**Confidence:** HIGH (core patterns), MEDIUM (Sleeper projections endpoint)

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

The backend is straightforward: two routes on the existing `main.py` stub, both querying the `Player` + `Matchup` tables via the established SQLAlchemy session factory. The search route uses a SQLite `LIKE` query on `full_name`. The player-detail route joins Player to Matchup, builds the appropriate signal dataclass, calls `score_player()`, and returns a serialized response. CORS must be enabled for local development so Next.js (port 3000) can hit FastAPI (port 8000).

The frontend uses Next.js App Router with two pages (`/` and `/player/[id]`). The search component is a `"use client"` component managing input state and a dropdown. The player page fetches the recommendation API on the server (server component) and renders a card. Scoring format selection is entirely client-side state using `useState`; changing format triggers a new fetch to the API with a `?format=` query param. The data freshness timestamp is derived from `updated_at` using a simple JS date calculation.

**Primary recommendation:** Build two FastAPI routes, one Next.js client search component, one server-rendered player page with a client island for format switching; use `use-debounce` library for the 300ms keystroke delay; render the Recommendation dataclass fields directly with no transformation layer.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| fastapi | 0.135.1 (already installed) | REST API framework | Already in pyproject.toml; locked from Phase 1 |
| sqlalchemy | 2.0.48 (already installed) | ORM + session for DB queries | Already in use across Phase 1/2 codebase |
| next | 15.x (to install) | App Router, RSC, dynamic routes | Locked from Phase 1 decision |
| tailwindcss | 4.x (to install) | Utility-first CSS | Locked from Phase 1/CONTEXT.md |
| typescript | 5.x | Type safety on frontend | Standard for Next.js projects |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| use-debounce | 10.x | Debounce search input in React | Prevents per-keystroke API calls; 300ms delay |
| next-themes | 0.4.x | Dark mode enforcement | Ensures dark class on html element without flash |
| @types/node, @types/react | latest | TypeScript definitions | Required for Next.js TS projects |
| uvicorn | already installed via fastapi | ASGI server for FastAPI | `uvicorn main:app --reload` during development |

### shadcn/ui Decision (Claude's Discretion)
Recommendation: use **raw Tailwind** for this project. shadcn/ui adds value for large component libraries, but this app has only two pages and the card has a fixed structure. Raw Tailwind with no extra dependency is simpler. If a `<Badge>`, `<Separator>`, or dropdown primitive is needed, shadcn's CLI can add individual components without adopting the full library.

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| use-debounce | lodash.debounce + useCallback | lodash adds weight; use-debounce is purpose-built and typed |
| raw Tailwind | shadcn/ui | shadcn adds value at scale; unnecessary for 2-page app |
| CORSMiddleware | Next.js API route proxy | Proxy adds a hop; CORS is simpler for localhost dev |

### Installation

Backend (no new packages needed — FastAPI already installed):
```bash
# Add uvicorn if not present
uv add "uvicorn[standard]"
```

Frontend (new Next.js project in `frontend/` subdirectory):
```bash
cd /Users/chetankonathala/Desktop/fantasy-football
npx create-next-app@latest frontend --typescript --tailwind --eslint --app --src-dir --import-alias "@/*"
cd frontend
npm install use-debounce next-themes
```

**Version verification:** Before finalizing, run:
```bash
npm view next version        # verify Next.js 15.x
npm view use-debounce version # verify 10.x
npm view next-themes version  # verify 0.4.x
```

---

## Architecture Patterns

### Recommended Project Structure

```
fantasy-football/
├── main.py                    # FastAPI app — Phase 3 adds routes here
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
        │   ├── page.tsx           # home: centered search bar only
        │   └── player/
        │       └── [id]/
        │           └── page.tsx   # player detail — server component, fetches API
        └── components/
            ├── SearchBar.tsx      # "use client" — input + dropdown
            ├── RecommendationCard.tsx  # "use client" — format selector + card body
            └── FreshnessStamp.tsx # pure component — relative time display
```

### Pattern 1: FastAPI Search Route
**What:** Case-insensitive LIKE query on `Player.full_name`, limited to 5 results, returns `id`, `full_name`, `position`, `team`
**When to use:** Every autocomplete keystroke after the frontend debounce fires

```python
# Source: FastAPI official docs + SQLAlchemy 2.0 select() pattern
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from src.fantasy.db.base import get_session_factory
from src.fantasy.db.models import Player

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

### Pattern 2: FastAPI Player-Detail Route
**What:** Fetches Player + Matchup, builds the correct signal type, calls `score_player()`, returns full recommendation + card signals
**When to use:** When frontend lands on `/player/[id]`

```python
# Source: engine.py contract (frozen post-Phase 2)
from src.fantasy.engine import score_player, SkillSignals, KickerSignals, DSTSignals, ScoringFormat

@app.get("/player/{player_id}")
def get_player_recommendation(
    player_id: int,
    format: str = "ppr",
    db: Session = Depends(get_db),
):
    player = db.query(Player).filter(Player.id == player_id).first()
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")

    # Resolve matchup rank (join through matchup_id)
    matchup_rank = None
    if player.matchup_id:
        from src.fantasy.db.models import Matchup
        matchup = db.query(Matchup).filter(Matchup.id == player.matchup_id).first()
        if matchup:
            matchup_rank = matchup.opponent_rank

    scoring_format = ScoringFormat(format)

    # Build signal type by position
    skill_positions = {"QB", "RB", "WR", "TE"}
    if player.position in skill_positions:
        signals = SkillSignals(
            position=player.position,
            matchup_rank=matchup_rank,
            injury_status=player.injury_status or None,
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

### Pattern 3: Sleeper Projected Points Fetch
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
    url = SLEEPER_PROJECTIONS_URL.format(season=season, week=week)
    resp = requests.get(url, params={"season_type": "regular"}, timeout=30)
    resp.raise_for_status()
    return resp.json()

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

### Pattern 4: Next.js Search Component (Client)
**What:** `"use client"` component with debounced fetch to `/search?q=`
**When to use:** Embedded in root layout so it persists across all pages

```typescript
// Source: Next.js docs + use-debounce library pattern
"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { useDebounce } from "use-debounce";

export function SearchBar() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<PlayerResult[]>([]);
  const [debouncedQuery] = useDebounce(query, 300);
  const router = useRouter();

  useEffect(() => {
    if (debouncedQuery.length < 2) { setResults([]); return; }
    fetch(`http://localhost:8000/search?q=${encodeURIComponent(debouncedQuery)}`)
      .then(r => r.json())
      .then(setResults)
      .catch(() => setResults([]));
  }, [debouncedQuery]);

  return (
    <div className="relative">
      <input
        value={query}
        onChange={e => setQuery(e.target.value)}
        placeholder="Search players..."
        className="w-full bg-zinc-900 border border-[#A5ACAF]/30 rounded-lg px-4 py-2 text-white placeholder:text-zinc-500 focus:outline-none focus:border-[#004C54]"
      />
      {results.length > 0 && (
        <ul className="absolute w-full bg-zinc-900 border border-[#A5ACAF]/20 rounded-lg mt-1 z-50">
          {results.map(p => (
            <li key={p.id} onClick={() => { router.push(`/player/${p.id}`); setResults([]); setQuery(""); }}
                className="px-4 py-2 hover:bg-zinc-800 cursor-pointer text-white text-sm">
              {p.full_name} — {p.position}, {p.team}
            </li>
          ))}
        </ul>
      )}
      {debouncedQuery.length >= 2 && results.length === 0 && (
        <div className="absolute w-full bg-zinc-900 border border-[#A5ACAF]/20 rounded-lg mt-1 px-4 py-2 text-zinc-400 text-sm">
          No players found
        </div>
      )}
    </div>
  );
}
```

### Pattern 5: Scoring Format Selector (Client Island)
**What:** `useState` for format; on change, refetch from API with `?format=` param; no page reload
**When to use:** Embedded inside the player detail page as a client component

```typescript
// Pattern: client island within server-rendered page
"use client";
import { useState, useEffect } from "react";

const FORMATS = ["ppr", "half_ppr", "standard"] as const;
type Format = typeof FORMATS[number];

export function RecommendationCard({ playerId }: { playerId: string }) {
  const [format, setFormat] = useState<Format>("ppr");
  const [rec, setRec] = useState<RecommendationResponse | null>(null);

  useEffect(() => {
    fetch(`http://localhost:8000/player/${playerId}?format=${format}`)
      .then(r => r.json())
      .then(setRec);
  }, [playerId, format]);

  // Verdict color map
  const verdictColor = {
    START: "text-green-400",
    SIT: "text-red-400",
    FLEX: "text-amber-400",
  };

  // ... render card
}
```

### Pattern 6: Data Freshness Timestamp
**What:** Convert ISO `updated_at` string to relative time without a library
**When to use:** Bottom of recommendation card (DATA-02)

```typescript
// Source: standard JS Date arithmetic — no library needed
function relativeTime(isoString: string): string {
  const diff = Date.now() - new Date(isoString).getTime();
  const minutes = Math.floor(diff / 60000);
  if (minutes < 60) return `Updated ${minutes} minute${minutes !== 1 ? "s" : ""} ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `Updated ${hours} hour${hours !== 1 ? "s" : ""} ago`;
  return `Updated ${Math.floor(hours / 24)} day(s) ago`;
}
```

### Anti-Patterns to Avoid

- **Importing SQLAlchemy inside engine.py:** `engine.py` has zero SQLAlchemy imports by design (enforced in Phase 2). The FastAPI route is responsible for DB queries and signal construction.
- **Joining on player name strings:** The codebase enforces canonical ID joins (`nflverse_id`). The search route returns `Player.id` (PK integer) as the navigation target, never the player name.
- **Global scoring format state:** The format selector is card-scoped, not a global context. Different tabs can show different formats without interference.
- **Calling `fetch_sleeper_players()` per request:** The Sleeper all-players endpoint is ~5MB. Projected points must be fetched similarly — once per refresh cycle in `scripts/refresh.py`, not on every API request.
- **Using `week` naming for raw week numbers in API response:** Field names follow `week1`=most recent, `week4`=oldest convention established in Phase 1. The API response must preserve this convention.
- **Forgetting `?format=` when format changes:** The scoring format must round-trip to the backend because `score_player()` is the authoritative scorer. The frontend cannot re-score locally.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Input debouncing | `setTimeout` in `onChange` + manual cleanup | `use-debounce` hook | Race conditions between cleanup and state updates; library handles this correctly |
| Relative timestamps | Full date formatting library | 5-line JS function (see Pattern 6) | No library needed for this simple case |
| CSS dark mode toggle | Custom JS class toggler | `next-themes` + `darkMode: 'class'` in Tailwind config | Avoids flash-of-light-mode on hydration |
| SQLAlchemy LIKE search | Regex filtering in Python | `Player.full_name.ilike(f"%{q}%")` | SQLite handles this efficiently with the existing index |
| API response type | Manual dict shapes | Pydantic `BaseModel` on FastAPI routes | Auto-generates OpenAPI schema, validates output |

**Key insight:** The most dangerous hand-roll risk is re-implementing scoring logic on the frontend. The `?format=` query param pattern is intentional — always round-trip to `score_player()` rather than trying to adjust the score client-side.

---

## Common Pitfalls

### Pitfall 1: Sleeper Projections Endpoint Unreliability
**What goes wrong:** `https://api.sleeper.com/projections/nfl/{season}/{week}` is undocumented and unofficial. It may return 404 during offseason, return empty objects for some players, or be blocked.
**Why it happens:** Sleeper sources projections from third-party providers (SportsRadar, RotoWire). The endpoint is not part of the public API contract.
**How to avoid:** Wrap `fetch_projected_points()` in a try/except; return `None` on any error; `SkillSignals.projected_points=None` is valid — the engine redistributes weight gracefully (see `_redistribute()` in engine.py).
**Warning signs:** `score_player()` returns valid recommendations even without projected_points — if they are suspiciously uniform, projections may be silently failing.

### Pitfall 2: CORS Blocking the Search Request
**What goes wrong:** Browser blocks the fetch from `localhost:3000` to `localhost:8000` with a CORS error in the console.
**Why it happens:** Different ports = different origins from the browser's perspective.
**How to avoid:** Add `CORSMiddleware` to FastAPI with `allow_origins=["http://localhost:3000"]` before any route definitions. For production, update to the actual deployed frontend URL.
**Warning signs:** Network tab shows a CORS preflight failure (OPTIONS request returning 400/405).

### Pitfall 3: `injury_status` Empty String vs None
**What goes wrong:** `Player.injury_status` is stored as `""` (empty string) for healthy players per `extract_player_data()` normalization (`injury_status = player.get("injury_status") or ""`). Engine expects `None` to mean healthy.
**Why it happens:** Sleeper returns `null` for healthy players; the normalize layer converts it to `""` to avoid NULL in DB.
**How to avoid:** In the FastAPI route, when constructing `SkillSignals`, pass `injury_status=player.injury_status or None` to convert empty string back to `None`.
**Warning signs:** Healthy players showing a "Questionable" penalty or unexpected SIT verdicts.

### Pitfall 4: `usage_share_l4w` Position Mismatch
**What goes wrong:** WR/TE should use `target_share`; RB should use `carry_share`; QB should pass all `None`. Mixing these produces wrong scores.
**Why it happens:** The Player model stores all three share types as separate columns. The route must select the right columns per position.
**How to avoid:** Use position-gated logic: `if position in ("WR", "TE"): use target_share columns; elif position == "RB": use carry_share columns; else (QB): pass [None, None, None, None]`.
**Warning signs:** QB snap-only scoring starts including carry share values; RB scores look like wide receiver target rates.

### Pitfall 5: Next.js Hydration Mismatch with Dark Mode
**What goes wrong:** Server renders light mode, client switches to dark — a flash of unstyled content or hydration error.
**Why it happens:** `className` on `<html>` differs between server and client when dark mode is applied dynamically.
**How to avoid:** Use `next-themes` with `attribute="class"` and force dark: `<ThemeProvider forcedTheme="dark">` — since dark-only is the locked decision, no toggle is needed.
**Warning signs:** Console shows "Text content does not match" hydration warning, or brief white flash on page load.

### Pitfall 6: Server Component Fetching vs Client Fetching
**What goes wrong:** The player detail page (`/player/[id]`) is a Next.js server component by default. Directly calling `fetch()` inside a server component works, but the scoring format selector is client-side state — this creates a split.
**Why it happens:** App Router mixes server/client components. The initial page load needs the default recommendation (server), but format changes need client-side refetch.
**How to avoid:** Make the player page a server component that fetches the initial data and passes it as props to `<RecommendationCard>` (a `"use client"` component). The card handles format-change refetches independently. Initial load is fast (no client JS waterfall), subsequent format changes use client-side fetch.
**Warning signs:** Format selector triggers full page navigation instead of in-place update, or the page flickers entirely on format change.

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

### Next.js App Router Dynamic Route
```
frontend/src/app/player/[id]/page.tsx
```
```typescript
// Source: Next.js App Router docs — dynamic segments
export default async function PlayerPage({ params }: { params: { id: string } }) {
  const data = await fetch(`http://localhost:8000/player/${params.id}?format=ppr`).then(r => r.json());
  return <RecommendationCard playerId={params.id} initialData={data} />;
}
```

### Tailwind Dark Mode Config (dark-only)
```javascript
// Source: Tailwind CSS docs + next-themes pattern
// tailwind.config.ts
module.exports = {
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        eagles: {
          green: "#004C54",
          silver: "#A5ACAF",
        },
      },
    },
  },
};
// layout.tsx: <html lang="en" className="dark">
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Next.js Pages Router | App Router with RSC | Next.js 13+ (stable 14) | Server components reduce client JS; dynamic routes use file-based `[id]` segments |
| `getServerSideProps` | `async` server component with `fetch()` | Next.js 13+ | Simpler data fetching pattern; no special export needed |
| Tailwind v3 `@apply` | Tailwind v4 CSS-first config | Tailwind v4 (2025) | Config moves to `tailwind.config.ts`; v4 is still in RC — **use v3.4.x** for stability |
| Manual CORS handling | `CORSMiddleware` | FastAPI 0.90+ | Built-in middleware, no custom decorator needed |

**Deprecated/outdated:**
- Tailwind v4: Still in active development as of early 2026 — use Tailwind **v3.4.x** (stable, widely documented). `create-next-app` may offer v4 opt-in; decline and specify v3.
- `pages/` directory pattern: Phase 3 should use App Router (`app/` directory), which `create-next-app` generates by default when `--app` flag is used.

---

## Open Questions

1. **Sleeper projected points endpoint availability during offseason / early week**
   - What we know: The endpoint `https://api.sleeper.com/projections/nfl/{season}/{week}` exists and returns `pts_ppr/pts_half_ppr/pts_std` per player
   - What's unclear: Whether projections are available early in the week (Monday/Tuesday before Sunday games) or only Thursday+ when lines are set
   - Recommendation: Implement with graceful fallback (`None`); log when projections are unavailable; test during active season only

2. **Player.id vs nflverse_id as URL parameter**
   - What we know: The search returns `Player.id` (integer PK); the URL is `/player/[id]`
   - What's unclear: Using the integer PK is simpler but couples frontend URLs to DB row IDs. Using `nflverse_id` is more stable but requires the search endpoint to return it.
   - Recommendation: Use `Player.id` (integer PK) for Phase 3 simplicity. The route `/player/123` is fine for a personal tool. Phase 4 can switch to slug URLs if needed.

3. **Frontend location within repo**
   - What we know: Next.js is locked; no existing `frontend/` directory exists; the project root has `main.py` + `src/`
   - What's unclear: Whether to co-locate frontend at `frontend/` (monorepo style) or a sibling directory
   - Recommendation: Create `frontend/` as a subdirectory of the repo root. Backend and frontend share the same git repo. `package.json` lives at `frontend/package.json`.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.x (already installed) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` (exists) |
| Quick run command | `uv run pytest tests/ -x -q` |
| Full suite command | `uv run pytest tests/ -v` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SRCH-01 | `/search?q=just` returns Justin Jefferson with position/team | integration | `uv run pytest tests/test_api.py::test_search_returns_autocomplete -x` | ❌ Wave 0 |
| SRCH-01 | `/search?q=x` (1 char) returns empty list | unit | `uv run pytest tests/test_api.py::test_search_min_chars -x` | ❌ Wave 0 |
| SRCH-01 | `/search?q=zzznomatch` returns empty list not 404 | unit | `uv run pytest tests/test_api.py::test_search_no_results -x` | ❌ Wave 0 |
| SRCH-02 | `GET /player/{id}` returns verdict, reasons, injury_status | integration | `uv run pytest tests/test_api.py::test_player_detail_returns_recommendation -x` | ❌ Wave 0 |
| RECD-04 | Player detail response includes `injury_status` and `practice_participation` | unit | `uv run pytest tests/test_api.py::test_player_detail_injury_fields -x` | ❌ Wave 0 |
| RECD-05 | Player detail response includes `snap_pct_l4w`, `target_share_l4w`, `carry_share_l4w` | unit | `uv run pytest tests/test_api.py::test_player_detail_usage_fields -x` | ❌ Wave 0 |
| DATA-02 | Player detail response includes `updated_at` as ISO string | unit | `uv run pytest tests/test_api.py::test_player_detail_updated_at -x` | ❌ Wave 0 |
| SRCH-02 | `GET /player/{id}?format=half_ppr` returns ScoringFormat.HALF_PPR in response | unit | `uv run pytest tests/test_api.py::test_player_format_selector -x` | ❌ Wave 0 |
| (Sleeper) | `fetch_projected_points()` handles HTTP error and returns None gracefully | unit | `uv run pytest tests/test_sleeper.py::test_fetch_projected_points_fallback -x` | ❌ Wave 0 |

**Frontend tests:** Frontend rendering is not covered by the pytest suite. Manual verification of the UI is the acceptance gate (loading states, verdict color, relative timestamp, format selector).

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_api.py -x -q`
- **Per wave merge:** `uv run pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_api.py` — FastAPI TestClient tests for `/search` and `/player/{id}`; covers SRCH-01, SRCH-02, RECD-04, RECD-05, DATA-02
- [ ] `tests/test_sleeper.py` — extend existing file with `test_fetch_projected_points_fallback` test (mock requests.get to raise HTTPError, assert None returned)
- [ ] FastAPI `TestClient` is available via `from fastapi.testclient import TestClient` — no extra install needed (bundled with FastAPI)

---

## Sources

### Primary (HIGH confidence)
- `src/fantasy/engine.py` — `Recommendation` dataclass shape (frozen post-Phase 2), `score_player()` signature, all signal types
- `src/fantasy/db/models.py` — `Player` and `Matchup` ORM columns; confirmed `updated_at`, injury fields, and all 12 usage stat columns
- `src/fantasy/db/base.py` — `get_session_factory()` pattern for FastAPI `Depends()` injection
- `src/fantasy/fetch/sleeper.py` — Existing Sleeper client; confirmed `injury_status or ""` normalization (Pitfall 3 root cause)
- `pyproject.toml` — Confirmed FastAPI 0.135.1 and SQLAlchemy 2.0.48 already installed; pytest 9.x available
- FastAPI official docs (https://fastapi.tiangolo.com/tutorial/cors/, https://fastapi.tiangolo.com/tutorial/sql-databases/)
- Next.js App Router docs (https://nextjs.org/docs/app/api-reference/file-conventions/dynamic-routes)

### Secondary (MEDIUM confidence)
- Sleeper projections endpoint `https://api.sleeper.com/projections/nfl/{season}/{week}` — confirmed via multiple GitHub discussions and the `sleeper-api-client` readthedocs page; response fields `pts_ppr`, `pts_half_ppr`, `pts_std` reported by multiple third-party wrappers
- `use-debounce` library pattern — multiple 2025 Next.js guides; official npm package
- `next-themes` dark mode pattern — official shadcn/ui Next.js setup guide + Tailwind dark mode docs

### Tertiary (LOW confidence)
- Tailwind v4 vs v3 status as of 2026 — recommendation to use v3.4.x based on general knowledge that v4 was in RC through late 2025; verify with `npm view tailwindcss version` before installing

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all backend dependencies confirmed in pyproject.toml; frontend stack (Next.js, Tailwind) locked from Phase 1 decisions
- Architecture: HIGH — engine contract is frozen, DB schema is frozen, patterns are standard FastAPI + Next.js App Router
- Pitfalls: HIGH for backend (confirmed from code inspection of normalize.py/engine.py); MEDIUM for frontend (dark mode hydration pitfall from documented next-themes pattern)
- Sleeper projections: MEDIUM — endpoint exists and is widely used but officially undocumented; fallback to None is mandatory

**Research date:** 2026-03-26
**Valid until:** 2026-04-26 (stable stack; Sleeper endpoint should be re-verified if > 30 days old)
