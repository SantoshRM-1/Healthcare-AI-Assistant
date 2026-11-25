"use client";

import Link from "next/link";
import { PublicHeader } from "@/components/public-header";
import { PublicFooter } from "@/components/public-footer";
import { DNAHelixCanvas } from "@/components/dna-helix-canvas";
import { NavigationLoadingLink } from "@/components/navigation-loading-link";

export default function HomePage() {
  return (
    <div className="bg-background-canvas text-on-surface font-body-md text-body-md antialiased min-h-screen relative overflow-x-hidden">
      {/* Background Orbs */}
      <div className="pointer-events-none fixed top-0 right-1/4 -z-10 h-96 w-96 rounded-full bg-accent-chroma/15 blur-[128px]"></div>
      <div className="pointer-events-none fixed bottom-1/3 left-10 -z-10 h-80 w-80 rounded-full bg-secondary-container/20 blur-[140px]"></div>

      <PublicHeader />

      <main className="w-full pt-20 bg-background-canvas min-h-[calc(100vh-200px)]">
        <div className="flex flex-col w-full relative overflow-hidden">
          {/* Interactive & Aesthetic Ambient Atmosphere */}
          <div className="relative w-full min-h-[920px] lg:h-[calc(100vh-5rem)] flex flex-col justify-between overflow-hidden">
            {/* ThreeJS 3D DNA Simulation Layer */}
            <div aria-hidden="true" className="absolute inset-0 w-full h-full bg-transparent pointer-events-none z-0">
              <DNAHelixCanvas />
            </div>

            {/* Deep Ambient Vignette Gradients & Radial Fog */}
            <div className="absolute inset-0 pointer-events-none z-[1] bg-gradient-to-t from-background-canvas via-transparent to-background-canvas/60"></div>
            <div className="absolute -top-40 right-1/4 w-[600px] h-[600px] bg-accent-chroma/10 rounded-full blur-[160px] pointer-events-none z-[1]"></div>
            <div className="absolute bottom-10 left-1/3 w-[500px] h-[500px] bg-secondary-container/15 rounded-full blur-[140px] pointer-events-none z-[1]"></div>

            {/* Main Content Container: Asymmetric Hero Grid */}
            <div className="relative z-10 w-full max-w-[1440px] mx-auto px-6 lg:px-margin-lg pt-12 lg:pt-20 flex-1 grid grid-cols-1 lg:grid-cols-12 gap-8 items-center">
              {/* Left Column: Editorial Typography & Navigation Directives */}
              <div className="lg:col-span-7 flex flex-col items-start space-y-6 lg:pr-8">
                {/* Eyebrow Badge */}
                <div className="inline-flex items-center gap-2.5 px-3.5 py-1.5 rounded-full bg-surface-container/70 shadow-sm backdrop-blur-md border border-glass-border">
                  <span className="w-1.5 h-1.5 rounded-full bg-text-primary animate-ping"></span>
                  <span className="w-1.5 h-1.5 rounded-full bg-text-primary -ml-4"></span>
                  <span className="font-label-code text-label-code uppercase tracking-[0.22em] text-text-highlight font-medium">
                    INTELLIGENT HEALTHCARE EXPERIENCE
                  </span>
                </div>

                {/* Master Headline */}
                <h1 className="font-display-hero text-headline-lg lg:text-display-hero text-text-primary tracking-[-0.035em] leading-[1.08] font-light max-w-2xl drop-shadow-[0_4px_30px_rgba(0,0,0,0.8)]">
                  Healthcare, Made More <span className="font-normal italic text-primary">Understandable.</span>
                </h1>

                {/* High-Register Editorial Subtitle */}
                <p className="font-body-lg text-body-md lg:text-body-lg text-on-surface-variant max-w-xl font-normal leading-relaxed tracking-normal">
                  Meet MedAssist AI — a healthcare assistant for understanding medical reports, exploring health information, and discussing complex details in plain language.
                </p>

                {/* Call to Action Cluster */}
                <div className="flex flex-wrap items-center gap-5 pt-3">
                  <NavigationLoadingLink
                    className="group relative inline-flex items-center justify-center px-8 py-3.5 rounded-full bg-primary text-on-primary font-body-md text-body-md font-medium tracking-wide shadow-xl transition-all duration-300 hover:scale-[1.02] hover:bg-white hover:shadow-[0_0_36px_rgba(206,204,220,0.35)]"
                    href="/dashboard"
                  >
                    <span className="relative z-10 flex items-center gap-2">
                      Start Program
                      <span className="material-symbols-outlined text-[18px] transition-transform duration-200 group-hover:translate-x-0.5">
                        arrow_forward
                      </span>
                    </span>
                    <div className="absolute inset-0 rounded-full bg-gradient-to-r from-transparent via-white/40 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500 blur-sm"></div>
                  </NavigationLoadingLink>

                  <Link
                    className="inline-flex items-center gap-2.5 px-6 py-3.5 rounded-full bg-surface-container-high/40 hover:bg-surface-container-highest/60 text-text-primary font-body-md text-body-md font-normal tracking-wide backdrop-blur-md shadow-sm border border-glass-border transition-all duration-200 group"
                    href="/procedures"
                  >
                    <span>Explore Procedures</span>
                    <span className="material-symbols-outlined text-[18px] text-text-highlight group-hover:translate-x-1 transition-transform duration-200">
                      north_east
                    </span>
                  </Link>
                </div>
              </div>

              {/* Right Column: Animated DNA visual */}
              <div className="lg:col-span-5 relative w-full h-[460px] lg:h-[580px] pointer-events-none flex items-center justify-center">
              </div>
            </div>

            {/* Bottom Horizontal Statistics & Capability Dock */}
            <div className="relative z-20 w-full max-w-[1440px] mx-auto px-6 lg:px-margin-lg pb-10 pt-6">
              <div className="w-full rounded-2xl bg-surface-container-lowest/85 backdrop-blur-2xl p-3 lg:p-4 shadow-[0_20px_50px_rgba(0,0,0,0.9)] border border-glass-border">
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 lg:gap-8 items-center divide-y sm:divide-y-0 lg:divide-x divide-surface-container-highest">
                  {/* Stat 1 */}
                  <div className="flex items-center gap-4 lg:px-4 first:pl-0">
                    <div className="w-10 h-10 rounded-full bg-surface-container-high/80 flex items-center justify-center flex-shrink-0 shadow-sm border border-glass-border">
                      <span className="w-2.5 h-2.5 rounded-full bg-primary shadow-[0_0_10px_rgba(234,232,249,0.9)] animate-pulse"></span>
                    </div>
                    <div className="min-w-0">
                      <h3 className="font-headline-sm text-body-md text-primary font-medium truncate">
                        AI-Powered Analysis
                      </h3>
                      <p className="font-body-sm text-caption text-surface-muted truncate mt-0.5">
                        Grounded answers from your reports
                      </p>
                    </div>
                  </div>

                  {/* Stat 2 */}
                  <div className="flex items-center gap-4 pt-4 sm:pt-0 lg:px-6">
                    <div className="w-10 h-10 rounded-full bg-surface-container-high/80 flex items-center justify-center flex-shrink-0 shadow-sm border border-glass-border">
                      <span className="material-symbols-outlined text-[20px] text-text-primary">folder_open</span>
                    </div>
                    <div className="min-w-0">
                      <h3 className="font-headline-sm text-body-md text-primary font-medium truncate">
                        Medical Report Support
                      </h3>
                      <p className="font-body-sm text-caption text-surface-muted truncate mt-0.5">
                        PDF, PNG, JPG &amp; WEBP reports
                      </p>
                    </div>
                  </div>

                  {/* Stat 3 */}
                  <div className="flex items-center gap-4 pt-4 sm:pt-0 lg:px-6">
                    <div className="w-10 h-10 rounded-full bg-surface-container-high/80 flex items-center justify-center flex-shrink-0 shadow-sm border border-glass-border">
                      <span className="material-symbols-outlined text-[20px] text-text-primary">translate</span>
                    </div>
                    <div className="min-w-0">
                      <h3 className="font-headline-sm text-body-md text-primary font-medium truncate">
                        Multilingual Assistance
                      </h3>
                      <p className="font-body-sm text-caption text-surface-muted truncate mt-0.5">
                        English, Kannada &amp; bilingual
                      </p>
                    </div>
                  </div>

                  {/* Stat 4 */}
                  <div className="flex items-center gap-4 pt-4 sm:pt-0 lg:px-6 last:pr-0">
                    <div className="w-10 h-10 rounded-full bg-surface-container-high/80 flex items-center justify-center flex-shrink-0 shadow-sm border border-glass-border">
                      <span className="material-symbols-outlined text-[20px] text-text-primary">format_image_left</span>
                    </div>
                    <div className="min-w-0">
                      <h3 className="font-headline-sm text-body-md text-primary font-medium truncate">
                        Intelligent Insights
                      </h3>
                      <p className="font-body-sm text-caption text-surface-muted truncate mt-0.5">
                        Zero-Hallucination Guardrails
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>

      <PublicFooter />
    </div>
  );
}
