"use client";

import { useState, useEffect } from "react";
import { API_BASE } from "@/lib/api";
import { PlayerHeadshot } from "@/components/PlayerHeadshot";

interface DynastyPlayer {
  id: number;
  player_name: string;
  position: string | null;
  team: string | null;
  age: number | null;
  value: number;
  overall_rank: number | null;
  position_rank: number | null;
  trend_30day: number | null;
  is_pick: boolean;
  sleeper_id: string | null;
  age_grade: string;
  position_tier: string;
}

const POSITIONS = ["ALL", "QB", "RB", "WR", "TE"];

const POS_COLORS: Record<string, string> = {
  QB: "bg-[#7C3AED]/20 text-[#A78BFA]",
  RB: "bg-[#059669]/20 text-[#34D399]",
  WR: "bg-[#2563EB]/20 text-[#60A5FA]",
  TE: "bg-[#D97706]/20 text-[#FBBF24]",
};

const TIER_COLORS: Record<string, string> = {
  "Tier 1": "text-[#FBBF24] font-bold",
  "Tier 2": "text-[#60A5FA]",
  "Tier 3": "text-[#A5ACAF]",
  "Tier 4": "text-[#6B7280]",
  "Tier 5": "text-[#4B5563]",
};

const AGE_GRADE_COLORS: Record<string, string> = {
  A: "text-[#22C55E] font-bold",
  B: "text-[#86EFAC]",
  C: "text-[#F59E0B]",
  D: "text-[#EF4444]",
  "N/A": "text-[#6B7280]",
};

function TrendBadge({ value }: { value: number | null }) {
  if (value === null) return null;
  const color = value > 0 ? "text-[#22C55E]" : value < 0 ? "text-[#EF4444]" : "text-[#6B7280]";
  return <span className={`text-[10px] font-semibold ${color}`}>{value > 0 ? "+" : ""}{value}</span>;
}

export function DynastyRankingsTab() {
  const [players, setPlayers] = useState<DynastyPlayer[]>([]);
  const [loading, setLoading] = useState(true);
  const [position, setPosition] = useState("ALL");

  useEffect(() => {
    setLoading(true);
    fetch(`${API_BASE}/dynasty/rankings?position=${position}&limit=200`)
      .then((r) => r.json())
      .then((data) => { setPlayers(data); setLoading(false); })
      .catch(() => setLoading(false));
  }, [position]);

  return (
    <div>
      {/* Position filter */}
      <div className="flex gap-2 mb-4">
        {POSITIONS.map((p) => (
          <button
            key={p}
            onClick={() => setPosition(p)}
            className={`px-3 py-1 rounded text-xs font-semibold transition-colors
              ${position === p
                ? "bg-[#004C54] text-white"
                : "bg-[#1F2937] text-[#A5ACAF] hover:text-white"
              }`}
          >
            {p}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="text-[#A5ACAF] text-sm py-12 text-center">Loading dynasty rankings…</div>
      ) : players.length === 0 ? (
        <div className="text-[#A5ACAF] text-sm py-12 text-center">
          No dynasty data. Run <code className="bg-[#1F2937] px-1 rounded">python scripts/refresh_dynasty.py</code> first.
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-[#6B7280] text-xs border-b border-[#1F2937]">
                <th className="text-left py-2 px-2 w-12">Rank</th>
                <th className="text-left py-2 px-2">Player</th>
                <th className="text-left py-2 px-2">Pos</th>
                <th className="text-left py-2 px-2">Age</th>
                <th className="text-left py-2 px-2">Age Grade</th>
                <th className="text-left py-2 px-2">Tier</th>
                <th className="text-right py-2 px-2">Value</th>
                <th className="text-right py-2 px-2">Trend</th>
              </tr>
            </thead>
            <tbody>
              {players.map((p, i) => (
                <tr
                  key={p.id}
                  className={`border-b border-[#1F2937]/50 hover:bg-[#1F2937]/40 transition-colors ${
                    i % 2 === 0 ? "bg-transparent" : "bg-[#111827]/50"
                  }`}
                >
                  <td className="py-2 px-2 text-[#6B7280] font-mono text-xs">{p.overall_rank ?? "—"}</td>
                  <td className="py-2 px-2">
                    <div className="flex items-center gap-2">
                      {p.sleeper_id && (
                        <PlayerHeadshot sleeperId={p.sleeper_id} playerName={p.player_name} position={p.position ?? "—"} size={28} />
                      )}
                      <div>
                        <div className="text-white font-medium">{p.player_name}</div>
                        {p.team && <div className="text-[#6B7280] text-[10px]">{p.team}</div>}
                      </div>
                    </div>
                  </td>
                  <td className="py-2 px-2">
                    {p.position && (
                      <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${POS_COLORS[p.position] ?? "bg-[#1F2937] text-[#A5ACAF]"}`}>
                        {p.position}
                      </span>
                    )}
                  </td>
                  <td className="py-2 px-2 text-[#A5ACAF]">{p.age?.toFixed(1) ?? "—"}</td>
                  <td className={`py-2 px-2 ${AGE_GRADE_COLORS[p.age_grade] ?? "text-[#A5ACAF]"}`}>
                    {p.age_grade}
                  </td>
                  <td className={`py-2 px-2 text-xs ${TIER_COLORS[p.position_tier] ?? "text-[#A5ACAF]"}`}>
                    {p.position_tier}
                  </td>
                  <td className="py-2 px-2 text-right text-white font-mono">{p.value.toLocaleString()}</td>
                  <td className="py-2 px-2 text-right"><TrendBadge value={p.trend_30day} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
