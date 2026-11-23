
"""Import verified-format Unicode Gurmukhi into the existing Japji SQLite database.

Run from the project root:
    python -m backend.import_gurmukhi
"""

import re
import sqlite3
from pathlib import Path

from .japji_db import connect

SOURCE = (
    Path(__file__).resolve().parent
    / "data_templates"
    / "japji_sahib_unicode.txt"
)

PUNJABI_DIGITS = str.maketrans(
    "੦੧੨੩੪੫੬੭੮੯",
    "0123456789"
)

VERSE_END = re.compile(r"॥\s*([੦-੯]+)\s*॥\s*$")



def parse_scripture(text):
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    # Start after the Japji Sahib introductory heading.
    jap_index = next(
        (i for i, line in enumerate(lines) if "ਜਪੁ" in line and "॥" in line),
        None
    )

    if jap_index is None:
        raise ValueError("Could not find the ॥ ਜਪੁ ॥ heading.")

    lines = lines[jap_index + 1:]

    pauris = {}
    current = []
    opening_salok_skipped = False

    for line in lines:
        # The concluding Salok is not one of the 38 Pauris.
        if line.startswith("ਸਲੋਕੁ"):
            break

        current.append(line)
        match = VERSE_END.search(line)

        if not match:
            continue

        marker_number = int(
            match.group(1).translate(PUNJABI_DIGITS)
        )

        # Skip ONLY the first marker 1 (opening Salok).
        if marker_number == 1 and not opening_salok_skipped:
            opening_salok_skipped = True
            current = []
            continue

        # Actual Pauri markers are numbered directly from 1 to 38.
        if 1 <= marker_number <= 38:
            if marker_number in pauris:
                raise ValueError(
                    f"Duplicate Pauri marker: {marker_number}"
                )

            pauris[marker_number] = "\n".join(current).strip()
            current = []

    if sorted(pauris) != list(range(1, 39)):
        raise ValueError(
            f"Expected Pauris 1–38; found: {sorted(pauris)}"
        )

    # Extract the concluding Salok, including its heading.
    salok_index = next(
        (i for i, line in enumerate(lines) if line.startswith("ਸਲੋਕੁ")),
        None
    )

    if salok_index is None:
        raise ValueError("Could not find the concluding Salok.")

    salok = "\n".join(lines[salok_index:]).strip()

    if not any("\u0a00" <= char <= "\u0a7f" for char in salok):
        raise ValueError("Salok does not contain Unicode Gurmukhi.")

    return pauris, salok


def main():
    if not SOURCE.exists():
        raise FileNotFoundError(f"Unicode source not found: {SOURCE}")

    text = SOURCE.read_text(encoding="utf-8")
    pauris, salok = parse_scripture(text)

    # Validate Unicode before touching the database.
    for number, content in pauris.items():
        if not any("\u0a00" <= c <= "\u0a7f" for c in content):
            raise ValueError(f"Pauri {number} has no Unicode Gurmukhi.")

    con = connect()

    try:
        # Add the Salok column if this database does not already have it.
        columns = {
            row["name"]
            for row in con.execute("PRAGMA table_info(japji_salok)")
        }

        if "original_gurmukhi" not in columns:
            con.execute(
                "ALTER TABLE japji_salok ADD COLUMN original_gurmukhi TEXT"
            )

        # Confirm that all 38 existing records are present.
        existing = con.execute(
            "SELECT COUNT(*) FROM japji_pauris"
        ).fetchone()[0]

        if existing != 38:
            raise ValueError(
                f"Expected 38 existing database records; found {existing}. "
                "Import your existing JSON first."
            )

        # Update only Gurmukhi and review-status fields.
        for number, content in pauris.items():
            con.execute(
                """
                UPDATE japji_pauris
                SET original_gurmukhi = ?,
                    extraction_status = 'unicode_converted_needs_review',
                    updated_at = CURRENT_TIMESTAMP
                WHERE pauri_number = ?
                """,
                (content, number)
            )

        salok_exists = con.execute(
            "SELECT COUNT(*) FROM japji_salok "
            "WHERE id = 'concluding_salok'"
        ).fetchone()[0]

        if salok_exists:
            con.execute(
                """
                UPDATE japji_salok
                SET original_gurmukhi = ?,
                    extraction_status = 'unicode_converted_needs_review',
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = 'concluding_salok'
                """,
                (salok,)
            )
        else:
            raise ValueError(
                "The concluding Salok record does not exist. "
                "Import the existing JSON first."
            )

        con.commit()

        print("Unicode Gurmukhi import successful.")
        print("Pauris updated:", len(pauris))
        print("Concluding Salok: updated")

        check = con.execute(
            """
            SELECT pauri_number, length(original_gurmukhi)
            FROM japji_pauris
            ORDER BY pauri_number
            """
        ).fetchall()

        print("\nDatabase verification:")
        for row in check:
            print(f"Pauri {row[0]}: {row[1]} characters")

    except Exception:
        con.rollback()
        raise

    finally:
        con.close()


if __name__ == "__main__":
    main()
