"use client";

import { useState } from "react";
import { initials } from "@/lib/format";
import { teamAbbr } from "@/lib/teams";

type Props = {
  name: string;
  team?: string;
  imageUrl?: string | null;
  size?: "sm" | "md" | "lg";
  className?: string;
};

const sizes = {
  sm: "h-9 w-9 text-[11px]",
  md: "h-11 w-11 text-xs",
  lg: "h-16 w-16 text-base",
};

export function PlayerAvatar({
  name,
  team,
  imageUrl,
  size = "md",
  className = "",
}: Props) {
  const [failed, setFailed] = useState(false);

  if (imageUrl && !failed) {
    return (
      // eslint-disable-next-line @next/next/no-img-element
      <img
        src={imageUrl}
        alt={name}
        onError={() => setFailed(true)}
        className={`${sizes[size]} rounded-full object-cover object-top border border-line bg-slate-100 ${className}`}
      />
    );
  }

  return (
    <div
      className={`${sizes[size]} rounded-full border border-line bg-slate-100 text-slate-700 flex flex-col items-center justify-center ${className}`}
      aria-label={`${name} avatar`}
      title={team ? `${name} · ${team}` : name}
    >
      <span className="font-semibold leading-none">{initials(name)}</span>
      {team && size !== "sm" ? (
        <span className="mt-0.5 text-[9px] font-medium text-muted leading-none">
          {teamAbbr(team)}
        </span>
      ) : null}
    </div>
  );
}
