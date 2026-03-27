"use client";

import { useEffect, useRef, useState } from "react";
import { FreshnessStamp } from "@/components/FreshnessStamp";

interface RecommendationResponse {
  verdict: "START" | "SIT" | "FLEX";
  score: number;
  reasons: string[];
  low_confidence: boolean;
  scoring_format: string;
  injury_status: string | null;
  practice_participation: string | null;
  snap_pct_l4w: (number | null)[];
  target_share_l4w: (number | null)[];
  carry_share_l4w: (number | null)[];
  updated_at: string;
  full_name: string;
  position: string;
  team: string;
}

type Format = "ppr" | "half_ppr" | "standard";

interface RecommendationCardProps {
  playerId: string;
  initialData: RecommendationResponse;
}

const VERDICT_COLORS: Record<string, string> = {
  START: "text-[#22C55E]",
  SIT: "text-[#EF4444]",
  FLEX: "text-[#F59E0B]",
};

const INJURY_BADGES: Record<string, { text: string; bg: string; label: string }> = {
  "": { text: "text-[#22C55E]", bg: "bg-[#052E16]", label: "Active" },
  "Questionable": { text: "text-[#F59E0B]", bg: "bg-[#1C1400]", label: "Questionable" },
  "Doubtful": { text: "text-[#F87171]", bg: "bg-[#1A0000]", label: "Doubtful" },
  "Out": { text: "text-[#EF4444]", bg: "bg-[#1A0000]", label: "Out" },
};

const FORMAT_LABELS: Record<Format, string> = {
  ppr: "PPR",
  half_ppr: "Half PPR",
  standard: "Standard",
};

function formatSparkRow(values: (number | null)[], asPercent: boolean): string {
  return values
    .map((v) => {
      if (v === null) return "—";
      if (asPercent) return `${Math.round(v * 100)}%`;
      return String(v);
    })
    .join(" · ");
}

function InjuryBadge({ status }: { status: string | null }) {
  const key = status ?? "";
  const badge = INJURY_BADGES[key] ?? INJURY_BADGES[""];
  return (
    <span className={`px-2 py-0.5 rounded text-sm ${badge.text} ${badge.bg}`}>
      {badge.label}
    </span>
  );
}

function SignalRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex justify-between items-center">
      <dt className="text-sm text-[#A5ACAF]">{label}</dt>
      <dd className="text-base text-white">{value}</dd>
    </div>
  );
}

