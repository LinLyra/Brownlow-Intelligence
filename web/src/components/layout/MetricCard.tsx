import type { ReactNode } from "react";

type Props = {
  label: string;
  value: string;
  icon?: ReactNode;
};

export function MetricCard({ label, value, icon }: Props) {
  return (
    <div className="card shadow-card p-4">
      <div className="flex items-start justify-between gap-2">
        <p className="label">{label}</p>
        {icon ? <span className="text-muted">{icon}</span> : null}
      </div>
      <p className="mt-2 text-2xl font-semibold num text-ink">{value}</p>
    </div>
  );
}
