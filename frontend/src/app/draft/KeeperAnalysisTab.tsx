"use client";

import { useState, useEffect, useRef } from "react";
import { API_BASE } from "@/lib/api";
import { PlayerHeadshot } from "@/components/PlayerHeadshot";

interface KeeperEntry {
  id: number;
  player_name: string;
  dynasty_value_id: number | null;
  keeper_round: number;
  notes: string | null;
  dynasty_value: number | null;
  dynasty_rank: number | null;
  keeper_cost_value: number;
  net_gain: number | null;
  recommendation: "KEEP" | "BORDERLINE" | "CUT" | null;
  position: string | null;
  age: number | null;
  sleeper_id: string | null;
  age_grade: string;
}

interface DynastyItem {
  id: number;
  player_name: string;
  position: string | null;
  team: string | null;
}

const REC_STYLES: Record<string, string> = {
  KEEP:       "bg-[#022c10] border border-[#22C55E]/40 text-[#22C55E]",
  BORDERLINE: "bg-[#1c1400] border border-[#F59E0B]/40 text-[#F59E0B]",
  CUT:        "bg-[#1a0000] border border-[#EF4444]/40 text-[#EF4444]",
};

const ROUND_LABELS: Record<number, string> = {
  1: "1st", 2: "2nd", 3: "3rd", 4: "4th", 5: "5th",
  6: "6th", 7: "7th", 8: "8th", 9: "9th", 10: "10th",
};
const roundLabel = (r: number) => ROUND_LABELS[r] ?? `${r}th`;

