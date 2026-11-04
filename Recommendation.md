# Recommendation: estimating washing-machine use from smart-meter data

*Audience: distribution utility. Evidence: 20 UK REFIT homes, 2013–2015; full details in
[RESULTS.md](RESULTS.md) and [DATA.md](DATA.md).*

## What we built and how well it works

A model that estimates washing-machine (WM) power from **1-minute whole-house readings**, trained on
4 homes and tested on 2 homes it had never seen.

| Question | Answer on the unseen homes |
|---|---|
| How many washes, and when? | **Good.** Finds **8 in 10 washes** (cycle recall 0.82), and **77 % of the washes it reports are real**: 703 predicted vs 657 true, about 1.07 per real wash. Minute-level on/off F1 is 0.695. |
| How much energy did the WM use over the period? | **Not reliable: under-estimated by 22–52 %** (−45.1 % pooled; −52.1 % and −22.0 % per home; the two homes actually used 0.70 and 0.24 kWh/day). Detected washes get about the right power; the shortfall is washes missed during busy periods (e.g. while a shower runs). |
| WM energy on a given day? | Typical error **252 Wh/day**, against a typical wash of about 0.3–0.7 kWh, so single days are unreliable |
| Minute-by-minute power? | Better than predicting "off" (MAE 14.29 vs 20.32 W) but not precise enough to show a customer |

Energy error even changes sign between homes: +3.3 % on the validation home, −52.1 % on one test
home. The model is a **wash detector**, not an energy meter.

**Suitable uses**
- **When households wash**: the share of washes at the evening peak, typical wash times, washes
  per week, for groups of customers. For example, to size and target a load-shifting programme.
- **Screening** for households that frequently wash at the evening peak, as a starting list to
  confirm by survey, not as a verdict.

**Not suitable**
- WM **energy totals** per home (at most a lower bound: missed washes are not counted).
- Per-customer, per-day statements ("you washed at 18:12 yesterday").
- Billing, or anything with financial consequences for the customer.
- Homes where washing usually overlaps big loads (electric showers, cooking), or with washer-dryers.
- Use outside the UK without retraining on local sub-metered data.

---

## Section 4: practical implications

### 4.1 Opportunity: move evening-peak washes off the network peak

**Evidence.** In six homes, 16.2 % of washes start on a **weekday between 16:00 and 19:59**, the
evening network peak, ranging from 2.2 % to **29.0 %** of a home's washes (House 10 starts
23 % of its washes at 19:00 alone). A wash uses a median 0.59 kWh, most of it in a ~15-minute
**~2 kW heating burst**, and three to eleven washes a week are typical. Homes 1 and 15 already use
night-time delay timers (many washes start 04:00–05:00), so shifting is clearly acceptable to some
households.

**Offer.** Target households where the model flags repeated peak-time washing with a
**"delay-start" nudge**: a message showing the cheaper off-peak window, ideally combined with a
time-of-use tariff or a small reward per shifted wash. This saves the customer money and reduces
peak demand; it moves energy rather than reducing it. A second message can promote 30 °C washes,
which cut the heater energy itself.

**How to measure whether it worked.**

1. **Randomised trial:** randomly split eligible households into treatment (nudge) and control
   groups, with at least 8 weeks of data before and after.
2. **Primary outcome:** share of washes starting in the weekday 16:00–20:00 window, measured with
   the cycle detector on the disaggregated signal. Compare change in treatment against change in
   control (difference-in-differences).
3. **Secondary outcome:** household energy use in the 16:00–20:00 window. This comes straight from
   the meter and needs no model, so it guards against model error.
4. **Check the measurement:** validate the detector on a small sub-metered or self-reported sample.
   About 1 in 5 reported washes is false and about 1 in 5 real washes is missed, so changes in
   detected washes should be confirmed before claiming success.

### 4.2 Limitations

- **Overlapping appliance signatures.** The model recognises a ~2 kW heater step plus the drum's
  minute-to-minute flicker. Ovens and hobs that cycle on and off look similar: in testing, an
  evening cooking load was read as a 0.7 kWh wash. Washes that run under big loads are missed: a
  1.1 kWh wash during a morning shower was missed completely. This is why energy totals are
  too low.
- **Missing and faulty data.** 6–25 % of minutes are missing per home, including a 41-day
  outage. The published "cleaned" data forward-fills sensor gaps, so a dead meter looks like a
  flat line: up to 12 % of minutes in some homes. We now treat flat runs of an hour or more as
  outages. Estimates must be flagged when data are incomplete, and outages should not be counted
  as "no washing".
- **Household differences.** Peak power is similar across homes (2.05–2.33 kW), but wash
  length (median 33–120 min), energy per wash (317–711 Wh) and timing vary several-fold. Four
  training homes cannot represent all households; energy error on a new home ranged from −52 % to
  +3 %.
- **From UK homes to India.**
  - **Different machines:** many Indian machines are cold-fill semi-automatic or top-loaders
    **without an internal heater**, which removes the signature this model relies on.
  - **Different appliance mix:** water heaters (geysers, 2–3 kW), air-conditioners and pumps
    overlap with the WM in power.
  - **Different supply and metering:** power cuts, inverter backups, voltage fluctuation, shared
    or multi-dwelling meters, and many meters reporting only every 15–30 minutes.
  - **What this means:** the UK model should not be transferred directly. It needs retraining and
    validation on sub-metered Indian homes, and the cycle rule needs re-tuning for low-power
    (~200–500 W) machines.

### 4.3 What gets harder with 15- or 30-minute smart-meter data

At 15 or 30 minutes, a whole wash spans only two to eight readings, and its defining feature, a
~15-minute 2 kW heating burst, becomes a single interval that is about 0.5 kWh higher than
usual. That bump looks the same as a kettle plus an oven, or a short shower. Every input this
model uses disappears: sharp on/off steps, the minute-level tumbling pattern, the timing of
heating within the wash. Start times can only be located to within the interval, so "did they wash
at 19:00 or 19:25" becomes unknowable. Short washes (House 1's are ~33 minutes) may fall entirely
inside one interval. What remains possible is **statistical**: estimating, over weeks and across
many homes, how much energy and how many likely washes there are from repeated ~0.3–0.7 kWh bumps,
ideally with labelled training data at that resolution. Results should be reported for groups
of customers rather than individual days. Measuring the loss by retraining this pipeline on data
resampled to 15/30 minutes is the obvious next experiment.
