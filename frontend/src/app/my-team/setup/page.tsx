"use client";

import { Suspense, useCallback, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@clerk/nextjs";
import { useDebounce } from "use-debounce";
import { API_BASE, authedFetch } from "@/lib/api";
import { PlayerHeadshot } from "@/components/PlayerHeadshot";

interface SearchResult {
  id: number;
  full_name: string;
  position: string;
  team: string;
}

interface RosterEntry extends SearchResult {
  sleeper_id?: string | null;
}

const FORMAT_OPTIONS = [
  { value: "ppr",      label: "Full PPR" },
  { value: "half_ppr", label: "Half PPR" },
  { value: "standard", label: "Standard" },
];

const POS_COLORS: Record<string, string> = {
  QB: "bg-[#7C3AED]/20 text-[#A78BFA]",
  RB: "bg-[#059669]/20 text-[#34D399]",
  WR: "bg-[#2563EB]/20 text-[#60A5FA]",
  TE: "bg-[#D97706]/20 text-[#FBBF24]",
  K:  "bg-[#374151] text-[#9CA3AF]",
};

export default function SetupPage() {
  return (
    <Suspense>
      <SetupPageInner />
    </Suspense>
  );
}

function SetupPageInner() {
  const { getToken, isLoaded, isSignedIn } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const fromDraft = searchParams.get("from_draft");

  // Step 1 — league settings
  const [name, setName] = useState("");
  const [format, setFormat] = useState("ppr");
  const [numTeams, setNumTeams] = useState(12);

  // Step 2 — roster builder
  const [step, setStep] = useState<1 | 2>(1);
  const [leagueId, setLeagueId] = useState<number | null>(null);
  const [roster, setRoster] = useState<RosterEntry[]>([]);
  const [query, setQuery] = useState("");
  const [debouncedQuery] = useDebounce(query, 300);
  const [results, setResults] = useState<SearchResult[]>([]);
  const [saving, setSaving] = useState(false);
  const [importStatus, setImportStatus] = useState<string | null>(null);

  // Search players
  useEffect(() => {
    if (debouncedQuery.length < 2) { setResults([]); return; }
    fetch(`${API_BASE}/search?q=${encodeURIComponent(debouncedQuery)}`)
      .then((r) => r.json())
      .then(setResults)
      .catch(() => {});
  }, [debouncedQuery]);

  // Auto-import from draft session once we have a leagueId
  const importFromDraft = useCallback(async (lid: number) => {
    if (!fromDraft) return;
    setImportStatus("Importing your draft picks…");
    const res = await authedFetch(
      `${API_BASE}/leagues/${lid}/roster/from-draft/${fromDraft}`,
      getToken,
      { method: "POST" }
    );
    const data = await res.json();
    setImportStatus(
      `Imported ${data.added_count} player${data.added_count !== 1 ? "s" : ""}` +
      (data.skipped_count > 0 ? ` (${data.skipped_count} picks/unmatched skipped)` : "") +
      ". You can add more below."
    );
    // Fetch the updated roster
    const leagueRes = await authedFetch(`${API_BASE}/leagues/${lid}`, getToken);
    const leagueData = await leagueRes.json();
    setRoster(
      (leagueData.roster ?? []).map((p: { id: number; full_name: string; position: string; team: string; sleeper_id?: string }) => ({
        id: p.id, full_name: p.full_name, position: p.position, team: p.team, sleeper_id: p.sleeper_id,
      }))
    );
  }, [fromDraft, getToken]);

  const handleCreateLeague = async () => {
    if (!name.trim()) return;
    setSaving(true);
    const res = await authedFetch(`${API_BASE}/leagues`, getToken, {
      method: "POST",
      body: JSON.stringify({ name: name.trim(), scoring_format: format, num_teams: numTeams }),
    });
    const data = await res.json();
    setLeagueId(data.id);
    setSaving(false);
    setStep(2);
    if (fromDraft) await importFromDraft(data.id);
  };

  const addPlayer = async (player: SearchResult) => {
    if (!leagueId || roster.find((p) => p.id === player.id)) return;
    await authedFetch(`${API_BASE}/leagues/${leagueId}/roster`, getToken, {
      method: "POST",
      body: JSON.stringify({ player_id: player.id }),
    });
    setRoster((prev) => [...prev, player]);
    setQuery("");
    setResults([]);
  };

  const removePlayer = async (playerId: number) => {
    if (!leagueId) return;
    const entry = roster.find((p) => p.id === playerId);
    if (!entry) return;
    // We need the roster_player_id — fetch the league to get it
    const res = await authedFetch(`${API_BASE}/leagues/${leagueId}`, getToken);
    const data = await res.json();
    const rosterEntry = data.roster?.find((p: { id: number; roster_player_id: number }) => p.id === playerId);
    if (rosterEntry?.roster_player_id) {
      await authedFetch(
        `${API_BASE}/leagues/${leagueId}/roster/${rosterEntry.roster_player_id}`,
        getToken,
        { method: "DELETE" }
      );
    }
    setRoster((prev) => prev.filter((p) => p.id !== playerId));
  };

  if (!isLoaded) return null;
  if (!isSignedIn) {
    router.push("/");
    return null;
  }

  return (
    <div className="max-w-2xl mx-auto px-6 py-10">
      <Link href="/my-team" className="text-sm text-[#A5ACAF] hover:text-white transition-colors">
        ← My Teams
      </Link>

      <h1 className="text-2xl font-extrabold text-white mt-4 mb-2">
        {step === 1 ? "Set Up Your League" : "Build Your Roster"}
      </h1>

      {/* Step indicator */}
      <div className="flex items-center gap-2 mb-8">
        {[1, 2].map((s) => (
          <div key={s} className={`h-1 flex-1 rounded-full transition-colors ${s <= step ? "bg-[#004C54]" : "bg-[#374151]"}`} />
        ))}
      </div>

      {/* ── STEP 1: League settings ── */}
      {step === 1 && (
        <div className="space-y-6">
          <div>
            <label className="text-xs text-[#6B7280] font-semibold uppercase tracking-wider block mb-2">
              League Name
            </label>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. The Homies League"
              className="w-full bg-[#1F2937] text-white rounded-lg px-4 py-3 text-sm outline-none border border-[#374151] focus:border-[#004C54] transition-colors"
            />
          </div>

          <div>
            <label className="text-xs text-[#6B7280] font-semibold uppercase tracking-wider block mb-2">
              Scoring Format
            </label>
            <div className="flex gap-2">
              {FORMAT_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  onClick={() => setFormat(opt.value)}
                  className={`flex-1 py-2.5 rounded-lg text-sm font-semibold transition-colors
                    ${format === opt.value ? "bg-[#004C54] text-white" : "bg-[#1F2937] text-[#A5ACAF] hover:text-white border border-[#374151]"}`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="text-xs text-[#6B7280] font-semibold uppercase tracking-wider block mb-2">
              Number of Teams
            </label>
            <div className="flex gap-2 flex-wrap">
              {[8, 10, 12, 14].map((n) => (
                <button
                  key={n}
                  onClick={() => setNumTeams(n)}
                  className={`px-4 py-2 rounded-lg text-sm font-semibold transition-colors
                    ${numTeams === n ? "bg-[#004C54] text-white" : "bg-[#1F2937] text-[#A5ACAF] hover:text-white border border-[#374151]"}`}
                >
                  {n}
                </button>
              ))}
            </div>
          </div>

          {fromDraft && (
            <div className="px-4 py-3 bg-[#004C54]/15 border border-[#004C54]/40 rounded-lg text-sm text-[#A5ACAF]">
              Your draft picks will be automatically imported after you name your league.
            </div>
          )}

          <button
            onClick={handleCreateLeague}
            disabled={!name.trim() || saving}
            className="w-full py-3 bg-[#004C54] hover:bg-[#005f6a] disabled:opacity-40 text-white font-bold rounded-lg transition-colors"
          >
            {saving ? "Creating…" : "Continue →"}
          </button>
        </div>
      )}

      {/* ── STEP 2: Roster builder ── */}
      {step === 2 && (
        <div className="space-y-6">
          {importStatus && (
            <div className="px-4 py-3 bg-[#004C54]/15 border border-[#004C54]/40 rounded-lg text-sm text-[#A5ACAF]">
              {importStatus}
            </div>
          )}

          {/* Search */}
          <div>
            <label className="text-xs text-[#6B7280] font-semibold uppercase tracking-wider block mb-2">
              Add Players
            </label>
            <div className="relative">
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search by name — e.g. Ja'Marr Chase"
                className="w-full bg-[#1F2937] text-white rounded-lg px-4 py-3 text-sm outline-none border border-[#374151] focus:border-[#004C54] transition-colors"
              />
              {results.length > 0 && (
                <div className="absolute z-10 top-full mt-1 w-full bg-[#1F2937] border border-[#374151] rounded-lg shadow-xl overflow-hidden">
                  {results.map((p) => (
                    <button
                      key={p.id}
                      onClick={() => addPlayer(p)}
                      disabled={!!roster.find((r) => r.id === p.id)}
                      className="w-full flex items-center gap-3 px-4 py-2.5 hover:bg-[#374151]/60 disabled:opacity-40 disabled:cursor-default transition-colors text-left"
                    >
                      <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${POS_COLORS[p.position] ?? "bg-[#374151] text-[#9CA3AF]"}`}>
                        {p.position}
                      </span>
                      <span className="text-white text-sm">{p.full_name}</span>
                      <span className="text-[#6B7280] text-xs ml-auto">{p.team}</span>
                      {roster.find((r) => r.id === p.id) && (
                        <span className="text-[#22C55E] text-xs">Added</span>
                      )}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Current roster */}
          <div>
            <div className="flex items-center justify-between mb-3">
              <label className="text-xs text-[#6B7280] font-semibold uppercase tracking-wider">
                Your Roster ({roster.length} players)
              </label>
            </div>
            {roster.length === 0 ? (
              <div className="py-8 text-center text-[#4B5563] text-sm border border-dashed border-[#374151] rounded-lg">
                Search for players above to build your roster.
              </div>
            ) : (
              <div className="space-y-2">
                {roster.map((p) => (
                  <div
                    key={p.id}
                    className="flex items-center gap-3 px-4 py-2.5 bg-[#1F2937]/60 border border-[#374151] rounded-lg"
                  >
                    <PlayerHeadshot
                      sleeperId={p.sleeper_id ?? null}
                      playerName={p.full_name}
                      position={p.position}
                      size={32}
                    />
                    <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${POS_COLORS[p.position] ?? "bg-[#374151] text-[#9CA3AF]"}`}>
                      {p.position}
                    </span>
                    <span className="text-white text-sm flex-1">{p.full_name}</span>
                    <span className="text-[#6B7280] text-xs">{p.team}</span>
                    <button
                      onClick={() => removePlayer(p.id)}
                      className="text-[#EF4444]/60 hover:text-[#EF4444] text-xs transition-colors ml-2"
                    >
                      Remove
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          <button
            onClick={() => router.push(`/my-team/${leagueId}`)}
            disabled={roster.length === 0}
            className="w-full py-3 bg-[#004C54] hover:bg-[#005f6a] disabled:opacity-40 text-white font-bold rounded-lg transition-colors"
          >
            View My Team →
          </button>
        </div>
      )}
    </div>
  );
}
