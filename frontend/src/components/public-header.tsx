"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import { useAuth, UserButton } from "@clerk/nextjs";
import { NavigationLoadingLink } from "@/components/navigation-loading-link";

export function PublicHeader() {
  const pathname = usePathname();
  const { isSignedIn } = useAuth();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const navLinks = [
    { label: "Home", href: "/" },
    { label: "About Us", href: "/about-us" },
    { label: "Procedures", href: "/procedures" },
  ];

  useEffect(() => setMobileMenuOpen(false), [pathname]);

  return (
    <header className="fixed top-4 inset-x-0 z-50 px-4 sm:px-6 pointer-events-none">
      <div className="pointer-events-auto relative h-16 max-w-5xl mx-auto px-3 sm:px-6 rounded-full bg-white/[0.07] backdrop-blur-2xl border border-white/10 shadow-[inset_0_1px_0_rgba(255,255,255,0.12)] flex items-center justify-between transition-all duration-300">
        {/* Brand Logo & Title */}
        <div className="flex items-center gap-2 sm:gap-4 min-w-0">
          <div className="w-8 h-8 rounded-lg bg-white/10 border border-white/20 flex items-center justify-center backdrop-blur-md shadow-sm flex-shrink-0">
            <span className="material-symbols-outlined text-[18px] text-primary" aria-hidden="true">biotech</span>
          </div>
          <Link className="flex items-center gap-2" href="/">
            <span className="font-headline-sm text-xs sm:text-body-lg tracking-[0.1em] sm:tracking-[0.18em] uppercase text-primary font-medium whitespace-nowrap">
              MEDASSIST AI
            </span>
            <span className="hidden sm:inline-block h-1.5 w-1.5 rounded-full bg-accent-chroma animate-pulse"></span>
          </Link>
        </div>

        {/* Navigation items */}
        <nav className="hidden md:flex items-center gap-10 font-body-sm text-body-sm uppercase tracking-[0.14em]">
          {navLinks.map((link) => {
            const isActive = pathname === link.href;
            return (
              <Link
                key={link.href}
                href={link.href}
                className={`transition-colors duration-200 ${
                  isActive
                    ? "text-primary font-medium tracking-wide drop-shadow-[0_0_12px_rgba(206,204,220,0.35)]"
                    : "text-on-surface-variant hover:text-on-surface"
                }`}
              >
                {link.label}
              </Link>
            );
          })}
        </nav>

        {/* Actions */}
        <div className="flex items-center gap-2 sm:gap-4 shrink-0">
          <button
            type="button"
            className="md:hidden w-8 h-8 rounded-full bg-surface-secondary/70 border border-glass-border flex items-center justify-center text-primary hover:bg-surface-secondary transition-colors"
            aria-label={mobileMenuOpen ? "Close navigation menu" : "Open navigation menu"}
            aria-expanded={mobileMenuOpen}
            onClick={() => setMobileMenuOpen((open) => !open)}
          >
            <span className="material-symbols-outlined text-[18px]" aria-hidden="true">{mobileMenuOpen ? "close" : "menu"}</span>
          </button>
          <NavigationLoadingLink
            className="relative inline-flex items-center justify-center px-3 sm:px-6 py-2.5 rounded-full bg-primary-container text-on-primary font-body-sm text-[11px] sm:text-body-sm whitespace-nowrap font-medium tracking-wide shadow-[0_0_24px_rgba(206,204,220,0.22)] hover:bg-primary hover:shadow-[0_0_32px_rgba(206,204,220,0.45)] transition-all duration-300"
            href={isSignedIn ? "/dashboard" : "/sign-in"}
          >
            Start Program
          </NavigationLoadingLink>

          {isSignedIn ? (
            <div className="flex items-center justify-center">
              <UserButton afterSignOutUrl="/" />
            </div>
          ) : (
            <Link
              href="/sign-in"
              className="w-8 h-8 rounded-full bg-surface-secondary/70 border border-glass-border flex items-center justify-center text-primary hover:bg-surface-secondary transition-colors"
              title="Sign In"
            >
              <span className="material-symbols-outlined text-[18px]">person</span>
            </Link>
          )}
        </div>
        {mobileMenuOpen && (
          <nav aria-label="Mobile navigation" className="md:hidden absolute left-0 right-0 top-[4.25rem] rounded-2xl border border-glass-border bg-surface-container-lowest/95 p-2 shadow-2xl backdrop-blur-2xl">
            {navLinks.map((link) => (
              <Link key={link.href} href={link.href} aria-current={pathname === link.href ? "page" : undefined} className={`block rounded-xl px-4 py-3 text-sm transition-colors ${pathname === link.href ? "bg-surface-container-high text-primary" : "text-on-surface-variant hover:bg-surface-container hover:text-on-surface"}`}>
                {link.label}
              </Link>
            ))}
          </nav>
        )}
      </div>
    </header>
  );
}
