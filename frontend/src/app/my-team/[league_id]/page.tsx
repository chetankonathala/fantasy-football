"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@clerk/nextjs";
import { API_BASE, authedFetch } from "@/lib/api";
import { PlayerHeadshot } from "@/components/PlayerHeadshot";

interface RosterPlayer {
  id: number;
  full_name: string;
  position: string;
  team: string;
  sleeper_id: string | null;
  verdict: "START" | "SIT" | "FLEX";
  score: number;
  reasons: string[];
  injury_status: string | null;
  vegas_implied_total: number | null;
  weather_flag: boolean;
  roster_player_id: number;
  position_slot: string;
}

interface League {
  id: number;
  name: string;
  scoring_format: string;
  num_teams: number;
  roster: RosterPlayer[];
}

const VERDICT_STYLES = {
  START: { bg: "bg-[#022c10] border-[#22C55E]/50", text: "text-[#22C55E]" },
  FLEX:  { bg: "bg-[#1c1400] border-[#F59E0B]/50", text: "text-[#F59E0B]" },
  SIT:   { bg: "bg-[#1a0000] border-[#EF4444]/50", text: "text-[#EF4444]" },
};

const POS_COLORS: Record<string, string> = {
  QB: "bg-[#7C3AED]/20 text-[#A78BFA]",
  RB: "bg-[#059669]/20 text-[#34D399]",
  WR: "bg-[#2563EB]/20 text-[#60A5FA]",
  TE: "bg-[#D97706]/20 text-[#FBBF24]",
  K:  "bg-[#374151] text-[#9CA3AF]",
};

const FORMAT_LABELS: Record<string, string> = {
  ppr: "Full PPR", half_ppr: "Half PPR", standard: "Standard",
};

