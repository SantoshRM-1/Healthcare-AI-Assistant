import type { Metadata } from "next";
import { ClerkProvider } from "@clerk/nextjs";
import { Providers } from "@/components/providers";
import "./globals.css";

export const metadata: Metadata = {
  title: "MedAssist AI | Medical Reports & Clinical Q&A",
  description: "A healthcare workspace for uploaded medical reports, source-aware questions, and conversation management.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <ClerkProvider>
      <html lang="en" className="dark">
        <head>
          <link rel="preconnect" href="https://fonts.googleapis.com" />
          <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
          <link
            href="https://fonts.googleapis.com/css2?family=Geist:wght@300;400;500;600&family=Hanken+Grotesk:wght@300;400;500;600&display=swap"
            rel="stylesheet"
          />
          <link
            href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200"
            rel="stylesheet"
          />
        </head>
        <body className="bg-background-canvas text-on-surface font-body-md text-body-md antialiased selection:bg-primary-container selection:text-on-primary-container relative min-h-screen">
          <Providers>{children}</Providers>
        </body>
      </html>
    </ClerkProvider>
  );
}
