import Link from "next/link";
import { RecommendationCard } from "@/components/RecommendationCard";
import { API_BASE } from "@/lib/api";

type PlayerPageProps = {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ format?: string }>;
};

// Show off-season notice when the NFL regular season is not active (March–August)
function isOffSeason(): boolean {
  const month = new Date().getMonth() + 1; // 1-12
  return month >= 3 && month <= 8;
}

export default async function PlayerPage({ params }: PlayerPageProps) {
  const { id } = await params;

  let data = null;
  let error = null;
  try {
    const res = await fetch(`${API_BASE}/player/${id}?format=ppr`, {
      cache: "no-store",
    });
    if (!res.ok) {
      error = res.status === 404 ? "Player not found" : "Could not load recommendation";
    } else {
      data = await res.json();
    }
  } catch {
    error = "Could not load recommendation";
  }

  if (error) {
    return (
      <div className="max-w-2xl mx-auto px-6 py-12">
        <div role="alert" className="bg-[#111827] rounded-xl p-6 text-center">
          <h2 className="text-xl font-bold text-white">Could not load recommendation</h2>
          <p className="text-[#A5ACAF] mt-2">
            There was a problem fetching data for this player.
          </p>
          <Link href="/" className="mt-4 inline-block px-4 py-2 bg-[#004C54] text-white rounded">
            ← Back to search
          </Link>
        </div>
      </div>
    );
  }

  const offSeason = isOffSeason();

  return (
    <div className="max-w-2xl mx-auto px-6 py-6">
      {/* Back link */}
      <Link href="/" className="text-sm text-[#A5ACAF] hover:text-white transition-colors">
        ← Back to search
      </Link>

      {/* Off-season banner */}
      {offSeason && (
        <div className="mt-4 px-4 py-3 rounded-lg bg-[#1C1400] border border-[#F59E0B]/40 text-sm text-[#F59E0B]">
          <span className="font-semibold">Off-season mode</span> — showing 2025 regular-season stats (weeks 15–18). Live verdicts resume when the 2026 season kicks off.
        </div>
      )}

      {/* Player header */}
      <div className="mt-5 flex items-center gap-4">
        {/* Position badge */}
        <div className="flex-shrink-0 w-12 h-12 rounded-full bg-[#004C54]/30 border border-[#004C54] flex items-center justify-center text-sm font-bold text-[#A5ACAF]">
          {data.position}
        </div>
        <div>
          <h1 className="text-2xl font-extrabold text-white leading-tight">{data.full_name}</h1>
          <p className="text-sm text-[#A5ACAF]">{data.position} · {data.team}</p>
        </div>
      </div>

      {/* Recommendation card */}
      <div className="mt-6">
        <RecommendationCard playerId={id} initialData={data} />
      </div>
    </div>
  );
}
