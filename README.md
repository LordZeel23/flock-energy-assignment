# REFIT: raw-data cleaning, washing-machine EDA and disaggregation

Take-home assignment for Flock Energy. A small, reproducible Python pipeline that

1. inspects and cleans the **raw** REFIT data for House 1 and resamples it to 1 minute,
2. explores **washing-machine (WM)** use in 6 houses of the **official cleaned** REFIT data,
3. trains and evaluates a **two-stage LightGBM** model (is the WM on? how much power?) that
   estimates WM power from the household aggregate at 1-minute resolution, against two simple
   baselines,
4. turns the results into a utility-facing recommendation.

| Document | Content |
|---|---|
| [DATA.md](DATA.md) | Raw-data coverage and quality findings, cleaning steps, gap/outlier decisions, remaining concerns |
| [RESULTS.md](RESULTS.md) | WM EDA, model results, validation design, failure analysis |
| [Recommendation.md](Recommendation.md) | One-page utility summary and answers to the Section 4 questions |

## Repository layout

```
run_all.py               one command: runs every stage below in order
src/config.py            paths, WM channel per house, every threshold, house split
src/clean_raw.py         Stage 1  raw House 1 -> inspection, cleaning, 1-min, plots
src/prepare_clean.py     Stage 2  official cleaned CSVs -> 1-min parquet cache (18 WM houses)
src/eda_washing.py       Stage 3  cycle detection, availability, patterns, sensitivity, plots
src/model.py             Stage 4  features, baselines, LightGBM, metrics, plots, failure cases
outputs/figures/         every figure referenced in the docs
outputs/tables/          every number quoted in the docs (CSV)
data/                    REFIT data (not in git, see below); data/cache/ is generated
```

## Setup and run

Tested on Windows 11 with Python 3.11.9.

```bash
pip install -r requirements.txt
```

The data is not in this repository (several GB). Download it from the University of Strathclyde:

- Raw data: <https://pureportal.strath.ac.uk/files/62090177/REFIT_RAW_081116.7z>
- Cleaned data: <https://pureportal.strath.ac.uk/files/62090184/CLEAN_REFIT_081116.7z>
- Cleaned-data readme: <https://pure.strath.ac.uk/ws/portalfiles/portal/62090183/CLEAN_READ_ME_081116.txt>
- Dataset page: <https://pureportal.strath.ac.uk/en/datasets/refit-electrical-load-measurements/>

Extract the two `.7z` archives (for example with 7-Zip) into `data/` so that the folder looks like
this:

```
data/REFIT_RAW_081116/RAW_House1_Part1.csv ... RAW_House21_Part2.csv
data/CLEAN_REFIT_081116/CLEAN_House1.csv ... CLEAN_House21.csv
data/CLEAN_READ_ME_081116.txt
```

Then run everything end to end:

```bash
python run_all.py
```

A full run takes about 11 minutes on a laptop (stage times: raw cleaning 59 s, cleaned-data cache
127 s, EDA 8 s, model 469 s) and regenerates `data/cache/`, `outputs/figures/` (16 PNGs) and
`outputs/tables/` (20 CSVs). Each stage can also be run on its own from `src/` (`python clean_raw.py`, etc.); stages 3 and 4
read the cache written by stage 2. All randomness is seeded (`RANDOM_SEED = 42`, LightGBM
`deterministic=True`), so reruns reproduce the tables exactly.

## Assumptions

- **Timestamps.** `Unix` is the authoritative time. In the *raw* files it is UK local wall-clock
  time (it jumps ±1 h at daylight-saving changes); in the *cleaned* files it is true UTC (the
  readme says so, and it matches the raw data at a 0 h shift in winter and +1 h in summer,
  correlation 0.999). Hour-of-day and day-of-week analysis uses Europe/London local time.
- **Units.** All power values are active power in watts; energy is integrated from 1-minute means
  (W x 1/60 h).
- **WM channel** per house is taken from the official readme (`WM_CHANNEL` in `src/config.py`).
  House 4 (two washing machines) and House 12 (none) are excluded.
- **Impossible values.** Aggregate > 23 kW (about a 100 A single-phase supply) or ≤ 0 W, and any
  appliance > 4 kW (above any 13 A plug load) are treated as sensor errors.

## Preprocessing decisions (details in [DATA.md](DATA.md))

- **Raw House 1:** where Part1 and Part2 overlap, Part2 is used; the ambiguous repeated hour at each
  autumn clock change is dropped; for duplicate timestamps the first non-missing value per channel
  is kept; impossible values are set to missing per channel; data is resampled to 1-minute means;
  gaps ≤ 5 min are linearly interpolated and longer gaps are left missing and flagged as outages.
