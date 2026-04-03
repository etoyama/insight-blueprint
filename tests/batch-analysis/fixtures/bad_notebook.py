import marimo

__generated_with = "0.13.0"
app = marimo.App(width="medium")


@app.cell
def _():
    import matplotlib.pyplot as plt
    import pandas as pd

    return (pd, plt)


@app.cell
def _(pd):
    df = pd.read_csv("tutorial/sample_data/sales.csv")
    return (df,)


@app.cell
def _(df, plt):
    # BAD: fig, ax without _ prefix — multiple-defs error
    fig, ax = plt.subplots()
    ax.scatter(df["temperature"], df["revenue"])
    ax.set_title("Temperature vs Revenue")
    plt.gcf()
    return


@app.cell
def _(df, plt):
    # BAD: fig, ax without _ prefix — multiple-defs error
    fig, ax = plt.subplots()
    ax.hist(df["revenue"], bins=20)
    ax.set_title("Revenue Distribution")
    plt.gcf()
    return


if __name__ == "__main__":
    app.run()
