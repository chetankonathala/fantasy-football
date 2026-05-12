"use client";

import { useState } from "react";
import { RookieClassTab } from "./RookieClassTab";
import { MovesTab } from "./MovesTab";
import { RisersFallersTab } from "./RisersFallersTab";
import { CheatSheetTab } from "./CheatSheetTab";

type Tab = "rookies" | "moves" | "risers" | "cheatsheet";

const TABS: { id: Tab; label: string }[] = [
  { id: "rookies",    label: "Rookie Class" },
  { id: "moves",      label: "Moves Feed" },
  { id: "risers",     label: "Risers & Fallers" },
  { id: "cheatsheet", label: "Cheat Sheet" },
];

export function OffseasonHub() {
  const [activeTab, setActiveTab] = useState<Tab>("rookies");

  return (
    <div>
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

      {activeTab === "rookies"    && <RookieClassTab />}
      {activeTab === "moves"      && <MovesTab />}
      {activeTab === "risers"     && <RisersFallersTab />}
      {activeTab === "cheatsheet" && <CheatSheetTab />}
    </div>
  );
}
