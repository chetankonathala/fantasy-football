import { SearchBar } from "@/components/SearchBar";

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
    desc: "Defense vs Position grades rank every opponent so you know who to attack.",
  },
  {
    icon: "🔄",
    title: "PPR / Half / Standard",
    desc: "Switch scoring formats on any player page and verdicts update instantly.",
  },
];

export default function Home() {
  return (
    <main className="min-h-screen flex flex-col">
      {/* HERO */}
      <section className="flex flex-col items-center justify-center px-6 py-24 text-center">
        {/* Accent pill */}
        <span className="mb-6 inline-block px-3 py-1 rounded-full text-xs font-semibold tracking-widest uppercase bg-[#004C54]/30 text-[#A5ACAF] border border-[#004C54]/60">
          Fantasy Football · Start/Sit Advisor
        </span>

        {/* Headline */}
        <h1 className="text-5xl sm:text-6xl font-extrabold text-white leading-tight max-w-2xl">
          Win your league with{" "}
          <span className="text-[#004C54]">data-driven</span> lineup decisions.
        </h1>

        {/* Subheadline */}
        <p className="mt-5 text-lg text-[#A5ACAF] max-w-xl">
          Instant START/SIT/FLEX verdicts powered by snap counts, target share, injury reports, and matchup grades — updated every week.
        </p>

        {/* Search bar */}
        <div className="mt-10 w-full max-w-lg">
          <SearchBar placeholder="Search any NFL player — e.g. Patrick Mahomes" size="lg" />
        </div>

        <p className="mt-3 text-xs text-[#A5ACAF]/60">
          2,600+ players · 2025 season data · Free
        </p>
      </section>

      {/* FEATURE CARDS */}
      <section className="px-6 pb-20 max-w-4xl mx-auto w-full">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {FEATURES.map((f) => (
            <div
              key={f.title}
              className="bg-[#111827] border border-[#004C54]/30 rounded-xl p-5 hover:border-[#004C54] transition-colors"
            >
              <span className="text-2xl">{f.icon}</span>
              <h3 className="mt-3 font-bold text-white">{f.title}</h3>
              <p className="mt-1 text-sm text-[#A5ACAF]">{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* FOOTER */}
      <footer className="border-t border-[#004C54]/30 py-6 text-center text-xs text-[#A5ACAF]/50">
        Fantasy Advisor · Built for winners
      </footer>
    </main>
  );
}
