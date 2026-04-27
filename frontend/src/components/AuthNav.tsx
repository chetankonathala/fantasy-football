"use client";

import { useAuth, SignInButton, UserButton } from "@clerk/nextjs";

export function AuthNav() {
  const { isSignedIn, isLoaded } = useAuth();

  if (!isLoaded) return <div className="w-8 h-8" />;

  if (isSignedIn) {
    return <UserButton />;
  }

  return (
    <SignInButton mode="modal">
      <button className="text-sm text-[#A5ACAF] hover:text-white transition-colors">
        Sign In
      </button>
    </SignInButton>
  );
}
