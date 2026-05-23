"""
GestureMed AI — AI Annotation Intelligence
Maps normalized pointer coordinates to body regions and
suggests clinical terminology for doctor annotations.
"""
from typing import Optional, Tuple


# Body region grid — maps normalized (x, y) to anatomical region
# The grid assumes a frontal standing-figure view within a 1.0 x 1.0 space
BODY_REGION_MAP = [
    # (x_min, x_max, y_min, y_max, region_name, clinical_term)
    (0.35, 0.65, 0.00, 0.12, "Head", "Cranial region"),
    (0.35, 0.65, 0.12, 0.20, "Neck", "Cervical region"),
    (0.25, 0.75, 0.20, 0.35, "Chest", "Thoracic region"),
    (0.25, 0.45, 0.20, 0.35, "Left Chest", "Left thorax"),
    (0.55, 0.75, 0.20, 0.35, "Right Chest", "Right thorax"),
    (0.35, 0.65, 0.35, 0.50, "Abdomen", "Abdominal region"),
    (0.35, 0.50, 0.35, 0.50, "Left Abdomen", "Left abdominal quadrant"),
    (0.50, 0.65, 0.35, 0.50, "Right Abdomen", "Right abdominal quadrant"),
    (0.35, 0.65, 0.50, 0.65, "Lower Abdomen / Pelvis", "Pelvic region"),
    (0.10, 0.35, 0.20, 0.55, "Left Arm", "Left upper extremity"),
    (0.65, 0.90, 0.20, 0.55, "Right Arm", "Right upper extremity"),
    (0.10, 0.35, 0.55, 0.75, "Left Forearm / Hand", "Left distal upper extremity"),
    (0.65, 0.90, 0.55, 0.75, "Right Forearm / Hand", "Right distal upper extremity"),
    (0.30, 0.50, 0.65, 0.85, "Left Leg", "Left lower extremity"),
    (0.50, 0.70, 0.65, 0.85, "Right Leg", "Right lower extremity"),
    (0.30, 0.50, 0.85, 1.00, "Left Foot", "Left distal lower extremity"),
    (0.50, 0.70, 0.85, 1.00, "Right Foot", "Right distal lower extremity"),
]

# Pain scale descriptors
PAIN_DESCRIPTORS = {
    1: {"label": "Minimal", "color": "#22C55E", "description": "Barely noticeable, no functional impairment"},
    2: {"label": "Mild", "color": "#84CC16", "description": "Noticeable discomfort, normal activity possible"},
    3: {"label": "Moderate", "color": "#F59E0B", "description": "Interferes with some activities"},
    4: {"label": "Severe", "color": "#EF4444", "description": "Severely limits activity, distressing"},
    5: {"label": "Extreme", "color": "#7C3AED", "description": "Unbearable, emergency evaluation required"},
}


def detect_body_region(x_norm: float, y_norm: float) -> Tuple[str, str]:
    """
    Map normalized (x, y) coordinates to an anatomical body region.
    Returns (display_name, clinical_term).
    """
    for x_min, x_max, y_min, y_max, name, clinical in BODY_REGION_MAP:
        if x_min <= x_norm <= x_max and y_min <= y_norm <= y_max:
            return name, clinical

    return "Unspecified region", "Region not mapped"


def get_pain_descriptor(level: int) -> Optional[dict]:
    """Get clinical pain descriptor for a 1-5 pain level."""
    return PAIN_DESCRIPTORS.get(level)


def build_annotation_label(
    x_norm: float,
    y_norm: float,
    pain_level: Optional[int] = None,
    note: Optional[str] = None,
) -> dict:
    """
    Build a complete annotation label from pointer position and optional context.
    Returns a dict ready for DB storage and Socket.IO broadcast.
    """
    region_name, clinical_term = detect_body_region(x_norm, y_norm)

    label_parts = [region_name]
    if pain_level:
        pain_info = get_pain_descriptor(pain_level)
        if pain_info:
            label_parts.append(f"Pain {pain_level}/5 ({pain_info['label']})")

    return {
        "body_region": region_name,
        "clinical_term": clinical_term,
        "display_label": " — ".join(label_parts),
        "note": note or "",
        "pain_level": pain_level,
        "pain_descriptor": get_pain_descriptor(pain_level) if pain_level else None,
    }


def suggest_clinical_notes(annotations: list) -> list:
    """
    Given a list of annotation dicts, suggest clinical documentation phrases.
    Returns a list of ready-to-use note strings for the doctor.
    """
    suggestions = []
    for ann in annotations:
        region = ann.get("body_region", "")
        pain = ann.get("pain_level")
        note = ann.get("note", "")

        if region and pain:
            pain_info = get_pain_descriptor(pain) or {}
            suggestions.append(
                f"Patient reports {pain_info.get('label', 'unspecified').lower()} pain "
                f"({pain}/5) in the {region.lower()}. "
                f"{pain_info.get('description', '')}."
            )
        elif region:
            suggestions.append(f"Area of clinical interest: {region}. {note}".strip(".") + ".")

    return suggestions
