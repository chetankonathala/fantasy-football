"use client";

import { useState, useEffect, useRef } from "react";
import { FreshnessStamp } from "@/components/FreshnessStamp";
import { PlayerHeadshot } from "@/components/PlayerHeadshot";
import { API_BASE } from "@/lib/api";

interface PlayerResult {
  id: number;
  full_name: string;
  position: string;
  team: string;
}

interface PlayerRec {
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
  sleeper_id: string | null;
  vegas_implied_total: number | null;
  game_total: number | null;
  weather_flag: boolean;
  wind_mph: number | null;
  precip_probability: number | null;
  is_dome: boolean | null;
}

interface CompareResponse {
  player_a: PlayerRec;
  player_b: PlayerRec;
}

type Format = "ppr" | "half_ppr" | "standard";

const VERDICT_COLORS: Record<string, string> = {
  START: "text-[#22C55E]",
  SIT: "text-[#EF4444]",
  FLEX: "text-[#F59E0B]",
};

const INJURY_BADGES: Record<string, { text: string; bg: string; label: string }> = {
  "": { text: "text-[#22C55E]", bg: "bg-[#052E16]", label: "Active" },
  Questionable: { text: "text-[#F59E0B]", bg: "bg-[#1C1400]", label: "Questionable" },
  Doubtful: { text: "text-[#F87171]", bg: "bg-[#1A0000]", label: "Doubtful" },
  Out: { text: "text-[#EF4444]", bg: "bg-[#1A0000]", label: "Out" },
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

function PlayerSearchInput({
  placeholder,
  onSelect,
}: {
  placeholder: string;
  onSelect: (player: PlayerResult) => void;
}) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<PlayerResult[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const [selectedName, setSelectedName] = useState("");
  const wrapperRef = useRef<HTMLDivElement>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (timerRef.current) clearTimeout(timerRef.current);
    if (query.length < 2) {
      setResults([]);
      setIsOpen(false);
      return;
    }
    timerRef.current = setTimeout(() => {
      fetch(`${API_BASE}/search?q=${encodeURIComponent(query)}`)
        .then((r) => r.json())
        .then((data: PlayerResult[]) => {
          setResults(data);
          setIsOpen(true);
        })
        .catch(() => {
          setResults([]);
        });
    }, 300);
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [query]);

  useEffect(() => {
    function handleMouseDown(e: MouseEvent) {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleMouseDown);
    return () => document.removeEventListener("mousedown", handleMouseDown);
  }, []);

  function handleSelect(player: PlayerResult) {
    setSelectedName(`${player.full_name} (${player.position}, ${player.team})`);
    setQuery("");
    setIsOpen(false);
    onSelect(player);
  }

  return (
    <div ref={wrapperRef} className="relative">
      <input
        type="text"
        value={selectedName || query}
        onChange={(e) => {
          setSelectedName("");
          setQuery(e.target.value);
        }}
        onFocus={() => {
          if (selectedName) {
            setSelectedName("");
          }
        }}
        placeholder={placeholder}
        className="w-full bg-[#111827] border border-[#A5ACAF] rounded-md px-4 py-2 text-sm text-white placeholder-[#A5ACAF] focus:border-[#004C54] focus:border-2 focus:outline-none"
      />
      {isOpen && results.length > 0 && (
        <ul className="absolute z-50 w-full mt-1 bg-[#111827] rounded-md shadow-lg overflow-hidden">
          {results.map((r) => (
            <li
              key={r.id}
              onClick={() => handleSelect(r)}
              className="px-4 min-h-[44px] flex items-center cursor-pointer text-white hover:bg-[#004C54]/30"
            >
              {r.full_name}
              <span className="text-[#A5ACAF] ml-2">
                — {r.position}, {r.team}
              </span>
            </li>
          ))}
        </ul>
      )}
      {isOpen && results.length === 0 && query.length >= 2 && (
        <ul className="absolute z-50 w-full mt-1 bg-[#111827] rounded-md shadow-lg overflow-hidden">
          <li className="px-4 py-3 text-[#A5ACAF] text-sm">No players found</li>
        </ul>
      )}
    </div>
  );
}

