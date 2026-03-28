"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { useDebounce } from "use-debounce";

interface PlayerResult {
  id: number;
  full_name: string;
  position: string;
  team: string;
}

interface SearchBarProps {
  placeholder?: string;
  size?: "sm" | "lg";
}

export function SearchBar({ placeholder = "Search players...", size = "sm" }: SearchBarProps) {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [debouncedQuery] = useDebounce(query, 300);
  const [results, setResults] = useState<PlayerResult[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);
  const wrapperRef = useRef<HTMLDivElement>(null);

  // Fetch results when debounced query changes
  useEffect(() => {
    if (debouncedQuery.length < 2) {
      setResults([]);
      setIsOpen(false);
      return;
    }
    setIsLoading(true);
    fetch(`http://localhost:8000/search?q=${encodeURIComponent(debouncedQuery)}`)
      .then((r) => r.json())
      .then((data: PlayerResult[]) => {
        setResults(data);
        setIsOpen(true);
        setIsLoading(false);
      })
      .catch(() => {
        setResults([]);
        setIsLoading(false);
      });
  }, [debouncedQuery]);

  // Click outside to close
  useEffect(() => {
    function handleMouseDown(e: MouseEvent) {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleMouseDown);
    return () => document.removeEventListener("mousedown", handleMouseDown);
  }, []);

  function selectPlayer(result: PlayerResult) {
    router.push(`/player/${result.id}`);
    setQuery("");
    setIsOpen(false);
    setActiveIndex(-1);
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActiveIndex((prev) => Math.min(prev + 1, results.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActiveIndex((prev) => Math.max(prev - 1, 0));
    } else if (e.key === "Enter") {
      if (activeIndex >= 0 && results[activeIndex]) {
        selectPlayer(results[activeIndex]);
      }
    } else if (e.key === "Escape") {
      setIsOpen(false);
      setActiveIndex(-1);
    }
  }

  const showDropdown =
    isOpen && (results.length > 0 || (debouncedQuery.length >= 2 && !isLoading));

  return (
    <div ref={wrapperRef} className="relative">
      <div className="relative">
        <input
          type="text"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setActiveIndex(-1);
          }}
          onKeyDown={handleKeyDown}
          onFocus={() => results.length > 0 && setIsOpen(true)}
          placeholder={placeholder}
          aria-label="Search players"
          role="combobox"
          aria-expanded={isOpen}
          aria-controls="search-listbox"
          aria-autocomplete="list"
          className={`w-full bg-[#111827] border border-[#A5ACAF] rounded-md px-4 text-white placeholder-[#A5ACAF] focus:border-[#004C54] focus:border-2 focus:outline-none ${size === "lg" ? "py-3 text-base" : "py-2 text-sm"}`}
        />
        {isLoading && (
          <div className="absolute right-3 top-1/2 -translate-y-1/2">
            <div className="w-4 h-4 border-2 border-[#A5ACAF] border-t-transparent rounded-full animate-spin" />
          </div>
        )}
      </div>

      {showDropdown && (
        <ul
          id="search-listbox"
          role="listbox"
          className="absolute z-50 w-full mt-1 bg-[#111827] rounded-md shadow-lg overflow-hidden"
        >
          {results.length === 0 ? (
            <li className="px-4 py-3 text-[#A5ACAF] text-sm">
              No players found
              <span className="block text-xs mt-1">
                Try a different name or check the spelling.
              </span>
            </li>
          ) : (
            results.map((r, i) => (
              <li
                key={r.id}
                role="option"
                aria-selected={i === activeIndex}
                onClick={() => selectPlayer(r)}
                onMouseEnter={() => setActiveIndex(i)}
                className={`px-4 min-h-[44px] flex items-center cursor-pointer text-white ${
                  i === activeIndex
                    ? "bg-[#004C54]/50"
                    : "hover:bg-[#004C54]/30"
                }`}
              >
                {r.full_name}
                <span className="text-[#A5ACAF] ml-2">
                  — {r.position}, {r.team}
                </span>
              </li>
            ))
          )}
        </ul>
      )}
    </div>
  );
}
