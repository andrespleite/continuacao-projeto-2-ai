"""
=============================================================================
 Premier League Historical Data Downloader
 Source: football-data.co.uk
 
 Downloads all Premier League seasons (1993/94 → 2025/26) and consolidates
 into a single CSV file ready for ML pipelines.
 
 Usage:
   python download_premier_league.py
   
 Output:
   ./premier_league_all_seasons.csv   (consolidated dataset)
   ./data/raw/E0_XXYY.csv            (individual season files)
=============================================================================
"""

import pandas as pd
import requests
import os
import time
import sys
from io import StringIO

# ─── Configuration ──────────────────────────────────────────────────────────

BASE_URL = "https://www.football-data.co.uk/mmz4281/{season}/E0.csv"
OUTPUT_DIR = "./data/raw"
OUTPUT_FILE = "./premier_league_all_seasons.csv"

# All available Premier League seasons (oldest → newest)
SEASONS = [
    "9394", "9495", "9596", "9697", "9798", "9899", "9900",  # 1993-2000
    "0001", "0102", "0203", "0304", "0405", "0506", "0607",  # 2000-2007
    "0708", "0809", "0910", "1011", "1112", "1213", "1314",  # 2007-2014
    "1415", "1516", "1617", "1718", "1819", "1920", "2021",  # 2014-2021
    "2122", "2223", "2324", "2425", "2526",                   # 2021-2026
]

# Core columns to keep (present in most seasons)
# Stats columns only available from 2000/01 onwards
CORE_COLUMNS = [
    "Season",       # added by script
    "Date",         # match date
    "HomeTeam",     # home team name
    "AwayTeam",     # away team name
    "FTHG",         # full time home goals
    "FTAG",         # full time away goals
    "FTR",          # full time result (H/D/A)
    "HTHG",         # half time home goals
    "HTAG",         # half time away goals
    "HTR",          # half time result
]

STATS_COLUMNS = [
    "HS",           # home shots
    "AS",           # away shots
    "HST",          # home shots on target
    "AST",          # away shots on target
    "HF",           # home fouls
    "AF",           # away fouls
    "HC",           # home corners
    "AC",           # away corners
    "HY",           # home yellow cards
    "AY",           # away yellow cards
    "HR",           # home red cards
    "AR",           # away red cards
    "Referee",      # referee name
]

ODDS_COLUMNS = [
    "B365H",        # Bet365 home odds
    "B365D",        # Bet365 draw odds
    "B365A",        # Bet365 away odds
]


def season_label(code: str) -> str:
    """Convert season code to readable label: '2425' → '2024/25'"""
    if len(code) == 4:
        first, second = int(code[:2]), int(code[2:])
        # Handle century boundary
        if first >= 90:
            return f"19{first:02d}/{second:02d}"
        else:
            return f"20{first:02d}/{second:02d}"
    return code


def download_season(season_code: str) -> pd.DataFrame | None:
    """Download a single season CSV and return as DataFrame."""
    url = BASE_URL.format(season=season_code)
    label = season_label(season_code)
    
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        
        # Some older files may have encoding issues
        for encoding in ["utf-8", "latin-1", "cp1252"]:
            try:
                df = pd.read_csv(
                    StringIO(response.content.decode(encoding)),
                    on_bad_lines="skip"
                )
                break
            except (UnicodeDecodeError, Exception):
                continue
        else:
            print(f"  ✗ {label} — encoding error")
            return None
        
        # Drop completely empty rows
        df.dropna(how="all", inplace=True)
        
        # Skip empty dataframes
        if df.empty or "HomeTeam" not in df.columns:
            print(f"  ✗ {label} — empty or invalid")
            return None
        
        # Add season label
        df["Season"] = label
        
        # Select available columns
        available = [c for c in CORE_COLUMNS + STATS_COLUMNS + ODDS_COLUMNS if c in df.columns]
        df = df[available]
        
        n_matches = len(df)
        n_stats = sum(1 for c in STATS_COLUMNS if c in df.columns)
        n_odds = sum(1 for c in ODDS_COLUMNS if c in df.columns)
        
        print(f"  ✓ {label} — {n_matches} matches | {n_stats} stat cols | {n_odds} odds cols")
        return df
        
    except requests.exceptions.RequestException as e:
        print(f"  ✗ {label} — download failed: {e}")
        return None


def main():
    print("=" * 65)
    print(" Premier League Historical Data Downloader")
    print(" Source: football-data.co.uk")
    print("=" * 65)
    print()
    
    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    all_seasons = []
    failed = []
    
    print(f"Downloading {len(SEASONS)} seasons...\n")
    
    for code in SEASONS:
        df = download_season(code)
        
        if df is not None:
            # Save individual season file
            filepath = os.path.join(OUTPUT_DIR, f"E0_{code}.csv")
            df.to_csv(filepath, index=False)
            all_seasons.append(df)
        else:
            failed.append(season_label(code))
        
        # Be polite to the server
        time.sleep(0.5)
    
    print()
    
    if not all_seasons:
        print("No data downloaded. Check your internet connection.")
        sys.exit(1)
    
    # Consolidate all seasons
    print("Consolidating all seasons...")
    consolidated = pd.concat(all_seasons, ignore_index=True)
    
    # Parse dates properly
    consolidated["Date"] = pd.to_datetime(
        consolidated["Date"], 
        dayfirst=True,   # UK date format: DD/MM/YYYY
        format="mixed",
        errors="coerce"
    )
    
    # Sort by date
    consolidated.sort_values("Date", inplace=True)
    consolidated.reset_index(drop=True, inplace=True)
    
    # Save consolidated file
    consolidated.to_csv(OUTPUT_FILE, index=False)
    
    # ─── Summary Report ────────────────────────────────────────────────
    print()
    print("=" * 65)
    print(" DOWNLOAD COMPLETE")
    print("=" * 65)
    print(f"  Total matches:    {len(consolidated):,}")
    print(f"  Seasons:          {len(all_seasons)}")
    print(f"  Date range:       {consolidated['Date'].min().strftime('%Y-%m-%d')} → "
          f"{consolidated['Date'].max().strftime('%Y-%m-%d')}")
    print(f"  Unique teams:     {consolidated['HomeTeam'].nunique()}")
    print()
    
    # Column availability summary
    print("  Column availability:")
    for col in STATS_COLUMNS + ODDS_COLUMNS:
        if col in consolidated.columns:
            n_valid = consolidated[col].notna().sum()
            pct = n_valid / len(consolidated) * 100
            print(f"    {col:10s} → {n_valid:>6,} rows ({pct:.0f}%)")
    
    print()
    print(f"  Output:           {OUTPUT_FILE}")
    print(f"  Individual files: {OUTPUT_DIR}/")
    
    if failed:
        print(f"\n  Failed seasons:   {', '.join(failed)}")
    
    # Quick class distribution
    print()
    print("  Result distribution (FTR):")
    counts = consolidated["FTR"].value_counts()
    for result, count in counts.items():
        pct = count / len(consolidated) * 100
        label = {"H": "Home Win", "D": "Draw", "A": "Away Win"}.get(result, result)
        print(f"    {label:10s} → {count:>5,} ({pct:.1f}%)")
    
    print()
    print("  Done! Ready for ML pipeline.")
    print("=" * 65)


if __name__ == "__main__":
    main()