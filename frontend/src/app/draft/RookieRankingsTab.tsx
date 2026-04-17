"use client";

import { useState, useEffect } from "react";
import { API_BASE } from "@/lib/api";
import { PlayerHeadshot } from "@/components/PlayerHeadshot";

interface RookiePlayer {
  id: number;
  player_name: string;
  position: string | null;
  team: string | null;
  age: number | null;
  value: number;
  overall_rank: number | null;
  position_rank: number | null;
  sleeper_id: string | null;
  age_grade: string;
  position_tier: string;
  ceiling: string;
  floor: string;
  landing_assessment: string;
  trend_30day: number | null;
}

const CEILING_COLORS: Record<string, string> = {
  Elite: "bg-[#7C3AED]/20 text-[#A78BFA] border border-[#7C3AED]/40",
  High:  "bg-[#059669]/20 text-[#34D399] border border-[#059669]/40",
  Mid:   "bg-[#D97706]/20 text-[#FBBF24] border border-[#D97706]/40",
  Low:   "bg-[#1F2937] text-[#6B7280]",
};

const FLOOR_COLORS: Record<string, string> = {
  Elite: "text-[#A78BFA]",
  High:  "text-[#34D399]",
  Mid:   "text-[#FBBF24]",
  Low:   "text-[#EF4444]",
  Unknown: "text-[#6B7280]",
};

const POS_COLORS: Record<string, string> = {
  QB: "bg-[#7C3AED]/20 text-[#A78BFA]",
  RB: "bg-[#059669]/20 text-[#34D399]",
  WR: "bg-[#2563EB]/20 text-[#60A5FA]",
  TE: "bg-[#D97706]/20 text-[#FBBF24]",
};

export function RookieRankingsTab() {
  const [rookies, setRookies] = useState<RookiePlayer[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API_BASE}/dynasty/rookies?limit=100`)
      .then((r) => r.json())
      .then((data) => { setRookies(data); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  if (loading) {
    return <div className="text-[#A5ACAF] text-sm py-12 text-center">Loading rookie rankings…</div>;
  }

  if (rookies.length === 0) {
    return (
      <div className="text-[#A5ACAF] text-sm py-12 text-center">
        No rookies found (age ≤ 23). Run{" "}
        <code className="bg-[#1F2937] px-1 rounded">python scripts/refresh_dynasty.py</code> to populate dynasty data.
      </div>
    );
  }

  return (
    <div>
      <p className="text-xs text-[#6B7280] mb-4">
        {rookies.length} players · Age ≤ 23 · Sorted by dynasty value rank
      </p>
      <div className="grid gap-3">
        {rookies.map((r, i) => (
          <div
            key={r.id}
            className="flex items-center gap-4 bg-[#1F2937]/60 rounded-lg px-4 py-3 border border-[#1F2937] hover:border-[#004C54]/60 transition-colors"
          >
            {/* Rank */}
            <div className="w-8 text-center text-[#6B7280] font-mono text-sm font-bold shrink-0">
              {r.overall_rank ?? i + 1}
            </div>

            {/* Headshot */}
            {r.sleeper_id && (
              <PlayerHeadshot sleeperId={r.sleeper_id} playerName={r.player_name} position={r.position ?? "—"} size={40} />
            )}

            {/* Name + position */}
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-white font-semibold">{r.player_name}</span>
                {r.position && (
                  <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${POS_COLORS[r.position] ?? "bg-[#1F2937] text-[#A5ACAF]"}`}>
                    {r.position}
                  </span>
                )}
                <span className="text-[#6B7280] text-xs">{r.age?.toFixed(1)}y</span>
              </div>
              <div className="text-xs text-[#A5ACAF] mt-0.5">{r.landing_assessment}</div>
            </div>

            {/* Ceiling / Floor */}
            <div className="flex flex-col items-end gap-1 shrink-0">
              <div className="flex items-center gap-1">
                <span className="text-[10px] text-[#6B7280]">Ceiling</span>
                <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${CEILING_COLORS[r.ceiling] ?? ""}`}>
                  {r.ceiling}
                </span>
              </div>
              <div className="flex items-center gap-1">
                <span className="text-[10px] text-[#6B7280]">Floor</span>
                <span className={`text-[10px] font-semibold ${FLOOR_COLORS[r.floor] ?? "text-[#A5ACAF]"}`}>
                  {r.floor}
                </span>
              </div>
            </div>

            {/* Value */}
            <div className="w-20 text-right shrink-0">
              <div className="text-white font-mono text-sm">{r.value.toLocaleString()}</div>
              <div className="text-[10px] text-[#6B7280]">{r.position_tier}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
