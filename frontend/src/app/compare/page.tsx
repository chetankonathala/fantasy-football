import Link from "next/link";
import { CompareView } from "@/components/CompareView";

export default function ComparePage() {
  return (
    <div className="max-w-5xl mx-auto px-6 py-6">
      <Link href="/" className="text-sm text-[#A5ACAF] hover:text-white transition-colors">
        &larr; Back to search
      </Link>
      <h1 className="mt-4 text-2xl font-extrabold text-white">Compare Players</h1>
      <p className="text-[#A5ACAF] text-sm mt-1">Search for two players to compare side-by-side</p>
      <div className="mt-6">
        <CompareView />
      </div>
    </div>
  );
}
