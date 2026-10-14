import type { Metadata } from "next";
import { ClerkProvider } from "@clerk/nextjs";
import { Providers } from "@/components/providers";
import "./globals.css";

export const metadata: Metadata = { title: "MedAssist AI", description: "Your healthcare conversation workspace" };
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <ClerkProvider><html lang="en"><body><Providers>{children}</Providers></body></html></ClerkProvider>;
}