function AddKeeperModal({ onClose, onAdded }: { onClose: () => void; onAdded: () => void }) {
  const [query, setQuery] = useState("");
  const [suggestions, setSuggestions] = useState<DynastyItem[]>([]);
  const [selected, setSelected] = useState<DynastyItem | null>(null);
  const [keeperRound, setKeeperRound] = useState(3);
  const [notes, setNotes] = useState("");
  const [saving, setSaving] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => { inputRef.current?.focus(); }, []);

  useEffect(() => {
    if (query.length < 2 || selected) { setSuggestions([]); return; }
    fetch(`${API_BASE}/dynasty/search?q=${encodeURIComponent(query)}`)
      .then((r) => r.json())
      .then(setSuggestions)
      .catch(() => setSuggestions([]));
  }, [query, selected]);

  const handleSelect = (item: DynastyItem) => {
    setSelected(item);
    setQuery(item.player_name);
    setSuggestions([]);
  };

  const handleSave = async () => {
    if (!selected) return;
    setSaving(true);
    await fetch(`${API_BASE}/dynasty/keepers`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        player_name: selected.player_name,
        dynasty_value_id: selected.id,
        keeper_round: keeperRound,
        notes: notes || null,
      }),
    });
    setSaving(false);
    onAdded();
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={onClose}>
      <div
        className="bg-[#111827] border border-[#1F2937] rounded-xl p-6 w-full max-w-md shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="text-white font-bold text-lg mb-4">Add Keeper</h2>

        {/* Player search */}
        <div className="relative mb-4">
          <label className="text-xs text-[#6B7280] mb-1 block">Player name</label>
          <input
            ref={inputRef}
            value={query}
            onChange={(e) => { setQuery(e.target.value); setSelected(null); }}
            placeholder="Search dynasty values…"
            className="w-full bg-[#1F2937] text-white rounded px-3 py-2 text-sm outline-none border border-[#374151] focus:border-[#004C54]"
          />
          {suggestions.length > 0 && (
            <ul className="absolute z-10 mt-1 w-full bg-[#1F2937] border border-[#374151] rounded-lg shadow-xl max-h-48 overflow-y-auto">
              {suggestions.map((s) => (
                <li
                  key={s.id}
                  onClick={() => handleSelect(s)}
                  className="px-3 py-2 text-sm text-white hover:bg-[#374151] cursor-pointer flex justify-between"
                >
                  <span>{s.player_name}</span>
                  <span className="text-[#6B7280] text-xs">{s.position} · {s.team}</span>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Keeper round */}
        <div className="mb-4">
          <label className="text-xs text-[#6B7280] mb-1 block">Keeper round (cost)</label>
          <div className="flex gap-1 flex-wrap">
            {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map((r) => (
              <button
                key={r}
                onClick={() => setKeeperRound(r)}
                className={`px-2 py-1 rounded text-xs font-medium transition-colors
                  ${keeperRound === r ? "bg-[#004C54] text-white" : "bg-[#374151] text-[#A5ACAF] hover:text-white"}`}
              >
                R{r}
              </button>
            ))}
          </div>
        </div>

        {/* Notes */}
        <div className="mb-5">
          <label className="text-xs text-[#6B7280] mb-1 block">Notes (optional)</label>
          <input
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="e.g. league penalty round"
            className="w-full bg-[#1F2937] text-white rounded px-3 py-2 text-sm outline-none border border-[#374151] focus:border-[#004C54]"
          />
        </div>

        <div className="flex gap-3">
          <button
            onClick={handleSave}
            disabled={!selected || saving}
            className="flex-1 bg-[#004C54] hover:bg-[#005f6a] disabled:opacity-40 text-white py-2 rounded text-sm font-semibold transition-colors"
          >
            {saving ? "Saving…" : "Save Keeper"}
          </button>
          <button onClick={onClose} className="px-4 py-2 text-sm text-[#A5ACAF] hover:text-white transition-colors">
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}

export function KeeperAnalysisTab() {
  const [keepers, setKeepers] = useState<KeeperEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);

  const load = () => {
    setLoading(true);
    fetch(`${API_BASE}/dynasty/keepers`)
      .then((r) => r.json())
      .then((data) => { setKeepers(data); setLoading(false); })
      .catch(() => setLoading(false));
  };

  useEffect(load, []);

  const handleDelete = async (id: number) => {
    await fetch(`${API_BASE}/dynasty/keepers/${id}`, { method: "DELETE" });
    load();
  };

  return (
    <div>
      {showModal && <AddKeeperModal onClose={() => setShowModal(false)} onAdded={load} />}

      <div className="flex justify-between items-center mb-5">
        <p className="text-xs text-[#6B7280]">
          Compare each player&apos;s keeper cost (draft pick value) against their dynasty value to get a KEEP / CUT verdict.
        </p>
        <button
          onClick={() => setShowModal(true)}
          className="bg-[#004C54] hover:bg-[#005f6a] text-white px-4 py-2 rounded text-sm font-semibold transition-colors shrink-0 ml-4"
        >
          + Add Keeper
        </button>
      </div>

      {loading ? (
        <div className="text-[#A5ACAF] text-sm py-12 text-center">Loading keepers…</div>
      ) : keepers.length === 0 ? (
        <div className="py-12 text-center">
          <p className="text-[#A5ACAF] text-sm mb-3">No keepers added yet.</p>
          <button onClick={() => setShowModal(true)} className="text-[#004C54] hover:text-[#00a0b0] text-sm transition-colors">
            Add your first keeper →
          </button>
        </div>
      ) : (
        <div className="grid gap-3">
          {keepers.map((k) => (
            <div
              key={k.id}
              className="bg-[#1F2937]/60 border border-[#1F2937] rounded-lg px-4 py-3 hover:border-[#004C54]/40 transition-colors"
            >
              <div className="flex items-center gap-4">
                {/* Headshot */}
                {k.sleeper_id && (
                  <PlayerHeadshot sleeperId={k.sleeper_id} playerName={k.player_name} position={k.position ?? "—"} size={40} />
                )}

                {/* Player info */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-white font-semibold">{k.player_name}</span>
                    {k.position && (
                      <span className="text-[10px] text-[#6B7280] bg-[#374151] px-1.5 py-0.5 rounded">{k.position}</span>
                    )}
                    {k.age && (
                      <span className="text-[10px] text-[#6B7280]">{k.age.toFixed(1)}y · Age Grade {k.age_grade}</span>
                    )}
                  </div>
                  {k.notes && <div className="text-xs text-[#6B7280] mt-0.5">{k.notes}</div>}
                </div>

                {/* Value comparison */}
                <div className="flex items-center gap-6 shrink-0 text-right">
                  <div>
                    <div className="text-[10px] text-[#6B7280] mb-0.5">Dynasty Value</div>
                    <div className="text-white font-mono text-sm">
                      {k.dynasty_value != null ? k.dynasty_value.toLocaleString() : "—"}
                    </div>
                    {k.dynasty_rank && <div className="text-[10px] text-[#6B7280]">#{k.dynasty_rank}</div>}
                  </div>

                  <div>
                    <div className="text-[10px] text-[#6B7280] mb-0.5">Keeper Cost</div>
                    <div className="text-[#A5ACAF] font-mono text-sm">{k.keeper_cost_value.toLocaleString()}</div>
                    <div className="text-[10px] text-[#6B7280]">Round {roundLabel(k.keeper_round)}</div>
                  </div>

                  <div>
                    <div className="text-[10px] text-[#6B7280] mb-0.5">Net Gain</div>
                    <div className={`font-mono text-sm font-bold ${
                      k.net_gain == null ? "text-[#6B7280]"
                      : k.net_gain >= 0 ? "text-[#22C55E]"
                      : "text-[#EF4444]"
                    }`}>
                      {k.net_gain != null ? (k.net_gain >= 0 ? "+" : "") + k.net_gain.toLocaleString() : "—"}
                    </div>
                  </div>

                  {/* Verdict badge */}
                  {k.recommendation && (
                    <div className={`px-3 py-1 rounded font-bold text-xs ${REC_STYLES[k.recommendation]}`}>
                      {k.recommendation}
                    </div>
                  )}
                </div>

                {/* Delete */}
                <button
                  onClick={() => handleDelete(k.id)}
                  className="text-[#4B5563] hover:text-[#EF4444] transition-colors text-sm ml-2"
                  title="Remove keeper"
                >
                  ✕
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Legend */}
      {keepers.length > 0 && (
        <div className="mt-6 pt-4 border-t border-[#1F2937] flex gap-6 text-xs text-[#6B7280]">
          <div><span className="text-[#22C55E] font-bold">KEEP</span> — dynasty value exceeds keeper cost by ≥1,000 pts</div>
          <div><span className="text-[#F59E0B] font-bold">BORDERLINE</span> — within 1,000 pts either way</div>
          <div><span className="text-[#EF4444] font-bold">CUT</span> — keeper cost exceeds dynasty value by &gt;500 pts</div>
        </div>
      )}
    </div>
  );
}
