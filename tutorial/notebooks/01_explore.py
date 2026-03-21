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
    """Load sample data and show basic info."""
    import marimo as mo

    raw_df = pd.read_csv("tutorial/sample_data/sales.csv", parse_dates=["date"])
    mo.md(
        f"""
        ## Raw Data Overview
        - **Rows**: {len(raw_df)}
        - **Columns**: {", ".join(raw_df.columns)}
        - **Date range**: {raw_df["date"].min().date()} ~ {raw_df["date"].max().date()}
        - **Stores**: {", ".join(raw_df["store_id"].unique())}
        """
    )
    return mo, raw_df


@app.cell
def _(raw_df):
    """Show descriptive statistics."""
    raw_df.describe()
    return


@app.cell
def _(LineageSession, raw_df, tracked_pipe):
    """Clean data with tracked_pipe (lineage tracking).

    insight-blueprint's data-lineage API records each transformation step
    with row count changes for reproducibility.
    """
    # ---- Create a lineage session tied to the analysis design ----
    # DEMO-H01 is the design_id you created with /analysis-design
    session = LineageSession(name="explore", design_id="DEMO-H01")

    # ---- Step 1: Drop rows with missing revenue ----
    df = raw_df.pipe(
        tracked_pipe(
            lambda d: d.dropna(subset=["revenue", "temperature"]),
            reason="revenue/temperature missing rows removed",
            session=session,
        )
    )

    # ---- Step 2: Keep only positive revenue ----
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
    """Show cleaned data summary."""
    mo.md(
        f"""
        ## Cleaned Data
        - **Rows**: {len(df)} (after cleaning)
        - **Products**: {", ".join(sorted(df["product"].unique()))}
        - **Time slots**: {", ".join(sorted(df["time_slot"].unique()))}
        """
    )
    return


@app.cell
def _(df, plt):
    """Hypothesis test: Temperature vs Iced Coffee Revenue (all data).

    Hypothesis DEMO-H01: "Higher temperature increases iced coffee revenue."
    Let's start with a simple scatter plot across all time slots.
    """
    iced = df[df["product"] == "iced_coffee"]

    _fig, _ax = plt.subplots()
    _ax.scatter(iced["temperature"], iced["revenue"], alpha=0.5, s=40)
    _ax.set_xlabel("Temperature (C)")
    _ax.set_ylabel("Revenue (JPY)")
    _ax.set_title("Temperature vs Iced Coffee Revenue (All Time Slots)")

    # Overall correlation
    corr = iced[["temperature", "revenue"]].corr().iloc[0, 1]
    _ax.annotate(
        f"r = {corr:.3f}", xy=(0.05, 0.95), xycoords="axes fraction", fontsize=14
    )
    return corr, iced


@app.cell
def _(corr, mo):
    """Interpret overall correlation."""
    mo.md(
        f"""
        ## Overall Correlation: r = {corr:.3f}

        There IS a positive correlation, but it's **moderate at best**.
        Something else might be going on. Let's split by **time slot**
        to see if the pattern changes.
        """
    )
    return


@app.cell
def _(iced, plt):
    """KEY DISCOVERY: Split by time slot reveals the morning reversal.

    This is the "aha moment" - the pattern differs dramatically
    between morning and afternoon.
    """
    _slots = ["morning", "afternoon", "evening"]
    _fig, _axes = plt.subplots(1, 3, figsize=(16, 5), sharey=True)

    for _ax, _slot in zip(_axes, _slots, strict=True):
        _subset = iced[iced["time_slot"] == _slot]
        _ax.scatter(_subset["temperature"], _subset["revenue"], alpha=0.5, s=40)
        _ax.set_xlabel("Temperature (C)")
        _ax.set_title(f"{_slot.capitalize()}")

        if len(_subset) > 2:
            _r = _subset[["temperature", "revenue"]].corr().iloc[0, 1]
            _ax.annotate(
                f"r = {_r:.3f}", xy=(0.05, 0.9), xycoords="axes fraction", fontsize=13
            )

    _axes[0].set_ylabel("Revenue (JPY)")
    _fig.suptitle("Temperature vs Iced Coffee Revenue — by Time Slot", fontsize=14)
    _fig.tight_layout()
    plt.gcf()
    return


@app.cell
def _(mo):
    """Interpretation of the discovery."""
    mo.md(
        """
        ## Discovery: Morning Reversal

        - **Afternoon**: Clear positive correlation (temperature up -> iced sales up)
        - **Morning**: Weak or no correlation (commuter demand dominates)
        - **Evening**: Moderate positive correlation

        **Conclusion for DEMO-H01**: Hypothesis is **supported with conditions**.
        The temperature effect exists but is **mediated by time of day**.

        **Next step**: Create a derived hypothesis (DEMO-H02) to formally test
        the time-slot mediation effect.

        ---

        ### What to do next in Claude Code:

        1. `/analysis-journal` — Record observations (this scatter plot) and the
           morning reversal as evidence
        2. `/analysis-reflection` — Conclude DEMO-H01 as "supported (conditional)"
        3. `/analysis-design` — Create DEMO-H02 with `parent_id=DEMO-H01`
        """
    )
    return


@app.cell
def _(export_lineage_as_mermaid, mo, session):
    """Export lineage as Mermaid diagram.

    This creates .insight/lineage/DEMO-H01.mmd which the
    /data-lineage skill can visualize.
    """
    mermaid = export_lineage_as_mermaid(session, project_path=".")
    mo.vstack(
        [
            mo.md("### Data Lineage: DEMO-H01"),
            mo.mermaid(mermaid),
        ]
    )
    return (mermaid,)


if __name__ == "__main__":
    app.run()
