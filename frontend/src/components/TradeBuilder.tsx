"use client";

import { useState, useEffect, useRef } from "react";
import { PlayerHeadshot } from "@/components/PlayerHeadshot";
import { API_BASE } from "@/lib/api";

interface DynastyItem {
  id: number;
  player_name: string;
  position: string | null;
  team: string | null;
  age: number | null;
  value: number;
  overall_rank: number | null;
  position_rank: number | null;
  trend_30day: number | null;
  is_pick: boolean;
  sleeper_id: string | null;
}

interface TradeAnalysis {
  verdict: "WIN" | "LOSE" | "FAIR";
  side_a_total: number;
  side_b_total: number;
  differential_pct: number;
  reasons: string[];
  side_a_items: DynastyItem[];
  side_b_items: DynastyItem[];
}

const VERDICT_COLORS = {
  WIN:  "text-[#22C55E]",
  LOSE: "text-[#EF4444]",
  FAIR: "text-[#F59E0B]",
};

const VERDICT_BG = {
  WIN:  "bg-[#022c10] border-[#22C55E]/40",
  LOSE: "bg-[#1a0000] border-[#EF4444]/40",
  FAIR: "bg-[#1c1400] border-[#F59E0B]/40",
};

const TREND_COLOR = (v: number | null) =>
  v === null ? "" : v > 0 ? "text-[#22C55E]" : v < 0 ? "text-[#EF4444]" : "text-[#A5ACAF]";

function TrendBadge({ value }: { value: number | null }) {
  if (value === null) return null;
  const sign = value > 0 ? "+" : "";
  return (
    <span className={`text-[10px] font-semibold ${TREND_COLOR(value)}`}>
      {sign}{value}
    </span>
  );
}

function DynastySearchInput({
  placeholder,
  onAdd,
  excluded,
}: {
  placeholder: string;
  onAdd: (item: DynastyItem) => void;
  excluded: number[];
}) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<DynastyItem[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const wrapperRef = useRef<HTMLDivElement>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (timerRef.current) clearTimeout(timerRef.current);
    if (query.length < 2) { setResults([]); setIsOpen(false); return; }
    timerRef.current = setTimeout(() => {
      fetch(`${API_BASE}/dynasty/search?q=${encodeURIComponent(query)}`)
        .then((r) => r.json())
        .then((data: DynastyItem[]) => {
          setResults(data.filter((d) => !excluded.includes(d.id)));
          setIsOpen(true);
        })
        .catch(() => setResults([]));
    }, 300);
    return () => { if (timerRef.current) clearTimeout(timerRef.current); };
  }, [query, excluded]);

  useEffect(() => {
    function handleMouseDown(e: MouseEvent) {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleMouseDown);
    return () => document.removeEventListener("mousedown", handleMouseDown);
  }, []);

  function handleSelect(item: DynastyItem) {
    onAdd(item);
    setQuery("");
    setIsOpen(false);
  }

  return (
    <div ref={wrapperRef} className="relative">
      <input
        type="text"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder={placeholder}
        className="w-full bg-[#0A0A0A] border border-[#1F2937] rounded-lg px-3 py-2 text-sm text-white placeholder-[#A5ACAF] focus:border-[#004C54] focus:outline-none"
      />
      {isOpen && results.length > 0 && (
        <ul className="absolute z-50 w-full mt-1 bg-[#111827] rounded-lg shadow-xl overflow-hidden border border-[#1F2937]">
          {results.map((r) => (
            <li
              key={r.id}
              onClick={() => handleSelect(r)}
              className="px-3 py-2.5 flex items-center gap-2.5 cursor-pointer hover:bg-[#004C54]/20 border-b border-[#1F2937] last:border-0"
            >
              {!r.is_pick && (
                <PlayerHeadshot
                  sleeperId={r.sleeper_id}
                  playerName={r.player_name}
                  position={r.position ?? ""}
                  size={28}
                />
              )}
              {r.is_pick && (
                <div className="w-7 h-7 rounded-full bg-[#004C54]/30 flex items-center justify-center text-[9px] font-bold text-[#A5ACAF] flex-shrink-0">
                  PICK
                </div>
              )}
              <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold text-white truncate">{r.player_name}</p>
                <p className="text-xs text-[#A5ACAF]">
                  {r.is_pick ? "Draft Pick" : `${r.position ?? "?"} · ${r.team ?? "?"}`}
                  {r.overall_rank && ` · #${r.overall_rank}`}
                </p>
              </div>
              <span className="text-xs font-bold text-[#A5ACAF]">{r.value.toLocaleString()}</span>
            </li>
          ))}
        </ul>
      )}
      {isOpen && results.length === 0 && query.length >= 2 && (
        <ul className="absolute z-50 w-full mt-1 bg-[#111827] rounded-lg shadow-xl border border-[#1F2937]">
          <li className="px-3 py-3 text-xs text-[#A5ACAF]">No results — try a name or "2026 Pick"</li>
        </ul>
      )}
    </div>
  );
}

