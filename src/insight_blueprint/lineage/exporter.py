"""Export lineage session as Mermaid diagram."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from insight_blueprint.lineage.tracker import LineageSession


def export_lineage_as_mermaid(
    session: LineageSession,
    *,
    output_path: str | Path | None = None,
    project_path: str | Path | None = None,
) -> str:
    """Generate a Mermaid diagram (graph LR) from a lineage session.

    Args:
        session: Target lineage session.
        output_path: Explicit file output path. Takes priority over project_path.
        project_path: Project root. When set (and output_path is None),
            writes to ``{project_path}/.insight/lineage/{id_or_name}.mmd``.

    Returns:
        Generated Mermaid text (always returned, even when written to file).
    """
    steps = session.steps
    if not steps:
        return ""

    lines: list[str] = ["graph LR"]
    first = steps[0]
    lines.append(
        f'    Step0["{_escape_mermaid(session.name)}<br/>{first.rows_before} rows"]'
    )

    for step in steps:
        n = step.step_number
        delta = f"+{step.rows_delta}" if step.rows_delta >= 0 else str(step.rows_delta)
        lines.append(f'    Step{n}["Step {n}<br/>{step.rows_after} rows"]')
        lines.append(
            f"    Step{n - 1} "
            f'-->|"{_escape_mermaid(step.reason)}<br/>{delta} rows"| '
            f"Step{n}"
        )

    mermaid_text = "\n".join(lines) + "\n"

    resolved_path = _resolve_output_path(session, output_path, project_path)
    if resolved_path is not None:
        resolved_path.parent.mkdir(parents=True, exist_ok=True)
        resolved_path.write_text(mermaid_text, encoding="utf-8")

    return mermaid_text


def _escape_mermaid(text: str) -> str:
    """Escape text for Mermaid labels."""
    return text.replace('"', "&quot;").replace("|", "&#124;").replace("\n", "<br/>")


def _resolve_output_path(
    session: LineageSession,
    output_path: str | Path | None,
    project_path: str | Path | None,
) -> Path | None:
    """Resolve the output file path."""
    if output_path is not None:
        return Path(output_path)
    if project_path is not None:
        name = session.design_id if session.design_id else session.name
        return Path(project_path) / ".insight" / "lineage" / f"{name}.mmd"
    return None
