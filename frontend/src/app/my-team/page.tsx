"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@clerk/nextjs";
import { API_BASE, authedFetch } from "@/lib/api";

interface League {
  id: number;
  name: string;
  scoring_format: string;
  num_teams: number;
  roster_count: number;
  created_at: string;
}

const FORMAT_LABELS: Record<string, string> = {
  ppr: "Full PPR",
  half_ppr: "Half PPR",
  standard: "Standard",
};

export default function MyTeamPage() {
  const { getToken, isLoaded, isSignedIn } = useAuth();
  const router = useRouter();
  const [leagues, setLeagues] = useState<League[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!isLoaded) return;
    if (!isSignedIn) { router.push("/"); return; }
    authedFetch(`${API_BASE}/leagues`, getToken)
      .then((r) => r.json())
      .then((data) => { setLeagues(data); setLoading(false); })
      .catch(() => setLoading(false));
  }, [isLoaded, isSignedIn, getToken, router]);

  if (!isLoaded || loading) {
    return (
      <div className="max-w-3xl mx-auto px-6 py-10">
        <div className="space-y-3">
          {[1, 2].map((i) => (
            <div key={i} className="h-24 rounded-xl bg-[#1F2937] animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto px-6 py-10">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-extrabold text-white">My Teams</h1>
          <p className="text-sm text-[#A5ACAF] mt-1">
            Your custom rosters with personalized START/SIT recommendations.
          </p>
        </div>
        <Link
          href="/my-team/setup"
          className="px-4 py-2 bg-[#004C54] hover:bg-[#005f6a] text-white text-sm font-bold rounded-lg transition-colors"
        >
          + New League
        </Link>
      </div>

      {leagues.length === 0 ? (
        <div className="text-center py-20 border border-dashed border-[#374151] rounded-xl">
          <p className="text-[#A5ACAF] text-base mb-2">No leagues yet.</p>
          <p className="text-[#6B7280] text-sm mb-6">
            Add your roster to get personalized start/sit advice for your actual players.
          </p>
          <Link
            href="/my-team/setup"
            className="px-5 py-2.5 bg-[#004C54] hover:bg-[#005f6a] text-white text-sm font-bold rounded-lg transition-colors"
          >
            Set Up Your First League
          </Link>
        </div>
      ) : (
        <div className="space-y-3">
          {leagues.map((league) => (
            <Link
              key={league.id}
              href={`/my-team/${league.id}`}
              className="block bg-[#1F2937]/60 border border-[#374151] hover:border-[#004C54]/60 rounded-xl px-5 py-4 transition-colors"
            >
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-white font-bold text-base">{league.name}</div>
                  <div className="text-[#A5ACAF] text-sm mt-0.5">
                    {FORMAT_LABELS[league.scoring_format] ?? league.scoring_format}
                    {" · "}
                    {league.num_teams} teams
                    {" · "}
                    {league.roster_count} players
                  </div>
                </div>
                <span className="text-[#004C54] font-semibold text-sm">View →</span>
              </div>
            </Link>
          ))}
          <Link
            href="/my-team/setup"
            className="block text-center py-3 border border-dashed border-[#374151] hover:border-[#004C54]/40 rounded-xl text-sm text-[#6B7280] hover:text-[#A5ACAF] transition-colors"
          >
            + Add another league
          </Link>
        </div>
      )}
    </div>
  );
}
