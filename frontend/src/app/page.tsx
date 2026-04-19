import { SearchBar } from "@/components/SearchBar";
import { TopPlayersBoard } from "@/components/TopPlayersBoard";
import { SpotlightSection } from "@/components/SpotlightSection";
import { API_BASE } from "@/lib/api";

const STATS = [
  { value: "2,600+", label: "Active Players" },
  { value: "18",     label: "Season Weeks" },
  { value: "3",      label: "Scoring Formats" },
  { value: "Hourly", label: "Data Refresh" },
];

const FEATURES = [
  {
    icon: "⚡",
    title: "Instant Verdicts",
    desc: "START, SIT, or FLEX — scored from real snap counts, target share, and matchup data.",
  },
  {
    icon: "🏥",
    title: "Live Injury Signals",
    desc: "Injury status and practice participation baked directly into every recommendation.",
  },
  {
    icon: "📊",
    title: "Matchup Intelligence",
    desc: "Defense vs. Position grades rank every opponent so you know who to attack.",
  },
  {
    icon: "🎰",
    title: "Vegas + Weather",
    desc: "Implied team totals and weather flags surface game-environment risk on every card.",
  },
];

export default async function Home() {
  // Fetch top players and spotlight in parallel
  const [initialPlayers, spotlightData] = await Promise.all([
    fetch(`${API_BASE}/top-players?position=ALL&limit=12&format=ppr`, { cache: "no-store" })
      .then((r) => (r.ok ? r.json() : []))
      .catch(() => []),
    fetch(`${API_BASE}/spotlight?format=ppr`, { cache: "no-store" })
      .then((r) => (r.ok ? r.json() : {}))
      .catch(() => ({})),
  ]);

  return (
    <main className="min-h-screen flex flex-col">

      {/* ── HERO ─────────────────────────────────────────────────── */}
      <section className="relative flex flex-col items-center justify-center px-6 pt-20 pb-14 text-center overflow-hidden">
        {/* Radial glow */}
        <div
          className="absolute inset-0 pointer-events-none"
          style={{
            background:
              "radial-gradient(ellipse 80% 50% at 50% -5%, rgba(0,76,84,0.28) 0%, transparent 70%)",
          }}
        />

        {/* Brand mark */}
        <span className="relative mb-4 text-xs font-bold tracking-[0.35em] uppercase text-[#004C54]">
          AUDIBLE
        </span>

        {/* Headline */}
        <h1 className="relative text-4xl sm:text-5xl font-extrabold text-white leading-tight max-w-2xl">
          Read the defense.{" "}
          <span
            className="text-transparent bg-clip-text"
            style={{ backgroundImage: "linear-gradient(90deg, #00828f, #00b4c2)" }}
          >
            Win your league.
          </span>
        </h1>

        {/* Subheadline */}
        <p className="relative mt-4 text-base text-[#A5ACAF] max-w-lg leading-relaxed">
          Instant START / SIT / FLEX verdicts powered by snap counts, target share,
          injury reports, Vegas totals, and matchup grades — updated every week.
        </p>

        {/* Search */}
        <div className="relative mt-8 w-full max-w-lg">
          <SearchBar placeholder="Search any NFL player — e.g. Patrick Mahomes" size="lg" />
        </div>

        <p className="relative mt-3 text-xs text-[#A5ACAF]/50">
          2,600+ players · 2025 season data · Free
        </p>
      </section>

      {/* ── POSITION SPOTLIGHT ───────────────────────────────────── */}
      <section className="px-6 pb-12 max-w-4xl mx-auto w-full">
        <div className="flex items-center justify-between mb-5">
          <div>
            <h2 className="text-xl font-extrabold text-white">Position Spotlights</h2>
            <p className="text-xs text-[#A5ACAF] mt-0.5">
              Top-ranked player at each position this week
            </p>
          </div>
          <span className="flex items-center gap-1.5 text-xs font-semibold text-[#22C55E]">
            <span className="w-2 h-2 rounded-full bg-[#22C55E] animate-pulse" />
            Live
          </span>
        </div>
        <SpotlightSection initialData={spotlightData} />
      </section>

      {/* ── STATS BAR ────────────────────────────────────────────── */}
      <section className="px-6 pb-10 max-w-4xl mx-auto w-full">
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {STATS.map((s) => (
            <div
              key={s.label}
              className="bg-[#111827] rounded-xl px-4 py-4 text-center border border-[#004C54]/20 hover:border-[#004C54]/50 transition-colors"
            >
              <p className="text-2xl font-extrabold text-white">{s.value}</p>
              <p className="text-xs text-[#A5ACAF] mt-1">{s.label}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── TOP PLAYERS BOARD ────────────────────────────────────── */}
      <section className="px-6 pb-12 max-w-4xl mx-auto w-full">
        <div className="flex items-center justify-between mb-5">
          <div>
            <h2 className="text-xl font-extrabold text-white">Top Players This Week</h2>
            <p className="text-xs text-[#A5ACAF] mt-0.5">
              Sorted by score · tap any player for full analysis
            </p>
          </div>
        </div>
        <TopPlayersBoard initialData={initialPlayers} />
      </section>

      {/* ── HOW IT WORKS ─────────────────────────────────────────── */}
      <section className="px-6 pb-16 max-w-4xl mx-auto w-full">
        <h2 className="text-xl font-extrabold text-white mb-5">How it works</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {FEATURES.map((f) => (
            <div
              key={f.title}
              className="bg-[#111827] border border-[#004C54]/20 rounded-xl p-5 hover:border-[#004C54]/60 transition-colors"
            >
              <span className="text-2xl">{f.icon}</span>
              <h3 className="mt-3 font-bold text-white">{f.title}</h3>
              <p className="mt-1 text-sm text-[#A5ACAF] leading-relaxed">{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── FOOTER ───────────────────────────────────────────────── */}
      <footer className="border-t border-[#004C54]/20 py-6 text-center text-xs text-[#A5ACAF]/40">
        AUDIBLE · Fantasy Football Advisor · Built for winners
      </footer>

    </main>
  );
}
