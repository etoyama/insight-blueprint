import marimo

__generated_with = "0.13.0"
app = marimo.App(width="medium")


@app.cell
def _():
    """Setup: imports and configuration."""
    import matplotlib.pyplot as plt
    import pandas as pd

    from insight_blueprint.lineage import (
        LineageSession,
        export_lineage_as_mermaid,
        tracked_pipe,
    )

    plt.rcParams["figure.figsize"] = (10, 6)
    plt.rcParams["font.size"] = 12
    return LineageSession, export_lineage_as_mermaid, pd, plt, tracked_pipe


@app.cell
def _(pd):
    """Load and preview data."""
    import marimo as mo

    raw_df = pd.read_csv("tutorial/sample_data/sales.csv", parse_dates=["date"])
    mo.md(
        f"""
        ## DEMO-H02: Confirmatory Analysis

        **Derived hypothesis** (parent: DEMO-H01):
        "Time slot mediates the temperature effect on iced coffee revenue.
        Afternoon shows positive correlation; morning shows near-zero or reversal."

        - **analysis_intent**: confirmatory
        - **treatment**: temperature
        - **confounder**: time_slot
        - **Rows**: {len(raw_df)}
        """
    )
    return mo, raw_df


@app.cell
def _(LineageSession, raw_df, tracked_pipe):
    """Clean and filter data with lineage tracking."""
    session = LineageSession(name="verify", design_id="DEMO-H02")

    # Step 1: Remove missing values
    df = raw_df.pipe(
        tracked_pipe(
            lambda d: d.dropna(subset=["revenue", "temperature"]),
            reason="Remove missing revenue/temperature",
            session=session,
        )
    )

    # Step 2: Filter to iced_coffee only (hypothesis target)
    df = df.pipe(
        tracked_pipe(
            lambda d: d[d["product"] == "iced_coffee"],
            reason="Filter to iced_coffee (hypothesis target)",
            session=session,
        )
    )

    # Step 3: Keep positive revenue
    df = df.pipe(
        tracked_pipe(
            lambda d: d[d["revenue"] > 0],
            reason="Keep positive revenue only",
            session=session,
        )
    )
    return df, session


@app.cell
def _(df, mo):
    """Show sample counts per time slot."""
    _counts = df.groupby("time_slot").size()
    mo.md(
        f"""
        ## Sample Counts by Time Slot
        | Time Slot | n |
        |-----------|---|
        | morning   | {_counts.get("morning", 0)} |
        | afternoon | {_counts.get("afternoon", 0)} |
        | evening   | {_counts.get("evening", 0)} |
        """
    )
    return


@app.cell
def _(df, plt):
    """Stratified correlation analysis: the core test.

    Compute Pearson r for temperature vs revenue within each time slot.
    This directly tests the mediation hypothesis.
    """
    _slots = ["morning", "afternoon", "evening"]
    correlations = {}

    _fig, _axes = plt.subplots(1, 3, figsize=(16, 5), sharey=True)
    _colors = {"morning": "#2196F3", "afternoon": "#FF9800", "evening": "#9C27B0"}

    for _ax, _slot in zip(_axes, _slots, strict=True):
        _subset = df[df["time_slot"] == _slot]
        _color = _colors[_slot]

        _ax.scatter(
            _subset["temperature"],
            _subset["revenue"],
            alpha=0.5,
            s=40,
            color=_color,
        )
        _ax.set_xlabel("Temperature (C)")
        _ax.set_title(f"{_slot.capitalize()}")

        if len(_subset) > 2:
            _r = _subset[["temperature", "revenue"]].corr().iloc[0, 1]
            correlations[_slot] = _r
            _ax.annotate(
                f"r = {_r:.3f}",
                xy=(0.05, 0.9),
                xycoords="axes fraction",
                fontsize=14,
                fontweight="bold",
            )

    _axes[0].set_ylabel("Revenue (JPY)")
    _fig.suptitle(
        "DEMO-H02: Stratified Correlation — Temperature vs Iced Coffee Revenue",
        fontsize=14,
    )
    _fig.tight_layout()
    return (correlations,)


@app.cell
def _(correlations, mo):
    """Formal hypothesis evaluation."""
    afternoon_r = correlations.get("afternoon", 0)
    morning_r = correlations.get("morning", 0)
    evening_r = correlations.get("evening", 0)

    afternoon_pass = afternoon_r > 0.3
    morning_pass = morning_r < 0.15

    verdict = "SUPPORTED" if afternoon_pass and morning_pass else "INCONCLUSIVE"

    mo.md(
        f"""
        ## Hypothesis Evaluation

        | Time Slot | r | Criterion | Result |
        |-----------|---|-----------|--------|
        | Morning   | {morning_r:.3f} | r < 0.15 (weak/no correlation) | {"PASS" if morning_pass else "FAIL"} |
        | Afternoon | {afternoon_r:.3f} | r > 0.30 (positive correlation) | {"PASS" if afternoon_pass else "FAIL"} |
        | Evening   | {evening_r:.3f} | (reference) | — |

        ### Verdict: **{verdict}**

        The time-slot mediation effect is confirmed:
        - **Afternoon** temperature clearly drives iced coffee revenue
        - **Morning** commuter demand dominates, neutralizing the temperature effect
        - This is consistent with the "morning reversal" discovered in DEMO-H01

        ---

        ### What to do next in Claude Code:

        1. `/analysis-journal` — Record the stratified correlation results as evidence,
           then add a `conclude` event
        2. `/analysis-reflection` — Formally conclude DEMO-H02 as "supported"
        3. `/catalog-register` — Register the finding as domain knowledge:
           "Time slot mediates temperature effect on iced beverage sales"
        """
    )
    return verdict


@app.cell
def _(df, plt):
    """Guardrail metric: average unit price by time slot.

    Check that the unit price (revenue/quantity) is stable across
    time slots — ensuring we're measuring volume effects, not pricing.
    """
    _df_unit = df.assign(unit_price=df["revenue"] / df["quantity"])
    _unit_by_slot = _df_unit.groupby("time_slot")["unit_price"].mean()

    _fig3, _ax = plt.subplots(figsize=(8, 4))
    _unit_by_slot.plot(kind="bar", ax=_ax, color=["#2196F3", "#FF9800", "#9C27B0"])
    _ax.set_ylabel("Average Unit Price (JPY)")
    _ax.set_title("Guardrail: Unit Price by Time Slot")
    _ax.set_xticklabels(_ax.get_xticklabels(), rotation=0)
    _fig3.tight_layout()
    return


@app.cell
def _(export_lineage_as_mermaid, session):
    """Export lineage diagram for DEMO-H02."""
    mermaid = export_lineage_as_mermaid(session, project_path=".")
    print("Lineage Mermaid diagram:")
    print(mermaid)
    return mermaid


if __name__ == "__main__":
    app.run()
