"""Create portfolio chart exports from the prepared Ember CSV tables."""
from __future__ import annotations
import csv
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "visuals"
OUT.mkdir(exist_ok=True)
NAVY = "#16324F"
TEAL = "#0E8A8A"
ORANGE = "#D97932"
MUTED = "#64748B"
GRID = "#E4EBEF"


def load_csv(name):
    with (ROOT / "data" / name).open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))

summary = load_csv("fact_country_year.csv")
fuel_rows = load_csv("fact_generation_source.csv")
for r in summary:
    for k in ("Year", "Generation (TWh)", "Emissions intensity (gCO2e/kWh)"):
        r[k] = float(r[k]) if r[k] else np.nan
for r in fuel_rows:
    r["Year"] = int(r["Year"])
    r["Generation (TWh)"] = float(r["Generation (TWh)"] or 0)

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 10,
    "axes.labelcolor": NAVY, "text.color": NAVY,
    "xtick.color": MUTED, "ytick.color": MUTED,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.spines.left": False, "axes.spines.bottom": False,
    "figure.facecolor": "white", "axes.facecolor": "white",
})

# 1. Intensity trend among a small, transparent comparison set.
selected = ["China", "United States", "India", "Germany", "Brazil"]
colors = {"China": TEAL, "United States": NAVY, "India": ORANGE,
          "Germany": "#7B61A8", "Brazil": "#55A36B"}
fig, ax = plt.subplots(figsize=(11, 6.4), constrained_layout=True)
for country in selected:
    rows = sorted((r for r in summary if r["Area"] == country), key=lambda r: r["Year"])
    ax.plot([r["Year"] for r in rows], [r["Emissions intensity (gCO2e/kWh)"] for r in rows],
            color=colors[country], linewidth=2.5, label=country)
ax.set_title("Power-sector carbon intensity has followed different paths", loc="left", fontsize=17, weight="bold", pad=18)
ax.text(0, 1.015, "Solid line = reported intensity (left axis) · dashed = generation (right axis) · selected producers",
        transform=ax.transAxes, color=MUTED, fontsize=10)
ax.set_ylabel("gCO₂e per kWh")
ax.set_xlabel("Year")
ax.set_xlim(2000, 2024)
ax.set_xticks(range(2000, 2025, 4))
ax.grid(axis="y", color=GRID, linewidth=.9)
ax2 = ax.twinx()
for country in selected:
    rows = sorted((r for r in summary if r["Area"] == country), key=lambda r: r["Year"])
    ax2.plot([r["Year"] for r in rows], [r["Generation (TWh)"] for r in rows],
             color=colors[country], linewidth=2.0, linestyle="--", alpha=.72)
ax2.set_ylabel("Generation (TWh)", color=MUTED)
ax2.spines["right"].set_visible(True)
ax2.spines["right"].set_color(GRID)
ax2.tick_params(axis="y", colors=MUTED)
ax.legend(frameon=False, ncol=5, loc="upper center", bbox_to_anchor=(.5, -.12))
fig.text(.01, -.02, "Source: Ember Yearly Electricity Data (downloaded 12 Oct 2026). Country selection is illustrative.", color=MUTED, fontsize=8)
fig.savefig(OUT / "01_carbon_intensity_trends.png", dpi=180, bbox_inches="tight")
plt.close(fig)

# 2. Clean share vs intensity for the full selected cohort. Bubble size reflects generation.
by = {(r["Area"], int(r["Year"])): r for r in summary}
source_map = {}
for r in fuel_rows:
    source_map.setdefault((r["Area"], r["Year"]), {})[r["Electricity source"]] = r["Generation (TWh)"]
clean_sources = ["Solar", "Wind", "Hydro", "Bioenergy", "Other renewables", "Nuclear"]
fossil_sources = ["Coal", "Gas", "Other fossil"]
plot = []
for (country, year), row in by.items():
    if year != 2024 or not np.isfinite(row["Generation (TWh)"]):
        continue
    mix = source_map.get((country, year), {})
    total = row["Generation (TWh)"]
    clean = sum(mix.get(s, 0) for s in clean_sources)
    fossil = sum(mix.get(s, 0) for s in fossil_sources)
    plot.append((country, 100 * clean / total if total else np.nan,
                 row["Emissions intensity (gCO2e/kWh)"], total, 100 * fossil / total if total else np.nan))
