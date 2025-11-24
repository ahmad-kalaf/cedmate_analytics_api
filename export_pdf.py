from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import pandas as pd
import json
import datetime
import os

from cedmate_analytics import generate_analytics_for_user, connect_firestore, fetch_for_user
from cedmate_analytics import OUTPUT_DIR  


def generate_export_pdf_for_user(user_id: str):
    """
    Creates a PDF summary for the given user.
    Includes:
      - Title page
      - All analytics plots (PNG)
      - Raw data tables (from Firestore)
    Uses only matplotlib (PdfPages).
    Returns the full output path.
    """

    print(f"📄 Starte PDF-Export für {user_id}")

    pdf_path = OUTPUT_DIR / f"export_{user_id}.pdf"

    # ------------------------------
    # 1. Fetch analytics + PNGs
    # ------------------------------
    results = generate_analytics_for_user(user_id)
    plot_paths = {k: Path(v) for k, v in results.items() if v and Path(v).exists()}

    # ------------------------------
    # 2. Fetch raw Firestore data
    # ------------------------------
    db_data = {}
    collections = ["stuhlgaenge", "stimmungen", "symptoms", "mahlzeiten"]

    # Re-fetch raw data (pandas DataFrames)
    
    db = connect_firestore()

    for col in collections:
        df = fetch_for_user(db, col, user_id)
        db_data[col] = df

    # ------------------------------
    # 3. Build PDF
    # ------------------------------
    with PdfPages(pdf_path) as pdf:

        # ----- Page 1: Title Page -----
        fig, ax = plt.subplots(figsize=(8.27, 11.69))  # A4 size
        ax.axis("off")

        title = "CEDmate – Datenexport"
        subtitle = f"Benutzer: {user_id}"
        timestamp = datetime.datetime.now().strftime("%d.%m.%Y – %H:%M")

        ax.text(0.5, 0.75, title, fontsize=24, ha="center", va="center")
        ax.text(0.5, 0.65, subtitle, fontsize=16, ha="center")
        ax.text(0.5, 0.60, f"Erstellt am: {timestamp}", fontsize=12, ha="center")

        pdf.savefig(fig)
        plt.close(fig)

        # ----- Pages 2+: Plots -----
        for name, path in plot_paths.items():
            fig, ax = plt.subplots(figsize=(8.27, 11.69))
            ax.axis("off")

            ax.set_title(name.capitalize(), fontsize=18, pad=20)

            img = plt.imread(str(path))
            ax.imshow(img)
            ax.axis("off")

            pdf.savefig(fig)
            plt.close(fig)

        # ----- Final pages: Raw Data -----
        for col, df in db_data.items():
            fig, ax = plt.subplots(figsize=(8.27, 11.69))
            ax.axis("off")

            ax.set_title(f"Rohdaten – {col}", fontsize=16, pad=20)

            if df.empty:
                ax.text(0.1, 0.8, "Keine Daten vorhanden.", fontsize=12)
            else:
                # Convert to table
                # Limit to first 30 rows for readability
                small_df = df.head(30)

                table = ax.table(
                    cellText=small_df.values,
                    colLabels=small_df.columns,
                    loc="center",
                    cellLoc="left",
                )
                table.scale(1, 1.2)

            pdf.savefig(fig)
            plt.close(fig)

    print(f"📄 PDF erstellt: {pdf_path}")
    return pdf_path
