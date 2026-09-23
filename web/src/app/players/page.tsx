import { Suspense } from "react";
import { PlayersView } from "@/components/players/PlayersView";

export default function PlayersPage() {
  return (
    <Suspense
      fallback={
        <div className="page-wrap text-sm text-muted">Loading players…</div>
      }
    >
      <PlayersView />
    </Suspense>
  );
}
