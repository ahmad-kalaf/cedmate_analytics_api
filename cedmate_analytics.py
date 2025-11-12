"""
CEDmate Analytics Plugin – robust
"""

import argparse
from pathlib import Path
import matplotlib.pyplot as plt
import pandas as pd
import firebase_admin
from firebase_admin import credentials, firestore

# -------------------------------------------------------------------
# Paths
# -------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = SCRIPT_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


# -------------------------------------------------------------------
# Firestore init
# -------------------------------------------------------------------
def connect_firestore(service_account_path: str | None = None):
    """
    Initialisiert Firestore; findet serviceAccount.json robust.
    - Default: lib/analytics/serviceAccount.json (neben diesem Skript)
    - Optional: Pfad via --creds übergeben
    """
    sa_path = Path(
        service_account_path) if service_account_path else SCRIPT_DIR / "serviceAccount.json"
    if not sa_path.exists():
        raise FileNotFoundError(
            f"serviceAccount.json nicht gefunden unter: {sa_path}\n"
            f"Lege die Datei hier ab: {SCRIPT_DIR}"
        )

    cred = credentials.Certificate(str(sa_path))
    try:
        firebase_admin.get_app()
    except ValueError:
        firebase_admin.initialize_app(cred)
    return firestore.client()


# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------
def _convert_firestore_timestamps(entry: dict):
    for k, v in list(entry.items()):
        # firebase_admin liefert Timestamp-Objekte mit .to_datetime()
        if hasattr(v, "to_datetime"):
            entry[k] = v.to_datetime()
    return entry


def _detect_time_col(df: pd.DataFrame) -> str | None:
    # 1) echte Datetime-Spalten
    dt_cols = [c for c in df.columns if pd.api.types.is_datetime64_any_dtype(df[c])]
    if dt_cols:
        return dt_cols[0]
    # 2) Spaltennamen-Heuristik
    name_order = ["zeit", "time", "datum", "date", "timestamp", "startzeit", "endzeit",
                  "mahlzeitzeitpunkt"]
    for key in name_order:
        cand = [c for c in df.columns if key in c.lower()]
        if cand:
            # versuche zu parsen
            try:
                df[cand[0]] = pd.to_datetime(df[cand[0]])
                return cand[0]
            except Exception:
                continue
    return None


def _detect_value_col(df: pd.DataFrame, preference: list[str]) -> str | None:
    # bevorzugte Namen
    for name in preference:
        cols = [c for c in df.columns if name == c.lower()]
        if cols and pd.api.types.is_numeric_dtype(df[cols[0]]):
            return cols[0]
    # sonst erste numerische Spalte
    num_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    return num_cols[0] if num_cols else None


def _df_from_user_subcollection(db, user_id: str, subcollection: str) -> pd.DataFrame:
    user_ref = db.collection("users").document(user_id)
    docs = user_ref.collection(subcollection).get()
    rows = []
    for d in docs:
        entry = d.to_dict() or {}
        entry["id"] = d.id
        rows.append(_convert_firestore_timestamps(entry))
    df = pd.DataFrame(rows) if rows else pd.DataFrame()
    print(f"Fetched {len(df)} docs from users/{user_id}/{subcollection}")
    return df


# -------------------------------------------------------------------
# Fetch layer (angepasst an deine Struktur)
# -------------------------------------------------------------------
def fetch_for_user(db, collection_name: str, user_id: str) -> pd.DataFrame:
    """
    Holt Daten aus users/<userId>/<collection_name>.
    collection_name z. B.: 'mahlzeiten', 'symptoms', 'stimmung', 'stuhlgang'
    """
    return _df_from_user_subcollection(db, user_id, collection_name)


# -------------------------------------------------------------------
# Plotter
# -------------------------------------------------------------------
def plot_stuhlgang(df: pd.DataFrame, user_id: str):
    if df.empty:
        print(f"No stuhlgang entries for '{user_id}'.")
        return None

    tcol = _detect_time_col(df)
    vcol = _detect_value_col(df,
                             ["konsistenz", "bristol", "typ", "score", "wert", "level",
                              "intensitaet", "intensität", "staerke", "stärke"]
                             )
    if not tcol or not vcol:
        print("Stuhlgang: keine geeignete Zeit/ Wert-Spalte gefunden.")
        return None

    out_path = OUTPUT_DIR / f"stuhlgang_scatter_{user_id}.png"
    plt.figure(figsize=(10, 5))
    plt.scatter(df[tcol], df[vcol], c=df[vcol])
    plt.xlabel("Zeit")
    plt.ylabel(vcol)
    plt.title(f"Stuhlgang – {user_id}")
    plt.tight_layout()
    plt.savefig(out_path)
    plt.close()
    return out_path


