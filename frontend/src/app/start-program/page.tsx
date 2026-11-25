"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@clerk/nextjs";

export default function StartProgramPage() {
  const router = useRouter();
  const { isLoaded, isSignedIn } = useAuth();

  useEffect(() => {
    if (isLoaded) {
      if (isSignedIn) {
        router.replace("/dashboard");
      } else {
        router.replace("/sign-in?redirect_url=/dashboard");
      }
    }
  }, [isLoaded, isSignedIn, router]);

  return (
    <div className="bg-background-canvas min-h-screen flex items-center justify-center p-6 text-on-surface">
      <div className="flex flex-col items-center gap-4">
        <div className="w-10 h-10 rounded-full border-2 border-primary border-t-transparent animate-spin"></div>
        <span className="font-label-code text-caption uppercase tracking-widest text-text-highlight">
          INITIALIZING CLINICAL ENCLAVE...
        </span>
      </div>
    </div>
  );
}
