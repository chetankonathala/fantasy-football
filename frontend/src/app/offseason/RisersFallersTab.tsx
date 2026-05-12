"use client";

import { useState, useEffect } from "react";
import { API_BASE } from "@/lib/api";
import { PlayerHeadshot } from "@/components/PlayerHeadshot";

interface TrendPlayer {
  id: number;
  player_name: string;
  position: string | null;
  team: string | null;
  age: number | null;
  value: number;
  overall_rank: number | null;
  position_rank: number | null;
  trend_30day: number | null;
  sleeper_id: string | null;
}

const POS_COLORS: Record<string, string> = {
  QB: "bg-[#7C3AED]/20 text-[#A78BFA]",
  RB: "bg-[#059669]/20 text-[#34D399]",
  WR: "bg-[#2563EB]/20 text-[#60A5FA]",
  TE: "bg-[#D97706]/20 text-[#FBBF24]",
};

function TrendCard({ player, direction }: { player: TrendPlayer; direction: "up" | "down" }) {
  const isUp = direction === "up";
  const trend = player.trend_30day ?? 0;
  return (
    <div className="flex items-center gap-3 bg-[#1F2937]/60 rounded-lg px-4 py-3 border border-[#1F2937] hover:border-[#004C54]/60 transition-colors">
      {player.sleeper_id && (
        <PlayerHeadshot sleeperId={player.sleeper_id} playerName={player.player_name} position={player.position ?? "—"} size={36} />
      )}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-white font-semibold text-sm">{player.player_name}</span>
          {player.position && (
            <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${POS_COLORS[player.position] ?? "bg-[#1F2937] text-[#A5ACAF]"}`}>
              {player.position}
            </span>
          )}
          {player.team && <span className="text-[#6B7280] text-xs">{player.team}</span>}
        </div>
        <div className="text-xs text-[#6B7280] mt-0.5">
          #{player.overall_rank ?? "—"} overall · #{player.position_rank ?? "—"} {player.position}
        </div>
      </div>
      <div className="text-right shrink-0">
        <div className={`font-mono font-bold text-base ${isUp ? "text-[#34D399]" : "text-[#EF4444]"}`}>
          {isUp ? "+" : ""}{trend.toLocaleString()}
        </div>
        <div className="text-[10px] text-[#6B7280]">30d trend</div>
      </div>
      <div className="text-right shrink-0 w-16">
        <div className="text-white font-mono text-sm">{player.value.toLocaleString()}</div>
        <div className="text-[10px] text-[#6B7280]">Dyn val</div>
      </div>
    </div>
  );
}

export function RisersFallersTab() {
  const [risers, setRisers] = useState<TrendPlayer[]>([]);
  const [fallers, setFallers] = useState<TrendPlayer[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API_BASE}/offseason/risers-fallers?limit=20`)
      .then((r) => r.json())
      .then((data) => {
        setRisers(data.risers ?? []);
        setFallers(data.fallers ?? []);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  if (loading) return <div className="text-[#A5ACAF] text-sm py-12 text-center">Loading dynasty trends…</div>;

  if (risers.length === 0 && fallers.length === 0) {
    return (
      <div className="text-[#A5ACAF] text-sm py-12 text-center">
        No trend data. Run{" "}
        <code className="bg-[#1F2937] px-1 rounded">uv run python scripts/refresh_dynasty.py</code> to populate.
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
      <div>
        <h2 className="text-sm font-bold text-[#34D399] mb-3 flex items-center gap-2">
          <span>↑</span> Biggest Risers <span className="text-[#6B7280] font-normal">(30-day)</span>
        </h2>
        <div className="grid gap-2">
          {risers.map((p) => <TrendCard key={p.id} player={p} direction="up" />)}
        </div>
      </div>
      <div>
        <h2 className="text-sm font-bold text-[#EF4444] mb-3 flex items-center gap-2">
          <span>↓</span> Biggest Fallers <span className="text-[#6B7280] font-normal">(30-day)</span>
        </h2>
        <div className="grid gap-2">
          {fallers.map((p) => <TrendCard key={p.id} player={p} direction="down" />)}
        </div>
      </div>
    </div>
  );
}
