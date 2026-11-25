"use client";

import Link from "next/link";
import { PublicHeader } from "@/components/public-header";
import { PublicFooter } from "@/components/public-footer";
import { NavigationLoadingLink } from "@/components/navigation-loading-link";

export default function AboutUsPage() {
  return (
    <div className="bg-background-canvas text-on-surface font-body-md text-body-md antialiased min-h-screen relative overflow-x-hidden">
      {/* Ambient background glows */}
      <div className="pointer-events-none fixed top-0 right-1/4 -z-10 h-96 w-96 rounded-full bg-accent-chroma/15 blur-[128px]"></div>
      <div className="pointer-events-none fixed bottom-1/3 left-10 -z-10 h-80 w-80 rounded-full bg-secondary-container/20 blur-[140px]"></div>

      <PublicHeader />

      <main className="w-full pt-24 bg-background-canvas min-h-[calc(100vh-200px)]">
        <div className="flex flex-col w-full">
          {/* Top Atmospheric Gradient Canvas */}
          <div className="relative w-full max-w-[1440px] mx-auto px-6 lg:px-margin-lg pt-12 pb-24 overflow-hidden">
            {/* Subtle Background Glow */}
            <div className="absolute -top-32 left-1/2 -translate-x-1/2 w-[720px] h-[340px] bg-accent-chroma/10 rounded-full blur-[140px] pointer-events-none -z-10"></div>

            {/* Hero / Header Section */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-gutter-lg items-end mb-space-2xl p-8 lg:p-12 rounded-2xl bg-surface-container-low/70 backdrop-blur-xl border border-glass-border shadow-2xl relative">
              <div className="lg:col-span-8 flex flex-col space-y-space-md">
                {/* Eyebrow Pill */}
                <div className="inline-flex items-center gap-3 w-fit px-3 py-1.5 rounded-full bg-surface-secondary/40 border border-glass-border backdrop-blur-md">
                  <span className="w-1.5 h-1.5 rounded-full bg-primary animate-ping"></span>
                  <span className="font-label-code text-label-code uppercase tracking-[0.2em] text-text-highlight">
                    ABOUT MEDASSIST AI
                  </span>
                  <span className="text-caption font-caption text-surface-muted">|</span>
                  <span className="font-label-code text-label-code text-surface-muted">GEN-SYS 4.8.1</span>
                </div>
                {/* Main Display Heading */}
                <h1 className="font-display-hero text-display-hero text-primary tracking-tight max-w-4xl">
                  Healthcare Intelligence, Reimagined
                </h1>
              </div>
              <div className="lg:col-span-4 flex flex-col justify-end">
                <p className="font-body-lg text-body-lg text-on-surface-variant leading-relaxed">
                  MedAssist AI helps people understand medical reports and healthcare information through intelligent AI-powered assistance.
                </p>
                <div className="flex items-center gap-4 mt-6">
                  <div className="h-[1px] w-12 bg-surface-muted"></div>
                  <span className="font-caption text-caption uppercase tracking-[0.18em] text-surface-muted">
                    MEDICAL REPORT Q&amp;A
                  </span>
                </div>
              </div>
            </div>

            {/* Editorial Manifesto Statement */}
            <div className="relative my-24 lg:my-32 max-w-5xl mx-auto text-center px-4">
              <div className="inline-flex items-center justify-center p-3 rounded-full bg-surface-secondary/30 border border-glass-border mb-8">
                <span className="material-symbols-outlined text-[24px] text-text-highlight">neurology</span>
              </div>
              <p className="font-headline-md text-headline-md lg:font-headline-lg lg:text-headline-lg text-primary font-light leading-snug tracking-tight">
                “Transforming dense clinical records into lucid, patient-empowered clarity.”
              </p>
              <div className="mt-8 flex items-center justify-center gap-3">
                <span className="h-[1px] w-8 bg-surface-muted"></span>
                <span className="font-label-code text-label-code uppercase tracking-[0.25em] text-text-highlight">
                  THE CORE MANDATE
                </span>
                <span className="h-[1px] w-8 bg-surface-muted"></span>
              </div>
            </div>

            {/* The 3 Foundational Pillars */}
            <div className="mb-space-2xl">
              <div className="flex flex-col md:flex-row md:items-end justify-between mb-12">
                <div>
                  <span className="font-label-code text-label-code uppercase tracking-[0.2em] text-text-highlight">
                    PILLARS OF REASONING
                  </span>
                  <h2 className="font-headline-lg text-headline-lg text-primary mt-2">
                    Designed for clearer medical conversations
                  </h2>
                </div>
                <p className="font-body-md text-body-md text-on-surface-variant max-w-md mt-4 md:mt-0">
                  Ask questions about uploaded reports, review source citations when available, and keep each conversation organized by session.
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                {/* Pillar 1 */}
                <div className="group relative rounded-xl bg-surface-container-low/70 border border-glass-border backdrop-blur-2xl p-8 flex flex-col justify-between transition-all duration-300 hover:bg-surface-container/80 shadow-lg">
                  <div className="absolute top-0 right-0 w-32 h-32 bg-accent-chroma/10 rounded-full blur-2xl pointer-events-none"></div>
                  <div>
                    <div className="flex items-center justify-between mb-8">
                      <span className="font-label-code text-label-code text-surface-muted uppercase tracking-[0.16em]">
                        PILLAR 01
                      </span>
                      <div className="w-10 h-10 rounded-full bg-surface-secondary/50 flex items-center justify-center text-primary group-hover:scale-110 transition-transform">
                        <span className="material-symbols-outlined text-[20px]">translate</span>
                      </div>
                    </div>
                    <h3 className="font-headline-sm text-headline-sm text-primary mb-4">
                      Clinical Contextualization
                    </h3>
                    <p className="font-body-md text-body-md text-on-surface-variant leading-relaxed">
                      Ask about report terminology, results, medicines, and recommendations in plain language. Responses can use the report context attached to the current conversation.
                    </p>
                  </div>

                  {/* Micro Visual Element: Reference Range Sparkline */}
                  <div className="mt-8 pt-6 bg-surface-container-lowest/60 border border-glass-border rounded-lg p-4">
                    <div className="flex justify-between items-center mb-2">
                      <span className="font-label-code text-label-code text-text-highlight">REPORT VALUES</span>
                      <span className="font-label-code text-label-code text-primary">ILLUSTRATIVE</span>
                    </div>
                    <svg className="w-full h-10 text-primary-container" fill="none" viewBox="0 0 200 40">
                      <rect fill="currentColor" fillOpacity="0.15" height="4" rx="2" width="140" x="30" y="18"></rect>
                      <rect fill="currentColor" fillOpacity="0.5" height="4" rx="2" width="70" x="60" y="18"></rect>
                      <circle cx="108" cy="20" fill="#EAE8F9" r="5"></circle>
                      <line stroke="#EAE8F9" strokeDasharray="2 2" strokeWidth="1.5" x1="108" x2="108" y1="6" y2="34"></line>
                    </svg>
                    <div className="flex justify-between font-caption text-caption text-surface-muted mt-1">
                      <span>Reference range</span>
                      <span className="text-text-highlight font-medium">From report</span>
                      <span>Result</span>
                    </div>
                  </div>
                </div>

                {/* Pillar 2 */}
                <div className="group relative rounded-xl bg-surface-container-low/70 border border-glass-border backdrop-blur-2xl p-8 flex flex-col justify-between transition-all duration-300 hover:bg-surface-container/80 shadow-lg">
                  <div className="absolute top-0 right-0 w-32 h-32 bg-secondary-container/20 rounded-full blur-2xl pointer-events-none"></div>
                  <div>
                    <div className="flex items-center justify-between mb-8">
                      <span className="font-label-code text-label-code text-surface-muted uppercase tracking-[0.16em]">
                        PILLAR 02
                      </span>
                      <div className="w-10 h-10 rounded-full bg-surface-secondary/50 flex items-center justify-center text-primary group-hover:scale-110 transition-transform">
                        <span className="material-symbols-outlined text-[20px]">verified_user</span>
                      </div>
                    </div>
                    <h3 className="font-headline-sm text-headline-sm text-primary mb-4">
                      Precision Safety Guardrails
                    </h3>
                    <p className="font-body-md text-body-md text-on-surface-variant leading-relaxed">
                      When an answer uses report text, the interface can show the source report and relevant section. General health information is not a substitute for professional medical advice.
                    </p>
                  </div>

                  {/* Micro Visual Element: Grounded Verification Vector */}
                  <div className="mt-8 pt-6 bg-surface-container-lowest/60 border border-glass-border rounded-lg p-4">
                    <div className="flex justify-between items-center mb-2">
                      <span className="font-label-code text-label-code text-text-highlight">SOURCE ATTRIBUTION</span>
                      <span className="font-label-code text-label-code text-primary">WHEN AVAILABLE</span>
                    </div>
                    <div className="flex flex-col gap-1.5 font-label-code text-label-code">
                      <div className="flex items-center justify-between p-1.5 rounded bg-surface-container-high/40 text-on-surface-variant">
                        <span className="truncate max-w-[170px]">Uploaded report</span>
                        <span className="text-primary font-medium">SOURCE</span>
                      </div>
                      <div className="flex items-center justify-between p-1.5 rounded bg-surface-container-high/40 text-on-surface-variant">
                        <span className="truncate max-w-[170px]">Relevant section</span>
                        <span className="text-primary font-medium">CITATION</span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Pillar 3 */}
                <div id="data-management" className="group relative rounded-xl bg-surface-container-low/70 border border-glass-border backdrop-blur-2xl p-8 flex flex-col justify-between transition-all duration-300 hover:bg-surface-container/80 shadow-lg">
                  <div className="absolute top-0 right-0 w-32 h-32 bg-accent-chroma/15 rounded-full blur-2xl pointer-events-none"></div>
                  <div>
                    <div className="flex items-center justify-between mb-8">
                      <span className="font-label-code text-label-code text-surface-muted uppercase tracking-[0.16em]">
                        PILLAR 03
                      </span>
                      <div className="w-10 h-10 rounded-full bg-surface-secondary/50 flex items-center justify-center text-primary group-hover:scale-110 transition-transform">
                        <span className="material-symbols-outlined text-[20px]">enhanced_encryption</span>
                      </div>
                    </div>
                    <h3 className="font-headline-sm text-headline-sm text-primary mb-4">
                      Conversation-scoped reports
                    </h3>
                    <p className="font-body-md text-body-md text-on-surface-variant leading-relaxed">
                      Reports are associated with the conversation where they were uploaded. Use the report controls to preview, download, retry processing, or delete a report.
                    </p>
                  </div>

                  {/* Micro Visual Element: Encryption Key State */}
                  <div className="mt-8 pt-6 bg-surface-container-lowest/60 border border-glass-border rounded-lg p-4">
                    <div className="flex justify-between items-center mb-2">
                      <span className="font-label-code text-label-code text-text-highlight">REPORT STORAGE</span>
                      <span className="font-label-code text-label-code text-primary">ACCOUNT LINKED</span>
                    </div>
                    <div className="w-full bg-surface-secondary/50 h-2 rounded-full overflow-hidden flex">
                      <div className="bg-primary h-full w-full animate-pulse"></div>
                    </div>
                    <div className="flex justify-between items-center mt-2 font-caption text-caption text-surface-muted">
                      <span>CONVERSATION SCOPE</span>
                      <span className="text-text-highlight">USER MANAGED</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Editorial Deep Dive: The Science of Clarity */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-gutter-lg items-center my-space-2xl py-12">
              <div className="lg:col-span-5 relative">
                <div className="relative w-full aspect-square rounded-2xl overflow-hidden bg-surface-container-low shadow-2xl border border-glass-border">
                  <div
                    className="w-full h-full bg-cover bg-center"
                    style={{ backgroundImage: "url('/scientist.png')" }}
                  >
                    <div className="absolute inset-0 bg-gradient-to-tr from-background-canvas via-transparent to-surface-secondary/30"></div>
                  </div>
                </div>
                {/* Overlapping Diagnostic Badge */}
                <div className="absolute -bottom-6 -right-6 p-6 rounded-xl bg-surface-container-high/90 border border-glass-border backdrop-blur-xl shadow-2xl max-w-xs">
                  <div className="flex items-center gap-3 mb-2">
                    <span className="w-2.5 h-2.5 rounded-full bg-primary"></span>
                    <span className="font-label-code text-label-code uppercase tracking-[0.14em] text-primary">
                      REPORT SOURCES
                    </span>
                  </div>
                  <p className="font-body-sm text-body-sm text-on-surface-variant">
                    Source details are shown when an answer uses relevant text from an uploaded report.
                  </p>
                </div>
              </div>

              <div className="lg:col-span-7 flex flex-col space-y-6 lg:pl-12 mt-12 lg:mt-0">
                <span className="font-label-code text-label-code uppercase tracking-[0.2em] text-text-highlight">
                  THE HUMAN IMPERATIVE
                </span>
                <h2 className="font-headline-lg text-headline-lg text-primary">
                  Patients shouldn’t need a medical degree to understand their own diagnosis.
                </h2>
                <p className="font-body-lg text-body-lg text-on-surface-variant leading-relaxed">
                  When an individual receives a blood panel, oncology staging document, or cytogenetic screening, they are often handed terrifying, cryptic jargon during moments of intense vulnerability.
                </p>
                <p className="font-body-md text-body-md text-on-surface-variant leading-relaxed">
                  MedAssist AI connects chat sessions, uploaded reports, and medical question answering so people can review their documents in one place. Its answers are informational and should be discussed with a qualified healthcare professional.
                </p>
                <div className="pt-4 grid grid-cols-2 gap-6">
                  <div className="p-4 rounded-lg bg-surface-container-lowest border border-glass-border">
                    <div className="font-headline-sm text-headline-sm text-primary">English + ಕನ್ನಡ</div>
                    <div className="font-body-sm text-body-sm text-on-surface-variant mt-1">
                      Choose English, Kannada, or bilingual responses for a conversation.
                    </div>
                  </div>
                  <div className="p-4 rounded-lg bg-surface-container-lowest border border-glass-border">
                    <div className="font-headline-sm text-headline-sm text-primary">Session scoped</div>
                    <div className="font-body-sm text-body-sm text-on-surface-variant mt-1">
                      Reports and chat history are linked to the signed-in account and conversation.
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Executive & Research Advisory Notes */}
            <div className="mt-space-2xl pt-16">
              <div className="text-center max-w-2xl mx-auto mb-16">
                <span className="font-label-code text-label-code uppercase tracking-[0.2em] text-text-highlight">
                  PRODUCT PRINCIPLES
                </span>
                <h2 className="font-headline-lg text-headline-lg text-primary mt-2">Built around clearer conversations</h2>
                <p className="font-body-md text-body-md text-on-surface-variant mt-3">
                  The product brings reports, source context, and conversation tools together in one workspace.
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
                {/* Product principle 1 */}
                <div className="rounded-xl bg-surface-container-low/70 border border-glass-border backdrop-blur-xl p-8 flex flex-col justify-between shadow-xl">
                  <div>
                    <div className="flex items-center gap-4 mb-6">
                      <div className="w-14 h-14 rounded-full overflow-hidden bg-surface-container-high flex items-center justify-center flex-shrink-0 text-primary border border-glass-border">
                        <span className="material-symbols-outlined text-[28px]">biotech</span>
                      </div>
                      <div>
                        <h4 className="font-headline-sm text-headline-sm text-primary">Plain-language context</h4>
                        <p className="font-body-sm text-body-sm text-text-highlight">Medical report Q&amp;A</p>
                        <span className="font-caption text-caption text-surface-muted">English and Kannada modes</span>
                      </div>
                    </div>
                    <p className="font-body-sm text-body-sm text-on-surface-variant italic leading-relaxed">
                      Answers can explain medical terminology and point back to report citations when relevant source text is available.
                    </p>
                  </div>
                  <div className="mt-8 pt-4 border-t border-glass-border flex items-center justify-between">
                    <span className="font-label-code text-label-code text-surface-muted">PATIENT CLARITY</span>
                    <span className="material-symbols-outlined text-[18px] text-text-highlight">fingerprint</span>
                  </div>
                </div>

                {/* Product principle 2 */}
                <div className="rounded-xl bg-surface-container-low/70 border border-glass-border backdrop-blur-xl p-8 flex flex-col justify-between shadow-xl">
                  <div>
                    <div className="flex items-center gap-4 mb-6">
                      <div className="w-14 h-14 rounded-full overflow-hidden bg-surface-container-high flex items-center justify-center flex-shrink-0 text-primary border border-glass-border">
                        <span className="material-symbols-outlined text-[28px]">verified_user</span>
                      </div>
                      <div>
                        <h4 className="font-headline-sm text-headline-sm text-primary">Visible source context</h4>
                        <p className="font-body-sm text-body-sm text-text-highlight">Report citations</p>
                        <span className="font-caption text-caption text-surface-muted">Report and section details</span>
                      </div>
                    </div>
                    <p className="font-body-sm text-body-sm text-on-surface-variant italic leading-relaxed">
                      Review source report names and sections alongside answers grounded in your uploaded documents.
                    </p>
                  </div>
                  <div className="mt-8 pt-4 border-t border-glass-border flex items-center justify-between">
                    <span className="font-label-code text-label-code text-surface-muted">SOURCE CONTEXT</span>
                    <span className="material-symbols-outlined text-[18px] text-text-highlight">fingerprint</span>
                  </div>
                </div>

                {/* Product principle 3 */}
                <div className="rounded-xl bg-surface-container-low/70 border border-glass-border backdrop-blur-xl p-8 flex flex-col justify-between shadow-xl">
                  <div>
                    <div className="flex items-center gap-4 mb-6">
                      <div className="w-14 h-14 rounded-full overflow-hidden bg-surface-container-high flex items-center justify-center flex-shrink-0 text-primary border border-glass-border">
                        <span className="material-symbols-outlined text-[28px]">neurology</span>
                      </div>
                      <div>
                        <h4 className="font-headline-sm text-headline-sm text-primary">Conversation control</h4>
                        <p className="font-body-sm text-body-sm text-text-highlight">Session management</p>
                        <span className="font-caption text-caption text-surface-muted">Chats and reports stay organized</span>
                      </div>
                    </div>
                    <p className="font-body-sm text-body-sm text-on-surface-variant italic leading-relaxed">
                      Rename, export, share by email, and manage the reports attached to a conversation.
                    </p>
                  </div>
                  <div className="mt-8 pt-4 border-t border-glass-border flex items-center justify-between">
                    <span className="font-label-code text-label-code text-surface-muted">USER CONTROL</span>
                    <span className="material-symbols-outlined text-[18px] text-text-highlight">fingerprint</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Protocol Status CTA Strip */}
            <div className="mt-28 relative rounded-2xl bg-surface-container-lowest border border-glass-border p-8 lg:p-14 overflow-hidden shadow-2xl">
              <div className="absolute -right-24 -bottom-24 w-96 h-96 bg-accent-chroma/15 rounded-full blur-[100px] pointer-events-none"></div>
              <div className="relative z-10 flex flex-col lg:flex-row lg:items-center justify-between gap-8">
                <div className="max-w-xl">
                  <div className="inline-flex items-center gap-2 mb-4">
                    <span className="w-2 h-2 rounded-full bg-primary"></span>
                    <span className="font-label-code text-label-code uppercase tracking-[0.2em] text-text-highlight">
                      EXPLORE OUR COMPUTATIONAL PIPELINE
                    </span>
                  </div>
                  <h3 className="font-headline-md text-headline-md text-primary">
                    Ready to experience clinical clarity?
                  </h3>
                  <p className="font-body-md text-body-md text-on-surface-variant mt-2">
                    Upload a PDF or supported image, then ask questions about the report in its conversation.
                  </p>
                </div>
                <div className="flex flex-col sm:flex-row items-center gap-4">
                  <Link
                    className="w-full sm:w-auto px-8 py-3.5 rounded-full bg-surface-secondary/60 text-primary hover:bg-surface-secondary font-body-sm text-body-sm tracking-wide text-center border border-glass-border transition-all duration-200"
                    href="/procedures"
                  >
                    View Procedures
                  </Link>
                  <NavigationLoadingLink
                    className="w-full sm:w-auto px-8 py-3.5 rounded-full bg-primary-container text-on-primary hover:bg-primary font-body-sm text-body-sm font-medium tracking-wide text-center shadow-[0_0_24px_rgba(206,204,220,0.25)] hover:shadow-[0_0_32px_rgba(206,204,220,0.45)] transition-all duration-300"
                    href="/dashboard"
                  >
                    Begin Analysis
                  </NavigationLoadingLink>
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
