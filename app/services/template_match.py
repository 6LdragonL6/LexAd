"""Template matching service: suggests rewrite templates.

First version reads from data/rewrite_templates.json if available, returns empty otherwise.
"""

from __future__ import annotations

from app.core.config import DATA_DIR
from app.schemas.models import RewriteTemplate, ThreeLayerReview
from app.utils.json_reader import read_json_list


def match_templates(review: ThreeLayerReview) -> list[RewriteTemplate]:
    """Find matching rewrite templates from the template library.

    Args:
        review: Three-layer review result.

    Returns:
        List of RewriteTemplate entries (empty in first version).
    """
    template_file = DATA_DIR / "rewrite_templates.json"
    templates_data = read_json_list(template_file)

    if not templates_data:
        return []

    # TODO: Implement real template matching logic.
    results: list[RewriteTemplate] = []
    for item in templates_data:
        results.append(RewriteTemplate(
            template_id=item.get("template_id", ""),
            title=item.get("title", ""),
            before=item.get("before", ""),
            after=item.get("after", ""),
            note=item.get("note", ""),
        ))
    return results