def plot_stimmung(df: pd.DataFrame, user_id: str):
    if df.empty:
        print(f"No stimmung entries for '{user_id}'.")
        return None

    tcol = _detect_time_col(df)
    vcol = _detect_value_col(df, ["wert", "score", "level"])
    if not tcol or not vcol:
        print("Stimmung: keine geeignete Zeit/ Wert-Spalte gefunden.")
        return None

    df = df.sort_values(tcol)
    out_path = OUTPUT_DIR / f"stimmung_line_{user_id}.png"
    plt.figure(figsize=(10, 5))
    plt.plot(df[tcol], df[vcol])
    plt.xlabel("Zeit")
    plt.ylabel("Stimmungswert")
    plt.title(f"Stimmung – {user_id}")
    plt.tight_layout()
    plt.savefig(out_path)
    plt.close()
    return out_path


def plot_symptome(df: pd.DataFrame, user_id: str):
    if df.empty:
        print(f"No symptome entries for '{user_id}'.")
        return None

    tcol = _detect_time_col(df)
    vcol = _detect_value_col(df,
                             ["intensitaet", "intensität", "staerke", "stärke", "wert", "score",
                              "level", "schmerz", "severity"]
                             )
    if not tcol or not vcol:
        print("Symptome: keine geeignete Zeit/ Wert-Spalte gefunden.")
        return None

    out_path = OUTPUT_DIR / f"symptome_scatter_{user_id}.png"
    plt.figure(figsize=(10, 5))
    plt.scatter(df[tcol], df[vcol], c=df[vcol])
    plt.xlabel("Zeit")
    plt.ylabel("Symptomstärke")
    plt.title(f"Symptome – {user_id}")
    plt.tight_layout()
    plt.savefig(out_path)
    plt.close()
    return out_path


def plot_mahlzeit(df: pd.DataFrame, user_id: str):
    """
    Erstellt ein Balkendiagramm mit der Anzahl der Mahlzeiten pro Tag.
    Erwartet eine Spalte mit Datum/Zeit (z. B. 'mahlzeitZeitpunkt').
    """
    if df.empty:
        print(f"No mahlzeiten entries for '{user_id}'.")
        return None

    # Zeitspalte automatisch erkennen (z. B. 'mahlzeitZeitpunkt')
    tcol = _detect_time_col(df)
    if not tcol:
        print("Mahlzeiten: keine Zeitspalte gefunden.")
        return None

    # sicherstellen, dass Spalte als datetime erkannt wird
    df[tcol] = pd.to_datetime(df[tcol], errors='coerce')
    df = df.dropna(subset=[tcol])

    # Gruppierung nach Datum
    df["datum"] = df[tcol].dt.date
    counts = df.groupby("datum").size()

    if counts.empty:
        print("Mahlzeiten: keine gruppierbaren Daten gefunden.")
        return None

    out_path = OUTPUT_DIR / f"mahlzeiten_bars_{user_id}.png"

    # Plot: Anzahl der Mahlzeiten pro Tag
    plt.figure(figsize=(10, 5))
    counts.plot(kind="bar", color="cornflowerblue", edgecolor="black")
    plt.xlabel("Datum")
    plt.ylabel("Anzahl Mahlzeiten")
    plt.title(f"Mahlzeiten pro Tag – {user_id}")
    plt.tight_layout()
    plt.savefig(out_path)
    plt.close()

    print(f"Saved Mahlzeiten diagram to {out_path}")
    return out_path


# -------------------------------------------------------------------
# Orchestrierung
# -------------------------------------------------------------------
def generate_analytics_for_user(user_id: str, service_account: str | None = None):
    """
    Einheitlicher Einstieg für CLI & Flutter.
    """
    db = connect_firestore(service_account)

    # ACHTUNG: Sammlungsnamen so wie in Firestore
    data = {
        "stuhlgang": fetch_for_user(db, "stuhlgaenge", user_id),
        "stimmung": fetch_for_user(db, "stimmungen", user_id),
        "symptome": fetch_for_user(db, "symptoms", user_id),  # englisch
        "mahlzeit": fetch_for_user(db, "mahlzeiten", user_id),  # plural
    }

    return {
        "stuhlgang": plot_stuhlgang(data["stuhlgang"], user_id),
        "stimmung": plot_stimmung(data["stimmung"], user_id),
        "symptome": plot_symptome(data["symptome"], user_id),
        "mahlzeit": plot_mahlzeit(data["mahlzeit"], user_id),
    }


# -------------------------------------------------------------------
# CLI
# -------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Generate CEDmate analytics for a specific user.")
    parser.add_argument("--user", required=True, help="Firebase UID des Users (users/<uid>/...)")
    parser.add_argument("--creds", help="Pfad zur serviceAccount.json (optional)")
    args = parser.parse_args()

    results = generate_analytics_for_user(args.user, args.creds)
    print("\n✓ Analytics complete.")
    for k, v in results.items():
        print(f"  {k}: {v if v else 'no output'}")


if __name__ == "__main__":
    main()
