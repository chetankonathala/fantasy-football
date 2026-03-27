"use client";

interface FreshnessStampProps {
  updatedAt: string; // ISO 8601 string
}

function relativeTime(isoString: string): string {
  const diff = Date.now() - new Date(isoString).getTime();
  const seconds = Math.floor(diff / 1000);
  if (seconds < 60) return "Updated just now";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `Updated ${minutes} minute${minutes !== 1 ? "s" : ""} ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `Updated ${hours} hour${hours !== 1 ? "s" : ""} ago`;
  const days = Math.floor(hours / 24);
  return `Updated ${days} day${days !== 1 ? "s" : ""} ago`;
}

export function FreshnessStamp({ updatedAt }: FreshnessStampProps) {
  return (
    <p className="text-sm text-[#A5ACAF] pt-2 mt-8">
      {relativeTime(updatedAt)}
    </p>
  );
}
