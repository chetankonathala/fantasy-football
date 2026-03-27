import { SearchBar } from "@/components/SearchBar";

export default function Home() {
  return (
    <main className="min-h-screen flex flex-col items-center justify-center px-8">
      <h1 className="text-4xl font-bold text-white">Fantasy Advisor</h1>
      <p className="text-base text-[#A5ACAF] mt-2">Start/Sit clarity, instantly.</p>
      <div className="mt-8 max-w-[480px] w-full">
        <SearchBar />
      </div>
    </main>
  );
}
