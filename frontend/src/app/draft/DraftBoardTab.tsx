"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { API_BASE } from "@/lib/api";
import { PlayerHeadshot } from "@/components/PlayerHeadshot";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface DynastyPlayer {
  id: number;
  player_name: string;
  position: string | null;
  team: string | null;
  age: number | null;
  value: number;
  overall_rank: number | null;
  position_rank: number | null;
  sleeper_id: string | null;
  age_grade: string;
  position_tier: string;
}

interface PickSlot {
  pick: number;
  round: number;
  pick_in_round: number;
  team_slot: number;
}

interface DraftSessionState {
  id: string;
  num_teams: number;
  num_rounds: number;
  user_team_slot: number;
  total_picks: number;
  current_pick: number;
  drafted_players: DynastyPlayer[];
  queued_players: DynastyPlayer[];
  pick_order: PickSlot[];
  user_picks: PickSlot[];
  created_at: string;
}

interface SessionSummary {
  id: string;
  num_teams: number;
  num_rounds: number;
  user_team_slot: number;
  picks_made: number;
  created_at: string;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const POS_COLORS: Record<string, string> = {
  QB: "bg-[#7C3AED]/20 text-[#A78BFA]",
  RB: "bg-[#059669]/20 text-[#34D399]",
  WR: "bg-[#2563EB]/20 text-[#60A5FA]",
  TE: "bg-[#D97706]/20 text-[#FBBF24]",
};

const POSITIONS = ["ALL", "QB", "RB", "WR", "TE"];

// ---------------------------------------------------------------------------
// Setup screen — create or resume a draft session
// ---------------------------------------------------------------------------

function SetupScreen({ onStart }: { onStart: (session: DraftSessionState) => void }) {
  const [numTeams, setNumTeams] = useState(12);
  const [numRounds, setNumRounds] = useState(15);
  const [userSlot, setUserSlot] = useState(6);
  const [creating, setCreating] = useState(false);
  const [sessions, setSessions] = useState<SessionSummary[]>([]);

  useEffect(() => {
    fetch(`${API_BASE}/draft/sessions`)
      .then((r) => r.json())
      .then(setSessions)
      .catch(() => {});
  }, []);

  const handleCreate = async () => {
    setCreating(true);
    const resp = await fetch(`${API_BASE}/draft/sessions`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ num_teams: numTeams, num_rounds: numRounds, user_team_slot: userSlot }),
    });
    const session = await resp.json();
    setCreating(false);
    onStart(session);
  };

  const handleResume = async (id: string) => {
    const resp = await fetch(`${API_BASE}/draft/sessions/${id}`);
    const session = await resp.json();
    onStart(session);
  };

  return (
    <div className="max-w-lg mx-auto">
      <div className="bg-[#1F2937]/60 border border-[#374151] rounded-xl p-6 mb-6">
        <h2 className="text-white font-bold text-base mb-5">Configure New Draft</h2>

        <div className="space-y-5">
          {/* Num teams */}
          <div>
            <label className="text-xs text-[#6B7280] block mb-2">Number of teams</label>
            <div className="flex gap-1 flex-wrap">
              {[8, 10, 12, 14].map((n) => (
                <button
                  key={n}
                  onClick={() => { setNumTeams(n); if (userSlot > n) setUserSlot(1); }}
                  className={`px-3 py-1.5 rounded text-sm font-medium transition-colors
                    ${numTeams === n ? "bg-[#004C54] text-white" : "bg-[#374151] text-[#A5ACAF] hover:text-white"}`}
                >
                  {n} teams
                </button>
              ))}
              <input
                type="number"
                min={2} max={20}
                value={numTeams}
                onChange={(e) => setNumTeams(parseInt(e.target.value) || 12)}
                className="w-20 bg-[#374151] text-white rounded px-2 py-1.5 text-sm outline-none border border-[#4B5563] focus:border-[#004C54]"
              />
            </div>
          </div>

          {/* Num rounds */}
          <div>
            <label className="text-xs text-[#6B7280] block mb-2">Number of rounds</label>
            <div className="flex gap-1 flex-wrap">
              {[15, 18, 20, 25].map((n) => (
                <button
                  key={n}
                  onClick={() => setNumRounds(n)}
                  className={`px-3 py-1.5 rounded text-sm font-medium transition-colors
                    ${numRounds === n ? "bg-[#004C54] text-white" : "bg-[#374151] text-[#A5ACAF] hover:text-white"}`}
                >
                  {n}
                </button>
              ))}
              <input
                type="number"
                min={1} max={30}
                value={numRounds}
                onChange={(e) => setNumRounds(parseInt(e.target.value) || 15)}
                className="w-20 bg-[#374151] text-white rounded px-2 py-1.5 text-sm outline-none border border-[#4B5563] focus:border-[#004C54]"
              />
            </div>
          </div>

          {/* Your draft slot */}
          <div>
            <label className="text-xs text-[#6B7280] block mb-2">Your draft position (slot)</label>
            <div className="flex gap-1 flex-wrap">
              {Array.from({ length: numTeams }, (_, i) => i + 1).map((slot) => (
                <button
                  key={slot}
                  onClick={() => setUserSlot(slot)}
                  className={`w-9 h-9 rounded text-sm font-medium transition-colors
                    ${userSlot === slot ? "bg-[#004C54] text-white" : "bg-[#374151] text-[#A5ACAF] hover:text-white"}`}
                >
                  {slot}
                </button>
              ))}
            </div>
          </div>
        </div>

        <button
          onClick={handleCreate}
          disabled={creating}
          className="mt-6 w-full bg-[#004C54] hover:bg-[#005f6a] disabled:opacity-40 text-white py-2.5 rounded text-sm font-bold transition-colors"
        >
          {creating ? "Starting draft…" : "Start Draft"}
        </button>
      </div>

      {/* Resume existing sessions */}
      {sessions.length > 0 && (
        <div>
          <h3 className="text-[#6B7280] text-xs font-semibold uppercase tracking-wider mb-3">Resume Previous Draft</h3>
          <div className="space-y-2">
            {sessions.map((s) => (
              <button
                key={s.id}
                onClick={() => handleResume(s.id)}
                className="w-full bg-[#1F2937]/60 border border-[#374151] hover:border-[#004C54]/60 rounded-lg px-4 py-3 text-left transition-colors"
              >
                <div className="flex justify-between items-center">
                  <div>
                    <span className="text-white text-sm font-medium">
                      {s.num_teams}-team · {s.num_rounds} rounds · Slot {s.user_team_slot}
                    </span>
                    <div className="text-xs text-[#6B7280] mt-0.5">{s.picks_made} picks made</div>
                  </div>
                  <span className="text-[#004C54] text-sm font-semibold">Resume →</span>
                </div>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Available players panel — searchable, filterable, click-to-draft or queue
// ---------------------------------------------------------------------------

function AvailablePlayersPanel({
  sessionId,
  draftedIds,
  queuedIds,
  onDraft,
  onQueue,
  onDequeue,
}: {
  sessionId: string;
  draftedIds: Set<number>;
  queuedIds: Set<number>;
  onDraft: (id: number) => void;
  onQueue: (id: number) => void;
  onDequeue: (id: number) => void;
}) {
  const [players, setPlayers] = useState<DynastyPlayer[]>([]);
  const [position, setPosition] = useState("ALL");
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);

  const load = useCallback(() => {
    setLoading(true);
    const params = new URLSearchParams({
      session_id: sessionId,
      position,
      q: query,
      limit: "60",
    });
    fetch(`${API_BASE}/draft/available?${params}`)
      .then((r) => r.json())
      .then((data) => { setPlayers(data); setLoading(false); })
      .catch(() => setLoading(false));
  }, [sessionId, position, query]);

  useEffect(() => { load(); }, [load]);
  // Reload when drafted set changes
  useEffect(() => { load(); }, [draftedIds.size, load]);

  return (
    <div className="flex flex-col h-full">
      <div className="mb-3 space-y-2">
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search players…"
          className="w-full bg-[#1F2937] text-white rounded px-3 py-1.5 text-sm outline-none border border-[#374151] focus:border-[#004C54]"
        />
        <div className="flex gap-1">
          {POSITIONS.map((p) => (
            <button
              key={p}
              onClick={() => setPosition(p)}
              className={`flex-1 py-1 rounded text-[10px] font-semibold transition-colors
                ${position === p ? "bg-[#004C54] text-white" : "bg-[#374151] text-[#6B7280] hover:text-white"}`}
            >
              {p}
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto space-y-1 pr-1" style={{ maxHeight: "520px" }}>
        {loading && <div className="text-[#6B7280] text-xs py-4 text-center">Loading…</div>}
        {!loading && players.length === 0 && (
          <div className="text-[#6B7280] text-xs py-4 text-center">No players available</div>
        )}
        {players.map((p) => {
          const isQueued = queuedIds.has(p.id);
          return (
            <div
              key={p.id}
              className={`flex items-center gap-2 px-2 py-1.5 rounded border transition-colors cursor-pointer
                ${isQueued
                  ? "bg-[#004C54]/10 border-[#004C54]/40"
                  : "bg-[#1F2937]/40 border-[#374151]/50 hover:border-[#004C54]/40"
                }`}
            >
              <div className="w-7 text-[#6B7280] text-[10px] font-mono shrink-0 text-center">
                {p.overall_rank ?? "—"}
              </div>
              {p.sleeper_id && (
                <PlayerHeadshot sleeperId={p.sleeper_id} playerName={p.player_name} position={p.position ?? "—"} size={24} />
              )}
              <div className="flex-1 min-w-0">
                <div className="text-white text-xs font-medium truncate">{p.player_name}</div>
                <div className="text-[#6B7280] text-[10px] flex items-center gap-1">
                  {p.position && (
                    <span className={`px-1 rounded text-[9px] font-bold ${POS_COLORS[p.position] ?? ""}`}>{p.position}</span>
                  )}
                  {p.team && <span>{p.team}</span>}
                  {p.age && <span>· {p.age.toFixed(0)}y</span>}
                </div>
              </div>
              <div className="flex gap-1 shrink-0">
                <button
                  onClick={() => isQueued ? onDequeue(p.id) : onQueue(p.id)}
                  title={isQueued ? "Remove from queue" : "Add to queue"}
                  className={`w-6 h-6 rounded text-xs transition-colors flex items-center justify-center
                    ${isQueued ? "bg-[#004C54] text-white" : "bg-[#374151] text-[#A5ACAF] hover:text-white"}`}
                >
                  {isQueued ? "★" : "☆"}
                </button>
                <button
                  onClick={() => onDraft(p.id)}
                  title="Draft this player"
                  className="w-6 h-6 rounded bg-[#22C55E]/20 text-[#22C55E] hover:bg-[#22C55E]/40 text-xs transition-colors flex items-center justify-center"
                >
                  +
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Draft board — main view
// ---------------------------------------------------------------------------

function DraftBoardView({ session: initialSession }: { session: DraftSessionState }) {
  const [session, setSession] = useState(initialSession);
  const [actionLoading, setActionLoading] = useState(false);
  const [activeView, setActiveView] = useState<"board" | "picks" | "queue">("board");

  const draftedIds = new Set(session.drafted_players.map((p) => p.id));
  const queuedIds = new Set(session.queued_players.map((p) => p.id));
  const totalPicks = session.num_teams * session.num_rounds;
  const isDraftComplete = session.current_pick > totalPicks;

  const apiAction = async (url: string, method: string, body?: object) => {
    setActionLoading(true);
    const resp = await fetch(url, {
      method,
      headers: body ? { "Content-Type": "application/json" } : {},
      body: body ? JSON.stringify(body) : undefined,
    });
    if (resp.ok && resp.status !== 204) {
      setSession(await resp.json());
    }
    setActionLoading(false);
  };

  const handleDraft = (id: number) => apiAction(`${API_BASE}/draft/sessions/${session.id}/picks`, "POST", { dynasty_value_id: id });
  const handleUndo = () => apiAction(`${API_BASE}/draft/sessions/${session.id}/picks`, "DELETE");
  const handleQueue = (id: number) => apiAction(`${API_BASE}/draft/sessions/${session.id}/queue`, "POST", { dynasty_value_id: id });
  const handleDequeue = (id: number) => apiAction(`${API_BASE}/draft/sessions/${session.id}/queue/${id}`, "DELETE");

  // Current pick details
  const currentPickSlot = !isDraftComplete ? session.pick_order[session.current_pick - 1] : null;
  const isUserPick = currentPickSlot?.team_slot === session.user_team_slot;

  // Group drafted picks by round for the board view
  const picksByRound: Record<number, { slot: PickSlot; player?: DynastyPlayer }[]> = {};
  for (const slot of session.pick_order) {
    if (!picksByRound[slot.round]) picksByRound[slot.round] = [];
    const playerAtPick = slot.pick <= session.current_pick - 1
      ? session.drafted_players[slot.pick - 1]
      : undefined;
    picksByRound[slot.round].push({ slot, player: playerAtPick });
  }

  const visibleRounds = Object.keys(picksByRound)
    .map(Number)
    .filter((r) => {
      const currentRound = currentPickSlot?.round ?? session.num_rounds;
      return r <= currentRound + 1;
    });

  return (
    <div className="grid grid-cols-1 xl:grid-cols-[1fr_280px] gap-6">
      {/* Left: board + controls */}
      <div>
        {/* Status bar */}
        <div className={`flex items-center justify-between px-4 py-3 rounded-lg mb-4 border
          ${isDraftComplete
            ? "bg-[#022c10] border-[#22C55E]/40"
            : isUserPick
              ? "bg-[#004C54]/20 border-[#004C54]/60"
              : "bg-[#1F2937]/60 border-[#374151]"
          }`}
        >
          <div>
            {isDraftComplete ? (
              <span className="text-[#22C55E] font-bold">Draft Complete!</span>
            ) : (
              <>
                <span className="text-white font-semibold">
                  Pick {session.current_pick} of {totalPicks}
                </span>
                <span className="text-[#A5ACAF] text-sm ml-2">
                  — Round {currentPickSlot?.round}, Slot {currentPickSlot?.team_slot}
                  {isUserPick && (
                    <span className="ml-2 text-[#00E5FF] font-bold animate-pulse">← YOUR PICK</span>
                  )}
                </span>
              </>
            )}
          </div>
          <div className="flex gap-2">
            {session.drafted_players.length > 0 && (
              <button
                onClick={handleUndo}
                disabled={actionLoading}
                className="px-3 py-1 rounded text-xs bg-[#374151] text-[#A5ACAF] hover:text-white disabled:opacity-40 transition-colors"
              >
                Undo
              </button>
            )}
          </div>
        </div>

        {/* Queue banner — if user has picks queued and it's their turn */}
        {isUserPick && session.queued_players.length > 0 && (
          <div className="bg-[#004C54]/15 border border-[#004C54]/40 rounded-lg px-4 py-2 mb-4">
            <div className="text-xs text-[#A5ACAF] mb-1">Your queue (next up):</div>
            <div className="flex gap-2 flex-wrap">
              {session.queued_players.map((p) => (
                <button
                  key={p.id}
                  onClick={() => handleDraft(p.id)}
                  disabled={actionLoading}
                  className="flex items-center gap-1.5 bg-[#004C54] hover:bg-[#005f6a] disabled:opacity-40 text-white px-2 py-1 rounded text-xs font-semibold transition-colors"
                >
                  {p.position && <span>{p.position}</span>}
                  {p.player_name}
                  <span className="text-[#A5ACAF]">Draft</span>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* View toggles */}
        <div className="flex gap-2 mb-4">
          {(["board", "picks", "queue"] as const).map((v) => (
            <button
              key={v}
              onClick={() => setActiveView(v)}
              className={`px-3 py-1 rounded text-xs font-medium transition-colors
                ${activeView === v ? "bg-[#1F2937] text-white" : "text-[#6B7280] hover:text-white"}`}
            >
              {v === "board" ? "Full Board" : v === "picks" ? `My Picks (${session.user_picks.length})` : `Queue (${session.queued_players.length})`}
            </button>
          ))}
        </div>

        {/* Board view: round-by-round grid */}
        {activeView === "board" && (
          <div className="overflow-x-auto">
            <div className="space-y-1 min-w-[600px]">
              {visibleRounds.map((round) => (
                <div key={round} className="flex gap-1">
                  <div className="w-10 shrink-0 text-[10px] text-[#6B7280] font-mono flex items-center justify-center">
                    R{round}
                  </div>
                  {picksByRound[round].map(({ slot, player }) => {
                    const isCurrentPick = slot.pick === session.current_pick;
                    const isUserSlot = slot.team_slot === session.user_team_slot;
                    const isDrafted = !!player;

                    return (
                      <div
                        key={slot.pick}
                        className={`flex-1 min-w-0 rounded px-1.5 py-1 border text-[10px] transition-colors
                          ${isCurrentPick
                            ? "border-[#004C54] bg-[#004C54]/20 ring-1 ring-[#004C54]/40"
                            : isDrafted
                              ? isUserSlot
                                ? "border-[#004C54]/30 bg-[#004C54]/10"
                                : "border-[#374151]/50 bg-[#1F2937]/30"
                              : isUserSlot
                                ? "border-[#374151] bg-[#1F2937]/20 border-dashed"
                                : "border-[#374151]/30 bg-transparent"
                          }`}
                      >
                        <div className="text-[#6B7280] font-mono">{slot.pick}</div>
                        {player ? (
                          <div>
                            <div className="text-white font-medium truncate leading-tight">{player.player_name}</div>
                            {player.position && (
                              <span className={`text-[8px] font-bold px-0.5 rounded ${POS_COLORS[player.position] ?? ""}`}>
                                {player.position}
                              </span>
                            )}
                          </div>
                        ) : isCurrentPick ? (
                          <div className="text-[#004C54] font-semibold">On the clock</div>
                        ) : (
                          <div className="text-[#374151]">{isUserSlot ? "Your pick" : "—"}</div>
                        )}
                      </div>
                    );
                  })}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* My picks view */}
        {activeView === "picks" && (
          <div className="space-y-2">
            {session.user_picks.map((slot) => {
              const player = slot.pick <= session.drafted_players.length
                ? session.drafted_players[slot.pick - 1]
                : undefined;
              const isNextPick = slot.pick === session.current_pick;
              return (
                <div
                  key={slot.pick}
                  className={`flex items-center gap-4 px-4 py-2.5 rounded-lg border
                    ${isNextPick
                      ? "border-[#004C54] bg-[#004C54]/15"
                      : player
                        ? "border-[#374151] bg-[#1F2937]/40"
                        : "border-[#374151]/40 bg-transparent"
                    }`}
                >
                  <div className="w-12 text-center shrink-0">
                    <div className="text-white text-sm font-mono">#{slot.pick}</div>
                    <div className="text-[#6B7280] text-[10px]">R{slot.round}</div>
                  </div>
                  {player ? (
                    <div className="flex items-center gap-3 flex-1">
                      {player.sleeper_id && (
                        <PlayerHeadshot sleeperId={player.sleeper_id} playerName={player.player_name} position={player.position ?? "—"} size={32} />
                      )}
                      <div>
                        <div className="text-white font-semibold">{player.player_name}</div>
                        <div className="flex items-center gap-1.5 text-xs text-[#A5ACAF]">
                          {player.position && (
                            <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${POS_COLORS[player.position] ?? ""}`}>
                              {player.position}
                            </span>
                          )}
                          {player.team && <span>{player.team}</span>}
                          <span>#{player.overall_rank} overall</span>
                        </div>
                      </div>
                      <div className="ml-auto text-right">
                        <div className="text-white font-mono text-sm">{player.value.toLocaleString()}</div>
                        <div className="text-[10px] text-[#6B7280]">{player.position_tier}</div>
                      </div>
                    </div>
                  ) : (
                    <div className={`text-sm ${isNextPick ? "text-[#00E5FF] font-bold" : "text-[#4B5563]"}`}>
                      {isNextPick ? "← On the clock!" : "Upcoming pick"}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}

        {/* Queue view */}
        {activeView === "queue" && (
          <div>
            {session.queued_players.length === 0 ? (
              <div className="text-[#6B7280] text-sm py-8 text-center">
                Queue is empty — star players in the Available panel to queue them.
              </div>
            ) : (
              <div className="space-y-2">
                {session.queued_players.map((p, i) => (
                  <div key={p.id} className="flex items-center gap-3 px-4 py-2.5 bg-[#004C54]/10 border border-[#004C54]/30 rounded-lg">
                    <div className="w-6 text-center text-[#6B7280] text-xs font-bold">{i + 1}</div>
                    {p.sleeper_id && <PlayerHeadshot sleeperId={p.sleeper_id} playerName={p.player_name} position={p.position ?? "—"} size={32} />}
                    <div className="flex-1 min-w-0">
                      <div className="text-white font-semibold">{p.player_name}</div>
                      <div className="flex items-center gap-1.5 text-xs text-[#A5ACAF]">
                        {p.position && (
                          <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${POS_COLORS[p.position] ?? ""}`}>{p.position}</span>
                        )}
                        {p.team && <span>{p.team}</span>}
                        <span>#{p.overall_rank}</span>
                      </div>
                    </div>
                    <div className="flex gap-2">
                      <button
                        onClick={() => handleDraft(p.id)}
                        disabled={actionLoading}
                        className="px-3 py-1 rounded text-xs bg-[#22C55E]/20 text-[#22C55E] hover:bg-[#22C55E]/30 disabled:opacity-40 transition-colors font-semibold"
                      >
                        Draft
                      </button>
                      <button
                        onClick={() => handleDequeue(p.id)}
                        disabled={actionLoading}
                        className="px-3 py-1 rounded text-xs bg-[#374151] text-[#A5ACAF] hover:text-white disabled:opacity-40 transition-colors"
                      >
                        Remove
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Right: available players */}
      <div className="xl:border-l xl:border-[#1F2937] xl:pl-5">
        <h3 className="text-[#6B7280] text-xs font-semibold uppercase tracking-wider mb-3">Available Players</h3>
        <AvailablePlayersPanel
          sessionId={session.id}
          draftedIds={draftedIds}
          queuedIds={queuedIds}
          onDraft={handleDraft}
          onQueue={handleQueue}
          onDequeue={handleDequeue}
        />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Root export
// ---------------------------------------------------------------------------

export function DraftBoardTab() {
  const [activeSession, setActiveSession] = useState<DraftSessionState | null>(null);

  if (!activeSession) {
    return <SetupScreen onStart={setActiveSession} />;
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <div className="text-xs text-[#6B7280]">
          {activeSession.num_teams}-team snake · {activeSession.num_rounds} rounds · Your slot: {activeSession.user_team_slot}
        </div>
        <button
          onClick={() => setActiveSession(null)}
          className="text-xs text-[#A5ACAF] hover:text-white transition-colors"
        >
          ← New Draft
        </button>
      </div>
      <DraftBoardView session={activeSession} />
    </div>
  );
}
