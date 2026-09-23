"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { NAV_ITEMS, SITE } from "@/lib/types";

export function AppNav() {
  const pathname = usePathname();

  return (
    <header className="sticky top-0 z-40 border-b border-white/10 bg-navy text-white">
      <div className="mx-auto flex max-w-[1200px] items-center gap-4 px-4 py-3 md:px-6">
        <Link href="/race" className="shrink-0 leading-tight">
          <div className="text-[11px] font-semibold tracking-[0.16em] text-gold">
            {SITE.shortName}
          </div>
          <div className="text-sm font-semibold whitespace-nowrap">
            Brownlow Intelligence
          </div>
        </Link>

        <nav
          className="flex min-w-0 flex-1 items-center justify-start gap-0.5 overflow-x-auto md:justify-center"
          aria-label="Primary"
        >
          {NAV_ITEMS.map((item) => {
            const active =
              pathname === item.href ||
              (item.href !== "/race" && pathname.startsWith(item.href));
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`relative shrink-0 whitespace-nowrap px-2.5 py-1.5 text-sm transition-colors sm:px-3 ${
                  active
                    ? "font-medium text-white"
                    : "text-white/65 hover:text-white"
                }`}
              >
                {item.label}
                {active ? (
                  <span
                    className="absolute inset-x-2.5 -bottom-0.5 h-0.5 rounded-full bg-gold sm:inset-x-3"
                    aria-hidden
                  />
                ) : null}
              </Link>
            );
          })}
        </nav>

        <div className="hidden shrink-0 text-right sm:block">
          <div className="font-script text-2xl leading-none text-gold-soft">
            {SITE.brand}
          </div>
          <div className="mt-0.5 text-[10px] tracking-[0.12em] text-white/55 uppercase">
            {SITE.brandTag}
          </div>
        </div>
      </div>
    </header>
  );
}
