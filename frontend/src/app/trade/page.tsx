import Link from "next/link";
import { TradeBuilder } from "@/components/TradeBuilder";

export default function TradePage() {
  return (
    <div className="max-w-4xl mx-auto px-6 py-6">
      <Link href="/" className="text-sm text-[#A5ACAF] hover:text-white transition-colors">
        &larr; Back to home
      </Link>

      <div className="mt-4 mb-2">
        <h1 className="text-2xl font-extrabold text-white">Dynasty Trade Analyzer</h1>
        <p className="text-sm text-[#A5ACAF] mt-1">
          Search players and picks on each side — get an instant WIN / LOSE / FAIR verdict
          powered by live FantasyCalc dynasty values.
        </p>
      </div>

      <div className="mt-6">
        <TradeBuilder />
      </div>

      <p className="mt-8 text-xs text-[#A5ACAF]/40 text-center">
        Values sourced from FantasyCalc · 1QB · 12-team · PPR · Updated daily
      </p>
    </div>
  );
}
