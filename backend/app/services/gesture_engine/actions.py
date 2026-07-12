"""
GestureMed AI — Gesture Action Handler
Maps recognized gestures to medical actions for both Patient and Doctor roles.
"""
import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class GestureAction:
    action_type: str
    message: str
    notification_level: str  # info | success | warning | critical
    metadata: dict = field(default_factory=dict)


class PatientGestureActions:
    """Maps patient gestures to clinical actions."""

    COOLDOWNS: dict = {
        "call_nurse": 5.0,
        "pain_level": 5.0,
        "request_water": 5.0,
        "feeling_good": 5.0,
        "need_help": 5.0,
        "emergency": 10.0,
    }

    def __init__(self):
        self._last_action: dict = {}
        self.pain_level: int = 0

    def _can_act(self, key: str) -> bool:
        cooldown = self.COOLDOWNS.get(key, 3.0)
        return time.time() - self._last_action.get(key, 0) >= cooldown

    def _record(self, key: str):
        self._last_action[key] = time.time()

    def handle(self, gesture: str, metadata: dict) -> Optional[GestureAction]:
        hold = metadata.get("hold_duration", 0)
        count = metadata.get("count", 0)

        if gesture == "PEACE" and hold > 1.0 and self._can_act("call_nurse"):
            self._record("call_nurse")
            return GestureAction("NURSE_CALLED", "Nurse Called — Help is on the way!", "success")

        if gesture.startswith("FINGERS_") and hold > 1.0:
            try:
                level = int(gesture.split("_")[1])
            except (IndexError, ValueError):
                level = count

            if 1 <= level <= 5 and self._can_act("pain_level"):
                self._record("pain_level")
                self.pain_level = level
                msgs = {
                    1: "Pain Level 1 — Minimal discomfort",
                    2: "Pain Level 2 — Mild pain",
                    3: "Pain Level 3 — Moderate pain",
                    4: "Pain Level 4 — Severe pain — Notifying staff",
                    5: "Pain Level 5 — Extreme pain — Medical team alerted!",
                }
                lvl = "critical" if level >= 4 else "warning"
                return GestureAction(f"PAIN_{level}", msgs[level], lvl, {"pain_level": level})

        if gesture == "PINCH" and hold > 1.0 and self._can_act("request_water"):
            self._record("request_water")
            return GestureAction("WATER_REQUESTED", "Water Requested — Coming soon!", "info")

        if gesture == "THUMBS_UP" and hold > 1.0 and self._can_act("feeling_good"):
            self._record("feeling_good")
            return GestureAction("POSITIVE_FEEDBACK", "Feeling Good reported", "success")

        if gesture == "THUMBS_DOWN" and hold > 1.0 and self._can_act("need_help"):
            self._record("need_help")
            return GestureAction("ASSISTANCE_NEEDED", "Assistance needed — Staff notified", "warning")

        if gesture == "OPEN_PALM" and hold > 2.5 and self._can_act("emergency"):
            self._record("emergency")
            return GestureAction("EMERGENCY", "EMERGENCY ALERT — Medical team responding!", "critical")

        return None


class DoctorGestureActions:
    """Maps doctor gestures to clinical interface actions."""

    def __init__(self):
        self._last_action: dict = {}
        self.zoom_level: float = 1.0
        self.marked_points: list = []

    def _can_act(self, key: str, cooldown: float = 2.0) -> bool:
        return time.time() - self._last_action.get(key, 0) >= cooldown

    def _record(self, key: str):
        self._last_action[key] = time.time()

    def handle(self, gesture: str, metadata: dict) -> Optional[GestureAction]:
        hold = metadata.get("hold_duration", 0)
        position = metadata.get("position")

        if gesture == "POINTING" and hold > 1.0 and self._can_act("mark_area"):
            self._record("mark_area")
            self.marked_points.append(position)
            return GestureAction("AREA_MARKED", "Area Marked", "info", {"position": position})

        if gesture == "PINCH" and hold > 1.5 and self._can_act("zoom"):
            self._record("zoom")
            self.zoom_level = min(4.0, self.zoom_level + 0.5)
            return GestureAction("ZOOM_IN", f"Zoom {self.zoom_level:.1f}x", "info", {"zoom": self.zoom_level})

        if gesture == "OPEN_PALM" and hold > 1.0 and self._can_act("zoom_out"):
            self._record("zoom_out")
            self.zoom_level = max(1.0, self.zoom_level - 0.5)
            return GestureAction("ZOOM_OUT", f"Zoom {self.zoom_level:.1f}x", "info", {"zoom": self.zoom_level})

        if gesture == "THUMBS_UP" and hold > 1.0 and self._can_act("approve"):
            self._record("approve")
            return GestureAction("APPROVED", "Approved", "success")

        if gesture == "THUMBS_DOWN" and hold > 1.0 and self._can_act("reject"):
            self._record("reject")
            return GestureAction("REJECTED", "Rejected", "error")

        if gesture == "PEACE" and hold > 1.0 and self._can_act("next_patient"):
            self._record("next_patient")
            return GestureAction("NEXT_RECORD", "Next Patient Record", "info")

        if gesture == "FIST" and hold > 1.0 and self._can_act("clear_marks"):
            self._record("clear_marks")
            self.marked_points.clear()
            return GestureAction("CLEARED", "Annotations Cleared", "info")

        return None
