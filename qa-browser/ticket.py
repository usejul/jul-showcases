"""Parse a PO ticket written in the QA format (see README.md).

The format is plain Markdown a Product Owner can write without knowing anything
about the test tool:

    Site : https://www.example.com/

    ## Étapes
    1. Si une bannière cookies s'affiche, cliquer "Accepter et fermer".
    2. Rechercher "arrosoir luxe".

    ## Critères de validation
    - Le panier contient "Arrosoir luxe : 15L".

Rules:
  * one action per numbered line;
  * anything in "double quotes" is copied verbatim from the site (a label, a
    product name, or the text to type) — nothing is ever generated;
  * a step starting with "Si" / "If" is optional: skipped when it does not apply;
  * each "Critères de validation" bullet is a yes/no check on the final page.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

QUOTED = re.compile(r"[\"“«]\s*([^\"”»]+?)\s*[\"”»]")


@dataclass
class Step:
    text: str
    quoted: list[str]
    optional: bool
    check: bool = False         # an assertion checked in place, mid-journey (no click)


@dataclass
class Ticket:
    title: str
    site: str
    steps: list[Step] = field(default_factory=list)
    criteria: list[Step] = field(default_factory=list)
    lang: str = "fr"            # "en" when the section headings are English
    tags: list[str] = field(default_factory=list)   # `Tags : smoke, checkout` — for suite filtering


def _item(line: str) -> Step:
    text = line.strip().rstrip(".")
    return Step(text=text, quoted=QUOTED.findall(text),
                optional=bool(re.match(r"(?i)^(si|if)\b", text)),
                check=bool(re.match(r"(?i)^(check|verify|assert|confirm|ensure|v[eé]rifi\w*|"
                                    r"s'assur\w*)\s+(that\b|que\b|:)", text)))


def _fragment_steps(fragments_dir, name: str) -> list[Step]:
    """The numbered steps of a shared setup fragment (fragments/<name>.md). Reused verbatim by
    every ticket that names it, so common arrange-steps ("get a book into the cart") live once
    and each ticket still runs them itself — DRY, and the tickets stay independent."""
    from pathlib import Path
    path = Path(fragments_dir or ".") / f"{name}.md"
    if not path.exists():
        raise ValueError(f"Setup fragment not found: {path}")
    return [_item(re.sub(r"^\d+[.)]\s+", "", ln.strip()))
            for ln in path.read_text(encoding="utf-8").splitlines() if re.match(r"^\d+[.)]\s+", ln.strip())]


def parse(md: str, fragments_dir=None) -> Ticket:
    title, site, section, lang = "", "", None, "fr"
    steps, criteria, tags, setup = [], [], [], []
    for raw in md.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("# ") and not title:
            title = line[2:].strip()
            continue
        m = re.match(r"(?i)^(site|url)\s*:\s*(\S+)", line)
        if m:
            site = m.group(2)
            continue
        m = re.match(r"(?i)^tags?\s*:\s*(.+)", line)
        if m:
            tags += [t.strip() for t in re.split(r"[,;]", m.group(1)) if t.strip()]
            continue
        m = re.match(r"(?i)^(setup|include)\s*:\s*(.+)", line)
        if m:
            setup += [s.strip() for s in re.split(r"[,;]", m.group(2)) if s.strip()]
            continue
        if line.startswith("#"):
            low = line.lower()
            if re.search(r"\b(steps?|acceptance|criteria)\b", low):
                lang = "en"
            section = ("steps" if ("étape" in low or "etape" in low or "step" in low) else
                       "criteria" if ("critère" in low or "critere" in low or "criteria" in low
                                      or "validation" in low) else None)
            continue
        if section == "steps" and re.match(r"^\d+[.)]\s+", line):
            steps.append(_item(re.sub(r"^\d+[.)]\s+", "", line)))
        elif section == "criteria" and re.match(r"^[-*]\s+", line):
            criteria.append(_item(re.sub(r"^[-*]\s+", "", line)))
    for name in reversed(setup):                    # a `Setup :` fragment runs first (arrange), in order
        steps = _fragment_steps(fragments_dir, name) + steps
    if not site:
        raise ValueError("ticket has no 'Site : <url>' line")
    if not steps:
        raise ValueError("ticket has no numbered steps under '## Étapes'")
    return Ticket(title=title, site=site, steps=steps, criteria=criteria, lang=lang, tags=tags)
