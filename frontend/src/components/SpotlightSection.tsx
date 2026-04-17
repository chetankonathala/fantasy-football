"use client";

import Link from "next/link";
import { PlayerHeadshot } from "@/components/PlayerHeadshot";

interface SpotlightPlayer {
  id: number;
  full_name: string;
  position: string;
  team: string;
  sleeper_id: string | null;
  verdict: "START" | "SIT" | "FLEX";
  score: number;
  reasons: string[];
  injury_status: string | null;
}

interface SpotlightData {
  QB?: SpotlightPlayer;
  RB?: SpotlightPlayer;
  WR?: SpotlightPlayer;
  TE?: SpotlightPlayer;
}

const VERDICT_COLORS: Record<string, string> = {
  START: "text-[#22C55E]",
  SIT:   "text-[#EF4444]",
  FLEX:  "text-[#F59E0B]",
};

const VERDICT_GLOW: Record<string, string> = {
  START: "rgba(34,197,94,0.10)",
  SIT:   "rgba(239,68,68,0.10)",
  FLEX:  "rgba(245,158,11,0.10)",
};

const VERDICT_BORDER: Record<string, string> = {
  START: "rgba(34,197,94,0.25)",
  SIT:   "rgba(239,68,68,0.25)",
  FLEX:  "rgba(245,158,11,0.25)",
};

const POS_LABELS: Record<string, string> = {
  QB: "QB1",
  RB: "RB1",
  WR: "WR1",
  TE: "TE1",
};

function SpotlightCard({ player }: { player: SpotlightPlayer }) {
  const glow = VERDICT_GLOW[player.verdict];
  const border = VERDICT_BORDER[player.verdict];
  const topReason = player.reasons[0] ?? "";

  return (
    <Link href={`/player/${player.id}`}>
      <div
        className="relative rounded-2xl p-5 flex flex-col items-center text-center cursor-pointer transition-transform hover:scale-[1.02] hover:brightness-110"
        style={{
          background: `radial-gradient(ellipse 90% 60% at 50% 0%, ${glow} 0%, #111827 60%)`,
          border: `1px solid ${border}`,
        }}
      >
        {/* Position badge */}
        <span className="absolute top-3 left-3 text-[10px] font-bold tracking-widest uppercase text-[#A5ACAF] bg-[#0A0A0A]/60 px-2 py-0.5 rounded-full">
          {POS_LABELS[player.position]}
        </span>

        {/* Headshot */}
        <div className="mt-4 mb-3">
          <PlayerHeadshot
            sleeperId={player.sleeper_id}
            playerName={player.full_name}
            position={player.position}
            size={72}
          />
        </div>

        {/* Name + team */}
        <p className="font-extrabold text-white text-sm leading-tight">{player.full_name}</p>
        <p className="text-xs text-[#A5ACAF] mt-0.5">{player.team}</p>

        {/* Verdict */}
        <p className={`mt-3 text-2xl font-extrabold tracking-wide ${VERDICT_COLORS[player.verdict]}`}>
          {player.verdict}
        </p>
        <p className="text-xs text-[#A5ACAF] mt-0.5">{player.score.toFixed(1)} pts</p>

        {/* Top reason */}
        {topReason && (
          <p className="mt-3 text-xs text-[#A5ACAF] leading-relaxed line-clamp-2 max-w-[160px]">
            {topReason}
          </p>
        )}
      </div>
    </Link>
  );
}

function SpotlightSkeleton() {
  return (
    <div className="rounded-2xl p-5 flex flex-col items-center bg-[#111827] border border-[#1F2937]">
      <div className="w-18 h-18 rounded-full bg-[#1F2937] animate-pulse mt-4 mb-3" style={{ width: 72, height: 72 }} />
      <div className="h-3.5 w-28 rounded bg-[#1F2937] animate-pulse mb-1.5" />
      <div className="h-3 w-14 rounded bg-[#1F2937] animate-pulse mb-3" />
      <div className="h-7 w-16 rounded bg-[#1F2937] animate-pulse mb-1" />
      <div className="h-3 w-20 rounded bg-[#1F2937] animate-pulse" />
    </div>
  );
}

interface SpotlightSectionProps {
  initialData: SpotlightData;
}

export function SpotlightSection({ initialData }: SpotlightSectionProps) {
  const positions = ["QB", "RB", "WR", "TE"] as const;
  const hasData = positions.some((p) => initialData[p]);

  if (!hasData) {
    return (
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {positions.map((p) => <SpotlightSkeleton key={p} />)}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
      {positions.map((pos) => {
        const player = initialData[pos];
        return player ? (
          <SpotlightCard key={pos} player={player} />
        ) : (
          <SpotlightSkeleton key={pos} />
        );
      })}
    </div>
  );
}
