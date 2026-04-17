"use client";

import { useState } from "react";

interface PlayerHeadshotProps {
  sleeperId: string | null;
  playerName: string;
  position: string;
  size?: number;
}

export function PlayerHeadshot({ sleeperId, playerName, position, size = 64 }: PlayerHeadshotProps) {
  const [failed, setFailed] = useState(false);

  if (!sleeperId || failed) {
    return (
      <div
        style={{ width: size, height: size }}
        className="rounded-full bg-[#004C54]/30 border border-[#004C54] flex items-center justify-center text-sm font-bold text-[#A5ACAF] flex-shrink-0"
      >
        {position}
      </div>
    );
  }

  return (
    <div
      style={{ width: size, height: size }}
      className="rounded-full overflow-hidden flex-shrink-0 bg-[#1F2937] border border-[#004C54]/40"
    >
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={`https://sleepercdn.com/content/nfl/players/${sleeperId}.jpg`}
        alt={playerName}
        width={size}
        height={size}
        className="w-full h-full object-cover object-top"
        onError={() => setFailed(true)}
      />
    </div>
  );
}
