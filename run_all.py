"""Run the whole pipeline end to end:  python run_all.py

  1. clean_raw      raw House 1 -> inspection, cleaning, 1-min, plots
  2. prepare_clean  official cleaned data -> 1-min parquet cache (18 WM houses)
  3. eda_washing    washing-machine cycles, patterns, sensitivity, plots
  4. model          LightGBM vs baselines, metrics, plots, failure cases

Outputs: outputs/figures/, outputs/tables/ (regenerated on every run).
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

import config as C  # noqa: E402
import clean_raw  # noqa: E402
import eda_washing  # noqa: E402
import model  # noqa: E402
import prepare_clean  # noqa: E402

STAGES = [
    ("1/4 raw cleaning (House 1)", clean_raw.main),
    ("2/4 prepare cleaned data", prepare_clean.main),
    ("3/4 washing-machine EDA", eda_washing.main),
    ("4/4 disaggregation model", model.main),
]


def main():
    C.check_data_available()
    C.ensure_output_dirs()
    t0 = time.time()
    for name, fn in STAGES:
        t = time.time()
        print(f"\n===== {name} =====", flush=True)
        fn()
        print(f"----- {name} done in {time.time() - t:.0f} s", flush=True)
    print(f"\nAll stages finished in {(time.time() - t0) / 60:.1f} min. "
          f"Figures: {C.FIG_DIR}  Tables: {C.TAB_DIR}")


if __name__ == "__main__":
    main()