export function RecommendationCard({ playerId, initialData }: RecommendationCardProps) {
  const [format, setFormat] = useState<Format>("ppr");
  const [rec, setRec] = useState<RecommendationResponse>(initialData);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const isFirstRender = useRef<boolean>(true);

  useEffect(() => {
    if (isFirstRender.current) {
      isFirstRender.current = false;
      return;
    }

    setIsLoading(true);
    fetch(`http://localhost:8000/player/${playerId}?format=${format}`)
      .then((res) => {
        if (!res.ok) throw new Error("fetch failed");
        return res.json();
      })
      .then((data: RecommendationResponse) => {
        setRec(data);
        setIsLoading(false);
      })
      .catch(() => {
        setError("Could not load recommendation");
        setIsLoading(false);
      });
  }, [format, playerId]);

  if (isLoading) {
    return (
      <div
        className="bg-[#111827] rounded-xl p-6"
        aria-busy="true"
        aria-label="Loading recommendation..."
      >
        {/* Verdict skeleton */}
        <div className="h-9 w-32 rounded bg-[#1F2937] animate-pulse" />
        {/* Format selector skeleton */}
        <div className="h-8 w-64 rounded bg-[#1F2937] animate-pulse mt-4" />
        {/* Reasoning skeleton */}
        <div className="mt-6 space-y-2">
          <div className="h-4 w-full rounded bg-[#1F2937] animate-pulse" />
          <div className="h-4 w-full rounded bg-[#1F2937] animate-pulse" />
          <div className="h-4 w-full rounded bg-[#1F2937] animate-pulse" />
          <div className="h-4 w-full rounded bg-[#1F2937] animate-pulse" />
        </div>
        {/* Signals skeleton */}
        <div className="mt-6 space-y-3">
          <div className="h-4 w-full rounded bg-[#1F2937] animate-pulse" />
          <div className="h-4 w-full rounded bg-[#1F2937] animate-pulse" />
          <div className="h-4 w-full rounded bg-[#1F2937] animate-pulse" />
          <div className="h-4 w-full rounded bg-[#1F2937] animate-pulse" />
          <div className="h-4 w-full rounded bg-[#1F2937] animate-pulse" />
          <div className="h-4 w-full rounded bg-[#1F2937] animate-pulse" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-[#111827] rounded-xl p-6">
        <div role="alert" className="text-center py-8">
          <h3 className="text-lg font-bold text-white">Could not load recommendation</h3>
          <p className="text-[#A5ACAF] mt-2">
            There was a problem fetching data for this player. Retry loading or search for another player.
          </p>
          <button
            onClick={() => {
              setError(null);
              setFormat(format);
            }}
            className="mt-4 px-4 py-2 bg-[#004C54] text-white rounded"
          >
            Retry Loading
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-[#111827] rounded-xl p-6">
      {/* VERDICT BLOCK */}
      <div className="flex items-baseline justify-between">
        <span
          aria-label={`Recommendation: ${rec.verdict}`}
          className={`text-4xl font-bold ${VERDICT_COLORS[rec.verdict]}`}
        >
          {rec.verdict}
        </span>
        <span className="text-sm text-[#A5ACAF]">Score: {rec.score.toFixed(1)}</span>
      </div>

      {/* Low confidence badge */}
      {rec.low_confidence && (
        <span className="inline-block mt-2 px-3 py-1 text-sm bg-[#A5ACAF]/20 text-[#A5ACAF] rounded">
          Low confidence — limited data
        </span>
      )}

      {/* SCORING FORMAT SELECTOR */}
      <div className="flex gap-2 mt-4">
        {(["ppr", "half_ppr", "standard"] as Format[]).map((f) => (
          <button
            key={f}
            onClick={() => setFormat(f)}
            className={`h-8 px-3 rounded text-sm min-h-[44px] ${
              format === f
                ? "bg-[#004C54] text-white font-bold"
                : "border border-[#A5ACAF] text-[#A5ACAF] hover:bg-[#004C54]/20"
            }`}
          >
            {FORMAT_LABELS[f]}
          </button>
        ))}
      </div>

      {/* REASONING BLOCK */}
      <div className="mt-6">
        <h3 className="text-sm text-[#A5ACAF]">Why</h3>
        <ul className="mt-2 space-y-2">
          {rec.reasons.map((reason, i) => (
            <li key={i} className="text-base text-white flex gap-2">
              <span className="text-[#A5ACAF]">·</span>
              <span>{reason}</span>
            </li>
          ))}
        </ul>
      </div>

      {/* SIGNALS BLOCK */}
      <div className="mt-6">
        <h3 className="text-sm text-[#A5ACAF]">Signals</h3>
        <dl className="mt-2 space-y-3">
          {/* Injury Status */}
          <SignalRow label="Injury Status" value={<InjuryBadge status={rec.injury_status} />} />

          {/* Practice Status */}
          <SignalRow label="Practice Status" value={rec.practice_participation ?? "N/A"} />

          {/* Snap % (L4W) */}
          <SignalRow label="Snap % (L4W)" value={formatSparkRow(rec.snap_pct_l4w, true)} />

          {/* Target Share or Carry Share (L4W) — position-dependent */}
          {rec.position === "RB" ? (
            <SignalRow label="Carry Share (L4W)" value={formatSparkRow(rec.carry_share_l4w, true)} />
          ) : ["WR", "TE"].includes(rec.position) ? (
            <SignalRow label="Target Share (L4W)" value={formatSparkRow(rec.target_share_l4w, true)} />
          ) : null}

          {/* Projected Points */}
          <SignalRow
            label="Projected Points"
            value={rec.score ? `${rec.score.toFixed(1)} pts` : "N/A"}
          />
        </dl>
      </div>

      {/* FRESHNESS STAMP */}
      <FreshnessStamp updatedAt={rec.updated_at} />
    </div>
  );
}
