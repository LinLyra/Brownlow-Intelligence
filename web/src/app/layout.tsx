import type { Metadata } from "next";
import { Caveat, Inter } from "next/font/google";
import { AppNav } from "@/components/layout/AppNav";
import { AppFooter } from "@/components/layout/AppFooter";
import { EvaluationModal } from "@/components/evaluation/EvaluationModal";
import "./globals.css";

const sans = Inter({
  subsets: ["latin"],
  variable: "--font-sans",
  display: "swap",
});

const script = Caveat({
  subsets: ["latin"],
  variable: "--font-script",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Brownlow Intelligence System | BIS 2026",
  description:
    "LLyra sports intelligence product modelling Brownlow Medal expected votes from AFL performance, coach recognition and match context.",
  openGraph: {
    title: "Brownlow Intelligence System | BIS 2026",
    description:
      "Expected Brownlow votes across 207 matches from a validated CatBoost pipeline.",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${sans.variable} ${script.variable} font-sans antialiased bg-bg text-ink`}
      >
        <AppNav />
        <main className="min-h-[70vh]">{children}</main>
        <AppFooter />
        <EvaluationModal />
      </body>
    </html>
  );
}