function TradeSide({
  label,
  sublabel,
  items,
  onAdd,
  onRemove,
  excluded,
  total,
  accentClass,
}: {
  label: string;
  sublabel: string;
  items: DynastyItem[];
  onAdd: (item: DynastyItem) => void;
  onRemove: (id: number) => void;
  excluded: number[];
  total: number;
  accentClass: string;
}) {
  return (
    <div className="flex flex-col gap-3">
      <div>
        <h3 className={`text-base font-extrabold ${accentClass}`}>{label}</h3>
        <p className="text-xs text-[#A5ACAF]">{sublabel}</p>
      </div>

      <DynastySearchInput
        placeholder="Search players or picks..."
        onAdd={onAdd}
        excluded={excluded}
      />

      {/* Item list */}
      <div className="space-y-2 min-h-[80px]">
        {items.length === 0 && (
          <p className="text-xs text-[#A5ACAF]/50 py-4 text-center">No players added yet</p>
        )}
        {items.map((item) => (
          <div
            key={item.id}
            className="flex items-center gap-2.5 bg-[#0A0A0A] rounded-lg px-3 py-2 border border-[#1F2937]"
          >
            {!item.is_pick ? (
              <PlayerHeadshot
                sleeperId={item.sleeper_id}
                playerName={item.player_name}
                position={item.position ?? ""}
                size={32}
              />
            ) : (
              <div className="w-8 h-8 rounded-full bg-[#004C54]/30 flex items-center justify-center text-[9px] font-bold text-[#A5ACAF] flex-shrink-0">
                PICK
              </div>
            )}
            <div className="flex-1 min-w-0">
              <p className="text-sm font-semibold text-white truncate leading-tight">{item.player_name}</p>
              <div className="flex items-center gap-1.5">
                <p className="text-xs text-[#A5ACAF]">
                  {item.is_pick ? "Pick" : `${item.position ?? "?"} · ${item.team ?? "?"}`}
                </p>
                <TrendBadge value={item.trend_30day} />
              </div>
            </div>
            <div className="text-right flex-shrink-0">
              <p className="text-sm font-bold text-white">{item.value.toLocaleString()}</p>
              {item.overall_rank && (
                <p className="text-[10px] text-[#A5ACAF]">#{item.overall_rank}</p>
              )}
            </div>
            <button
              onClick={() => onRemove(item.id)}
              className="ml-1 text-[#A5ACAF] hover:text-[#EF4444] transition-colors text-lg leading-none flex-shrink-0"
              aria-label="Remove"
            >
              ×
            </button>
          </div>
        ))}
      </div>

      {/* Side total */}
      {items.length > 0 && (
        <div className="flex justify-between items-center pt-1 border-t border-[#1F2937]">
          <span className="text-xs text-[#A5ACAF]">Total value</span>
          <span className="text-sm font-extrabold text-white">{total.toLocaleString()} pts</span>
        </div>
      )}
    </div>
  );
}

function ValueBar({ totalA, totalB }: { totalA: number; totalB: number }) {
  const total = totalA + totalB;
  if (total === 0) return null;
  const pctA = (totalA / total) * 100;
  return (
    <div className="mt-4">
      <div className="flex justify-between text-xs text-[#A5ACAF] mb-1">
        <span>You receive</span>
        <span>You give</span>
      </div>
      <div className="h-2 rounded-full bg-[#1F2937] overflow-hidden flex">
        <div
          className="h-full bg-[#004C54] rounded-l-full transition-all duration-500"
          style={{ width: `${pctA}%` }}
        />
        <div
          className="h-full bg-[#374151] rounded-r-full transition-all duration-500"
          style={{ width: `${100 - pctA}%` }}
        />
      </div>
      <div className="flex justify-between text-xs font-bold mt-1">
        <span className="text-white">{totalA.toLocaleString()}</span>
        <span className="text-white">{totalB.toLocaleString()}</span>
      </div>
    </div>
  );
}

