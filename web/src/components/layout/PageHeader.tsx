type Props = {
  kicker?: string;
  title: string;
  subtitle?: string;
  actions?: React.ReactNode;
};

export function PageHeader({ kicker, title, subtitle, actions }: Props) {
  return (
    <div className="mb-6 flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
      <div>
        {kicker ? (
          <p className="mb-1 text-[11px] font-medium uppercase tracking-[0.14em] text-gold">
            {kicker}
          </p>
        ) : null}
        <h1 className="text-2xl font-semibold tracking-tight text-ink md:text-3xl">
          {title}
        </h1>
        {subtitle ? (
          <p className="mt-2 max-w-2xl text-sm text-muted md:text-base">
            {subtitle}
          </p>
        ) : null}
      </div>
      {actions}
    </div>
  );
}
