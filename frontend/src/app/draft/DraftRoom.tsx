"use client";

import { useState } from "react";
import { DynastyRankingsTab } from "./DynastyRankingsTab";
import { RookieRankingsTab } from "./RookieRankingsTab";
import { KeeperAnalysisTab } from "./KeeperAnalysisTab";
import { DraftBoardTab } from "./DraftBoardTab";

type Tab = "rankings" | "rookies" | "keepers" | "board";

const TABS: { id: Tab; label: string }[] = [
  { id: "rankings", label: "Dynasty Rankings" },
  { id: "rookies",  label: "Rookie Class" },
  { id: "keepers",  label: "Keeper Analysis" },
  { id: "board",    label: "Draft Board" },
];

export function DraftRoom() {
  const [activeTab, setActiveTab] = useState<Tab>("rankings");

  return (
    <div>
      {/* Tab bar */}
      <div className="flex gap-1 border-b border-[#1F2937] mb-6">
        {TABS.map((t) => (
          <button
            key={t.id}
            onClick={() => setActiveTab(t.id)}
            className={`px-4 py-2 text-sm font-medium transition-colors rounded-t
              ${activeTab === t.id
                ? "text-white border-b-2 border-[#004C54] bg-[#1F2937]"
                : "text-[#A5ACAF] hover:text-white"
              }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {activeTab === "rankings" && <DynastyRankingsTab />}
      {activeTab === "rookies"  && <RookieRankingsTab />}
      {activeTab === "keepers"  && <KeeperAnalysisTab />}
      {activeTab === "board"    && <DraftBoardTab />}
    </div>
  );
}
