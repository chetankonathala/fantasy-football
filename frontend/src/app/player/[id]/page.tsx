import { RecommendationCard } from "@/components/RecommendationCard";

// TypeScript type for Next.js 16 page props
type PlayerPageProps = {
  params: Promise<{ id: string }>;
};

export default async function PlayerPage({ params }: PlayerPageProps) {
  const { id } = await params; // MUST await — sync access removed in Next.js 16

  // Server-side fetch for initial data (PPR default)
  let data = null;
  let error = null;
  try {
    const res = await fetch(`http://localhost:8000/player/${id}?format=ppr`, {
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
      <div className="max-w-2xl mx-auto px-8 py-12">
        <div role="alert" className="bg-[#111827] rounded-xl p-6 text-center">
          <h2 className="text-xl font-bold text-white">Could not load recommendation</h2>
          <p className="text-[#A5ACAF] mt-2">
            There was a problem fetching data for this player. Retry loading or search for another player.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto px-8 py-6">
      {/* Player header */}
      <h1 className="text-xl font-bold text-white">{data.full_name}</h1>
      <p className="text-sm text-[#A5ACAF]">{data.position} · {data.team}</p>

      {/* Recommendation card with 24px top gap */}
      <div className="mt-6">
        <RecommendationCard playerId={id} initialData={data} />
      </div>
    </div>
  );
}
