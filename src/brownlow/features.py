from __future__ import annotations
import numpy as np
import pandas as pd

ID_COLS = {"brownlow_votes", "match_id", "player_id", "season"}
RAW_NUMERIC = [
    "coaches_votes","supercoach_score","afl_fantasy_score","rating_points","kicks","marks","handballs",
    "disposals","effective_disposals","goals","behinds","hitouts","tackles","rebounds","inside_fifties",
    "clearances","clangers","free_kicks_for","free_kicks_against","contested_possessions",
    "uncontested_possessions","contested_marks","marks_inside_fifty","one_percenters","bounces","goal_assists",
    "time_on_ground_percentage","centre_clearances","stoppage_clearances","score_involvements","metres_gained",
    "turnovers","intercepts","tackles_inside_fifty","contest_def_losses","contest_def_one_on_ones",
    "contest_off_one_on_ones","contest_off_wins","def_half_pressure_acts","effective_kicks","f50_ground_ball_gets",
    "ground_ball_gets","hitouts_to_advantage","intercept_marks","marks_on_lead","pressure_acts","ruck_contests",
    "score_launches","shots_at_goal","spoils"
]
RELATIVE_BASE = [
    "coaches_votes","supercoach_score","afl_fantasy_score","rating_points","disposals","effective_disposals",
    "goals","tackles","inside_fifties","clearances","contested_possessions","score_involvements","metres_gained",
    "intercepts","pressure_acts","hitouts_to_advantage","marks_inside_fifty","goal_assists","spoils"
]

def _safe_div(a, b):
    return a / b.replace(0, np.nan)

def add_context(df: pd.DataFrame) -> pd.DataFrame:
    x = df.copy()
    x["team_won"] = (x.player_team == x.match_winner).astype("int8")
    x["close_game"] = (x.match_margin.abs() <= 12).astype("int8")
    x["blowout"] = (x.match_margin.abs() >= 40).astype("int8")
    x["is_2020"] = (x.season == 2020).astype("int8")
    x["goals_3p"] = (x.goals >= 3).astype("int8")
    x["goals_5p"] = (x.goals >= 5).astype("int8")
    x["disp_30p"] = (x.disposals >= 30).astype("int8")
    x["disp_35p"] = (x.disposals >= 35).astype("int8")
    x["clear_10p"] = (x.clearances >= 10).astype("int8")
    x["tackles_10p"] = (x.tackles >= 10).astype("int8")
    return x

def add_match_relative(df: pd.DataFrame) -> pd.DataFrame:
    x = df.copy()
    g = x.groupby("match_id", observed=True)
    for c in RELATIVE_BASE:
        if c not in x: continue
        mean = g[c].transform("mean")
        std = g[c].transform("std").replace(0, np.nan)
        x[f"{c}__match_z"] = ((x[c] - mean) / std).fillna(0)
        x[f"{c}__match_pct"] = g[c].rank(pct=True, method="average")
        x[f"{c}__match_rank"] = g[c].rank(ascending=False, method="average")
        total = g[c].transform("sum")
        x[f"{c}__match_share"] = _safe_div(x[c], total).fillna(0)
    return x

def add_team_relative(df: pd.DataFrame) -> pd.DataFrame:
    x = df.copy()
    g = x.groupby(["match_id", "player_team"], observed=True)
    for c in ["disposals","clearances","contested_possessions","score_involvements","metres_gained","goals","intercepts"]:
        total = g[c].transform("sum")
        x[f"{c}__team_share"] = _safe_div(x[c], total).fillna(0)
        x[f"{c}__team_rank"] = g[c].rank(ascending=False, method="average")
    return x

def add_lagged_history(df: pd.DataFrame) -> pd.DataFrame:
    # Strictly past matches only. Safe for rolling CV and 2026 inference.
    x = df.sort_values(["match_date", "match_id", "player_id"]).copy()
    gp = x.groupby("player_id", observed=True, sort=False)
    past_games = gp.cumcount()
    past_votes = gp.brownlow_votes.transform(lambda s: s.fillna(0).cumsum().shift(1))
    past_polls = gp.brownlow_votes.transform(lambda s: s.fillna(0).gt(0).cumsum().shift(1))
    x["career_games_prior"] = past_games
    x["career_votes_prior"] = past_votes.fillna(0)
    x["career_vote_rate_prior"] = (x.career_votes_prior / x.career_games_prior.replace(0, np.nan)).fillna(0)
    x["career_poll_rate_prior"] = (past_polls.fillna(0) / x.career_games_prior.replace(0, np.nan)).fillna(0)
    return x.sort_index()

def build_features(df: pd.DataFrame) -> pd.DataFrame:
    x = add_context(df)
    x = add_match_relative(x)
    x = add_team_relative(x)
    x = add_lagged_history(x)
    return x

CATEGORICAL = ["venue_name","player_team","player_position","match_home_team","match_away_team"]
DROP_ALWAYS = ["brownlow_votes","player_first_name","player_last_name","team_coach","match_winner","match_date","match_local_time"]

def model_columns(df: pd.DataFrame):
    cats = [c for c in CATEGORICAL if c in df.columns]
    nums = [c for c in df.columns if c not in set(DROP_ALWAYS + cats) and pd.api.types.is_numeric_dtype(df[c])]
    # Avoid raw IDs as memorisation shortcuts by default; history features encode prior recognition safely.
    nums = [c for c in nums if c not in ["match_id","player_id"]]
    return nums, cats
