import { SignIn } from "@clerk/nextjs";
import Link from "next/link";

export default function SignInPage() {
  return (
    <main className="min-h-screen flex flex-col items-center justify-center bg-background-canvas text-on-surface p-6 relative overflow-hidden">
      {/* Background Orbs */}
      <div className="pointer-events-none fixed top-0 right-1/4 -z-10 h-96 w-96 rounded-full bg-accent-chroma/15 blur-[128px]"></div>
      <div className="pointer-events-none fixed bottom-1/3 left-10 -z-10 h-80 w-80 rounded-full bg-secondary-container/20 blur-[140px]"></div>

      <div className="mb-6 text-center flex flex-col items-center">
        <Link
          href="/"
          className="mb-4 w-12 h-12 rounded-xl bg-surface-secondary border border-glass-border flex items-center justify-center text-primary shadow-[0_0_24px_rgba(109,113,138,0.35)]"
        >
          <span className="material-symbols-outlined text-[24px]">biotech</span>
        </Link>
        <h1 className="font-headline-lg text-2xl font-light text-primary tracking-tight">MedAssist AI</h1>
        <p className="font-caption text-caption uppercase tracking-[0.2em] text-text-highlight mt-1">
          Medical report assistant
        </p>
      </div>

      <div className="rounded-2xl border border-glass-border shadow-2xl p-2 bg-surface-container-lowest/80 backdrop-blur-2xl">
        <SignIn
          routing="path"
          path="/sign-in"
          signUpUrl="/sign-up"
          fallbackRedirectUrl="/dashboard"
          appearance={{
            elements: {
              card: "bg-transparent shadow-none",
            },
          }}
        />
      </div>
    </main>
  );
}
