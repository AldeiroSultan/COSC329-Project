"""All model constants. Every number here is documented in docs/MODEL.md."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

# ---------------------------------------------------------------- paths
ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
STUDENTS_CSV = DATA_DIR / "processed" / "students.csv"
LEARNED_CPTS_JSON = DATA_DIR / "processed" / "learned_cpts.json"
OUTPUT_DIR = ROOT / "output"

# ---------------------------------------------------------------- nodes
CONCEPTS = ["C1", "C2", "C3"]

NODE_DIFFICULTY = {c: f"Difficulty_{c}" for c in CONCEPTS}
NODE_MASTERY = {c: f"Mastery_{c}" for c in CONCEPTS}
NODE_QUIZ = {c: f"Quiz_{c}" for c in CONCEPTS}
NODE_DAYS = "DaysLeft"
NODE_STRESS = "Stress"
NODE_SLEEP = "Sleep"
NODE_EXAM = "ExamSuccess"

# ---------------------------------------------------------------- states (order matters: CPT columns follow it)
DIFFICULTY_STATES = ["easy", "medium", "hard"]
MASTERY_STATES = ["low", "high"]
QUIZ_STATES = ["low", "high"]
DAYS_STATES = ["few", "some", "many"]
STRESS_STATES = ["low", "high"]
SLEEP_STATES = ["poor", "good"]
EXAM_STATES = ["fail", "pass"]


def days_bucket(days_until_exam: int) -> str:
    """Map a raw day count to a DaysLeft state: few (<=3), some (4-10), many (>10)."""
    if days_until_exam <= 3:
        return "few"
    if days_until_exam <= 10:
        return "some"
    return "many"


# ---------------------------------------------------------------- hand-crafted CPT values (MODEL.md §2a)
P_DIFFICULTY = {"easy": 0.3, "medium": 0.4, "hard": 0.3}
P_DAYS = {"few": 0.2, "some": 0.4, "many": 0.4}
P_MASTERY_HIGH_GIVEN_DIFFICULTY = {"easy": 0.80, "medium": 0.55, "hard": 0.25}
P_QUIZ_HIGH_GIVEN_MASTERY = {"high": 0.85, "low": 0.20}
P_STRESS_HIGH_GIVEN_DAYS = {"few": 0.80, "some": 0.45, "many": 0.20}
P_SLEEP_POOR_GIVEN_STRESS = {"high": 0.65, "low": 0.25}
# P(pass | number of concepts mastered, stress)
P_PASS_GIVEN_K_STRESS = {
    0: {"low": 0.10, "high": 0.05},
    1: {"low": 0.35, "high": 0.25},
    2: {"low": 0.70, "high": 0.55},
    3: {"low": 0.95, "high": 0.85},
}

# ---------------------------------------------------------------- learning (DATA.md)
N_STUDENTS = 5000
RANDOM_SEED = 329
LAPLACE_ALPHA = 1.0

# ---------------------------------------------------------------- decision (MODEL.md §4-5)
@dataclass(frozen=True)
class Action:
    key: str
    label: str
    hours: float
    mastery_boost: float     # fraction of the remaining (1 - P(high)) gap closed, before urgency
    target: str              # "all" concepts or only the "weakest"
    stress_delta: float      # added to P(Stress=high), clipped to [0, 1]


ACTIONS: list[Action] = [
    Action("intense", "Intense 5-hour mandatory study block", 5.0, 0.35, "all", +0.20),
    Action("focused", "2.5-hour focused session on weakest concept", 2.5, 0.50, "weakest", +0.03),
    Action("light", "Light 1-hour review", 1.0, 0.20, "all", -0.04),
    Action("rest", "Rest day (planner sessions cleared)", 0.0, 0.0, "all", -0.08),
]

URGENCY = {"few": 1.0, "some": 0.7, "many": 0.3}

# UTILITY[exam_state][stress_state]
UTILITY = {
    "pass": {"low": 100.0, "high": 85.0},
    "fail": {"low": 10.0, "high": 0.0},
}
TIME_COST_PER_HOUR = 1.0

# ---------------------------------------------------------------- calendar
EVENT_TAG = "[BayesPlanner]"
DEFAULT_STUDY_START_HOUR = 10  # sessions start at 10:00 local time
TIMEZONE = "America/Vancouver"
