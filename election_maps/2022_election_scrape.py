import pdfplumber
import re
import pandas as pd

PDF_PATH = "laverne_voting_results.pdf"
BY_DISTRICT_OUTPUT_CSV = "laverne_target_races_by_district.csv"
AGGREGATE_OUTPUT_CSV = "laverne_target_races.csv"

TARGET_RACES = [
    "LA VERNE CY GEN MUNI-CNC 1",
    "LA VERNE CY GEN MUNI-CNC 3",
    "LA VERNE CY GEN MUNI-CNC 4",
    "22ND STATE SENATE DIST",
    "41ST ASSEMBLY DIST",
    "31ST CONGRESS DIST",
    "28TH CONGRESS DIST",
    "SUPERVISOR 1ST DISTRICT",
    "GOVERNOR",
    "SUPERINTENDENT PUBLIC INST",
    "SECRETARY OF STATE",
    "ATTORNEY GENERAL",
]

HEADER_KEYWORDS = [
    "SENATOR", "ASSEMBLY", "CONGRESS", "JUDGE", "GOVERNOR", "SHERIFF",
    "ASSESSOR", "CONTROLLER", "TREASURER", "ATTORNEY GENERAL",
    "INSURANCE COMMISSIONER", "SUPERINTENDENT", "SECRETARY OF STATE",
    "LIEUTENANT GOVERNOR", "SUPERVISOR", "STATE SENATE", "STATE BD",
    "MUNI-CNC", "CY GEN"
]

REPORT_METADATA_PREFIXES = (
    "BALLOTS CAST",
    "JOB ",
    "PAGE ",
    "REGISTRATION",
    "RUN ",
    "TO BE HELD",
    "TOTAL",
    "VOTE CAST",
    "VOTES CAST",
)

PARTY_CODES = r"(REP|DEM|NP|GRN|PF|LIB|AI)"
candidate_re = re.compile(
    rf"^([A-Z][A-Za-z.'\"\-() ]+?)\s+(?:{PARTY_CODES}\s+)?(\d{{1,5}})$"
)

FALLBACK_BOUNDS = [36, 221, 401, 584, 792]


def get_column_bounds(page):
    xs = set()
    for line in page.lines:
        if abs(line["x0"] - line["x1"]) < 1:
            xs.add(round(line["x0"]))
    for rect in page.rects:
        if rect["width"] < 2:
            xs.add(round(rect["x0"]))
    xs = sorted(xs)
    if len(xs) >= 3:
        bounds = [0] + xs + [int(page.width)]
        cleaned = [bounds[0]]
        for x in bounds[1:]:
            if x - cleaned[-1] > 20:
                cleaned.append(x)
        if len(cleaned) >= 4:
            return cleaned
    print("  (no reliable column lines detected -- using fallback bounds)")
    return FALLBACK_BOUNDS


def assign_column(x0, bounds):
    for i in range(len(bounds) - 1):
        if bounds[i] <= x0 < bounds[i + 1]:
            return i
    return len(bounds) - 2


def extract_records(pdf_path):
    records = []
    with pdfplumber.open(pdf_path) as pdf:
        col_bounds = get_column_bounds(pdf.pages[0])
        print(f"Using column bounds: {col_bounds}")

        for page_num, page in enumerate(pdf.pages, start=1):
            words = page.extract_words()
            for w in words:
                w["col"] = assign_column(w["x0"], col_bounds)

            cols = {}
            for w in words:
                cols.setdefault(w["col"], []).append(w)

            for col_idx, col_words in cols.items():
                col_words.sort(key=lambda w: (round(w["top"]), w["x0"]))
                lines = {}
                for w in col_words:
                    key = round(w["top"] / 3)
                    lines.setdefault(key, []).append(w["text"])
                for key in sorted(lines):
                    records.append({
                        "page": page_num,
                        "col": col_idx,
                        "line": " ".join(lines[key])
                    })
    return records


def parse_records(records, debug=False):
    parsed_rows = []
    current_race = None
    current_council = None
    in_target_race = False
    detected_headers = []

    for rec in records:
        line = rec["line"].strip()

        council_match = re.search(r"CITY OF LA VERNE (\d(?:ST|ND|RD|TH)) COUNCIL", line)
        if council_match:
            current_council = council_match.group(1)
            current_race = None
            in_target_race = False
            continue

        if line.startswith(REPORT_METADATA_PREFIXES):
            current_race = None
            in_target_race = False
            continue

        if any(kw in line for kw in HEADER_KEYWORDS):
            current_race = line
            detected_headers.append((current_council, line))
            in_target_race = any(t in line for t in TARGET_RACES)
            continue

        if in_target_race:
            m = candidate_re.match(line)
            if m:
                name, party, votes = m.groups()
                parsed_rows.append({
                    "council_district": current_council,
                    "race": current_race,
                    "candidate": name.strip(),
                    "votes": int(votes),
                    "party": party
                })

    if debug:
        print("\n--- All detected race headers (council, header text) ---")
        for council, header in detected_headers:
            flag = "  <-- MUNI-CNC" if "MUNI-CNC" in header else ""
            print(f"  [{council}] {header}{flag}")

    return pd.DataFrame(parsed_rows)


def add_vote_shares(df, group_cols, total_cols):
    totals = df.groupby(
        group_cols,
        as_index=False,
        dropna=False,
    )["votes"].sum()

    totals["race_total"] = totals.groupby(
        total_cols,
        dropna=False,
    )["votes"].transform("sum")
    totals["vote_share_pct"] = (totals["votes"] / totals["race_total"] * 100).round(2)
    return totals


def main():
    records = extract_records(PDF_PATH)
    print(f"Total lines extracted: {len(records)}")

    df = parse_records(records, debug=True)
    print(f"\nTotal candidate rows parsed: {len(df)}")

    if df.empty:
        print("No rows parsed.")
        return

    # Keep council_district in the grouping so races aren't merged across districts.
    by_district = add_vote_shares(
        df,
        ["council_district", "race", "candidate", "party"],
        ["council_district", "race"],
    )

    by_district = by_district.sort_values(
        ["council_district", "race", "votes"], ascending=[True, True, False]
    )

    aggregate = add_vote_shares(
        df,
        ["race", "candidate", "party"],
        ["race"],
    )
    aggregate = aggregate.sort_values(
        ["race", "votes"], ascending=[True, False]
    )

    by_district.to_csv(BY_DISTRICT_OUTPUT_CSV, index=False)
    aggregate.to_csv(AGGREGATE_OUTPUT_CSV, index=False)
    print(f"Saved {len(by_district)} rows to {BY_DISTRICT_OUTPUT_CSV}")
    print(f"Saved {len(aggregate)} rows to {AGGREGATE_OUTPUT_CSV}")


if __name__ == "__main__":
    main()