fig, ax = plt.subplots(figsize=(11, 7), constrained_layout=True)
xx = [p[1] for p in plot]
yy = [p[2] for p in plot]
sizes = [45 + 260 * np.sqrt(p[3] / max(x[3] for x in plot)) for p in plot]
ax.scatter(xx, yy, s=sizes, c="#94A3B8", alpha=.72, edgecolor="white", linewidth=1.2, zorder=2)
focus = {"China", "United States", "India", "Germany", "Brazil"}
for country, x, y, gen, fossil in plot:
    if country in focus:
        ax.scatter([x], [y], s=95, c=colors[country], edgecolor="white", linewidth=1.2, zorder=3)
        offset = (7, 8) if country != "India" else (7, -14)
        ax.annotate(country, (x, y), xytext=offset, textcoords="offset points", fontsize=9, color=colors[country], weight="bold")
ax.set_title("A higher clean share does not always mean lower intensity", loc="left", fontsize=17, weight="bold", pad=18)
ax.text(0, 1.015, "2024 · 30 largest producers by reported generation · bubble size = total generation",
        transform=ax.transAxes, color=MUTED, fontsize=10)
ax.set_xlabel("Clean generation share (%) · includes nuclear")
ax.set_ylabel("Reported emissions intensity (gCO₂e/kWh)")
ax.grid(color=GRID, linewidth=.9)
ax.set_axisbelow(True)
fig.text(.01, -.02, "Source: Ember Yearly Electricity Data (downloaded 12 Oct 2026). Clean = nuclear + renewables.", color=MUTED, fontsize=8)
fig.savefig(OUT / "02_clean_share_vs_intensity_2024.png", dpi=180, bbox_inches="tight")
plt.close(fig)

# 3. 100% stacked fuel mix for five example producers.
fuel_order = ["Coal", "Gas", "Other fossil", "Nuclear", "Hydro", "Wind", "Solar", "Bioenergy", "Other renewables"]
fuel_colors = {"Coal": "#9B4A36", "Gas": "#D97932", "Other fossil": "#E6AD56",
               "Nuclear": "#7565A9", "Hydro": "#318D94", "Wind": "#61B9AA",
               "Solar": "#E4C84F", "Bioenergy": "#7EAA67", "Other renewables": "#9BBA8B"}
fig, ax = plt.subplots(figsize=(11, 6.6), constrained_layout=True)
for country in selected:
    row = by.get((country, 2024))
    if not row or not row["Generation (TWh)"]:
        continue
    total = row["Generation (TWh)"]
    mix = source_map.get((country, 2024), {})
    left = 0
    for source in fuel_order:
        value = 100 * mix.get(source, 0) / total
        ax.barh(country, value, left=left, color=fuel_colors[source], height=.62,
                label=source if country == selected[0] else None)
        left += value
ax.set_xlim(0, 100)
ax.invert_yaxis()
ax.set_xlabel("Share of total generation (%)")
ax.set_title("The 2024 electricity mix varies widely", loc="left", fontsize=17, weight="bold", pad=18)
ax.text(0, 1.015, "Selected large producers · source categories shown individually",
        transform=ax.transAxes, color=MUTED, fontsize=10)
ax.grid(axis="x", color=GRID, linewidth=.9)
ax.set_axisbelow(True)
ax.legend(frameon=False, ncol=3, loc="upper center", bbox_to_anchor=(.5, -.15))
fig.text(.01, -.03, "Source: Ember Yearly Electricity Data (downloaded 12 Oct 2026). Aggregate fuel rows excluded.", color=MUTED, fontsize=8)
fig.savefig(OUT / "03_generation_mix_2024.png", dpi=180, bbox_inches="tight")
plt.close(fig)
print(f"Saved three charts to {OUT}")
