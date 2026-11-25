"use client";

import Link from "next/link";
import { PublicHeader } from "@/components/public-header";
import { PublicFooter } from "@/components/public-footer";
import { NavigationLoadingLink } from "@/components/navigation-loading-link";

export default function ProceduresPage() {
  return (
    <div className="bg-background-canvas text-on-surface font-body-md text-body-md antialiased min-h-screen relative overflow-x-hidden">
      {/* Ambient background glows */}
      <div className="pointer-events-none fixed top-0 right-1/4 -z-10 h-96 w-96 rounded-full bg-accent-chroma/15 blur-[128px]"></div>
      <div className="pointer-events-none fixed bottom-1/3 left-10 -z-10 h-80 w-80 rounded-full bg-secondary-container/20 blur-[140px]"></div>

      <PublicHeader />

      <main className="w-full pt-20 bg-background-canvas min-h-[calc(100vh-200px)]">
        <div className="flex flex-col w-full">
          {/* Top Ambient Glow Accent */}
          <div className="relative w-full max-w-[1440px] mx-auto px-6 lg:px-margin-lg pt-12 pb-24 overflow-hidden">
            {/* Atmospheric subtle background glow */}
            <div className="pointer-events-none absolute -top-24 left-1/2 -translate-x-1/2 w-[700px] h-[350px] bg-accent-chroma/10 blur-[130px] rounded-full"></div>

            {/* Editorial Header Section */}
            <header className="relative z-10 flex flex-col max-w-4xl mx-auto text-center items-center">
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-surface-container/80 backdrop-blur-md mb-6 shadow-sm border border-glass-border">
                <span className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse"></span>
                <span className="font-caption text-caption uppercase tracking-[0.22em] text-text-highlight">
                  System Telemetry &amp; Protocol
                </span>
              </div>
              <h1 className="font-display-hero text-display-hero text-primary tracking-[-0.03em] font-light mb-4">
                How It Works
              </h1>
              <p className="font-headline-sm text-headline-sm text-text-highlight font-normal tracking-tight mb-4">
                The MedAssist AI Clinical Workflow
              </p>
              <p className="font-body-lg text-body-lg text-on-surface-variant max-w-2xl font-light leading-relaxed">
                An end-to-end intelligent pipeline translating complex diagnostics into structured, patient-accessible clarity.
              </p>
            </header>

            {/* Master Editorial Timeline */}
            <div className="relative z-10 mt-20 max-w-5xl mx-auto">
              {/* Fine Silver Spine Connecting Line */}
              <div className="absolute left-6 md:left-1/2 top-4 bottom-12 w-[1px] -translate-x-1/2 bg-gradient-to-b from-primary/30 via-accent-chroma/40 to-transparent"></div>

              {/* STEP 01 */}
              <section className="relative flex flex-col md:flex-row items-start mb-20 group">
                {/* Center Timeline Node Badge */}
                <div className="absolute left-6 md:left-1/2 -translate-x-1/2 flex items-center justify-center w-12 h-12 rounded-full bg-surface-container-lowest border border-glass-border backdrop-blur-md shadow-lg z-20 transition-transform duration-300 group-hover:scale-110">
                  <span className="font-label-code text-label-code text-primary font-semibold tracking-wider">01</span>
                </div>
                {/* Left Column: Content Card */}
                <div className="w-full md:w-[calc(50%-3rem)] pl-16 md:pl-0 md:pr-4">
                  <div className="p-6 md:p-8 rounded-xl bg-surface-container/70 border border-glass-border backdrop-blur-2xl shadow-xl transition-all duration-300 hover:bg-surface-container-high/80">
                    <div className="flex items-center justify-between gap-4 mb-4">
                      <span className="font-label-code text-label-code uppercase tracking-[0.18em] text-accent-chroma">
                        Ingestion Phase
                      </span>
                      <span className="material-symbols-outlined text-primary text-[20px]">cloud_upload</span>
                    </div>
                    <h2 className="font-headline-md text-headline-md text-primary font-normal tracking-tight mb-3">
                      Upload a medical report
                    </h2>
                    <p className="font-body-md text-body-md text-on-surface-variant font-light leading-relaxed mb-5">
                      Upload laboratory reports, prescriptions, discharge summaries, and other medical documents as PDFs or images.
                    </p>
                    <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg bg-surface-container-lowest/80 border border-glass-border text-text-highlight">
                      <span className="w-1.5 h-1.5 rounded-full bg-secondary"></span>
                      <span className="font-label-code text-label-code text-on-surface-variant">
                        Supports PDF, PNG, JPG, JPEG, and WEBP uploads.
                      </span>
                    </div>
                  </div>
                </div>
                {/* Right Column: Visual Instrument */}
                <div className="hidden md:flex w-[calc(50%-3rem)] ml-auto pl-4 items-center">
                  <div className="w-full p-5 rounded-xl bg-surface-container-lowest/70 border border-glass-border backdrop-blur-md shadow-md">
                    <div className="flex items-center justify-between mb-3 text-caption font-caption text-surface-muted uppercase tracking-[0.14em]">
                      <span>Report upload</span>
                      <span>Illustrative preview</span>
                    </div>
                    <div className="flex items-center gap-3 p-3 rounded-lg bg-surface-container/50 border border-glass-border">
                      <span className="material-symbols-outlined text-text-highlight text-[28px]">description</span>
                      <div className="flex flex-col min-w-0 flex-1">
                        <span className="font-body-sm text-body-sm text-primary font-medium truncate">
                          example-lab-report.pdf
                        </span>
                        <span className="font-caption text-caption text-surface-muted">
                          File name and size appear after upload
                        </span>
                      </div>
                      <span className="material-symbols-outlined text-primary text-[20px]">check_circle</span>
                    </div>
                  </div>
                </div>
              </section>

              {/* STEP 02 */}
              <section className="relative flex flex-col md:flex-row items-start mb-20 group">
                <div className="absolute left-6 md:left-1/2 -translate-x-1/2 flex items-center justify-center w-12 h-12 rounded-full bg-surface-container-lowest border border-glass-border backdrop-blur-md shadow-lg z-20 transition-transform duration-300 group-hover:scale-110">
                  <span className="font-label-code text-label-code text-primary font-semibold tracking-wider">02</span>
                </div>
                {/* Left Column: Visual Instrument */}
                <div className="hidden md:flex w-[calc(50%-3rem)] pr-4 items-center">
                  <div className="w-full p-5 rounded-xl bg-surface-container-lowest/70 border border-glass-border backdrop-blur-md shadow-md">
                    <div className="flex items-center justify-between mb-3 text-caption font-caption text-surface-muted uppercase tracking-[0.14em]">
                      <span>Extracted report fields</span>
                      <span>Illustrative examples</span>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <div className="px-2.5 py-1 rounded bg-surface-container text-primary font-label-code text-label-code flex items-center gap-1.5 border border-glass-border">
                        <span className="w-1.5 h-1.5 rounded-full bg-accent-chroma"></span>
                        <span>Test results</span>
                      </div>
                      <div className="px-2.5 py-1 rounded bg-surface-container text-primary font-label-code text-label-code flex items-center gap-1.5 border border-glass-border">
                        <span className="w-1.5 h-1.5 rounded-full bg-accent-chroma"></span>
                        <span>Medication list</span>
                      </div>
                      <div className="px-2.5 py-1 rounded bg-surface-container text-primary font-label-code text-label-code flex items-center gap-1.5 border border-glass-border">
                        <span className="w-1.5 h-1.5 rounded-full bg-accent-chroma"></span>
                        <span>Diagnosis</span>
                      </div>
                      <div className="px-2.5 py-1 rounded bg-surface-container text-primary font-label-code text-label-code flex items-center gap-1.5 border border-glass-border">
                        <span className="w-1.5 h-1.5 rounded-full bg-accent-chroma"></span>
                        <span>Recommendations</span>
                      </div>
                    </div>
                  </div>
                </div>
                {/* Right Column: Content Card */}
                <div className="w-full md:w-[calc(50%-3rem)] pl-16 md:pl-4 ml-auto">
                  <div className="p-6 md:p-8 rounded-xl bg-surface-container/70 border border-glass-border backdrop-blur-2xl shadow-xl transition-all duration-300 hover:bg-surface-container-high/80">
                    <div className="flex items-center justify-between gap-4 mb-4">
                      <span className="font-label-code text-label-code uppercase tracking-[0.18em] text-accent-chroma">
                        Semantic Extraction
                      </span>
                      <span className="material-symbols-outlined text-primary text-[20px]">neurology</span>
                    </div>
                    <h2 className="font-headline-md text-headline-md text-primary font-normal tracking-tight mb-3">
                      Extract relevant medical information
                    </h2>
                    <p className="font-body-md text-body-md text-on-surface-variant font-light leading-relaxed mb-5">
                      Neural entity recognition parses key lab biomarkers, dosage intervals, and diagnostic impressions into distinct computational nodes.
                    </p>
                    <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg bg-surface-container-lowest/80 border border-glass-border text-text-highlight">
                      <span className="w-1.5 h-1.5 rounded-full bg-secondary"></span>
                      <span className="font-label-code text-label-code text-on-surface-variant">
                        Ontology alignment via SNOMED CT and LOINC standards.
                      </span>
                    </div>
                  </div>
                </div>
              </section>

              {/* STEP 03 */}
              <section className="relative flex flex-col md:flex-row items-start mb-20 group">
                <div className="absolute left-6 md:left-1/2 -translate-x-1/2 flex items-center justify-center w-12 h-12 rounded-full bg-surface-container-lowest border border-glass-border backdrop-blur-md shadow-lg z-20 transition-transform duration-300 group-hover:scale-110">
                  <span className="font-label-code text-label-code text-primary font-semibold tracking-wider">03</span>
                </div>
                {/* Left Column: Content Card */}
                <div className="w-full md:w-[calc(50%-3rem)] pl-16 md:pl-0 md:pr-4">
                  <div className="p-6 md:p-8 rounded-xl bg-surface-container/70 border border-glass-border backdrop-blur-2xl shadow-xl transition-all duration-300 hover:bg-surface-container-high/80">
                    <div className="flex items-center justify-between gap-4 mb-4">
                      <span className="font-label-code text-label-code uppercase tracking-[0.18em] text-accent-chroma">
                        Contextual Synthesis
                      </span>
                      <span className="material-symbols-outlined text-primary text-[20px]">biotech</span>
                    </div>
                    <h2 className="font-headline-md text-headline-md text-primary font-normal tracking-tight mb-3">
                      Analyze the available medical context
                    </h2>
                    <p className="font-body-md text-body-md text-on-surface-variant font-light leading-relaxed mb-5">
                      Organizes the uploaded report context and conversation history to help answer a user’s question.
                    </p>
                    <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg bg-surface-container-lowest/80 border border-glass-border text-text-highlight">
                      <span className="w-1.5 h-1.5 rounded-full bg-secondary"></span>
                      <span className="font-label-code text-label-code text-on-surface-variant">
                        Uses available report context when relevant.
                      </span>
                    </div>
                  </div>
                </div>
                {/* Right Column: Visual Instrument */}
                <div className="hidden md:flex w-[calc(50%-3rem)] ml-auto pl-4 items-center">
                  <div className="w-full p-5 rounded-xl bg-surface-container-lowest/70 border border-glass-border backdrop-blur-md shadow-md">
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-caption text-caption text-surface-muted uppercase tracking-[0.14em]">
                        Example conversation context
                      </span>
                      <span className="font-label-code text-label-code text-text-highlight">Illustrative workflow</span>
                    </div>
                    <svg className="w-full h-20 text-accent-chroma" fill="none" viewBox="0 0 320 80">
                      <path d="M0 60 C40 60, 60 25, 100 25 C140 25, 160 55, 200 45 C240 35, 270 15, 320 18" stroke="currentColor" strokeLinecap="round" strokeWidth="1.5"></path>
                      <circle cx="100" cy="25" fill="#eae8f9" r="3"></circle>
                      <circle cx="200" cy="45" fill="#eae8f9" r="3"></circle>
                      <line stroke="currentColor" strokeDasharray="4 4" strokeOpacity="0.15" x1="0" x2="320" y1="70" y2="70"></line>
                    </svg>
                    <div className="flex justify-between items-center text-caption font-caption text-surface-muted mt-1">
                      <span>Earlier report</span>
                      <span className="text-primary font-medium">Current conversation</span>
                      <span>New results</span>
                    </div>
                  </div>
                </div>
              </section>

              {/* STEP 04 */}
              <section className="relative flex flex-col md:flex-row items-start mb-20 group">
                <div className="absolute left-6 md:left-1/2 -translate-x-1/2 flex items-center justify-center w-12 h-12 rounded-full bg-surface-container-lowest border border-glass-border backdrop-blur-md shadow-lg z-20 transition-transform duration-300 group-hover:scale-110">
                  <span className="font-label-code text-label-code text-primary font-semibold tracking-wider">04</span>
                </div>
                {/* Left Column: Visual Instrument */}
                <div className="hidden md:flex w-[calc(50%-3rem)] pr-4 items-center">
                  <div className="w-full p-5 rounded-xl bg-surface-container-lowest/70 border border-glass-border backdrop-blur-md shadow-md space-y-3">
                    <div className="flex items-center justify-between text-caption font-caption text-surface-muted uppercase tracking-[0.14em]">
                      <span>Example explanation</span>
                      <span className="text-primary">Illustrative only</span>
                    </div>
                    <div className="p-3 rounded-lg bg-surface-container/40 border border-glass-border">
                      <span className="text-caption font-caption uppercase tracking-wider text-surface-muted block mb-1">
                        Example clinical wording
                      </span>
                      <p className="font-label-code text-label-code text-text-highlight">
                        &quot;Unremarkable parenchyma without focal consolidation or pleural effusion.&quot;
                      </p>
                    </div>
                    <div className="p-3 rounded-lg bg-surface-secondary/30 border border-glass-border">
                      <span className="text-caption font-caption uppercase tracking-wider text-accent-chroma block mb-1">
                        Example plain-language explanation
                      </span>
                      <p className="font-body-sm text-body-sm text-primary">
                        Your lung tissue appears completely healthy with no fluid accumulation or infection.
                      </p>
                    </div>
                  </div>
                </div>
                {/* Right Column: Content Card */}
                <div className="w-full md:w-[calc(50%-3rem)] pl-16 md:pl-4 ml-auto">
                  <div className="p-6 md:p-8 rounded-xl bg-surface-container/70 border border-glass-border backdrop-blur-2xl shadow-xl transition-all duration-300 hover:bg-surface-container-high/80">
                    <div className="flex items-center justify-between gap-4 mb-4">
                      <span className="font-label-code text-label-code uppercase tracking-[0.18em] text-accent-chroma">
                        Plain-language explanation
                      </span>
                      <span className="material-symbols-outlined text-primary text-[20px]">psychology_alt</span>
                    </div>
                    <h2 className="font-headline-md text-headline-md text-primary font-normal tracking-tight mb-3">
                      Understand important findings
                    </h2>
                    <p className="font-body-md text-body-md text-on-surface-variant font-light leading-relaxed mb-5">
                      Synthesizes critical diagnostic findings into plain-language summaries with highlighted definitions, removing clinical obfuscation.
                    </p>
                    <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg bg-surface-container-lowest/80 border border-glass-border text-text-highlight">
                      <span className="w-1.5 h-1.5 rounded-full bg-secondary"></span>
                      <span className="font-label-code text-label-code text-on-surface-variant">
                        Clearer explanations while preserving the report’s meaning.
                      </span>
                    </div>
                  </div>
                </div>
              </section>

              {/* STEP 05 */}
              <section className="relative flex flex-col md:flex-row items-start group">
                <div className="absolute left-6 md:left-1/2 -translate-x-1/2 flex items-center justify-center w-12 h-12 rounded-full bg-surface-container-lowest border border-glass-border backdrop-blur-md shadow-lg z-20 transition-transform duration-300 group-hover:scale-110">
                  <span className="font-label-code text-label-code text-primary font-semibold tracking-wider">05</span>
                </div>
                {/* Left Column: Content Card */}
                <div className="w-full md:w-[calc(50%-3rem)] pl-16 md:pl-0 md:pr-4">
                  <div className="p-6 md:p-8 rounded-xl bg-surface-container/70 border border-glass-border backdrop-blur-2xl shadow-xl transition-all duration-300 hover:bg-surface-container-high/80">
                    <div className="flex items-center justify-between gap-4 mb-4">
                      <span className="font-label-code text-label-code uppercase tracking-[0.18em] text-accent-chroma">
                        Consultation Empowerment
                      </span>
                      <span className="material-symbols-outlined text-primary text-[20px]">stethoscope</span>
                    </div>
                    <h2 className="font-headline-md text-headline-md text-primary font-normal tracking-tight mb-3">
                      Explore relevant healthcare guidance
                    </h2>
                    <p className="font-body-md text-body-md text-on-surface-variant font-light leading-relaxed mb-5">
                      Formulates evidence-based questions for your physician and actionable lifestyle considerations based on parsed diagnostics.
                    </p>
                    <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg bg-surface-container-lowest/80 border border-glass-border text-text-highlight">
                      <span className="w-1.5 h-1.5 rounded-full bg-secondary"></span>
                      <span className="font-label-code text-label-code text-on-surface-variant">
                        Prepares printable clinical brief for your physician.
                      </span>
                    </div>
                  </div>
                </div>
                {/* Right Column: Visual Instrument */}
                <div className="hidden md:flex w-[calc(50%-3rem)] ml-auto pl-4 items-center">
                  <div className="w-full p-5 rounded-xl bg-surface-container-lowest/70 border border-glass-border backdrop-blur-md shadow-md space-y-3">
                    <div className="flex items-center justify-between text-caption font-caption text-surface-muted uppercase tracking-[0.14em]">
                      <span>Physician Inquiry Docket</span>
                      <span className="text-text-highlight">3 Actionable Prompts</span>
                    </div>
                    <div className="flex items-start gap-2.5 p-3 rounded-lg bg-surface-container/50 border border-glass-border">
                      <span className="material-symbols-outlined text-text-highlight text-[18px] mt-0.5">help</span>
                      <p className="font-body-sm text-body-sm text-primary font-light">
                        &quot;How does the elevated serum ferritin influence our current iron supplementation plan?&quot;
                      </p>
                    </div>
                    <div className="flex items-start gap-2.5 p-3 rounded-lg bg-surface-container/50 border border-glass-border">
                      <span className="material-symbols-outlined text-text-highlight text-[18px] mt-0.5">event_repeat</span>
                      <p className="font-body-sm text-body-sm text-primary font-light">
                        &quot;Should we schedule a follow-up lipid fraction panel in 90 or 180 days?&quot;
                      </p>
                    </div>
                  </div>
                </div>
              </section>
            </div>

            {/* Editorial Clinical Assurance Callout */}
            <div className="relative z-10 mt-28 max-w-4xl mx-auto p-8 rounded-2xl bg-surface-container-lowest/80 border border-glass-border backdrop-blur-2xl shadow-2xl flex flex-col md:flex-row items-center justify-between gap-8">
              <div className="flex flex-col max-w-xl">
                <div className="flex items-center gap-2 mb-2">
                  <span className="material-symbols-outlined text-primary text-[20px]">verified_user</span>
                  <span className="font-caption text-caption uppercase tracking-[0.2em] text-text-highlight">
                    Report and conversation management
                  </span>
                </div>
                <h3 className="font-headline-sm text-headline-sm text-primary font-normal tracking-tight mb-2">
                  Reports stay linked to their conversation.
                </h3>
                <p className="font-body-sm text-body-sm text-on-surface-variant font-light leading-relaxed">
                  Uploaded reports and conversations are stored for the features you use. Manage your reports and remove conversations from your account when you no longer need them.
                </p>
              </div>
              <div className="flex flex-col sm:flex-row items-center gap-4 w-full md:w-auto">
                <NavigationLoadingLink
                  className="w-full sm:w-auto px-8 py-3 rounded-full bg-primary-container text-on-primary font-body-sm text-body-sm font-medium tracking-wide text-center transition-all duration-300 shadow-[0_0_24px_rgba(206,204,220,0.22)] hover:bg-primary hover:shadow-[0_0_32px_rgba(206,204,220,0.45)]"
                  href="/dashboard"
                >
                  Begin Assessment
                </NavigationLoadingLink>
              </div>
            </div>
          </div>
        </div>
      </main>

      <PublicFooter />
    </div>
  );
}
