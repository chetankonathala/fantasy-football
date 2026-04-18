"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { API_BASE } from "@/lib/api";
import { PlayerHeadshot } from "@/components/PlayerHeadshot";

interface Recommendation {
  verdict: "START" | "SIT" | "FLEX";
  score: number;
  reasons: string[];
  matchup_rank: number | null;
  injury_status: string | null;
  projected_points: number | null;
  vegas_implied_total: number | null;
  weather_flag: boolean;
  player_name: string;
  position: string;
  sleeper_id: string | null;
}

interface RosterPlayer {
  full_name: string;
  position: string;
  lineup_slot: string;
  is_bench: boolean;
  on_ir: boolean;
  espn_injury_status: string | null;
  recommendation: Recommendation | null;
}

interface MyTeamData {
  team_id: number;
  record: string;
  points_for: number;
  roster: RosterPlayer[];
}

const VERDICT_STYLES = {
  START: { bg: "bg-[#022c10] border-[#22C55E]/50", text: "text-[#22C55E]", label: "START" },
  FLEX:  { bg: "bg-[#1c1400] border-[#F59E0B]/50", text: "text-[#F59E0B]", label: "FLEX"  },
  SIT:   { bg: "bg-[#1a0000] border-[#EF4444]/50", text: "text-[#EF4444]", label: "SIT"   },
};

const POS_COLORS: Record<string, string> = {
  QB:    "bg-[#7C3AED]/20 text-[#A78BFA]",
  RB:    "bg-[#059669]/20 text-[#34D399]",
  WR:    "bg-[#2563EB]/20 text-[#60A5FA]",
  TE:    "bg-[#D97706]/20 text-[#FBBF24]",
  K:     "bg-[#374151] text-[#9CA3AF]",
  "D/ST":"bg-[#374151] text-[#9CA3AF]",
};

function ScoreBar({ score }: { score: number }) {
  const pct = Math.min(100, Math.max(0, score));
  const color = score >= 70 ? "#22C55E" : score >= 50 ? "#F59E0B" : "#EF4444";
  return (
    <div className="w-full h-1 bg-[#374151] rounded-full mt-1.5">
      <div className="h-1 rounded-full transition-all" style={{ width: `${pct}%`, backgroundColor: color }} />
    </div>
  );
}

