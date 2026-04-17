import Link from "next/link";
import { DraftRoom } from "./DraftRoom";

export const metadata = { title: "Draft Room — Fantasy Advisor" };

export default function DraftPage() {
  return (
    <div className="max-w-7xl mx-auto px-6 py-6">
      <Link href="/" className="text-sm text-[#A5ACAF] hover:text-white transition-colors">
        &larr; Back to home
      </Link>
      <div className="mt-4 mb-6">
        <h1 className="text-2xl font-extrabold text-white">Dynasty Draft Room</h1>
        <p className="text-sm text-[#A5ACAF] mt-1">
          Dynasty rankings, rookie grades, keeper analysis, and live draft board — all in one place.
        </p>
      </div>
      <DraftRoom />
    </div>
  );
}
