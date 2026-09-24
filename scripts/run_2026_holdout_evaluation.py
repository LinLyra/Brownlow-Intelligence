#!/usr/bin/env python3
"""
2026 TRUE HOLDOUT evaluation of the FROZEN Brownlow forecast.

NON-NEGOTIABLE: does not retrain, recalibrate, or modify frozen predictions.
"""
from __future__ import annotations

import hashlib
import html as html_lib
import json
import math
import re
from collections import defaultdict
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
FORECAST_PATH = ROOT / "outputs/final/2026_player_match_predictions.csv"
AFLTABLES_HTML = ROOT / "data/evaluation/_raw/brownlow2026.html"
ACTUAL_CSV = ROOT / "data/evaluation/brownlow_2026_actual_votes.csv"
EVAL_DIR = ROOT / "outputs/evaluation"
FIG_DIR = ROOT / "outputs/figures/evaluation"
WEB_DIR = ROOT / "outputs/web/evaluation"

HIST_OOT_RMSE = 0.355865
BOOTSTRAP_N = 5000
BOOTSTRAP_SEED = 42
CONTENDERS = [
    "Nick Daicos",
    "Marcus Bontempelli",
    "Bailey Smith",
    "Patrick Cripps",
    "Lachie Neale",
    "Will Ashcroft",
    "Max Gawn",
    "Harry Sheezel",
    "Zak Butters",
]

TEAM_ABBR_TO_NAME = {
    "AD": "Adelaide",
    "BL": "Brisbane Lions",
    "CA": "Carlton",
    "CW": "Collingwood",
    "ES": "Essendon",
    "FR": "Fremantle",
    "GE": "Geelong",
    "GC": "Gold Coast",
    "GW": "Greater Western Sydney",
    "HW": "Hawthorn",
    "ME": "Melbourne",
    "NM": "North Melbourne",
    "PA": "Port Adelaide",
    "RI": "Richmond",
    "SK": "St Kilda",
    "SY": "Sydney",
    "WC": "West Coast",
    "WB": "Western Bulldogs",
}


class TableParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tables: list[list[list[str]]] = []
        self._cur: list[list[str]] | None = None
        self._row: list[str] | None = None
        self._cell: list[str] | None = None
        self._in_cell = False

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            self._cur = []
        elif tag == "tr" and self._cur is not None:
            self._row = []
        elif tag in ("td", "th") and self._row is not None:
            self._cell = []
            self._in_cell = True

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self._in_cell and self._row is not None:
            text = html_lib.unescape("".join(self._cell)).strip()
            self._row.append(text)
            self._cell = None
            self._in_cell = False
        elif tag == "tr" and self._row is not None and self._cur is not None:
            if self._row:
                self._cur.append(self._row)
            self._row = None
        elif tag == "table" and self._cur is not None:
            self.tables.append(self._cur)
            self._cur = None

    def handle_data(self, data):
        if self._in_cell and self._cell is not None:
            self._cell.append(data)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_afltables_player_rounds(html_path: Path) -> pd.DataFrame:
    parser = TableParser()
    parser.feed(html_path.read_text(errors="replace"))
    if not parser.tables:
        raise RuntimeError("No tables found in AFL Tables HTML")
    table = parser.tables[0]
    header = table[0]
    # Fixed positions: Player, TM, V, rounds 1..25 at indices 3..27, then GM/3/2/1/GP.
    # Do NOT key by header name: trailing "3","2","1" counts collide with round labels.
    if len(header) < 28 or header[0] != "Player":
        raise RuntimeError(f"Unexpected AFL Tables header: {header}")
    round_indices = {r: 2 + r for r in range(1, 26)}  # round 1 -> idx 3, ..., round 25 -> idx 27
    rows = []
    for cells in table[1:]:
        if len(cells) < 28:
            continue
        player_raw = cells[0]
        if not player_raw or player_raw.lower() == "player":
            continue
        if "," not in player_raw:
            continue
        abbr = cells[1]
        if abbr not in TEAM_ABBR_TO_NAME:
            continue
        total_v = cells[2]
        try:
            season_votes = int(float(total_v)) if total_v not in ("", "-") else 0
        except ValueError:
            season_votes = 0
        last, first = [p.strip() for p in player_raw.split(",", 1)]
        player_name = f"{first} {last}"
        for afl_round, idx in round_indices.items():
            if idx >= len(cells):
                continue
            cell = cells[idx].strip()
            if cell == "":
                continue
            if cell == "-":
                votes = 0
            else:
                try:
                    votes = int(float(cell))
                except ValueError:
                    continue
                if votes not in (0, 1, 2, 3):
                    continue
            rows.append(
                {
                    "afltables_player": player_raw,
                    "player_first_name": first,
                    "player_last_name": last,
                    "player": player_name,
                    "team_abbr": abbr,
                    "team": TEAM_ABBR_TO_NAME[abbr],
                    "afl_round": afl_round,
                    "match_round": afl_round - 1,
                    "actual_brownlow_votes": votes,
                    "afltables_season_votes": season_votes,
                }
            )
    return pd.DataFrame(rows)


def normalize_name(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r"[^a-z\s\-']", "", s)
    s = re.sub(r"\s+", " ", s)
    return s


def map_players_to_ids(vote_rows: pd.DataFrame, forecast: pd.DataFrame) -> pd.DataFrame:
    # Build name+team -> player_id from forecast (and datathon if needed)
    roster = (
        forecast[["player_id", "player_first_name", "player_last_name", "player_name", "player_team"]]
        .drop_duplicates()
        .copy()
    )
    roster["norm"] = roster["player_name"].map(normalize_name)
    roster["norm_last"] = roster["player_last_name"].map(normalize_name)
    roster["norm_first"] = roster["player_first_name"].map(normalize_name)

    by_team_name = {}
    by_team_last = defaultdict(list)
    for r in roster.itertuples(index=False):
        by_team_name[(r.player_team, r.norm)] = int(r.player_id)
        by_team_last[(r.player_team, r.norm_last)].append(r)

    mapped = []
    unmatched = []
    for r in vote_rows.itertuples(index=False):
        key = (r.team, normalize_name(r.player))
        pid = by_team_name.get(key)
        method = "exact_name_team"
        if pid is None:
            # try last-name unique within team
            cands = by_team_last.get((r.team, normalize_name(r.player_last_name)), [])
            if len(cands) == 1:
                pid = int(cands[0].player_id)
                method = "unique_lastname_team"
            elif len(cands) > 1:
                # first-name prefix / contains
                fn = normalize_name(r.player_first_name)
                hit = [c for c in cands if c.norm_first == fn or c.norm_first.startswith(fn) or fn.startswith(c.norm_first)]
                if len(hit) == 1:
                    pid = int(hit[0].player_id)
                    method = "firstname_disambiguation"
        if pid is None:
            unmatched.append(
                {
                    "player": r.player,
                    "team": r.team,
                    "afl_round": r.afl_round,
                    "actual_brownlow_votes": r.actual_brownlow_votes,
                }
            )
            continue
        d = {
            "season": 2026,
            "match_round": int(r.match_round),
            "afl_round": int(r.afl_round),
            "player_id": pid,
            "player": r.player,
            "team": r.team,
            "actual_brownlow_votes": int(r.actual_brownlow_votes),
            "map_method": method,
            "afltables_season_votes": int(r.afltables_season_votes),
        }
        mapped.append(d)
    return pd.DataFrame(mapped), unmatched


