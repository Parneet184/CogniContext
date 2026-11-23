"""Apply the assistant's provisional emotion annotations for an end-to-end MVP test.
These are draft interpretations, not authoritative scripture commentary.
Run from project root: python -m backend.seed_japji_emotions
"""
from .japji_db import replace_emotion_mappings

# Provisional mappings recovered from the earlier project discussion.
# Multiple emotions per Pauri are intentional.
DRAFT_EMOTION_MAP = {
    1: ["lost", "overwhelmed"],
    2: ["overwhelmed", "at_peace"],
    3: ["grateful", "overwhelmed"],
    4: ["grateful", "at_peace"],
    5: ["lost", "grateful", "at_peace"],
    6: ["lost", "grateful"],
    7: ["frustrated", "overwhelmed"],
    8: ["heavy_sad", "at_peace"],
    9: ["lost", "grateful"],
    10: ["overwhelmed", "at_peace"],
    11: ["lost", "at_peace"],
    12: ["lost", "overwhelmed"],
    13: ["heavy_sad", "at_peace"],
    14: ["lost", "at_peace"],
    15: ["heavy_sad", "grateful"],
    16: ["overwhelmed", "grateful"],
    17: ["grateful", "overwhelmed"],
    18: ["heavy_sad", "overwhelmed"],
    19: ["grateful", "overwhelmed"],
    20: ["frustrated", "heavy_sad"],
    21: ["lost", "overwhelmed"],
    22: ["overwhelmed", "grateful"],
    23: ["frustrated", "at_peace"],
    24: ["overwhelmed", "grateful"],
    25: ["heavy_sad", "grateful"],
    26: ["grateful", "overwhelmed"],
    27: ["at_peace", "grateful"],
    28: ["frustrated", "at_peace"],
    29: ["at_peace", "lost"],
    30: ["overwhelmed", "at_peace"],
    31: ["grateful", "at_peace"],
    32: ["lost", "grateful"],
    33: ["frustrated", "overwhelmed"],
    34: ["heavy_sad", "frustrated"],
    35: ["lost", "overwhelmed"],
    36: ["lost", "at_peace"],
    37: ["at_peace", "grateful"],
    38: ["frustrated", "at_peace"],
}

if __name__ == "__main__":
    count = replace_emotion_mappings(DRAFT_EMOTION_MAP, confirmed=False)
    print(f"Applied {count} provisional Pauri-emotion mappings across 38 Pauris.")
    print("Status: draft only; not user-confirmed or theologically validated.")
    print("Concluding Salok draft tags (not yet stored in the Pauri mapping table): grateful, at_peace, heavy_sad.")
