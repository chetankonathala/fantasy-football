"use client";

import { useState, useEffect } from "react";
import { API_BASE } from "@/lib/api";

interface Move {
  id: number;
  player_name: string;
  position: string | null;
  from_team: string | null;
  to_team: string | null;
  move_type: string;
  fantasy_impact: string | null;
  impact_direction: string | null;
  impact_note: string | null;
  dynasty_value: number | null;
  sleeper_id: string | null;
}

const POS_COLORS: Record<string, string> = {
  QB: "bg-[#7C3AED]/20 text-[#A78BFA]",
  RB: "bg-[#059669]/20 text-[#34D399]",
  WR: "bg-[#2563EB]/20 text-[#60A5FA]",
  TE: "bg-[#D97706]/20 text-[#FBBF24]",
};

const IMPACT_COLORS: Record<string, string> = {
  high:   "text-[#34D399]",
  medium: "text-[#FBBF24]",
  low:    "text-[#6B7280]",
};

const DIRECTION_ICON: Record<string, string> = {
  up:      "↑",
  down:    "↓",
  neutral: "→",
};

const DIRECTION_COLOR: Record<string, string> = {
  up:      "text-[#34D399]",
  down:    "text-[#EF4444]",
  neutral: "text-[#6B7280]",
};

const MOVE_TYPE_LABELS: Record<string, string> = {
  free_agent:    "Free Agent",
  trade:         "Trade",
  cut:           "Cut",
  draft_pick:    "Draft Pick",
  undrafted_fa:  "UDFA",
};

const POSITIONS  = ["All", "QB", "RB", "WR", "TE"];
const IMPACTS    = ["All", "high", "medium", "low"];
const MOVE_TYPES = ["All", "free_agent", "trade", "cut"];

export function MovesTab() {
  const [moves, setMoves] = useState<Move[]>([]);
  const [loading, setLoading] = useState(true);
  const [posFilter, setPosFilter] = useState("All");
  const [impactFilter, setImpactFilter] = useState("All");
  const [typeFilter, setTypeFilter] = useState("All");
  const [teamSearch, setTeamSearch] = useState("");

  useEffect(() => {
    const params = new URLSearchParams({ limit: "200" });
    if (posFilter !== "All") params.set("position", posFilter);
    if (impactFilter !== "All") params.set("impact", impactFilter);
    if (typeFilter !== "All") params.set("move_type", typeFilter);
    if (teamSearch.trim()) params.set("team", teamSearch.trim().toUpperCase());
    setLoading(true);
    fetch(`${API_BASE}/offseason/moves?${params}`)
      .then((r) => r.json())
      .then((data) => { setMoves(data.moves ?? []); setLoading(false); })
      .catch(() => setLoading(false));
  }, [posFilter, impactFilter, typeFilter, teamSearch]);

  return (
    <div>
      {/* Filters */}
      <div className="flex flex-wrap gap-4 mb-5">
        <div className="flex items-center gap-2">
          <span className="text-xs text-[#6B7280]">Position</span>
          <div className="flex gap-1">
            {POSITIONS.map((p) => (
              <button key={p} onClick={() => setPosFilter(p)}
                className={`px-2.5 py-1 text-xs rounded font-medium transition-colors
                  ${posFilter === p ? "bg-[#004C54] text-white" : "bg-[#1F2937] text-[#A5ACAF] hover:text-white"}`}>
                {p}
              </button>
            ))}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-[#6B7280]">Impact</span>
          <div className="flex gap-1">
            {IMPACTS.map((im) => (
              <button key={im} onClick={() => setImpactFilter(im)}
                className={`px-2.5 py-1 text-xs rounded font-medium transition-colors capitalize
                  ${impactFilter === im ? "bg-[#004C54] text-white" : "bg-[#1F2937] text-[#A5ACAF] hover:text-white"}`}>
                {im}
              </button>
            ))}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-[#6B7280]">Type</span>
          <div className="flex gap-1">
            {MOVE_TYPES.map((mt) => (
              <button key={mt} onClick={() => setTypeFilter(mt)}
                className={`px-2.5 py-1 text-xs rounded font-medium transition-colors
                  ${typeFilter === mt ? "bg-[#004C54] text-white" : "bg-[#1F2937] text-[#A5ACAF] hover:text-white"}`}>
                {mt === "All" ? "All" : MOVE_TYPE_LABELS[mt] ?? mt}
              </button>
            ))}
          </div>
        </div>
        <input
          type="text"
          placeholder="Team (e.g. PHI)"
          value={teamSearch}
          onChange={(e) => setTeamSearch(e.target.value)}
          className="px-3 py-1 text-xs bg-[#1F2937] text-white rounded border border-[#374151] focus:border-[#004C54] focus:outline-none w-28"
        />
      </div>

      {loading && <div className="text-[#A5ACAF] text-sm py-12 text-center">Loading offseason moves…</div>}

      {!loading && moves.length === 0 && (
        <div className="text-[#A5ACAF] text-sm py-12 text-center">
          No moves found. Run{" "}
          <code className="bg-[#1F2937] px-1 rounded">uv run python scripts/refresh_offseason_moves.py</code> to detect team changes.
        </div>
      )}

      {!loading && moves.length > 0 && (
        <>
          <p className="text-xs text-[#6B7280] mb-4">{moves.length} moves · Sorted by dynasty value</p>
          <div className="grid gap-2">
            {moves.map((m) => (
              <div
                key={m.id}
                className="flex items-center gap-4 bg-[#1F2937]/60 rounded-lg px-4 py-3 border border-[#1F2937] hover:border-[#004C54]/60 transition-colors"
              >
                {/* Direction arrow */}
                <div className={`text-lg font-bold shrink-0 w-6 text-center ${DIRECTION_COLOR[m.impact_direction ?? "neutral"]}`}>
                  {DIRECTION_ICON[m.impact_direction ?? "neutral"]}
                </div>

                {/* Name + position */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-white font-semibold">{m.player_name}</span>
                    {m.position && (
                      <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${POS_COLORS[m.position] ?? "bg-[#1F2937] text-[#A5ACAF]"}`}>
                        {m.position}
                      </span>
                    )}
                    <span className="text-[10px] text-[#6B7280] bg-[#111827] px-1.5 py-0.5 rounded">
                      {MOVE_TYPE_LABELS[m.move_type] ?? m.move_type}
                    </span>
                  </div>
                  {m.impact_note && (
                    <div className="text-xs text-[#A5ACAF] mt-0.5 truncate">{m.impact_note}</div>
                  )}
                </div>

                {/* Team change */}
                <div className="text-xs text-[#A5ACAF] shrink-0 text-right">
                  {m.from_team && m.to_team ? (
                    <span>{m.from_team} <span className="text-[#004C54]">→</span> {m.to_team}</span>
                  ) : m.to_team ? (
                    <span className="text-[#34D399]">+ {m.to_team}</span>
                  ) : m.from_team ? (
                    <span className="text-[#EF4444]">− {m.from_team}</span>
                  ) : null}
                </div>

                {/* Impact badge */}
                {m.fantasy_impact && (
                  <div className={`text-xs font-semibold capitalize w-14 text-right shrink-0 ${IMPACT_COLORS[m.fantasy_impact] ?? ""}`}>
                    {m.fantasy_impact}
                  </div>
                )}

                {/* Dynasty value */}
                {m.dynasty_value != null && (
                  <div className="w-16 text-right shrink-0">
                    <div className="text-white font-mono text-sm">{m.dynasty_value.toLocaleString()}</div>
                    <div className="text-[10px] text-[#6B7280]">Dyn val</div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