function PlayerColumn({ rec }: { rec: PlayerRec }) {
  return (
    <div className="bg-[#111827] rounded-xl p-5">
      {/* Header */}
      <div className="flex items-center gap-3 mb-4">
        <PlayerHeadshot
          sleeperId={rec.sleeper_id}
          playerName={rec.full_name}
          position={rec.position}
          size={48}
        />
        <div>
          <h2 className="text-lg font-extrabold text-white">{rec.full_name}</h2>
          <p className="text-sm text-[#A5ACAF]">
            {rec.position} · {rec.team}
          </p>
        </div>
      </div>

      {/* Verdict */}
      <div className="flex items-baseline justify-between mb-3">
        <span className={`text-3xl font-bold ${VERDICT_COLORS[rec.verdict]}`}>
          {rec.verdict}
        </span>
        <span className="text-sm text-[#A5ACAF]">Score: {rec.score.toFixed(1)}</span>
      </div>

      {/* Low confidence */}
      {rec.low_confidence && (
        <span className="inline-block mb-3 px-3 py-1 text-sm bg-[#A5ACAF]/20 text-[#A5ACAF] rounded">
          Low confidence — limited data
        </span>
      )}

      {/* Injury badge */}
      <div className="mb-3">
        <InjuryBadge status={rec.injury_status} />
      </div>

      {/* Weather flag */}
      {rec.weather_flag && (
        <div className="flex items-center gap-2 px-3 py-2 rounded bg-[#1C1400] border border-[#F59E0B]/40 mb-3">
          <span className="text-[#F59E0B] text-sm font-semibold">Weather Alert</span>
          <span className="text-[#A5ACAF] text-sm">
            {rec.wind_mph !== null && rec.wind_mph > 15 && `Wind ${Math.round(rec.wind_mph)} mph`}
            {rec.wind_mph !== null && rec.wind_mph > 15 && rec.precip_probability !== null && rec.precip_probability > 30 && " · "}
            {rec.precip_probability !== null && rec.precip_probability > 30 && `${rec.precip_probability}% precip`}
          </span>
        </div>
      )}

      {/* Reasons */}
      <div className="mb-4">
        <h3 className="text-sm text-[#A5ACAF] mb-2">Why</h3>
        <ul className="space-y-1">
          {rec.reasons.map((reason, i) => (
            <li key={i} className="text-sm text-white flex gap-2">
              <span className="text-[#A5ACAF]">·</span>
              <span>{reason}</span>
            </li>
          ))}
        </ul>
      </div>

      {/* Signals */}
      <div>
        <h3 className="text-sm text-[#A5ACAF] mb-2">Signals</h3>
        <dl className="space-y-2">
          <SignalRow label="Snap % (L4W)" value={formatSparkRow(rec.snap_pct_l4w, true)} />
          {rec.position === "RB" ? (
            <SignalRow label="Carry Share (L4W)" value={formatSparkRow(rec.carry_share_l4w, true)} />
          ) : ["WR", "TE"].includes(rec.position) ? (
            <SignalRow label="Target Share (L4W)" value={formatSparkRow(rec.target_share_l4w, true)} />
          ) : null}
          {rec.vegas_implied_total != null && (
            <SignalRow
              label="Implied Team Total"
              value={
                <span>
                  {rec.vegas_implied_total.toFixed(1)} pts
                  {rec.game_total != null && (
                    <span className="text-[#A5ACAF] text-sm ml-2">
                      (O/U {rec.game_total.toFixed(1)})
                    </span>
                  )}
                </span>
              }
            />
          )}
        </dl>
      </div>

      {/* Freshness */}
      <FreshnessStamp updatedAt={rec.updated_at} />
    </div>
  );
}

function SkeletonColumn() {
  return (
    <div className="bg-[#111827] rounded-xl p-5" aria-busy="true">
      <div className="h-5 w-40 rounded bg-[#1F2937] animate-pulse mb-2" />
      <div className="h-4 w-24 rounded bg-[#1F2937] animate-pulse mb-4" />
      <div className="h-8 w-20 rounded bg-[#1F2937] animate-pulse mb-3" />
      <div className="space-y-2 mt-4">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="h-4 w-full rounded bg-[#1F2937] animate-pulse" />
        ))}
      </div>
    </div>
  );
}

function PlaceholderColumn({ label }: { label: string }) {
  return (
    <div className="bg-[#111827] rounded-xl p-5 flex items-center justify-center min-h-[200px]">
      <p className="text-[#A5ACAF] text-sm">{label}</p>
    </div>
  );
}

export function CompareView() {
  const [playerA, setPlayerA] = useState<number | null>(null);
  const [playerB, setPlayerB] = useState<number | null>(null);
  const [format, setFormat] = useState<Format>("ppr");
  const [compareData, setCompareData] = useState<CompareResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (playerA === null || playerB === null) {
      setCompareData(null);
      return;
    }
    setIsLoading(true);
    setError(null);
    fetch(`${API_BASE}/compare?a=${playerA}&b=${playerB}&format=${format}`)
      .then((res) => {
        if (!res.ok) throw new Error("fetch failed");
        return res.json();
      })
      .then((data: CompareResponse) => {
        setCompareData(data);
        setIsLoading(false);
      })
      .catch(() => {
        setError("Could not load comparison. Check that the backend is running.");
        setIsLoading(false);
      });
  }, [playerA, playerB, format]);

  return (
    <div>
      {/* Player search inputs */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
        <PlayerSearchInput
          placeholder="Search Player A..."
          onSelect={(p) => setPlayerA(p.id)}
        />
        <PlayerSearchInput
          placeholder="Search Player B..."
          onSelect={(p) => setPlayerB(p.id)}
        />
      </div>

      {/* Scoring format selector */}
      <div className="flex gap-2 mb-6">
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

      {/* Error state */}
      {error && (
        <div role="alert" className="text-center py-6 text-[#EF4444]">
          {error}
        </div>
      )}

      {/* Comparison grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {isLoading ? (
          <>
            <SkeletonColumn />
            <SkeletonColumn />
          </>
        ) : compareData ? (
          <>
            <PlayerColumn rec={compareData.player_a} />
            <PlayerColumn rec={compareData.player_b} />
          </>
        ) : (
          <>
            <PlaceholderColumn label="Select Player A" />
            <PlaceholderColumn label="Select Player B" />
          </>
        )}
      </div>
    </div>
  );
}