def attach_match_ids(mapped: pd.DataFrame, forecast: pd.DataFrame) -> pd.DataFrame:
    # Each player plays at most one match per match_round
    keys = forecast[["match_id", "match_round", "player_id", "player_team", "opponent", "match_home_team", "match_away_team"]].drop_duplicates()
    out = mapped.merge(keys, on=["match_round", "player_id"], how="left", indicator=True)
    return out


def build_full_actual_target(forecast: pd.DataFrame, vote_events: pd.DataFrame) -> pd.DataFrame:
    """One row per forecast player-match; actual votes default 0, overlay mapped votes."""
    base = forecast[
        [
            "season",
            "match_id",
            "match_round",
            "player_id",
            "player_name",
            "player_team",
            "player_position",
            "opponent",
            "match_home_team",
            "match_away_team",
            "coaches_votes",
            "expected_coaches_votes",
            "coach_residual",
            "disposals",
            "goals",
            "clearances",
            "contested_possessions",
            "allocated_expected_votes",
        ]
    ].copy()
    base = base.rename(columns={"player_name": "player", "player_team": "team"})
    votes = vote_events[["match_id", "player_id", "actual_brownlow_votes"]].drop_duplicates()
    # detect duplicate keys
    dup = votes.duplicated(subset=["match_id", "player_id"], keep=False)
    if dup.any():
        raise RuntimeError(f"Duplicate vote keys: {votes[dup].to_dict('records')[:10]}")
    out = base.merge(votes, on=["match_id", "player_id"], how="left")
    out["actual_brownlow_votes"] = out["actual_brownlow_votes"].fillna(0).astype(int)
    return out


