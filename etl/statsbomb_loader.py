"""
statsbomb_loader.py — Carrega TODOS os dados StatsBomb Open Data (JSON) e salva como CSV.

Utiliza todas as competicoes disponíveis no dataset aberto do StatsBomb.
Os dados sao baixados via HTTP (GitHub) pelo pacote statsbombpy e convertidos
para 3 granularidades:
  - team_outcome  : uma linha por partida (resultado, placar, estatisticas de 1o tempo)
  - team_sog      : uma linha por partida (chutes, gols, distribuicao)
  - player_sog    : uma linha por jogador por partida

Cada competicao gera um contexto proprio:
  comp{competition_id}_s{season_id}_{nome_sanitizado}

Uso:
  python -m etl.statsbomb_loader           # processa tudo
  python -m etl.statsbomb_loader --force   # regenera mesmo que CSVs existam
"""

import sys
import re
import warnings
import argparse
from pathlib import Path

import pandas as pd

warnings.filterwarnings("ignore")

try:
    from statsbombpy import sb
except ImportError:
    print("[ERRO] statsbombpy nao instalado. Execute: pip install statsbombpy")
    sys.exit(1)

RAW_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"

SOG_OUTCOMES = {"Goal", "Saved", "Saved To Post"}
YELLOW_CARDS = {"Yellow Card", "Second Yellow"}
RED_CARDS    = {"Red Card"}


