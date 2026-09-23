import { SITE } from "@/lib/types";

export function AppFooter() {
  return (
    <footer className="mt-10 border-t border-line bg-surface">
      <div className="mx-auto flex max-w-[1200px] flex-col gap-2 px-4 py-5 text-sm text-muted md:flex-row md:items-center md:justify-between md:px-6">
        <p>
          {SITE.shortName} {SITE.productName} ·{" "}
          <span className="font-script text-lg text-ink">{SITE.brand}</span>
        </p>
        <p>Data-driven analysis for a deeper understanding of the game.</p>
      </div>
    </footer>
  );
}