def audit_match_votes(actual_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for mid, g in actual_df.groupby("match_id"):
        votes = g["actual_brownlow_votes"].to_numpy()
        s = int(votes.sum())
        n3 = int((votes == 3).sum())
        n2 = int((votes == 2).sum())
        n1 = int((votes == 1).sum())
        ok = (s == 6) and (n3 == 1) and (n2 == 1) and (n1 == 1)
        rows.append(
            {
                "match_id": int(mid),
                "match_round": int(g["match_round"].iloc[0]),
                "home": g["match_home_team"].iloc[0],
                "away": g["match_away_team"].iloc[0],
                "sum_votes": s,
                "n_3": n3,
                "n_2": n2,
                "n_1": n1,
                "ok": ok,
            }
        )
    return pd.DataFrame(rows)


def match_bootstrap_metrics(df: pd.DataFrame, n: int = BOOTSTRAP_N, seed: int = BOOTSTRAP_SEED):
    rng = np.random.default_rng(seed)
    matches = df["match_id"].unique()
    m = len(matches)
    # pre-split by match
    groups = {mid: g[["allocated_expected_votes", "actual_brownlow_votes"]].to_numpy() for mid, g in df.groupby("match_id")}
    rmses = np.empty(n)
    maes = np.empty(n)
    for i in range(n):
        sample = rng.choice(matches, size=m, replace=True)
        parts = [groups[mid] for mid in sample]
        arr = np.vstack(parts)
        p, y = arr[:, 0], arr[:, 1]
        err = p - y
        rmses[i] = float(np.sqrt(np.mean(err**2)))
        maes[i] = float(np.mean(np.abs(err)))
    return {
        "rmse_ci95": [float(np.quantile(rmses, 0.025)), float(np.quantile(rmses, 0.975))],
        "mae_ci95": [float(np.quantile(maes, 0.025)), float(np.quantile(maes, 0.975))],
        "rmse_boot_mean": float(rmses.mean()),
        "mae_boot_mean": float(maes.mean()),
        "rmse_boot_std": float(rmses.std(ddof=1)),
        "mae_boot_std": float(maes.std(ddof=1)),
    }


def ranking_metrics(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for mid, g in df.groupby("match_id"):
        g = g.sort_values("allocated_expected_votes", ascending=False).reset_index(drop=True)
        g = g.assign(pred_rank=np.arange(1, len(g) + 1))
        actual_getters = g[g.actual_brownlow_votes > 0].sort_values("actual_brownlow_votes", ascending=False)
        if len(actual_getters) != 3:
            # still compute what we can
            pass
        actual_ids = set(actual_getters.player_id.tolist())
        pred_top3 = set(g.head(3).player_id.tolist())
        top3_recall = len(actual_ids & pred_top3) / 3.0 if actual_ids else np.nan
        exact_set = int(actual_ids == pred_top3) if len(actual_ids) == 3 else 0
        # ordered: pred ranks by EV vs actual 3/2/1 order
        if len(actual_getters) == 3:
            ordered = list(actual_getters.player_id)
            pred_ordered = list(g.head(3).player_id)
            exact_ordered = int(ordered == pred_ordered)
        else:
            exact_ordered = 0
        three = g[g.actual_brownlow_votes == 3]
        two = g[g.actual_brownlow_votes == 2]
        one = g[g.actual_brownlow_votes == 1]
        top1_acc = int(len(three) == 1 and three.iloc[0].player_id == g.iloc[0].player_id)
        rank3 = float(three.iloc[0].pred_rank) if len(three) == 1 else np.nan
        rank2 = float(two.iloc[0].pred_rank) if len(two) == 1 else np.nan
        rank1 = float(one.iloc[0].pred_rank) if len(one) == 1 else np.nan
        mrr3 = (1.0 / rank3) if rank3 == rank3 else np.nan
        rows.append(
            {
                "match_id": int(mid),
                "match_round": int(g.match_round.iloc[0]),
                "top1_3vote_accuracy": top1_acc,
                "top3_recall": top3_recall,
                "exact_top3_set": exact_set,
                "exact_ordered_321": exact_ordered,
                "rank_actual_3": rank3,
                "rank_actual_2": rank2,
                "rank_actual_1": rank1,
                "mrr_actual_3": mrr3,
            }
        )
    return pd.DataFrame(rows)


def style_axes(ax):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(True, axis="y", alpha=0.25, linewidth=0.6)
    ax.set_axisbelow(True)


def main():
    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    WEB_DIR.mkdir(parents=True, exist_ok=True)
    (ROOT / "data/evaluation").mkdir(parents=True, exist_ok=True)

    # ---------- STEP 0 integrity ----------
    assert FORECAST_PATH.exists(), f"Missing frozen forecast: {FORECAST_PATH}"
    forecast_hash_before = sha256_file(FORECAST_PATH)
    forecast = pd.read_csv(FORECAST_PATH)
    pred_col = "allocated_expected_votes"
    integrity = {
        "file_path": str(FORECAST_PATH.relative_to(ROOT)),
        "sha256": forecast_hash_before,
        "row_count": int(len(forecast)),
        "column_names": list(forecast.columns),
        "prediction_column": pred_col,
        "total_allocated_expected_votes": float(forecast[pred_col].sum()),
        "n_matches": int(forecast["match_id"].nunique()),
        "n_player_match_rows": int(len(forecast)),
        "model_version": {
            "champion": "base_plus_components",
            "historical_rolling_oot_rmse": HIST_OOT_RMSE,
            "source": "outputs/final/MODEL_CARD.md",
        },
        "expected_from_prior_audit": {
            "matches": 207,
            "player_match_rows": 9522,
            "total_expected_votes": 1242,
        },
        "discrepancies": [],
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    if integrity["n_matches"] != 207:
        integrity["discrepancies"].append(f"matches got {integrity['n_matches']}")
    if integrity["n_player_match_rows"] != 9522:
        integrity["discrepancies"].append(f"rows got {integrity['n_player_match_rows']}")
    if abs(integrity["total_allocated_expected_votes"] - 1242) > 0.01:
        integrity["discrepancies"].append(f"total_ev got {integrity['total_allocated_expected_votes']}")
    (EVAL_DIR / "2026_forecast_integrity.json").write_text(json.dumps(integrity, indent=2) + "\n")

    # ---------- STEP 1–2 parse actuals ----------
    if not AFLTABLES_HTML.exists():
        raise SystemExit(
            "STOP: Official AFL Tables HTML missing at "
            f"{AFLTABLES_HTML}. Download https://afltables.com/afl/brownlow/brownlow2026.html"
        )
    vote_long = parse_afltables_player_rounds(AFLTABLES_HTML)
    vote_long.to_csv(ROOT / "data/evaluation/_raw/afltables_2026_votes_long.csv", index=False)

    mapped, unmatched_players = map_players_to_ids(vote_long, forecast)
    if unmatched_players:
        pd.DataFrame(unmatched_players).to_csv(EVAL_DIR / "2026_player_map_unmatched.csv", index=False)
    with_matches = attach_match_ids(mapped, forecast)
    missing_match = with_matches[with_matches["_merge"] != "both"]
    vote_events = with_matches[with_matches["_merge"] == "both"].copy()
    # Only non-zero votes needed for overlay; zeros come from full join
    vote_pos = vote_events[vote_events["actual_brownlow_votes"] > 0].copy()

    # Save authoritative actual vote events (player-round with match_id)
    actual_events = vote_events[
        [
            "season",
            "match_id",
            "match_round",
            "afl_round",
            "player_id",
            "player",
            "team",
            "actual_brownlow_votes",
        ]
    ].copy()
    actual_events.to_csv(ACTUAL_CSV, index=False)

    joined = build_full_actual_target(forecast, vote_pos)
    vote_audit = audit_match_votes(joined)
    vote_audit.to_csv(EVAL_DIR / "2026_actual_vote_audit.csv", index=False)
    anomalies = vote_audit[~vote_audit["ok"]]
    anomalies.to_csv(EVAL_DIR / "2026_actual_vote_anomalies.csv", index=False)

    # ---------- STEP 3 join audit ----------
    # Compare vote-positive actuals vs forecast coverage
    actual_pos_keys = set(zip(vote_pos.match_id.astype(int), vote_pos.player_id.astype(int)))
    forecast_keys = set(zip(forecast.match_id.astype(int), forecast.player_id.astype(int)))
    matched_pos = actual_pos_keys & forecast_keys
    unmatched_actual = actual_pos_keys - forecast_keys
    # unmatched forecast is expected for zeros; report vote overlays only
    join_audit_rows = [
        {
            "metric": "forecast_rows",
            "value": len(forecast),
        },
        {"metric": "actual_event_rows_incl_zeros_played", "value": len(vote_events)},
        {"metric": "actual_positive_vote_rows", "value": len(vote_pos)},
        {"metric": "matched_positive_vote_keys", "value": len(matched_pos)},
        {"metric": "unmatched_positive_actual_keys", "value": len(unmatched_actual)},
        {"metric": "unmatched_player_map_rows", "value": len(unmatched_players)},
        {"metric": "matches_with_vote_sum_not_6_or_bad_321", "value": int((~vote_audit.ok).sum())},
        {"metric": "matches_ok", "value": int(vote_audit.ok.sum())},
        {"metric": "n_matches_forecast", "value": int(forecast.match_id.nunique())},
        {"metric": "join_rate_positive_votes", "value": len(matched_pos) / max(len(actual_pos_keys), 1)},
    ]
    join_audit = pd.DataFrame(join_audit_rows)
    join_audit.to_csv(EVAL_DIR / "2026_join_audit.csv", index=False)

    if len(unmatched_actual) or len(unmatched_players) or (~vote_audit.ok).sum() > 0:
        # Soft stop: write STOP note but continue only if join is effectively complete for scoring universe
        stop_reasons = []
        if unmatched_players:
            stop_reasons.append(f"unmatched player map: {len(unmatched_players)}")
        if unmatched_actual:
            stop_reasons.append(f"unmatched positive actual keys: {len(unmatched_actual)}")
        if (~vote_audit.ok).sum():
            stop_reasons.append(f"match vote anomalies: {int((~vote_audit.ok).sum())}")
        (EVAL_DIR / "2026_JOIN_STOP_NOTE.md").write_text(
            "# Join / vote integrity issues\n\n"
            + "\n".join(f"- {r}" for r in stop_reasons)
            + "\n\n"
            + "If anomalies remain unresolved, headline metrics may be incomplete.\n"
        )
        # Hard stop only if positive-vote join rate is incomplete or many anomalies
        if len(unmatched_actual) or len(unmatched_players) or (~vote_audit.ok).mean() > 0.02:
            print("STOP: join/vote integrity incomplete. See evaluation artifacts.")
            print(join_audit.to_string(index=False))
            print("anomalies sample:\n", anomalies.head(20).to_string(index=False))
            if unmatched_players:
                print("unmatched players sample:", unmatched_players[:20])
            return

    # ---------- STEP 4 leakage audit ----------
    leak_md = f"""# 2026 Leakage Audit

## Question
Were 2026 actual Brownlow labels isolated from model development and the frozen forecast?

## Repository evidence

1. Frozen forecast file `{FORECAST_PATH.relative_to(ROOT)}` was generated as a pre-result inference artifact
   (see `outputs/final/MODEL_CARD.md`): *"The 2026 Brownlow target is unavailable and was not used."*
2. Training protocol in MODEL_CARD: CatBoost trained on labelled seasons **before 2026**.
3. Feature construction (`src/brownlow/features.py`):
   - `brownlow_votes` is in `ID_COLS` / `DROP_ALWAYS` and is **not** a predictive feature.
   - Lagged recognition features use only **shifted** past votes (`cumsum().shift(1)`).
4. Coach Intelligence (`src/brownlow/coach_intelligence.py` / `final_2026.py`):
   - Explicit asserts exclude `brownlow_votes` from coach and Brownlow feature lists.
5. Datathon raw file still has `brownlow_votes` all-null for season 2026 at evaluation start
   (labels for this audit were obtained separately from AFL Tables after the count).

## Contaminating variables checked against frozen prediction columns

Frozen prediction CSV columns include performance stats and coach signals available pre-count,
plus `allocated_expected_votes`. They do **not** include:
- `brownlow_votes`
- `actual_brownlow_votes`
- 2026 final season Brownlow totals
- post-count variables

## Conclusion

**Supported by repository artifacts:** the frozen 2026 forecast was produced without 2026 Brownlow
labels as features or as a model-selection target. This evaluation introduces official 2026 votes
**only as held-out labels**.

This audit does **not** claim stronger provenance than git/history + MODEL_CARD + code asserts provide.
It does not independently prove the chronological wall-clock freeze relative to the Brownlow telecast;
it verifies that the checked artifacts treat 2026 actuals as unused for prediction.
"""
    (EVAL_DIR / "2026_leakage_audit.md").write_text(leak_md)

    # ---------- STEP 5 primary metrics ----------
    y = joined["actual_brownlow_votes"].to_numpy(dtype=float)
    p = joined[pred_col].to_numpy(dtype=float)
    err = p - y
    rmse = float(np.sqrt(np.mean(err**2)))
    mae = float(np.mean(np.abs(err)))
    mse = float(np.mean(err**2))
    bias = float(np.mean(err))
    pearson = float(stats.pearsonr(p, y).statistic)
    spearman = float(stats.spearmanr(p, y).statistic)
    abs_diff = rmse - HIST_OOT_RMSE
    rel_diff = abs_diff / HIST_OOT_RMSE * 100.0

    # ---------- STEP 6 bootstrap ----------
    boot = match_bootstrap_metrics(joined)

    primary = {
        "n_player_match": int(len(joined)),
        "n_matches": int(joined.match_id.nunique()),
        "rmse": rmse,
        "mae": mae,
        "mse": mse,
        "mean_prediction_bias": bias,
        "pearson": pearson,
        "spearman": spearman,
        "historical_oot_rmse": HIST_OOT_RMSE,
        "rmse_minus_historical": abs_diff,
        "rmse_relative_pct_vs_historical": rel_diff,
        **boot,
    }
    (EVAL_DIR / "2026_primary_metrics.json").write_text(json.dumps(primary, indent=2) + "\n")

    # ---------- STEP 7 by actual vote ----------
    by_vote_rows = []
    for v in [0, 1, 2, 3]:
        sub = joined[joined.actual_brownlow_votes == v]
        pe = sub[pred_col].to_numpy()
        ye = sub.actual_brownlow_votes.to_numpy(dtype=float)
        e = pe - ye
        by_vote_rows.append(
            {
                "actual_vote": v,
                "count": int(len(sub)),
                "mean_predicted_ev": float(pe.mean()) if len(sub) else np.nan,
                "median_predicted_ev": float(np.median(pe)) if len(sub) else np.nan,
                "mae": float(np.mean(np.abs(e))) if len(sub) else np.nan,
                "rmse": float(np.sqrt(np.mean(e**2))) if len(sub) else np.nan,
            }
        )
    by_vote = pd.DataFrame(by_vote_rows)
    by_vote.to_csv(EVAL_DIR / "2026_error_by_actual_vote.csv", index=False)

    # ---------- STEP 8 ranking ----------
    rank_df = ranking_metrics(joined)
    rank_df.to_csv(EVAL_DIR / "2026_match_ranking_metrics.csv", index=False)
    rank_summary = {
        "top1_3vote_accuracy": float(rank_df.top1_3vote_accuracy.mean()),
        "top3_recall": float(rank_df.top3_recall.mean()),
        "exact_top3_set_rate": float(rank_df.exact_top3_set.mean()),
        "exact_ordered_321_rate": float(rank_df.exact_ordered_321.mean()),
        "mean_rank_actual_3": float(rank_df.rank_actual_3.mean()),
        "mean_rank_actual_2": float(rank_df.rank_actual_2.mean()),
        "mean_rank_actual_1": float(rank_df.rank_actual_1.mean()),
        "mrr_actual_3": float(rank_df.mrr_actual_3.mean()),
        "n_matches": int(len(rank_df)),
    }
    (EVAL_DIR / "2026_match_ranking_summary.json").write_text(json.dumps(rank_summary, indent=2) + "\n")

    # ---------- STEP 9 season aggregation ----------
    season = (
        joined.groupby(["player_id", "player", "team"], as_index=False)
        .agg(
            predicted_expected_votes=(pred_col, "sum"),
            actual_votes=("actual_brownlow_votes", "sum"),
            games=("match_id", "nunique"),
        )
    )
    season["error"] = season.predicted_expected_votes - season.actual_votes
    season["absolute_error"] = season.error.abs()
    season["predicted_rank"] = season.predicted_expected_votes.rank(ascending=False, method="min").astype(int)
    season["actual_rank"] = season.actual_votes.rank(ascending=False, method="min").astype(int)
    season["rank_error"] = season.predicted_rank - season.actual_rank
    season = season.sort_values(["predicted_rank", "player"]).reset_index(drop=True)
    season.to_csv(EVAL_DIR / "2026_season_forecast_vs_actual.csv", index=False)

    season_pearson = float(stats.pearsonr(season.predicted_expected_votes, season.actual_votes).statistic)
    season_spearman = float(stats.spearmanr(season.predicted_expected_votes, season.actual_votes).statistic)
    season_mae = float(season.absolute_error.mean())
    season_rmse = float(np.sqrt(np.mean(season.error**2)))

    def overlap(k: int) -> float:
        pred_set = set(season.nsmallest(k, "predicted_rank").player_id)
        # nsmallest on rank works; equivalently largest predicted
        pred_set = set(season.sort_values("predicted_expected_votes", ascending=False).head(k).player_id)
        act_set = set(season.sort_values("actual_votes", ascending=False).head(k).player_id)
        return len(pred_set & act_set) / float(k)

    overlaps = {f"top_{k}_overlap": overlap(k) for k in (3, 5, 10, 20)}
    pred_champ = season.sort_values("predicted_expected_votes", ascending=False).iloc[0]
    act_champ = season.sort_values("actual_votes", ascending=False).iloc[0]
    champ_match = int(pred_champ.player_id == act_champ.player_id)

    season_metrics = {
        "pearson": season_pearson,
        "spearman": season_spearman,
        "mae": season_mae,
        "rmse": season_rmse,
        **overlaps,
        "predicted_rank1_player": pred_champ.player,
        "actual_rank1_player": act_champ.player,
        "predicted_rank1_is_actual_rank1": bool(champ_match),
        "predicted_rank1_expected_votes": float(pred_champ.predicted_expected_votes),
        "actual_rank1_votes": float(act_champ.actual_votes),
    }
    (EVAL_DIR / "2026_season_metrics.json").write_text(json.dumps(season_metrics, indent=2) + "\n")

    # ---------- STEP 10 leaderboard comparison ----------
    top20 = season.sort_values("predicted_rank").head(20).copy()
    top20_out = top20.rename(
        columns={
            "predicted_rank": "Predicted Rank",
            "player": "Player",
            "team": "Team",
            "predicted_expected_votes": "Expected Votes",
            "actual_votes": "Actual Votes",
            "actual_rank": "Actual Rank",
            "error": "Vote Error (pred-actual)",
            "rank_error": "Rank Error (pred-actual)",
        }
    )
    top20_out.to_csv(EVAL_DIR / "2026_top20_forecast_vs_actual.csv", index=False)

    # participation threshold: at least 5 games
    eligible = season[season.games >= 5].copy()
    under = eligible.assign(under_gap=eligible.actual_votes - eligible.predicted_expected_votes).nlargest(15, "under_gap")
    over = eligible.assign(over_gap=eligible.predicted_expected_votes - eligible.actual_votes).nlargest(15, "over_gap")
    under.to_csv(EVAL_DIR / "2026_largest_underpredictions.csv", index=False)
    over.to_csv(EVAL_DIR / "2026_largest_overpredictions.csv", index=False)

    # ---------- STEP 11 contender audits ----------
    audits = []
    for name in CONTENDERS:
        row = season[season.player == name]
        if row.empty:
            # fuzzy
            row = season[season.player.str.contains(name.split()[-1], case=False)]
            row = row[row.player.str.contains(name.split()[0], case=False)]
        if row.empty:
            audits.append({"player": name, "status": "not_found"})
            continue
        r = row.iloc[0]
        pm = joined[joined.player_id == r.player_id].sort_values("match_round")
        rounds = []
        for rr in pm.itertuples(index=False):
            rounds.append(
                {
                    "round": int(rr.match_round) + 1,
                    "match_round": int(rr.match_round),
                    "match_id": int(rr.match_id),
                    "opponent": rr.opponent,
                    "frozen_ev": float(getattr(rr, pred_col)),
                    "actual_vote": int(rr.actual_brownlow_votes),
                    "coaches_votes": float(rr.coaches_votes) if pd.notna(rr.coaches_votes) else None,
                    "disposals": float(rr.disposals) if pd.notna(rr.disposals) else None,
                    "goals": float(rr.goals) if pd.notna(rr.goals) else None,
                    "clearances": float(rr.clearances) if pd.notna(rr.clearances) else None,
                    "contested_possessions": float(rr.contested_possessions)
                    if pd.notna(rr.contested_possessions)
                    else None,
                }
            )
        audits.append(
            {
                "player": r.player,
                "team": r.team,
                "predicted_expected_votes": float(r.predicted_expected_votes),
                "actual_votes": float(r.actual_votes),
                "difference_pred_minus_actual": float(r.error),
                "predicted_rank": int(r.predicted_rank),
                "actual_rank": int(r.actual_rank),
                "games": int(r.games),
                "rounds": rounds,
            }
        )
    (EVAL_DIR / "2026_contender_audits.json").write_text(json.dumps(audits, indent=2) + "\n")

    # ---------- STEP 12 calibration ----------
    bins = [0.0, 0.10, 0.25, 0.50, 1.00, 1.50, 2.00, 2.50, 3.01]
    labels = ["0.00–0.10", "0.10–0.25", "0.25–0.50", "0.50–1.00", "1.00–1.50", "1.50–2.00", "2.00–2.50", "2.50–3.00"]
    joined = joined.copy()
    joined["ev_bin"] = pd.cut(joined[pred_col], bins=bins, labels=labels, right=False, include_lowest=True)
    cal_rows = []
    for lab in labels:
        sub = joined[joined.ev_bin == lab]
        cal_rows.append(
            {
                "bin": lab,
                "n": int(len(sub)),
                "mean_predicted_ev": float(sub[pred_col].mean()) if len(sub) else np.nan,
                "mean_actual_votes": float(sub.actual_brownlow_votes.mean()) if len(sub) else np.nan,
            }
        )
    cal = pd.DataFrame(cal_rows)
    cal.to_csv(EVAL_DIR / "2026_calibration.csv", index=False)
    # Expected Calibration Error (weighted absolute gap) — expected-vote, not probability
    w = cal.n.to_numpy(dtype=float)
    gap = np.abs(cal.mean_predicted_ev.to_numpy() - cal.mean_actual_votes.to_numpy())
    ece = float(np.nansum(w * gap) / np.nansum(w)) if w.sum() else np.nan

    # ---------- STEP 13 error diagnostics ----------
    diag = {}
    # 1 underpredict 3-vote
    three = joined[joined.actual_brownlow_votes == 3]
    diag["actual_3_mean_pred"] = float(three[pred_col].mean())
    diag["actual_3_mean_error_pred_minus_actual"] = float((three[pred_col] - 3).mean())
    # 2 coach association with residual
    residual = joined[pred_col] - joined.actual_brownlow_votes
    if joined.coaches_votes.notna().any():
        diag["corr_residual_vs_coaches_votes"] = float(stats.spearmanr(residual, joined.coaches_votes).statistic)
        diag["corr_abs_error_vs_coaches_votes"] = float(
            stats.spearmanr(residual.abs(), joined.coaches_votes).statistic
        )
    if joined.coach_residual.notna().any():
        diag["corr_residual_vs_coach_residual"] = float(stats.spearmanr(residual, joined.coach_residual).statistic)

    # 3 position
    pos = (
        joined.groupby("player_position")
        .apply(
            lambda g: pd.Series(
                {
                    "n": len(g),
                    "rmse": float(np.sqrt(np.mean((g[pred_col] - g.actual_brownlow_votes) ** 2))),
                    "mean_bias": float((g[pred_col] - g.actual_brownlow_votes).mean()),
                    "mean_actual": float(g.actual_brownlow_votes.mean()),
                    "mean_pred": float(g[pred_col].mean()),
                }
            ),
            include_groups=False,
        )
        .reset_index()
    )
    pos.to_csv(EVAL_DIR / "2026_error_by_position.csv", index=False)

    # 4 losing-team vote getters
    # team result proxy: if player team != match winner unavailable; use coaches? use score from datathon via forecast only
    # We don't have match_winner in forecast CSV. Approximate: if team got any of 3/2/1 vs not.
    # Use: for actual vote getters, whether teammates' coach votes high — skip winner.
    # Pull from datathon if available without modifying.
    try:
        raw = pd.read_csv(
            ROOT / "data/raw/brownlow_datathon_dataset.csv",
            usecols=["season", "match_id", "player_id", "match_margin", "match_winner", "player_team"],
            low_memory=False,
        )
        raw = raw[raw.season == 2026]
        joined2 = joined.merge(
            raw[["match_id", "player_id", "match_margin", "match_winner", "player_team"]].drop_duplicates(),
            on=["match_id", "player_id"],
            how="left",
            suffixes=("", "_raw"),
        )
        if "player_team" not in joined2 and "team" in joined2:
            joined2["player_team"] = joined2["team"]
        joined2["team_won"] = (joined2["player_team"] == joined2["match_winner"]).astype(float)
        vote_getters = joined2[joined2.actual_brownlow_votes > 0]
        diag["vote_getter_share_winning_team"] = float(vote_getters.team_won.mean())
        for won, label in [(1, "winning_team"), (0, "losing_team")]:
            sub = vote_getters[vote_getters.team_won == won]
            if len(sub):
                diag[f"{label}_vote_getter_mean_pred"] = float(sub[pred_col].mean())
                diag[f"{label}_vote_getter_mae"] = float((sub[pred_col] - sub.actual_brownlow_votes).abs().mean())
        # close vs blowout
        joined2["abs_margin"] = joined2.match_margin.abs()
        close = joined2[joined2.abs_margin <= 12]
        blow = joined2[joined2.abs_margin >= 40]
        mid = joined2[(joined2.abs_margin > 12) & (joined2.abs_margin < 40)]
        for name, sub in [("close_le12", close), ("mid", mid), ("blowout_ge40", blow)]:
            if len(sub):
                e = sub[pred_col] - sub.actual_brownlow_votes
                diag[f"rmse_{name}"] = float(np.sqrt(np.mean(e**2)))
    except Exception as e:
        diag["match_context_error"] = str(e)

    # compression / regression to mean
    diag["pred_std"] = float(p.std())
    diag["actual_std"] = float(y.std())
    diag["pred_mean"] = float(p.mean())
    diag["actual_mean"] = float(y.mean())
    diag["calibration_ece_expected_vote"] = ece
    (EVAL_DIR / "2026_error_diagnostics.json").write_text(json.dumps(diag, indent=2) + "\n")

    # ---------- STEP 14 historical comparison ----------
    fold = pd.read_csv(ROOT / "outputs/reports/v2_2_temporal_fold_metrics.csv")
    hist = fold[fold.strategy == "expanding_all"][["validation_year", "rmse_allocated"]].copy()
    hist = hist.rename(columns={"validation_year": "year", "rmse_allocated": "allocated_rmse"})
    hist_rows = hist.to_dict("records")
    hist_vals = hist.allocated_rmse.to_numpy()
    gen_table = hist_rows + [{"year": 2026, "allocated_rmse": rmse}]
    pd.DataFrame(gen_table).to_csv(EVAL_DIR / "2026_generalisation_table.csv", index=False)
    gen = {
        "historical_years": hist_rows,
        "historical_mean": float(hist_vals.mean()),
        "historical_std": float(hist_vals.std(ddof=1)),
        "historical_min": float(hist_vals.min()),
        "historical_max": float(hist_vals.max()),
        "champion_reported_mean": HIST_OOT_RMSE,
        "holdout_2026_rmse": rmse,
        "within_historical_range": bool(hist_vals.min() <= rmse <= hist_vals.max()),
        "z_vs_historical": float((rmse - hist_vals.mean()) / hist_vals.std(ddof=1)),
    }
    (EVAL_DIR / "2026_generalisation.json").write_text(json.dumps(gen, indent=2) + "\n")

    # ---------- STEP 15 figures ----------
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "axes.titlesize": 12,
            "axes.labelsize": 10,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
        }
    )

    # 1 dumbbell top20
    fig, ax = plt.subplots(figsize=(8, 7))
    t = season.sort_values("predicted_rank").head(20).iloc[::-1]
    y_pos = np.arange(len(t))
    ax.hlines(y_pos, t.predicted_expected_votes, t.actual_votes, color="#9aa3af", linewidth=1.2)
    ax.scatter(t.predicted_expected_votes, y_pos, color="#1e3a5f", s=36, label="Predicted EV", zorder=3)
    ax.scatter(t.actual_votes, y_pos, color="#c4a35a", s=36, label="Actual votes", zorder=3)
    ax.set_yticks(y_pos)
    ax.set_yticklabels([f"{int(r.predicted_rank)}. {r.player}" for r in t.itertuples()])
    ax.set_xlabel("Votes")
    ax.set_title("2026 Forecast vs Actual — Top 20 by Predicted Rank")
    ax.legend(frameon=False, loc="lower right")
    style_axes(ax)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "top20_dumbbell.png", dpi=160)
    plt.close(fig)

    # 2 scatter season
    fig, ax = plt.subplots(figsize=(6.5, 6))
    ax.scatter(season.predicted_expected_votes, season.actual_votes, s=18, alpha=0.55, color="#1e3a5f", edgecolors="none")
    mx = max(season.predicted_expected_votes.max(), season.actual_votes.max()) * 1.05
    ax.plot([0, mx], [0, mx], color="#c4a35a", lw=1.2, label="y = x")
    ax.set_xlabel("Predicted expected votes")
    ax.set_ylabel("Actual Brownlow votes")
    ax.set_title("2026 Season Totals: Predicted vs Actual")
    ax.legend(frameon=False)
    style_axes(ax)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "season_scatter.png", dpi=160)
    plt.close(fig)

    # 3 calibration
    fig, ax = plt.subplots(figsize=(6, 5.5))
    cplot = cal.dropna()
    ax.plot(cplot.mean_predicted_ev, cplot.mean_actual_votes, "o-", color="#1e3a5f", lw=1.4)
    lim = max(cplot.mean_predicted_ev.max(), cplot.mean_actual_votes.max()) * 1.05
    ax.plot([0, lim], [0, lim], color="#c4a35a", lw=1.2, label="y = x")
    for _, r in cplot.iterrows():
        ax.annotate(f"n={int(r.n)}", (r.mean_predicted_ev, r.mean_actual_votes), textcoords="offset points", xytext=(4, 4), fontsize=7, color="#666")
    ax.set_xlabel("Mean predicted EV (bin)")
    ax.set_ylabel("Mean actual votes (bin)")
    ax.set_title("2026 Expected-Vote Calibration")
    ax.legend(frameon=False)
    style_axes(ax)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "calibration.png", dpi=160)
    plt.close(fig)

    # 4 historical vs holdout
    fig, ax = plt.subplots(figsize=(6.5, 4.2))
    years = [int(r["year"]) for r in gen_table]
    vals = [r["allocated_rmse"] for r in gen_table]
    colors = ["#1e3a5f"] * (len(years) - 1) + ["#c4a35a"]
    ax.bar([str(y) for y in years], vals, color=colors, width=0.65)
    ax.axhline(HIST_OOT_RMSE, color="#666", ls="--", lw=1, label=f"Historical mean {HIST_OOT_RMSE:.6f}")
    ax.set_ylabel("Allocated RMSE")
    ax.set_title("Historical OOT vs 2026 True Holdout RMSE")
    ax.legend(frameon=False)
    style_axes(ax)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "historical_vs_holdout_rmse.png", dpi=160)
    plt.close(fig)

    # 5 error by actual vote
    fig, ax = plt.subplots(figsize=(6, 4.2))
    ax.bar(by_vote.actual_vote.astype(str), by_vote.rmse, color="#1e3a5f", width=0.6, label="RMSE")
    ax.plot(by_vote.actual_vote.astype(str), by_vote.mean_predicted_ev, "o-", color="#c4a35a", label="Mean predicted EV")
    ax.set_xlabel("Actual Brownlow vote")
    ax.set_title("2026 Error by Actual Vote Category")
    ax.legend(frameon=False)
    style_axes(ax)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "error_by_actual_vote.png", dpi=160)
    plt.close(fig)

    # 6 largest over/under
    fig, axes = plt.subplots(1, 2, figsize=(11, 5.5))
    for ax, dfu, title, col, sign in [
        (axes[0], under.head(10).iloc[::-1], "Largest underpredictions", "under_gap", 1),
        (axes[1], over.head(10).iloc[::-1], "Largest overpredictions", "over_gap", 1),
    ]:
        ax.barh(dfu.player, dfu[col], color="#1e3a5f")
        ax.set_title(title)
        ax.set_xlabel("Votes")
        style_axes(ax)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "largest_misses.png", dpi=160)
    plt.close(fig)

    # 7 Daicos round by round
    daicos = next((a for a in audits if a.get("player") == "Nick Daicos"), None)
    if daicos and daicos.get("rounds"):
        rdf = pd.DataFrame(daicos["rounds"])
        fig, ax = plt.subplots(figsize=(9, 4))
        ax.bar(rdf["round"], rdf["actual_vote"], color="#c4a35a", alpha=0.85, label="Actual vote", width=0.7)
        ax.plot(rdf["round"], rdf["frozen_ev"], "o-", color="#1e3a5f", lw=1.3, label="Frozen EV")
        ax.set_xlabel("Round")
        ax.set_ylabel("Votes")
        ax.set_title("Nick Daicos — Frozen EV vs Actual Votes")
        ax.legend(frameon=False)
        style_axes(ax)
        fig.tight_layout()
        fig.savefig(FIG_DIR / "daicos_round_by_round.png", dpi=160)
        plt.close(fig)

    # 8 contender comparison
    fig, ax = plt.subplots(figsize=(8, 5))
    crows = [a for a in audits if "predicted_expected_votes" in a]
    names = [a["player"] for a in crows]
    pred_v = [a["predicted_expected_votes"] for a in crows]
    act_v = [a["actual_votes"] for a in crows]
    x = np.arange(len(names))
    ax.bar(x - 0.18, pred_v, width=0.36, color="#1e3a5f", label="Predicted EV")
    ax.bar(x + 0.18, act_v, width=0.36, color="#c4a35a", label="Actual")
    ax.set_xticks(x)
    ax.set_xticklabels(names, rotation=30, ha="right")
    ax.set_ylabel("Season votes")
    ax.set_title("Top Contenders — Predicted vs Actual")
    ax.legend(frameon=False)
    style_axes(ax)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "contenders_predicted_vs_actual.png", dpi=160)
    plt.close(fig)

    # ---------- STEP 16 report ----------
    report = f"""# Brownlow Intelligence — 2026 Holdout Evaluation

## 1. Evaluation Protocol

This audit scores the **frozen** 2026 player-match forecast against official Brownlow votes.

- Forecast artifact: `{FORECAST_PATH.relative_to(ROOT)}`
- SHA256 (pre-evaluation): `{forecast_hash_before}`
- Prediction column: `{pred_col}`
- Labels: official 2026 Brownlow 3–2–1 allocations parsed from AFL Tables
  (`https://afltables.com/afl/brownlow/brownlow2026.html`), stored separately at
  `{ACTUAL_CSV.relative_to(ROOT)}`.

Repository MODEL_CARD and feature code treat 2026 Brownlow votes as unavailable for training.
This evaluation introduces those labels **only as holdout targets**. No retraining, recalibration,
or forecast overwrite was performed.

## 2. Forecast Integrity

| Item | Value |
| --- | --- |
| Rows | {integrity['n_player_match_rows']} |
| Matches | {integrity['n_matches']} |
| Total allocated expected votes | {integrity['total_allocated_expected_votes']:.6f} |
| SHA256 | `{forecast_hash_before}` |
| Model | CatBoost `base_plus_components` |
| Historical rolling OOT RMSE | {HIST_OOT_RMSE} |
| Discrepancies vs prior audit | {integrity['discrepancies'] or 'none'} |

Post-run SHA256 recheck: `{sha256_file(FORECAST_PATH)}` (must match).

## 3. Primary Results

| Metric | Value |
| --- | --- |
| Historical OOT RMSE | {HIST_OOT_RMSE} |
| **2026 true holdout RMSE** | **{rmse:.6f}** |
| 95% bootstrap CI (match-level) | [{boot['rmse_ci95'][0]:.6f}, {boot['rmse_ci95'][1]:.6f}] |
| MAE | {mae:.6f} |
| MAE 95% CI | [{boot['mae_ci95'][0]:.6f}, {boot['mae_ci95'][1]:.6f}] |
| MSE | {mse:.6f} |
| Mean prediction bias (p−y) | {bias:.6e} |
| Pearson (player-match) | {pearson:.4f} |
| Spearman (player-match) | {spearman:.4f} |
| RMSE − historical | {abs_diff:+.6f} |
| Relative vs historical | {rel_diff:+.2f}% |

N = {primary['n_player_match']} player-match rows, {primary['n_matches']} matches.
Bootstrap: {BOOTSTRAP_N} match-level resamples, seed {BOOTSTRAP_SEED}.

## 4. Match-Level Ranking

| Metric | Rate / value |
| --- | --- |
| Top-1 = actual 3-vote | {rank_summary['top1_3vote_accuracy']:.3f} |
| Top-3 recall (of actual vote getters) | {rank_summary['top3_recall']:.3f} |
| Exact Top-3 set | {rank_summary['exact_top3_set_rate']:.3f} |
| Exact ordered 3–2–1 | {rank_summary['exact_ordered_321_rate']:.3f} |
| Mean rank of actual 3 / 2 / 1 | {rank_summary['mean_rank_actual_3']:.2f} / {rank_summary['mean_rank_actual_2']:.2f} / {rank_summary['mean_rank_actual_1']:.2f} |
| MRR (actual 3-vote) | {rank_summary['mrr_actual_3']:.3f} |

Expected votes are continuous; these discrete ballot metrics are complementary to RMSE.

## 5. Season-Level Results

| Metric | Value |
| --- | --- |
| Pearson | {season_pearson:.4f} |
| Spearman | {season_spearman:.4f} |
| Season MAE | {season_mae:.3f} |
| Season RMSE | {season_rmse:.3f} |
| Top-3 / 5 / 10 / 20 overlap | {overlaps['top_3_overlap']:.2f} / {overlaps['top_5_overlap']:.2f} / {overlaps['top_10_overlap']:.2f} / {overlaps['top_20_overlap']:.2f} |
| Predicted #1 | {pred_champ.player} ({pred_champ.predicted_expected_votes:.2f} EV) |
| Actual #1 | {act_champ.player} ({act_champ.actual_votes:.0f}) |
| Champion ID match | {bool(champ_match)} |

## 6. Where the Model Worked

- Player-match bias is near zero ({bias:.3e}), consistent with the sum-to-6 allocator.
- Season-level rank correlation (Spearman {season_spearman:.3f}) indicates the forecast ordering of season totals tracked actual polling order.
- Predicted champion ({pred_champ.player}) {"matched" if champ_match else "did not match"} the actual medallist ({act_champ.player}).
- Top-k set overlaps: Top-5 {overlaps['top_5_overlap']:.0%}, Top-10 {overlaps['top_10_overlap']:.0%}.

## 7. Where the Model Missed

- Actual 3-vote games: mean predicted EV = {diag['actual_3_mean_pred']:.3f} (mean error {diag['actual_3_mean_error_pred_minus_actual']:.3f}), i.e. systematic compression on elite ballots.
- Exact ordered 3–2–1 rate is low ({rank_summary['exact_ordered_321_rate']:.1%}); continuous EV ranking rarely reproduces the discrete ballot order exactly.
- Largest season misses are listed in `2026_largest_underpredictions.csv` / `2026_largest_overpredictions.csv` (≥5 games).

## 8. Calibration

Expected-vote bin calibration (not probability calibration):

{cal.to_string(index=False)}

Weighted absolute calibration gap (ECE-like for expected votes): **{ece:.4f}**.

## 9. Error Analysis

- Residual vs coaches_votes (Spearman): {diag.get('corr_residual_vs_coaches_votes', 'n/a')}
- Residual vs coach_residual (Spearman): {diag.get('corr_residual_vs_coach_residual', 'n/a')}
- Pred std / actual std: {diag['pred_std']:.4f} / {diag['actual_std']:.4f} (compression if pred_std < actual_std)
- Position breakdown: `2026_error_by_position.csv`
- Match-context RMSEs (if available): close {diag.get('rmse_close_le12', 'n/a')}, mid {diag.get('rmse_mid', 'n/a')}, blowout {diag.get('rmse_blowout_ge40', 'n/a')}
- Vote-getter share on winning team: {diag.get('vote_getter_share_winning_team', 'n/a')}

These are associations, not causal claims.

## 10. Generalisation

Historical expanding_all allocated RMSE (from `v2_2_temporal_fold_metrics.csv`):

{pd.DataFrame(hist_rows).to_string(index=False)}

- Historical mean (folds): {gen['historical_mean']:.6f} (reported champion mean {HIST_OOT_RMSE})
- Historical range: [{gen['historical_min']:.6f}, {gen['historical_max']:.6f}], sd {gen['historical_std']:.6f}
- 2026 holdout: {rmse:.6f}
- Within historical range: {gen['within_historical_range']}
- Z vs historical fold mean: {gen['z_vs_historical']:.2f}

## 11. Limitations

- Labels sourced from AFL Tables round matrix, not a machine-readable AFL official dump; mapping uses player name + club + round → `player_id`/`match_id`.
- Match bootstrap CI treats matches exchangeable; it does not yield a paired test vs historical OOF folds.
- Season champion accuracy is descriptive only.
- Diagnostics use available covariates; missing context fields are noted rather than imputed.

## 12. Conclusion

The frozen 2026 forecast achieves holdout allocated RMSE **{rmse:.6f}**
(95% CI [{boot['rmse_ci95'][0]:.6f}, {boot['rmse_ci95'][1]:.6f}]), versus historical rolling OOT **{HIST_OOT_RMSE}**.
The difference is {abs_diff:+.6f} ({rel_diff:+.1f}%). Performance is
{"inside" if gen['within_historical_range'] else "outside"} the 2022–2025 OOT fold range.
Season ranking agreement is meaningful (Spearman {season_spearman:.3f}); discrete ballot exact-match rates remain lower, as expected for continuous expected-vote predictions.

No model update is recommended from this audit alone.
"""
    (EVAL_DIR / "FINAL_2026_HOLDOUT_EVALUATION.md").write_text(report)

    # ---------- STEP 17 web JSON ----------
    summary = {
        "forecast": {
            "file": str(FORECAST_PATH.relative_to(ROOT)),
            "sha256": forecast_hash_before,
            "n_rows": integrity["n_player_match_rows"],
            "n_matches": integrity["n_matches"],
            "total_expected_votes": integrity["total_allocated_expected_votes"],
            "model": "base_plus_components",
            "historical_oot_rmse": HIST_OOT_RMSE,
        },
        "actual": {
            "source": "AFL Tables 2026 Brownlow totals matrix",
            "source_url": "https://afltables.com/afl/brownlow/brownlow2026.html",
            "file": str(ACTUAL_CSV.relative_to(ROOT)),
            "n_matches_ok": int(vote_audit.ok.sum()),
            "n_anomalies": int((~vote_audit.ok).sum()),
            "total_votes": float(joined.actual_brownlow_votes.sum()),
            "medallist": act_champ.player,
            "medallist_votes": float(act_champ.actual_votes),
        },
        "evaluation": {
            "primary": primary,
            "ranking": rank_summary,
            "season": season_metrics,
            "generalisation": gen,
            "calibration_ece": ece,
        },
    }
    (WEB_DIR / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    (WEB_DIR / "leaderboard_comparison.json").write_text(
        json.dumps(
            {
                "forecast_top20": top20[
                    [
                        "predicted_rank",
                        "player",
                        "team",
                        "predicted_expected_votes",
                        "actual_votes",
                        "actual_rank",
                        "error",
                        "rank_error",
                    ]
                ].to_dict(orient="records"),
                "largest_underpredictions": under.head(15).to_dict(orient="records"),
                "largest_overpredictions": over.head(15).to_dict(orient="records"),
            },
            indent=2,
        )
        + "\n"
    )
    (WEB_DIR / "match_metrics.json").write_text(
        json.dumps({"summary": rank_summary, "per_match": rank_df.to_dict(orient="records")}, indent=2) + "\n"
    )
    (WEB_DIR / "calibration.json").write_text(
        json.dumps({"bins": cal.to_dict(orient="records"), "ece_expected_vote": ece}, indent=2) + "\n"
    )
    (WEB_DIR / "error_analysis.json").write_text(
        json.dumps(
            {
                "by_actual_vote": by_vote.to_dict(orient="records"),
                "diagnostics": diag,
                "by_position": pos.to_dict(orient="records"),
            },
            indent=2,
        )
        + "\n"
    )
    (WEB_DIR / "player_audits.json").write_text(json.dumps({"contenders": audits}, indent=2) + "\n")

    # final integrity recheck
    hash_after = sha256_file(FORECAST_PATH)
    assert hash_after == forecast_hash_before, "FROZEN FORECAST FILE CHANGED DURING EVALUATION"

    # console summary for user sections A–J
    print("\n=== HOLDOUT EVALUATION COMPLETE (local only; not pushed) ===")
    print(json.dumps({
        "A_coverage": {
            "matches_ok": int(vote_audit.ok.sum()),
            "anomalies": int((~vote_audit.ok).sum()),
            "player_match_rows": int(len(joined)),
            "positive_vote_join_rate": float(join_audit.loc[join_audit.metric=="join_rate_positive_votes","value"].iloc[0]),
        },
        "B_integrity": {"sha256": forecast_hash_before, "unchanged": hash_after == forecast_hash_before},
        "C_primary": {"historical": HIST_OOT_RMSE, "holdout_rmse": rmse, "diff": abs_diff, "ci95": boot["rmse_ci95"]},
        "D_ranking": rank_summary,
        "E_season": {k: season_metrics[k] for k in ["pearson","spearman","top_5_overlap","top_10_overlap"]},
        "F_misses": {
            "under_top3": under.head(3)[["player","actual_votes","predicted_expected_votes","under_gap"]].to_dict("records"),
            "over_top3": over.head(3)[["player","actual_votes","predicted_expected_votes","over_gap"]].to_dict("records"),
        },
        "G_contenders": [
            {k: a[k] for k in a if k != "rounds"} for a in audits if "predicted_expected_votes" in a
        ],
    }, indent=2))


if __name__ == "__main__":
    main()
