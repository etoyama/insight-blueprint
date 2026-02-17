#!/usr/bin/env python3
"""
extract_docs.py - Extract implementation details from .claude/docs/

Usage:
    python extract_docs.py .claude/docs/ --format json > migration-data.json
    python extract_docs.py .claude/docs/ --format yaml > migration-data.yaml

Bundled with migrate-to-spec skill for automated spec-workflow migration.
"""

import argparse
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any


def extract_design_decisions(design_file: Path) -> Dict[str, Any]:
    """Extract architecture decisions from DESIGN.md"""
    if not design_file.exists():
        return {}
    
    content = design_file.read_text()
    
    return {
        "architecture": extract_section(content, "Architecture"),
        "data_model": extract_section(content, "Data Model"),
        "api_design": extract_section(content, "API"),
        "decisions": extract_adrs(content),
        "risks": extract_section(content, "Risk"),
    }


def extract_section(content: str, heading: str) -> str:
    """Extract content under a markdown heading"""
    pattern = rf"#+\s*{heading}.*?\n(.*?)(?=\n#+|\Z)"
    match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
    return match.group(1).strip() if match else ""


def extract_adrs(content: str) -> List[Dict[str, str]]:
    """Extract Architecture Decision Records"""
    adrs = []
    pattern = r"ADR-\d+:?\s*(.*?)(?=ADR-|\Z)"
    matches = re.finditer(pattern, content, re.DOTALL)
    
    for match in matches:
        adrs.append({
            "title": match.group(1).split('\n')[0].strip(),
            "content": match.group(1).strip()
        })
    
    return adrs


def extract_research(research_dir: Path) -> List[Dict[str, Any]]:
    """Extract research notes from research/ directory"""
    if not research_dir.exists():
        return []
    
    research = []
    for md_file in research_dir.glob("*.md"):
        research.append({
            "topic": md_file.stem,
            "content": md_file.read_text(),
            "date": datetime.fromtimestamp(md_file.stat().st_mtime).isoformat()
        })
    
    return research


def extract_logs(logs_dir: Path) -> Dict[str, List[Dict]]:
    """Extract Codex/Gemini consultation logs"""
    if not logs_dir.exists():
        return {"codex": [], "gemini": []}
    
    cli_tools_log = logs_dir / "cli-tools.jsonl"
    logs = {"codex": [], "gemini": []}
    
    if cli_tools_log.exists():
        for line in cli_tools_log.read_text().splitlines():
            try:
                entry = json.loads(line)
                tool_type = entry.get("tool", "").lower()
                if "codex" in tool_type:
                    logs["codex"].append(entry)
                elif "gemini" in tool_type:
                    logs["gemini"].append(entry)
            except json.JSONDecodeError:
                continue
    
    return logs


def infer_user_stories(design: Dict, research: List) -> List[str]:
    """Infer user stories from implementation context"""
    stories = []
    
    # Look for user-focused language in design docs
    design_content = " ".join(str(v) for v in design.values())
    
    # Simple heuristics for user story extraction
    if "authentication" in design_content.lower():
        stories.append("As a user, I want to securely log in, so that I can access protected features")
    
    if "api" in design_content.lower():
        stories.append("As a developer, I want to integrate via API, so that I can automate workflows")
    
    # Add from research insights
    for r in research:
        if "user" in r["content"].lower():
            # Extract sentences containing "user"
            sentences = r["content"].split(".")
            for s in sentences:
                if "user" in s.lower():
                    stories.append(f"Inferred: {s.strip()}")
    
    return stories[:5]  # Limit to top 5


def main():
    parser = argparse.ArgumentParser(
        description="Extract implementation details for spec-workflow migration"
    )
    parser.add_argument("docs_dir", type=Path, help="Path to .claude/docs/")
    parser.add_argument(
        "--format", choices=["json", "yaml"], default="json",
        help="Output format"
    )
    
    args = parser.parse_args()
    docs_dir = args.docs_dir
    
    # Extract all components
    design_file = docs_dir / "DESIGN.md"
    research_dir = docs_dir / "research"
    logs_dir = docs_dir.parent / "logs"
    
    extraction = {
        "extracted_at": datetime.now().isoformat(),
        "design": extract_design_decisions(design_file),
        "research": extract_research(research_dir),
        "logs": extract_logs(logs_dir),
        "inferred_user_stories": infer_user_stories(
            extract_design_decisions(design_file),
            extract_research(research_dir)
        ),
    }
    
    # Output
    if args.format == "json":
        print(json.dumps(extraction, indent=2))
    else:
        import yaml
        print(yaml.dump(extraction, default_flow_style=False))


if __name__ == "__main__":
    main()