- **Cleaned data:** used as published (already de-duplicated, spike-filtered, DST-corrected). The
  same 1-minute and ≤ 5-minute-gap rule is applied. Minutes where WM > aggregate (impossible,
  < 0.1 % of minutes in the houses used) are excluded from model training and scoring. For the
  model, the aggregate is treated as missing wherever it is exactly flat for an hour or more:
  a stuck, forward-filled sensor (up to 8 % of a model house's minutes).

## Validation design

- **Split by house:** train on houses 2, 7, 10, 15; validate on house 9; test on houses 8 and 17,
  which are never used for EDA, feature choice or tuning.
- **Split by time within the training houses:** the model only sees the first 80 % of each training
  house's timeline. The last 20 % (spring–summer 2015), after a 1-day embargo that is longer
  than the ±60-minute input window, is a second test set ("same house, future months").
- **No random shuffling of minutes**, because neighbouring windows overlap almost completely and a
  random split would leak near-copies of test inputs into training.
- The validation house is used only to (a) pick the feature set, (b) pick the on/off thresholds and
  (c) pick the final model among four candidates (single vs two-stage, with or without cycle
  post-processing), always by on/off F1.

## Trade-offs

- **LightGBM on hand-made window features rather than a neural network.** The plan was to keep it
  quick to train, easy to inspect and easy to reproduce. The idea of predicting the midpoint of a
  window comes from Seq2Point, but the window is summarised with rolling statistics instead of a CNN.
- **One feature set chosen on validation:** clock-time features were dropped (they encode the
  training houses' own habits). The gain on validation was small (RMSE 142.7 W vs 143.1 W with
  them) but the model is more transferable.
- **Fixed 600 boosting rounds instead of early stopping:** the validation error curve is almost
  flat, so early stopping stopped after about 15 trees, an under-fitted model (see RESULTS.md).
- **The final model is a good wash detector but a poor energy meter.**
  - *What it gained:* against a single regressor with the same features and post-processing,
    the two-stage model raised unseen-house cycle F1 from 0.56 to 0.79 and cut predicted washes
    from 1,489 to 703 (657 true). Per-minute MAE now beats always-off (14.29 vs 20.32 W).
  - *What it lost:* total energy went from −26.9 % to −45.1 %. The model now stays silent when a
    wash is buried under big loads, and those missed washes are where the energy goes.
  - *How it was chosen:* on the validation house by on/off F1, before the test results were seen.
    There, energy improved to +3.3 %, which did not transfer.
  - We report this rather than tuning on the test houses. The use case in Recommendation.md
    (timing of washes) needs detection, not energy totals.
- **Simple cleaning rules** rather than reproducing the official REFIT corrections (e.g. moving
  appliance monitors that householders swapped). These are documented as remaining concerns.
- **Six EDA houses and seven model houses** out of 18 available, chosen on data quality.

## Research used

- **Murray, D., Stankovic, L. & Stankovic, V. (2017).** *An electrical load measurements dataset of
  United Kingdom households from a two-year longitudinal study.* Scientific Data 4, 160122.
  Used for the dataset description, sampling, known collection issues and the raw-vs-cleaned
  distinction. The dataset licence also asks for: Murray, D. et al. (2015), *A data management
  platform for personalised real-time energy feedback*, EEDAL'15.
- **Zhang, C., Zhong, M., Wang, Z., Goddard, N. & Sutton, C. (2018).** *Sequence-to-point learning
  with neural networks for non-intrusive load monitoring.* AAAI-18. Adopted: predict the appliance
  power at the **midpoint** of a window of aggregate readings (non-causal context on both sides),
  and test on houses not seen in training.
- **Kelly, J. & Knottenbelt, W. (2015).** *Neural NILM: deep neural networks applied to energy
  disaggregation.* BuildSys '15. Adopted: defining appliance activations with an on-power
  threshold plus minimum on/off durations (our cycle rule), testing on unseen houses, and
  reporting several complementary metrics (on/off precision/recall/F1, relative error in total
  energy, mean absolute error) instead of one number.

## AI tools used

This project was built with **Claude Code** (Anthropic) as a coding assistant. It drafted the
scripts, ran the analysis and drafted the documentation, working phase by phase from an agreed
plan; each phase's outputs were reviewed before moving on. Analysis decisions (rules that differed
from the plan, the house split, dropping features) were checked against the data and are explained
in the docs. All numbers in the docs come from `outputs/tables/`.

## Possible improvements (next steps, in priority order)

Already done after the first version: masking stuck-aggregate periods, cycle post-processing of
predictions, steady-load features, and the two-stage model (see Trade-offs).

1. **Recover washes hidden under big loads**, the main cause of the −45.1 % energy error. Options:
   - train with more examples of overlapping loads, e.g. by adding real WM cycles to other houses'
     busy periods (synthetic mixing, as in Kelly & Knottenbelt 2015);
   - lower the classifier cut-off only when a large load is running.
2. **More training houses / leave-one-house-out cross-validation.** Results vary strongly between
   houses (energy error +3.3 % on validation, −52.1 % and −22.0 % on the test houses); a
   single validation house is a thin basis for choosing settings.
3. **A Seq2Point CNN** on the same split, to see whether learned shape features beat hand-made ones.
4. **A coarse-resolution experiment:** resample to 15/30 minutes and retrain to measure how much
   accuracy is lost (see Recommendation.md).
5. **Per-appliance plausibility limits** in the raw cleaning (for example fridge > 1 kW), and
   filling Part2 outages from Part1 where the two raw files overlap.
