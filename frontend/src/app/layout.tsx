import type { Metadata } from "next";
import { Inter } from "next/font/google";
import Link from "next/link";
import "./globals.css";
import { SearchBar } from "@/components/SearchBar";

const inter = Inter({
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Fantasy Advisor",
  description: "Start/Sit clarity, instantly.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className={`${inter.className} pt-14`}>
        <header className="fixed top-0 left-0 right-0 z-40 h-14 flex items-center justify-between px-8 bg-[#111827] border-b border-[#004C54]">
          <Link href="/" className="text-sm font-bold text-white">
            Fantasy Advisor
          </Link>
          <div className="flex items-center gap-5">
            <Link href="/compare" className="text-sm text-[#A5ACAF] hover:text-white transition-colors">
              Compare
            </Link>
            <Link href="/trade" className="text-sm text-[#A5ACAF] hover:text-white transition-colors">
              Trade
            </Link>
            <Link href="/my-team" className="text-sm text-[#A5ACAF] hover:text-white transition-colors">
              My Team
            </Link>
            <Link href="/draft" className="text-sm text-[#A5ACAF] hover:text-white transition-colors">
              Draft Room
            </Link>
          </div>
          <div className="w-80">
            <SearchBar />
          </div>
        </header>
        {children}
      </body>
    </html>
  );
}
