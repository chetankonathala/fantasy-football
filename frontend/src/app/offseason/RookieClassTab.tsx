"use client";

import { useState, useEffect } from "react";
import { API_BASE } from "@/lib/api";
import { PlayerHeadshot } from "@/components/PlayerHeadshot";

interface Rookie {
  id: number;
  player_name: string;
  position: string | null;
  team: string | null;
  college: string | null;
  nfl_round: number | null;
  nfl_pick: number | null;
  age: number | null;
  dynasty_value: number | null;
  dynasty_overall_rank: number | null;
  dynasty_position_rank: number | null;
  opportunity_grade: string | null;
  opportunity_note: string | null;
  year1_projection: number | null;
  sleeper_id: string | null;
}

const POS_COLORS: Record<string, string> = {
  QB: "bg-[#7C3AED]/20 text-[#A78BFA]",
  RB: "bg-[#059669]/20 text-[#34D399]",
  WR: "bg-[#2563EB]/20 text-[#60A5FA]",
  TE: "bg-[#D97706]/20 text-[#FBBF24]",
};

const GRADE_COLORS: Record<string, string> = {
  A: "bg-[#059669]/20 text-[#34D399] border border-[#059669]/40",
  B: "bg-[#2563EB]/20 text-[#60A5FA] border border-[#2563EB]/40",
  C: "bg-[#D97706]/20 text-[#FBBF24] border border-[#D97706]/40",
  D: "bg-[#1F2937] text-[#6B7280] border border-[#374151]",
};

const POSITIONS = ["All", "QB", "RB", "WR", "TE"];
const GRADES = ["All", "A", "B", "C", "D"];

function ordinal(n: number): string {
  const s = ["th", "st", "nd", "rd"];
  const v = n % 100;
  return n + (s[(v - 20) % 10] || s[v] || s[0]);
}

export function RookieClassTab() {
  const [rookies, setRookies] = useState<Rookie[]>([]);
  const [loading, setLoading] = useState(true);
  const [posFilter, setPosFilter] = useState("All");
  const [gradeFilter, setGradeFilter] = useState("All");

  useEffect(() => {
    const params = new URLSearchParams({ limit: "200" });
    if (posFilter !== "All") params.set("position", posFilter);
    if (gradeFilter !== "All") params.set("grade", gradeFilter);
    setLoading(true);
    fetch(`${API_BASE}/offseason/rookies?${params}`)
      .then((r) => r.json())
      .then((data) => { setRookies(data.rookies ?? []); setLoading(false); })
      .catch(() => setLoading(false));
  }, [posFilter, gradeFilter]);

  return (
    <div>
      {/* Filters */}
      <div className="flex flex-wrap gap-4 mb-5">
        <div className="flex items-center gap-2">
          <span className="text-xs text-[#6B7280]">Position</span>
          <div className="flex gap-1">
            {POSITIONS.map((p) => (
              <button
                key={p}
                onClick={() => setPosFilter(p)}
                className={`px-2.5 py-1 text-xs rounded font-medium transition-colors
                  ${posFilter === p ? "bg-[#004C54] text-white" : "bg-[#1F2937] text-[#A5ACAF] hover:text-white"}`}
              >
                {p}
              </button>
            ))}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-[#6B7280]">Grade</span>
          <div className="flex gap-1">
            {GRADES.map((g) => (
              <button
                key={g}
                onClick={() => setGradeFilter(g)}
                className={`px-2.5 py-1 text-xs rounded font-medium transition-colors
                  ${gradeFilter === g ? "bg-[#004C54] text-white" : "bg-[#1F2937] text-[#A5ACAF] hover:text-white"}`}
              >
                {g}
              </button>
            ))}
          </div>
        </div>
      </div>

      {loading && <div className="text-[#A5ACAF] text-sm py-12 text-center">Loading 2026 rookie class…</div>}

      {!loading && rookies.length === 0 && (
        <div className="text-[#A5ACAF] text-sm py-12 text-center">
          No rookies found. Run{" "}
          <code className="bg-[#1F2937] px-1 rounded">uv run python scripts/refresh_rookies.py</code> to populate.
        </div>
      )}

      {!loading && rookies.length > 0 && (
        <>
          <p className="text-xs text-[#6B7280] mb-4">{rookies.length} rookies · 2026 NFL Draft class · Sorted by dynasty consensus</p>
          <div className="grid gap-3">
            {rookies.map((r, i) => (
              <div
                key={r.id}
                className="flex items-center gap-4 bg-[#1F2937]/60 rounded-lg px-4 py-3 border border-[#1F2937] hover:border-[#004C54]/60 transition-colors"
              >
                {/* Rank */}
                <div className="w-8 text-center text-[#6B7280] font-mono text-sm font-bold shrink-0">
                  {r.dynasty_overall_rank ?? i + 1}
                </div>

                {/* Headshot */}
                {r.sleeper_id && (
                  <PlayerHeadshot sleeperId={r.sleeper_id} playerName={r.player_name} position={r.position ?? "—"} size={40} />
                )}

                {/* Name + details */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-white font-semibold">{r.player_name}</span>
                    {r.position && (
                      <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${POS_COLORS[r.position] ?? "bg-[#1F2937] text-[#A5ACAF]"}`}>
                        {r.position}
                      </span>
                    )}
                    {r.team && <span className="text-[#A5ACAF] text-xs font-semibold">{r.team}</span>}
                    {r.nfl_round && r.nfl_pick && (
                      <span className="text-[10px] text-[#6B7280]">
                        Rd {r.nfl_round}, {ordinal(r.nfl_pick)} overall
                      </span>
                    )}
                  </div>
                  <div className="text-xs text-[#6B7280] mt-0.5 truncate">
                    {r.college && <span>{r.college}</span>}
                    {r.opportunity_note && <span className="ml-2 text-[#A5ACAF]">{r.opportunity_note}</span>}
                  </div>
                </div>

                {/* Grade + proj */}
                <div className="flex flex-col items-end gap-1.5 shrink-0">
                  {r.opportunity_grade && (
                    <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${GRADE_COLORS[r.opportunity_grade] ?? ""}`}>
                      Grade {r.opportunity_grade}
                    </span>
                  )}
                  {r.year1_projection != null && (
                    <div className="text-right">
                      <div className="text-white font-mono text-sm">{r.year1_projection.toFixed(0)}</div>
                      <div className="text-[10px] text-[#6B7280]">Yr1 PPR pts</div>
                    </div>
                  )}
                </div>

                {/* Dynasty value */}
                {r.dynasty_value != null && (
                  <div className="w-16 text-right shrink-0">
                    <div className="text-white font-mono text-sm">{r.dynasty_value.toLocaleString()}</div>
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
