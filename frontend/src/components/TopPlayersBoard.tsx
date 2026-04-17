"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { PlayerHeadshot } from "@/components/PlayerHeadshot";
import { API_BASE } from "@/lib/api";

interface TopPlayer {
  id: number;
  full_name: string;
  position: string;
  team: string;
  sleeper_id: string | null;
  verdict: "START" | "SIT" | "FLEX";
  score: number;
  injury_status: string | null;
}

type PositionTab = "ALL" | "QB" | "RB" | "WR" | "TE";

const TABS: PositionTab[] = ["ALL", "QB", "RB", "WR", "TE"];

const VERDICT_COLORS: Record<string, string> = {
  START: "text-[#22C55E]",
  SIT:   "text-[#EF4444]",
  FLEX:  "text-[#F59E0B]",
};

const VERDICT_BORDER: Record<string, string> = {
  START: "border-l-[#22C55E]",
  SIT:   "border-l-[#EF4444]",
  FLEX:  "border-l-[#F59E0B]",
};

function PlayerCard({ player }: { player: TopPlayer }) {
  return (
    <Link href={`/player/${player.id}`}>
      <div
        className={`group bg-[#111827] rounded-xl p-3 flex items-center gap-3 transition-all hover:bg-[#1A2535] border border-[#1F2937] border-l-2 hover:border-[#004C54]/40 cursor-pointer ${VERDICT_BORDER[player.verdict]}`}
      >
        <PlayerHeadshot
          sleeperId={player.sleeper_id}
          playerName={player.full_name}
          position={player.position}
          size={44}
        />
        <div className="flex-1 min-w-0">
          <p className="font-bold text-white text-sm truncate leading-tight">
            {player.full_name}
          </p>
          <p className="text-xs text-[#A5ACAF] mt-0.5">
            {player.position} · {player.team ?? "—"}
          </p>
        </div>
        <div className="flex flex-col items-end gap-0.5 flex-shrink-0">
          <span className={`text-sm font-extrabold ${VERDICT_COLORS[player.verdict]}`}>
            {player.verdict}
          </span>
          <span className="text-xs text-[#A5ACAF]">{player.score.toFixed(1)} pts</span>
        </div>
      </div>
    </Link>
  );
}

function SkeletonCard() {
  return (
    <div className="bg-[#111827] rounded-xl p-3 flex items-center gap-3 border border-[#1F2937] border-l-2 border-l-[#1F2937]">
      <div className="w-11 h-11 rounded-full bg-[#1F2937] animate-pulse flex-shrink-0" />
      <div className="flex-1 space-y-2">
        <div className="h-3.5 w-32 rounded bg-[#1F2937] animate-pulse" />
        <div className="h-3 w-16 rounded bg-[#1F2937] animate-pulse" />
      </div>
      <div className="space-y-1.5 items-end flex flex-col">
        <div className="h-3.5 w-10 rounded bg-[#1F2937] animate-pulse" />
        <div className="h-3 w-12 rounded bg-[#1F2937] animate-pulse" />
      </div>
    </div>
  );
}

interface TopPlayersBoardProps {
  initialData: TopPlayer[];
}

export function TopPlayersBoard({ initialData }: TopPlayersBoardProps) {
  const [activeTab, setActiveTab] = useState<PositionTab>("ALL");
  const [players, setPlayers] = useState<TopPlayer[]>(initialData);
  const [isLoading, setIsLoading] = useState(false);
  const isInitialTab = activeTab === "ALL" && players === initialData;

  useEffect(() => {
    if (isInitialTab) return;
    setIsLoading(true);
    fetch(`${API_BASE}/top-players?position=${activeTab}&limit=12&format=ppr`)
      .then((r) => r.json())
      .then((data: TopPlayer[]) => {
        setPlayers(data);
        setIsLoading(false);
      })
      .catch(() => setIsLoading(false));
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTab]);

  return (
    <div>
      {/* Position tabs */}
      <div className="flex gap-2 mb-4 flex-wrap">
        {TABS.map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-3 py-1.5 rounded-lg text-sm font-semibold transition-colors ${
              activeTab === tab
                ? "bg-[#004C54] text-white"
                : "bg-[#111827] text-[#A5ACAF] hover:text-white hover:bg-[#1F2937]"
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Grid */}
      {isLoading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {Array.from({ length: 12 }).map((_, i) => <SkeletonCard key={i} />)}
        </div>
      ) : players.length === 0 ? (
        <div className="py-12 text-center text-[#A5ACAF] text-sm">
          No player data available — updates when the NFL season is active.
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {players.map((p) => <PlayerCard key={p.id} player={p} />)}
        </div>
      )}
    </div>
  );
}
