import Link from "next/link";

export function PublicFooter() {
  return (
    <footer className="w-full bg-surface-container-lowest mt-space-2xl border-t border-glass-border">
      <div className="max-w-[1440px] mx-auto px-6 lg:px-margin-lg py-7 flex flex-col md:flex-row items-center justify-between gap-5">
        <div className="flex items-center gap-4">
          <div className="w-7 h-7 rounded-lg bg-surface-secondary/70 border border-glass-border flex items-center justify-center text-primary flex-shrink-0">
            <span className="material-symbols-outlined text-[17px]" aria-hidden="true">biotech</span>
          </div>
          <span className="font-headline-sm text-body-md tracking-[0.2em] uppercase text-text-highlight font-medium">
            MEDASSIST AI
          </span>
          <span className="text-caption font-caption text-surface-muted pl-4 border-l border-surface-container-high hidden sm:inline">
            MEDICAL REPORT INTELLIGENCE
          </span>
        </div>

        <div className="flex flex-wrap items-center gap-8 font-body-sm text-body-sm text-on-surface-variant">
          <Link className="hover:text-on-surface transition-colors" href="/about-us">
            About
          </Link>
          <Link className="hover:text-on-surface transition-colors" href="/procedures">
            Procedures
          </Link>
          <Link className="hover:text-on-surface transition-colors" href="/about-us">
            Clinical Validation
          </Link>
          <Link className="hover:text-on-surface transition-colors" href="/about-us#data-management">
            Privacy &amp; data
          </Link>
        </div>

        <div className="font-caption text-caption text-surface-muted">
          © {new Date().getFullYear()} MedAssist AI. Medical information is not a substitute for professional care.
        </div>
      </div>
    </footer>
  );
}
