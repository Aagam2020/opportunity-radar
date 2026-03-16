"""Helpers for cleaning and validating job descriptions."""

from __future__ import annotations

from html import unescape
from html.parser import HTMLParser

WEAK_DESCRIPTION_MARKERS = (
    "enable javascript",
    "you need to enable javascript",
    "loading",
    "click here",
    "apply on company website",
)

MIN_DESCRIPTION_CHARACTERS = 300


class _HTMLTextExtractor(HTMLParser):
    """Convert small ATS HTML fragments into readable plain text."""

    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self._ignored_tag_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style"}:
            self._ignored_tag_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"} and self._ignored_tag_depth > 0:
            self._ignored_tag_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._ignored_tag_depth:
            return

        text = " ".join(data.split())
        if text:
            self.parts.append(text)


def html_to_text(value: str) -> str:
    """Convert raw HTML into readable plain text."""
    parser = _HTMLTextExtractor()
    parser.feed(unescape(value or ""))
    return "\n".join(parser.parts).strip()


def join_text_parts(parts: list[str]) -> str:
    """Combine description sections while dropping empty or duplicate text."""
    combined: list[str] = []
    seen: set[str] = set()

    for part in parts:
        cleaned = str(part).strip()
        normalized = " ".join(cleaned.split()).lower()

        if not cleaned or normalized in seen:
            continue

        combined.append(cleaned)
        seen.add(normalized)

    return "\n\n".join(combined).strip()


def is_weak_description(
    description: str,
    *,
    title: str = "",
    company: str = "",
) -> bool:
    """Return True when the description is too weak to trust for analysis."""
    cleaned = str(description).strip()
    if not cleaned:
        return True

    lowered = cleaned.lower()
    if any(marker in lowered for marker in WEAK_DESCRIPTION_MARKERS):
        return True

    if len(cleaned) < MIN_DESCRIPTION_CHARACTERS:
        return True

    words = cleaned.split()

    title_company_only = join_text_parts(
        [
            title,
            f"{title} @ {company}" if title and company else "",
            company,
        ]
    )
    if title_company_only and lowered == title_company_only.lower():
        return True

    # Some weak pages only repeat the title/company plus one placeholder line.
    non_title_lines = [
        line.strip()
        for line in cleaned.splitlines()
        if line.strip() and line.strip().lower() not in {title.strip().lower(), company.strip().lower()}
    ]
    if len(non_title_lines) <= 1 and len(words) < 80:
        return True

    return False