export default function LeagueRosterPage() {
  const { league_id } = useParams<{ league_id: string }>();
  const { getToken, isLoaded, isSignedIn } = useAuth();
  const router = useRouter();
  const [league, setLeague] = useState<League | null>(null);
  const [loading, setLoading] = useState(true);
  const [removing, setRemoving] = useState<number | null>(null);

  const load = useCallback(async () => {
    const res = await authedFetch(`${API_BASE}/leagues/${league_id}`, getToken);
    if (!res.ok) { router.push("/my-team"); return; }
    setLeague(await res.json());
    setLoading(false);
  }, [league_id, getToken, router]);

  useEffect(() => {
    if (!isLoaded) return;
    if (!isSignedIn) { router.push("/"); return; }
    load();
  }, [isLoaded, isSignedIn, load, router]);

  const removePlayer = async (rosterPlayerId: number) => {
    setRemoving(rosterPlayerId);
    await authedFetch(`${API_BASE}/leagues/${league_id}/roster/${rosterPlayerId}`, getToken, { method: "DELETE" });
    setLeague((prev) => prev ? { ...prev, roster: prev.roster.filter((p) => p.roster_player_id !== rosterPlayerId) } : prev);
    setRemoving(null);
  };

  const deleteLeague = async () => {
    if (!confirm(`Delete "${league?.name}"? This cannot be undone.`)) return;
    await authedFetch(`${API_BASE}/leagues/${league_id}`, getToken, { method: "DELETE" });
    router.push("/my-team");
  };

  if (!isLoaded || loading) {
    return (
      <div className="max-w-4xl mx-auto px-6 py-10 space-y-3">
        {[1,2,3,4].map((i) => <div key={i} className="h-16 rounded-lg bg-[#1F2937] animate-pulse" />)}
      </div>
    );
  }
  if (!league) return null;

  const starters = league.roster.filter((p) => p.position_slot === "starter");
  const bench    = league.roster.filter((p) => p.position_slot === "bench");
  const ir       = league.roster.filter((p) => p.position_slot === "ir");
  const general  = league.roster.filter((p) => !["starter","bench","ir"].includes(p.position_slot));
  const allRoster = [...starters, ...general, ...bench, ...ir];

  const startCount = league.roster.filter((p) => p.verdict === "START").length;
  const flexCount  = league.roster.filter((p) => p.verdict === "FLEX").length;
  const sitCount   = league.roster.filter((p) => p.verdict === "SIT").length;

  return (
    <div className="max-w-4xl mx-auto px-6 py-10">
      <Link href="/my-team" className="text-sm text-[#A5ACAF] hover:text-white transition-colors">
        ← My Teams
      </Link>

      <div className="flex items-start justify-between mt-4 mb-6 flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-extrabold text-white">{league.name}</h1>
          <p className="text-sm text-[#A5ACAF] mt-1">
            {FORMAT_LABELS[league.scoring_format]} · {league.num_teams} teams · {league.roster.length} players
          </p>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex gap-3 text-xs font-bold">
            <span className="text-[#22C55E]">{startCount} START</span>
            <span className="text-[#F59E0B]">{flexCount} FLEX</span>
            <span className="text-[#EF4444]">{sitCount} SIT</span>
          </div>
          <Link
            href={`/my-team/setup?edit=${league_id}`}
            className="px-3 py-1.5 bg-[#1F2937] border border-[#374151] hover:border-[#004C54]/60 text-[#A5ACAF] hover:text-white text-xs rounded-lg transition-colors"
          >
            + Add Player
          </Link>
          <button
            onClick={deleteLeague}
            className="text-xs text-[#EF4444]/50 hover:text-[#EF4444] transition-colors"
          >
            Delete
          </button>
        </div>
      </div>

      {league.roster.length === 0 ? (
        <div className="py-16 text-center border border-dashed border-[#374151] rounded-xl">
          <p className="text-[#A5ACAF] mb-4">No players on this roster yet.</p>
          <Link href={`/my-team/setup`} className="px-4 py-2 bg-[#004C54] text-white text-sm font-bold rounded-lg">
            Add Players
          </Link>
        </div>
      ) : (
        <div className="space-y-2">
          {allRoster.map((p) => {
            const vs = VERDICT_STYLES[p.verdict];
            return (
              <div
                key={p.roster_player_id}
                className="flex items-center gap-3 px-4 py-3 bg-[#1F2937]/60 border border-[#374151] hover:border-[#004C54]/30 rounded-xl transition-colors"
              >
                <PlayerHeadshot sleeperId={p.sleeper_id} playerName={p.full_name} position={p.position} size={40} />

                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-white font-semibold">{p.full_name}</span>
                    <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${POS_COLORS[p.position] ?? "bg-[#374151] text-[#9CA3AF]"}`}>
                      {p.position}
                    </span>
                    <span className="text-[#6B7280] text-xs">{p.team}</span>
                    {p.injury_status && (
                      <span className="text-[10px] font-semibold text-[#EF4444] bg-[#EF4444]/10 px-1.5 py-0.5 rounded">
                        {p.injury_status}
                      </span>
                    )}
                    {p.weather_flag && (
                      <span className="text-[10px] text-[#F59E0B] bg-[#F59E0B]/10 px-1.5 py-0.5 rounded">
                        Weather
                      </span>
                    )}
                  </div>
                  {p.reasons[0] && (
                    <p className="text-[11px] text-[#6B7280] mt-0.5 truncate">{p.reasons[0]}</p>
                  )}
                </div>

                <div className="flex items-center gap-4 shrink-0">
                  {p.vegas_implied_total != null && (
                    <div className="text-right hidden sm:block">
                      <div className="text-[10px] text-[#6B7280]">Vegas</div>
                      <div className="text-[#A5ACAF] text-sm font-mono">{p.vegas_implied_total.toFixed(1)}</div>
                    </div>
                  )}
                  <div className="text-right">
                    <div className="text-[10px] text-[#6B7280]">Score</div>
                    <div className="text-white text-sm font-mono">{p.score.toFixed(1)}</div>
                  </div>
                  <div className={`px-3 py-1.5 rounded border font-bold text-sm min-w-[56px] text-center ${vs.bg} ${vs.text}`}>
                    {p.verdict}
                  </div>
                  <button
                    onClick={() => removePlayer(p.roster_player_id)}
                    disabled={removing === p.roster_player_id}
                    className="text-[#EF4444]/40 hover:text-[#EF4444] text-xs disabled:opacity-40 transition-colors"
                  >
                    ✕
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
