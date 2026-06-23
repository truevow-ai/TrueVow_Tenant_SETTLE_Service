"""
Smoke test for _common/extract.py (PI relevance + outcome/injury extraction).
Run: python settle_data_scraping_factory/_common/test_extract.py
Exits 0/1. Combines synthetic precision tests with a real-data abstention test.
"""

import sys
from extract import extract, find_amounts
from fetcher import Fetcher

failures = []


def check(name, cond):
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
    if not cond:
        failures.append(name)


def main() -> int:
    print("Synthetic — positive MVA verdict:")
    t1 = ("The jury awarded the plaintiff $1,250,000 in damages for the cervical spine "
          "injuries he sustained in the motor vehicle accident caused by the defendant's negligence.")
    e1 = extract(t1)
    check("is_pi True", e1.is_pi)
    check("amount == 1,250,000", e1.amount == 1_250_000)
    check("case_type motor_vehicle_accident", e1.case_type == "motor_vehicle_accident")
    check("injuries include neck", "neck" in e1.injuries)
    check("injuries include back", "back" in e1.injuries)
    check("amount_snippet quotes the figure", e1.amount_snippet and "1,250,000" in e1.amount_snippet)
    check("confidence > 0.4", e1.confidence > 0.4)

    print("Synthetic — settlement w/ scale word + wrongful death:")
    t2 = ("The parties reached a confidential settlement of $1.5 million to resolve the "
          "wrongful death claim arising from the defendant's negligence.")
    e2 = extract(t2)
    check("is_pi True (2+ terms)", e2.is_pi)
    check("amount == 1,500,000 (scale)", e2.amount == 1_500_000)
    check("outcome_type settlement", e2.outcome_type == "settlement")
    check("injuries include fatality", "fatality" in e2.injuries)

    print("Synthetic — K/M suffixes:")
    check("$750K -> 750000", any(h.value == 750_000 for h in find_amounts("a $750K verdict was returned")))
    check("$2.5M -> 2500000", any(h.value == 2_500_000 for h in find_amounts("settled for $2.5M in damages")))

    print("Synthetic — NEGATIVE / abstention (no hallucination):")
    t3 = ("In re Amendments to Florida Rule of Criminal Procedure 3.851 and Florida Rule "
          "of Appellate Procedure 9.142. The Court adopts the proposed amendments.")
    e3 = extract(t3)
    check("non-PI -> is_pi False", e3.is_pi is False)
    check("non-PI -> amount None", e3.amount is None)
    check("years/citations not treated as money", not find_amounts("decided in 2008, 1 So. 3d 163, page 12"))

    print("Real data — run over 5 so3d Florida cases (must abstain on non-PI, no fake $):")
    try:
        with Fetcher(min_delay=0.3) as f:
            # reuse Piece 3's fetcher logic inline (metadata -> first FL cases -> text)
            import json as _json
            vols = f.get_json("https://static.case.law/so3d/VolumesMetadata.json").json()
            vol = vols[0]["volume_folder"]
            metas = f.get_json(f"https://static.case.law/so3d/{vol}/CasesMetadata.json").json()
            fl = [m for m in metas if (m.get("jurisdiction") or {}).get("name_long") == "Florida"][:5]
            ran = 0
            hallucinated = 0
            for m in fl:
                case = f.get_json(f"https://static.case.law/so3d/{vol}/cases/{m['file_name']}.json").json()
                ops = (case.get("casebody") or {}).get("opinions") or []
                text = "\n".join(o.get("text", "") for o in ops)
                e = extract(text)
                ran += 1
                # If extractor says not-PI it must NOT emit an amount.
                if (not e.is_pi) and e.amount is not None:
                    hallucinated += 1
            check("ran over real cases", ran == 5)
            check("no amount emitted on non-PI cases (zero fabrication)", hallucinated == 0)
    except Exception as ex:
        check(f"real-data run (no exception) [{str(ex)[:60]}]", False)

    print()
    if failures:
        print(f"RESULT: FAILED ({len(failures)}) -> {failures}")
        return 1
    print("RESULT: ALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