def _sanitize(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")


def _competition_type(comp_name: str) -> str:
    """Classifica o tipo de competicao para a feature competition_type."""
    low = comp_name.lower()
    if "world cup" in low and "women" not in low and "u20" not in low:
        return "World Cup"
    elif any(k in low for k in ("league", "liga", "ligue", "bundesliga",
                                "serie", "premier", "mls", "super league",
                                "indian", "profesional", "north american")):
        return "Domestic League"
    else:
        return "Continental"


def _cards_df(ev: pd.DataFrame) -> pd.DataFrame:
    parts = []
    if "foul_committed_card" in ev.columns:
        fc = ev[ev["foul_committed_card"].notna()][["period", "team", "foul_committed_card"]]
        parts.append(fc.rename(columns={"foul_committed_card": "card"}))
    if "bad_behaviour_card" in ev.columns:
        bb = ev[ev["bad_behaviour_card"].notna()][["period", "team", "bad_behaviour_card"]]
        parts.append(bb.rename(columns={"bad_behaviour_card": "card"}))
    return pd.concat(parts) if parts else pd.DataFrame(columns=["period", "team", "card"])


# ---------------------------------------------------------------------------
# Extracao por partida
# ---------------------------------------------------------------------------

def _outcome_row(mid, mrow, ev, context, comp_type):
    home = str(mrow["home_team"])
    away = str(mrow["away_team"])
    hs   = int(mrow["home_score"])
    as_  = int(mrow["away_score"])
    outcome = 0 if hs > as_ else (1 if hs == as_ else 2)

    shots    = ev[ev["type"] == "Shot"]
    shots_ht = shots[shots["period"] == 1]
    h_ht     = shots_ht[shots_ht["team"] == home]
    a_ht     = shots_ht[shots_ht["team"] == away]

    ht_shots_h = len(h_ht);   ht_shots_a = len(a_ht)
    ht_sog_h   = int(h_ht["shot_outcome"].isin(SOG_OUTCOMES).sum())
    ht_sog_a   = int(a_ht["shot_outcome"].isin(SOG_OUTCOMES).sum())
    ht_goals_h = int((h_ht["shot_outcome"] == "Goal").sum())
    ht_goals_a = int((a_ht["shot_outcome"] == "Goal").sum())
    total_goals = int((shots["shot_outcome"] == "Goal").sum())

    fouls_ht   = ev[(ev["type"] == "Foul Committed") & (ev["period"] == 1)]
    ht_fouls_h = int((fouls_ht["team"] == home).sum())
    ht_fouls_a = int((fouls_ht["team"] == away).sum())

    corners     = ev[(ev["type"] == "Pass") & (ev.get("pass_type", pd.Series(dtype=str)).eq("Corner")
                                                if "pass_type" in ev.columns
                                                else pd.Series([False]*len(ev), index=ev.index))]
    corners_ht  = corners[corners["period"] == 1]
    ht_corn_h   = int((corners_ht["team"] == home).sum())
    ht_corn_a   = int((corners_ht["team"] == away).sum())
    total_corn  = len(corners)

    cards = _cards_df(ev)
    ht_yel_h = int(((cards["period"]==1)&(cards["team"]==home)&(cards["card"].isin(YELLOW_CARDS))).sum())
    ht_yel_a = int(((cards["period"]==1)&(cards["team"]==away)&(cards["card"].isin(YELLOW_CARDS))).sum())
    total_yel = int(cards["card"].isin(YELLOW_CARDS).sum())
    total_red = int(cards["card"].isin(RED_CARDS).sum())

    return {
        "match_id": mid, "match_date": str(mrow["match_date"]),
        "home_team": home, "away_team": away, "home_score": hs, "away_score": as_,
        "outcome": outcome,
        "ht_goals_home": ht_goals_h,   "ht_goals_away": ht_goals_a,
        "ht_goals_diff": ht_goals_h - ht_goals_a,
        "ht_shots_home": ht_shots_h,   "ht_shots_away": ht_shots_a,
        "ht_shots_diff": ht_shots_h - ht_shots_a,
        "ht_sog_home": ht_sog_h,       "ht_sog_away": ht_sog_a,
        "ht_sog_diff": ht_sog_h - ht_sog_a,
        "ht_fouls_home": ht_fouls_h,   "ht_fouls_away": ht_fouls_a,
        "ht_fouls_diff": ht_fouls_h - ht_fouls_a,
        "ht_corners_home": ht_corn_h,  "ht_corners_away": ht_corn_a,
        "ht_yellow_cards_home": ht_yel_h, "ht_yellow_cards_away": ht_yel_a,
        "total_goals": total_goals, "total_corners": total_corn,
        "total_yellow_cards": total_yel, "total_red_cards": total_red,
        "source_context": context, "competition_type": comp_type,
    }


def _sog_row(mid, mrow, ev, context, comp_type):
    home = str(mrow["home_team"]); away = str(mrow["away_team"])
    hs   = int(mrow["home_score"]); as_  = int(mrow["away_score"])
    shots    = ev[ev["type"] == "Shot"]
    shots_ht = shots[shots["period"] == 1]
    h_ht = shots_ht[shots_ht["team"] == home]
    a_ht = shots_ht[shots_ht["team"] == away]
    total_goals     = hs + as_
    goals_home_frac = (hs / total_goals) if total_goals > 0 else 0.5
    return {
        "match_id": mid, "match_date": str(mrow["match_date"]),
        "ht_shots_home": len(h_ht),   "ht_shots_away": len(a_ht),
        "ht_sog_home": int(h_ht["shot_outcome"].isin(SOG_OUTCOMES).sum()),
        "ht_sog_away": int(a_ht["shot_outcome"].isin(SOG_OUTCOMES).sum()),
        "ht_goals_home": int((h_ht["shot_outcome"] == "Goal").sum()),
        "ht_goals_away": int((a_ht["shot_outcome"] == "Goal").sum()),
        "total_goals": total_goals, "goals_home_frac": goals_home_frac,
        "source_context": context, "competition_type": comp_type,
    }


def _player_rows(mid, match_date, ev, context, comp_type):
    rows = []
    for pid in ev["player_id"].dropna().unique():
        pev  = ev[ev["player_id"] == pid]
        name = pev["player"].dropna().iloc[0] if pev["player"].notna().any() else ""
        shots     = pev[pev["type"] == "Shot"]
        total_sog = int(shots["shot_outcome"].isin(SOG_OUTCOMES).sum())
        ht        = pev[pev["period"] == 1]
        ht_passes   = int((ht["type"] == "Pass").sum())
        ht_touches  = int((ht["type"] == "Carry").sum())
        ht_dribbles = int(((ht["type"] == "Dribble") &
                           (ht.get("dribble_outcome", pd.Series(dtype=str)) == "Complete")).sum())
        rows.append({
            "player_id": int(pid), "player_name": name,
            "match_id": mid, "match_date": str(match_date),
            "total_sog": total_sog,
            "ht_passes": ht_passes, "ht_touches": ht_touches, "ht_dribbles": ht_dribbles,
            "source_context": context, "competition_type": comp_type,
        })
    return rows


# ---------------------------------------------------------------------------
# Orquestrador principal
# ---------------------------------------------------------------------------

def build_raw_csvs(raw_dir: Path = RAW_DIR, force: bool = False):
    """
    Baixa e processa TODOS os dados StatsBomb Open Data.
    Cria um CSV por competicao/temporada por granularidade em raw_dir.
    """
    raw_dir.mkdir(parents=True, exist_ok=True)

    competitions = sb.competitions()
    total_comps  = len(competitions)
    print(f"  {total_comps} competicoes encontradas no StatsBomb Open Data.")

    grand_total_matches  = 0
    grand_total_players  = 0

    for idx, (_, crow) in enumerate(competitions.iterrows(), 1):
        cid   = int(crow["competition_id"])
        sid   = int(crow["season_id"])
        cname = str(crow["competition_name"])
        sname = str(crow["season_name"])
        ctx   = f"comp{cid}_s{sid}_{_sanitize(cname)}_{_sanitize(sname)}"
        ctype = _competition_type(cname)

        files = [raw_dir / f"{ctx}_{g}.csv" for g in ("team_outcome", "team_sog", "player_sog")]
        if not force and all(f.exists() for f in files):
            print(f"  [{idx}/{total_comps}] skip  {cname} {sname}")
            continue

        print(f"\n  [{idx}/{total_comps}] {cname} {sname}  (type={ctype})")

        try:
            matches = sb.matches(competition_id=cid, season_id=sid)
        except Exception as exc:
            print(f"  [AVISO] Nao foi possivel carregar partidas: {exc}")
            continue

        total = len(matches)
        print(f"  {total} partidas")

        rows_out, rows_sog, rows_plr = [], [], []

        for i, (_, mrow) in enumerate(matches.iterrows(), 1):
            mid = int(mrow["match_id"])
            sys.stdout.write(f"\r    {i}/{total} match_id={mid}   ")
            sys.stdout.flush()
            try:
                ev = sb.events(match_id=mid)
                rows_out.append(_outcome_row(mid, mrow, ev, ctx, ctype))
                rows_sog.append(_sog_row(mid, mrow, ev, ctx, ctype))
                rows_plr.extend(_player_rows(mid, mrow["match_date"], ev, ctx, ctype))
            except Exception as exc:
                print(f"\n    [AVISO] match_id={mid} ignorado: {exc}")

        print()
        if rows_out:
            pd.DataFrame(rows_out).to_csv(raw_dir / f"{ctx}_team_outcome.csv", index=False)
            pd.DataFrame(rows_sog).to_csv(raw_dir / f"{ctx}_team_sog.csv",     index=False)
            pd.DataFrame(rows_plr).to_csv(raw_dir / f"{ctx}_player_sog.csv",   index=False)
            grand_total_matches += len(rows_out)
            grand_total_players += len(rows_plr)
            print(f"  [ok] {len(rows_out)} partidas | {len(rows_plr)} registros de jogador")

    print(f"\n  === Total: {grand_total_matches} partidas | {grand_total_players} registros de jogador ===")
    print("  Conversao JSON -> CSV concluida.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="StatsBomb JSON -> CSV")
    parser.add_argument("--force", action="store_true", help="Regenera CSVs existentes")
    args = parser.parse_args()
    build_raw_csvs(force=args.force)