export function TradeBuilder() {
  const [sideA, setSideA] = useState<DynastyItem[]>([]);
  const [sideB, setSideB] = useState<DynastyItem[]>([]);
  const [analysis, setAnalysis] = useState<TradeAnalysis | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const totalA = sideA.reduce((s, i) => s + i.value, 0);
  const totalB = sideB.reduce((s, i) => s + i.value, 0);
  const allIds = [...sideA, ...sideB].map((i) => i.id);

  function addToSide(side: "a" | "b", item: DynastyItem) {
    if (side === "a") setSideA((prev) => [...prev, item]);
    else setSideB((prev) => [...prev, item]);
    setAnalysis(null);
  }

  function removeFromSide(side: "a" | "b", id: number) {
    if (side === "a") setSideA((prev) => prev.filter((i) => i.id !== id));
    else setSideB((prev) => prev.filter((i) => i.id !== id));
    setAnalysis(null);
  }

  async function runAnalysis() {
    if (sideA.length === 0 || sideB.length === 0) {
      setError("Add at least one player or pick to each side.");
      return;
    }
    setIsLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/dynasty/trade`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ side_a: sideA.map((i) => i.id), side_b: sideB.map((i) => i.id) }),
      });
      if (!res.ok) throw new Error("Analysis failed");
      setAnalysis(await res.json());
    } catch {
      setError("Could not analyze trade. Check backend is running.");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      {/* Trade sides */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-[#111827] rounded-2xl p-5 border border-[#1F2937]">
          <TradeSide
            label="You Receive"
            sublabel="Players and picks coming to you"
            items={sideA}
            onAdd={(item) => addToSide("a", item)}
            onRemove={(id) => removeFromSide("a", id)}
            excluded={allIds}
            total={totalA}
            accentClass="text-[#22C55E]"
          />
        </div>
        <div className="bg-[#111827] rounded-2xl p-5 border border-[#1F2937]">
          <TradeSide
            label="You Give"
            sublabel="Players and picks leaving your roster"
            items={sideB}
            onAdd={(item) => addToSide("b", item)}
            onRemove={(id) => removeFromSide("b", id)}
            excluded={allIds}
            total={totalB}
            accentClass="text-[#EF4444]"
          />
        </div>
      </div>

      {/* Value bar */}
      {(sideA.length > 0 || sideB.length > 0) && (
        <ValueBar totalA={totalA} totalB={totalB} />
      )}

      {/* Analyze button */}
      <button
        onClick={runAnalysis}
        disabled={isLoading || sideA.length === 0 || sideB.length === 0}
        className="w-full py-3 rounded-xl font-extrabold text-white bg-[#004C54] hover:bg-[#005f6b] disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
      >
        {isLoading ? "Analyzing..." : "Analyze Trade"}
      </button>

      {error && (
        <p role="alert" className="text-sm text-[#EF4444] text-center">{error}</p>
      )}

      {/* Verdict */}
      {analysis && (
        <div className={`rounded-2xl p-6 border ${VERDICT_BG[analysis.verdict]}`}>
          <div className="flex items-center justify-between mb-4">
            <span className={`text-4xl font-extrabold tracking-wide ${VERDICT_COLORS[analysis.verdict]}`}>
              {analysis.verdict}
            </span>
            <span className="text-sm text-[#A5ACAF]">
              {Math.abs(analysis.differential_pct).toFixed(1)}% {analysis.verdict === "FAIR" ? "gap" : analysis.verdict === "WIN" ? "in your favor" : "against you"}
            </span>
          </div>
          <ul className="space-y-2">
            {analysis.reasons.map((r, i) => (
              <li key={i} className="flex gap-2 text-sm text-white">
                <span className="text-[#A5ACAF] flex-shrink-0">·</span>
                <span>{r}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
