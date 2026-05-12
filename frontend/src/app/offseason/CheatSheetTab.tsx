"use client";

import { useState, useEffect } from "react";
import { API_BASE } from "@/lib/api";
import { PlayerHeadshot } from "@/components/PlayerHeadshot";

interface CheatSheetPlayer {
  id: number;
  player_name: string;
  position: string | null;
  team: string | null;
  age: number | null;
  value: number;
  overall_rank: number | null;
  position_rank: number | null;
  trend_30day: number | null;
  tier: string;
  is_rookie: boolean;
  opportunity_grade: string | null;
  year1_projection: number | null;
  nfl_round: number | null;
  sleeper_id: string | null;
}

const POS_COLORS: Record<string, string> = {
  QB: "bg-[#7C3AED]/20 text-[#A78BFA]",
  RB: "bg-[#059669]/20 text-[#34D399]",
  WR: "bg-[#2563EB]/20 text-[#60A5FA]",
  TE: "bg-[#D97706]/20 text-[#FBBF24]",
};

const TIER_COLORS: Record<string, string> = {
  elite:  "border-l-4 border-l-[#A78BFA]",
  strong: "border-l-4 border-l-[#34D399]",
  value:  "border-l-4 border-l-[#FBBF24]",
  depth:  "border-l-4 border-l-[#374151]",
};

const TIER_LABELS: Record<string, string> = {
  elite:  "Elite",
  strong: "Strong",
  value:  "Value",
  depth:  "Depth",
};

const GRADE_COLORS: Record<string, string> = {
  A: "text-[#34D399]",
  B: "text-[#60A5FA]",
  C: "text-[#FBBF24]",
  D: "text-[#6B7280]",
};

const POSITIONS = ["QB", "RB", "WR", "TE"];

export function CheatSheetTab() {
  const [positions, setPositions] = useState<Record<string, CheatSheetPlayer[]>>({});
  const [loading, setLoading] = useState(true);
  const [activePos, setActivePos] = useState("RB");
  const [tierFilter, setTierFilter] = useState("All");

  useEffect(() => {
    fetch(`${API_BASE}/offseason/cheat-sheet`)
      .then((r) => r.json())
      .then((data) => { setPositions(data.positions ?? {}); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  const players = positions[activePos] ?? [];
  const filtered = tierFilter === "All" ? players : players.filter((p) => p.tier === tierFilter);

  if (loading) return <div className="text-[#A5ACAF] text-sm py-12 text-center">Building cheat sheet…</div>;

  return (
    <div>
      <p className="text-xs text-[#6B7280] mb-4">
        Dynasty consensus rankings for your 2026 DFK draft. Rookies flagged with opportunity grade.
      </p>

      {/* Position tabs */}
      <div className="flex gap-1 mb-4">
        {POSITIONS.map((pos) => (
          <button
            key={pos}
            onClick={() => setActivePos(pos)}
            className={`px-4 py-1.5 text-sm font-bold rounded transition-colors
              ${activePos === pos
                ? `${POS_COLORS[pos]} border border-current/30`
                : "text-[#6B7280] bg-[#1F2937] hover:text-white"}`}
          >
            {pos} <span className="font-normal text-[10px] ml-1">{positions[pos]?.length ?? 0}</span>
          </button>
        ))}
      </div>

      {/* Tier filter */}
      <div className="flex items-center gap-2 mb-5">
        <span className="text-xs text-[#6B7280]">Tier</span>
        {["All", "elite", "strong", "value", "depth"].map((t) => (
          <button
            key={t}
            onClick={() => setTierFilter(t)}
            className={`px-2.5 py-1 text-xs rounded font-medium capitalize transition-colors
              ${tierFilter === t ? "bg-[#004C54] text-white" : "bg-[#1F2937] text-[#A5ACAF] hover:text-white"}`}
          >
            {t === "All" ? "All" : TIER_LABELS[t]}
          </button>
        ))}
      </div>

      {filtered.length === 0 && (
        <div className="text-[#A5ACAF] text-sm py-12 text-center">
          No players found. Run{" "}
          <code className="bg-[#1F2937] px-1 rounded">uv run python scripts/refresh_dynasty.py</code> to populate.
        </div>
      )}

      <div className="grid gap-2">
        {filtered.map((p) => (
          <div
            key={p.id}
            className={`flex items-center gap-4 bg-[#1F2937]/60 rounded-lg px-4 py-3 border border-[#1F2937] hover:border-[#004C54]/60 transition-colors ${TIER_COLORS[p.tier] ?? ""}`}
          >
            {/* Rank */}
            <div className="w-8 text-center text-[#6B7280] font-mono text-sm font-bold shrink-0">
              {p.position_rank}
            </div>

            {p.sleeper_id && (
              <PlayerHeadshot sleeperId={p.sleeper_id} playerName={p.player_name} position={p.position ?? "—"} size={36} />
            )}

            {/* Name + metadata */}
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-white font-semibold">{p.player_name}</span>
                {p.team && <span className="text-[#A5ACAF] text-xs font-semibold">{p.team}</span>}
                {p.age && <span className="text-[#6B7280] text-xs">{p.age.toFixed(1)}y</span>}
                {p.is_rookie && (
                  <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-[#004C54]/30 text-[#34D399] border border-[#004C54]/40">
                    ROOK {p.nfl_round ? `R${p.nfl_round}` : ""}
                  </span>
                )}
                {p.opportunity_grade && (
                  <span className={`text-[10px] font-bold ${GRADE_COLORS[p.opportunity_grade]}`}>
                    Grade {p.opportunity_grade}
                  </span>
                )}
              </div>
              {p.year1_projection != null && (
                <div className="text-xs text-[#6B7280] mt-0.5">
                  Yr1 proj: <span className="text-[#A5ACAF]">{p.year1_projection.toFixed(0)} PPR pts</span>
                </div>
              )}
            </div>

            {/* Trend */}
            {p.trend_30day != null && (
              <div className={`text-xs font-mono shrink-0 ${p.trend_30day > 0 ? "text-[#34D399]" : p.trend_30day < 0 ? "text-[#EF4444]" : "text-[#6B7280]"}`}>
                {p.trend_30day > 0 ? "+" : ""}{p.trend_30day}
              </div>
            )}

            {/* Tier label */}
            <div className="text-[10px] text-[#6B7280] capitalize w-12 text-right shrink-0">
              {TIER_LABELS[p.tier]}
            </div>

            {/* Dynasty value */}
            <div className="w-16 text-right shrink-0">
              <div className="text-white font-mono text-sm">{p.value.toLocaleString()}</div>
              <div className="text-[10px] text-[#6B7280]">#{p.overall_rank} ovr</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
