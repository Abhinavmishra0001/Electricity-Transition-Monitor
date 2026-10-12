"""Prepare Ember annual electricity data for the Power BI portfolio project.

Run from this directory: python3 prepare_data.py
Uses only Python's standard library.
"""
from __future__ import annotations
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "data" / "ember_global_yearly.csv"
FACT = ROOT / "data" / "fact_country_year.csv"
GENERATION = ROOT / "data" / "fact_generation_source.csv"
START_YEAR, END_YEAR = 2000, 2024


def num(value: str) -> float | None:
    return float(value) if value not in ("", "NA", "null") else None


def main() -> None:
    with RAW.open(newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    selected = [r for r in rows if r["Area type"] == "Country or economy"
                and START_YEAR <= int(r["Year"]) <= END_YEAR]
    total_rows = [r for r in selected if r["Electricity source"] == "Total generation"]
    latest = {}
    for r in total_rows:
        if r["Year"] == str(END_YEAR) and num(r["Generation (TWh)"]) is not None:
            latest[r["Area"]] = num(r["Generation (TWh)"])
    top_areas = {area for area, _ in sorted(latest.items(), key=lambda x: x[1], reverse=True)[:30]}
    selected = [r for r in selected if r["Area"] in top_areas]

    total_by_key = {}
    for r in selected:
        if r["Electricity source"] == "Total generation":
            total_by_key[(r["Area"], r["Year"])] = r

    summary_fields = ["Area", "ISO 3 code", "Year", "Continent", "Ember region",
                      "Generation (TWh)", "Emissions (MtCO2e)",
                      "Emissions intensity (gCO2e/kWh)"]
    summary_rows = []
    for r in total_rows:
        if r["Area"] not in top_areas:
            continue
        summary_rows.append({
            "Area": r["Area"], "ISO 3 code": r["ISO 3 code"], "Year": r["Year"],
            "Continent": r["Continent"], "Ember region": r["Ember region"],
            "Generation (TWh)": r["Generation (TWh)"],
            "Emissions (MtCO2e)": r["Emissions (MtCO2e)"],
            "Emissions intensity (gCO2e/kWh)": r["Emissions intensity (gCO2e/kWh)"],
        })
    with FACT.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=summary_fields); w.writeheader(); w.writerows(summary_rows)

    detail = [r for r in selected if r["Is aggregated source"].lower() == "false"
              and r["Electricity source"] not in ("Demand", "Net imports")]
    detail_fields = ["Area", "ISO 3 code", "Year", "Electricity source", "Generation (TWh)",
                     "Share of generation (%)", "Capacity (GW)", "Emissions (MtCO2e)",
                     "Emissions intensity (gCO2e/kWh)"]
    with GENERATION.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=detail_fields); w.writeheader()
        w.writerows({k: r.get(k, "") for k in detail_fields} for r in detail)

    print(f"Selected {len(top_areas)} countries, {len(summary_rows)} country-years, "
          f"{len(detail)} fuel rows ({START_YEAR}-{END_YEAR}).")

if __name__ == "__main__":
    main()