function PlayerCard({ player }: { player: RosterPlayer }) {
  const rec = player.recommendation;
  const verdict = rec ? VERDICT_STYLES[rec.verdict] : null;
  const isStarter = !player.is_bench && !player.on_ir;

  return (
    <div className={`rounded-lg border px-4 py-3 transition-colors
      ${player.on_ir ? "border-[#374151]/40 bg-[#111827]/40 opacity-60"
        : isStarter ? "border-[#1F2937] bg-[#1F2937]/60 hover:border-[#004C54]/50"
        : "border-[#1F2937]/50 bg-[#111827]/40 hover:border-[#374151]"}`}
    >
      <div className="flex items-center gap-3">
        {/* Slot badge */}
        <div className="w-12 text-center shrink-0">
          <div className="text-[10px] text-[#6B7280] font-semibold">{player.lineup_slot}</div>
        </div>

        {/* Headshot */}
        {rec?.sleeper_id && (
          <PlayerHeadshot sleeperId={rec.sleeper_id} playerName={player.full_name} position={player.position} size={36} />
        )}

        {/* Name + injury */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className={`font-semibold ${isStarter ? "text-white" : "text-[#A5ACAF]"}`}>
              {player.full_name}
            </span>
            {player.position && (
              <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${POS_COLORS[player.position] ?? "bg-[#374151] text-[#9CA3AF]"}`}>
                {player.position}
              </span>
            )}
            {player.espn_injury_status && (
              <span className="text-[10px] text-[#EF4444] font-semibold bg-[#EF4444]/10 px-1.5 py-0.5 rounded">
                {player.espn_injury_status}
              </span>
            )}
          </div>

          {rec && (
            <>
              <ScoreBar score={rec.score} />
              {rec.reasons[0] && (
                <div className="text-[10px] text-[#6B7280] mt-1 truncate">{rec.reasons[0]}</div>
              )}
            </>
          )}
          {!rec && (
            <div className="text-[10px] text-[#4B5563] mt-1">No matchup data available</div>
          )}
        </div>

        {/* Stats */}
        <div className="flex items-center gap-4 shrink-0 text-right">
          {rec?.projected_points != null && (
            <div>
              <div className="text-[10px] text-[#6B7280]">Proj</div>
              <div className="text-white text-sm font-mono">{rec.projected_points.toFixed(1)}</div>
            </div>
          )}
          {rec?.vegas_implied_total != null && (
            <div>
              <div className="text-[10px] text-[#6B7280]">Vegas</div>
              <div className="text-[#A5ACAF] text-sm font-mono">{rec.vegas_implied_total.toFixed(1)}</div>
            </div>
          )}
          {rec?.matchup_rank != null && (
            <div>
              <div className="text-[10px] text-[#6B7280]">Matchup</div>
              <div className={`text-sm font-mono ${rec.matchup_rank <= 10 ? "text-[#22C55E]" : rec.matchup_rank >= 23 ? "text-[#EF4444]" : "text-[#A5ACAF]"}`}>
                #{rec.matchup_rank}
              </div>
            </div>
          )}

          {/* Verdict */}
          {verdict && (
            <div className={`px-3 py-1.5 rounded border font-bold text-sm min-w-[56px] text-center ${verdict.bg} ${verdict.text}`}>
              {verdict.label}
            </div>
          )}
          {!rec && (
            <div className="px-3 py-1.5 rounded border border-[#374151]/40 text-[#4B5563] text-sm min-w-[56px] text-center">
              —
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default function MyTeamPage() {
  const [data, setData] = useState<MyTeamData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [format, setFormat] = useState("ppr");

  useEffect(() => {
    setLoading(true);
    fetch(`${API_BASE}/my-team?format=${format}`)
      .then((r) => r.json())
      .then((d) => { setData(d); setLoading(false); })
      .catch((e) => { setError(e.message); setLoading(false); });
  }, [format]);

  const starters = data?.roster.filter((p) => !p.is_bench && !p.on_ir) ?? [];
  const bench    = data?.roster.filter((p) => p.is_bench) ?? [];
  const ir       = data?.roster.filter((p) => p.on_ir) ?? [];

  const startCount  = starters.filter((p) => p.recommendation?.verdict === "START").length;
  const flexCount   = starters.filter((p) => p.recommendation?.verdict === "FLEX").length;
  const sitCount    = starters.filter((p) => p.recommendation?.verdict === "SIT").length;

  return (
    <div className="max-w-4xl mx-auto px-6 py-6">
      <Link href="/" className="text-sm text-[#A5ACAF] hover:text-white transition-colors">
        &larr; Back to home
      </Link>

      <div className="mt-4 mb-6 flex items-start justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-extrabold text-white">My Team</h1>
          <p className="text-sm text-[#A5ACAF] mt-1">
            Deep Football Knowers (DFK) · ESPN · 2025
          </p>
        </div>

        {data && (
          <div className="flex items-center gap-6">
            <div className="text-center">
              <div className="text-2xl font-bold text-white">{data.record}</div>
              <div className="text-[10px] text-[#6B7280]">RECORD</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-white">{data.points_for.toFixed(1)}</div>
              <div className="text-[10px] text-[#6B7280]">PTS FOR</div>
            </div>
            {/* Verdict summary */}
            <div className="flex gap-2 text-xs font-bold">
              <span className="text-[#22C55E]">{startCount} START</span>
              <span className="text-[#F59E0B]">{flexCount} FLEX</span>
              <span className="text-[#EF4444]">{sitCount} SIT</span>
            </div>
          </div>
        )}
      </div>

      {/* Format selector */}
      <div className="flex gap-2 mb-6">
        {["ppr", "half_ppr", "standard"].map((f) => (
          <button key={f} onClick={() => setFormat(f)}
            className={`px-3 py-1 rounded text-xs font-semibold transition-colors
              ${format === f ? "bg-[#004C54] text-white" : "bg-[#1F2937] text-[#A5ACAF] hover:text-white"}`}>
            {f === "ppr" ? "Full PPR" : f === "half_ppr" ? "Half PPR" : "Standard"}
          </button>
        ))}
      </div>

      {loading && <div className="text-[#A5ACAF] text-sm py-12 text-center">Loading your roster…</div>}
      {error && <div className="text-[#EF4444] text-sm py-8 text-center">Error: {error}</div>}

      {data && !loading && (
        <div className="space-y-6">
          {/* Starters */}
          <section>
            <h2 className="text-xs font-semibold text-[#6B7280] uppercase tracking-wider mb-3">Starters</h2>
            <div className="space-y-2">
              {starters.map((p) => <PlayerCard key={p.full_name} player={p} />)}
            </div>
          </section>

          {/* Bench */}
          {bench.length > 0 && (
            <section>
              <h2 className="text-xs font-semibold text-[#6B7280] uppercase tracking-wider mb-3">Bench</h2>
              <div className="space-y-2">
                {bench.map((p) => <PlayerCard key={p.full_name} player={p} />)}
              </div>
            </section>
          )}

          {/* IR */}
          {ir.length > 0 && (
            <section>
              <h2 className="text-xs font-semibold text-[#6B7280] uppercase tracking-wider mb-3">Injured Reserve</h2>
              <div className="space-y-2">
                {ir.map((p) => <PlayerCard key={p.full_name} player={p} />)}
              </div>
            </section>
          )}
        </div>
      )}
    </div>
  );
}
