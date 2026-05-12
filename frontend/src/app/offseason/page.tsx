import Link from "next/link";
import { OffseasonHub } from "./OffseasonHub";

export const metadata = { title: "Offseason Hub — Fantasy Advisor" };

export default function OffseasonPage() {
  return (
    <div className="max-w-7xl mx-auto px-6 py-6">
      <Link href="/" className="text-sm text-[#A5ACAF] hover:text-white transition-colors">
        &larr; Back to home
      </Link>
      <div className="mt-4 mb-6">
        <h1 className="text-2xl font-extrabold text-white">Offseason Hub</h1>
        <p className="text-sm text-[#A5ACAF] mt-1">
          2026 rookie class, offseason moves, risers &amp; fallers, and pre-draft cheat sheet — updated after the NFL Draft.
        </p>
      </div>
      <OffseasonHub />
    </div>
  );
}
