"use client";

import { useState } from "react";
import { teamAbbr, teamColor, teamLogo } from "@/lib/teams";

type Props = {
  team: string;
  size?: "sm" | "md";
  showName?: boolean;
};

const sizes = {
  sm: "h-5 w-5 text-[8px]",
  md: "h-7 w-7 text-[10px]",
};

/** Always-visible team mark; optional logo with graceful fallback. */
export function TeamBadge({ team, size = "sm", showName = true }: Props) {
  const logo = teamLogo(team);
  const [failed, setFailed] = useState(false);
  const abbr = teamAbbr(team);
  const color = teamColor(team);
  const light = ["#FFD200", "#FF7900"].includes(color.toUpperCase());

  return (
    <span className="inline-flex items-center gap-1.5 min-w-0">
      {logo && !failed ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={logo}
          alt=""
          onError={() => setFailed(true)}
          className={`${sizes[size].split(" ")[0]} ${sizes[size].split(" ")[1]} object-contain shrink-0`}
        />
      ) : (
        <span
          className={`${sizes[size]} inline-flex items-center justify-center rounded-full font-bold shrink-0 ${
            light ? "text-ink" : "text-white"
          }`}
          style={{ backgroundColor: color }}
          aria-hidden
        >
          {abbr.slice(0, 3)}
        </span>
      )}
      {showName ? <span className="truncate">{team}</span> : null}
    </span>
  );
}
