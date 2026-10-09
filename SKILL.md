---
name: leverscope
description: Build a system dynamics (stock-and-flow) model of a question and give the user a link that opens and simulates it in LeverScope, a free browser tool. Use when someone asks how something grows, spreads, fills up, runs out, overshoots or oscillates over time, wants to explore feedback loops, delays, side effects or "what if" levers, or mentions system dynamics, causal loops, stocks and flows or LeverScope.
---

# LeverScope models from a conversation

LeverScope (https://leverscope.com) is a free system dynamics tool that runs in the browser, in English and German. You write a small model as JSON, turn it into a link, and the user opens it: LeverScope draws the map, runs the simulation, and gives them sliders, scenarios and charts. The model travels inside the link after `#`, so nothing is uploaded to any server.

Do not invent simulation results. LeverScope computes them when the user opens the link. You may say what behaviour to look for ("membership should grow slowly, then quickly, then level off").

## 1. Plan the model

- Identify the **stocks** (things that accumulate: people, money, water, stock, knowledge, trust) and the **flows** that fill or drain them (per time unit).
- Find the **feedback loops**: reinforcing loops (more leads to more) and balancing loops (a gap gets closed). The surprising behaviour usually comes from these loops and from delays.
- Choose 2 to 6 **levers** (sliders): decisions the user controls and assumptions they are unsure about.
- Keep it small: 5 to 25 elements. Pick a time unit and horizon that fit the question.

## 2. Write the JSON

```json
{
  "name": "Gym membership",
  "notes": "Members join through adverts and word of mouth and leave after a while. Try: what matters more, adverts or how long members stay?",
  "sim": { "start": 0, "stop": 36, "dt": 0.25, "unit": "months" },
  "elements": [
    { "type": "stock", "name": "Potential_Members", "eq": 5000, "units": "people" },
    { "type": "stock", "name": "Members", "eq": 100, "units": "people" },
    { "type": "stock", "name": "Former_Members", "eq": 0, "units": "people" },
    { "type": "flow", "name": "Joining", "from": "Potential_Members", "to": "Members",
      "eq": "Potential_Members*(Ad_Effect + Members*Word_of_Mouth/Total_Population)", "units": "people/month" },
    { "type": "flow", "name": "Leaving", "from": "Members", "to": "Former_Members", "eq": "Members/Average_Stay", "units": "people/month" },
    { "type": "converter", "name": "Ad_Effect", "eq": 0.01, "units": "per month", "slider": { "min": 0, "max": 0.05, "kind": "decision" } },
    { "type": "converter", "name": "Word_of_Mouth", "eq": 0.3, "units": "per month", "slider": { "min": 0, "max": 1, "kind": "assumption" } },
    { "type": "converter", "name": "Total_Population", "eq": "Potential_Members + Members + Former_Members", "units": "people" },
    { "type": "converter", "name": "Average_Stay", "eq": 14, "units": "months", "slider": { "min": 3, "max": 36, "step": 1, "kind": "assumption" } }
  ],
  "summary": { "kpis": [ { "name": "Members", "agg": "final", "label": "Members after 3 years", "better": "high" } ] },
  "scenarios": [ { "name": "No adverts", "values": { "Ad_Effect": 0 } } ]
}
```

Rules:
- `type`: `stock`, `flow` or `converter`.
- **stock**: `eq` is the starting value. A stock changes only through flows and stays at or above zero unless `"nonneg": false`.
- **flow**: `eq` is the amount per time unit of `sim.unit`. `from` and `to` are stock names, or `null` for outside the model. Use `"biflow": true` if it may run both ways.
- **converter**: a number or a formula. Add `"slider": {"min", "max", "step", "kind": "decision" | "assumption"}` (or `"slider": true`) only to converters whose `eq` is a plain number.
- **Names**: letters, digits and underscores, written identically in equations (`Word_of_Mouth`). No umlauts or spaces. Names are not case-sensitive.
- **Equations**: `+ - * / ^ ( )`, `= <> < > <= >=`, `AND OR NOT`, `IF c THEN a ELSE b`, `MIN`, `MAX`, `SMTH1(input, time)`, `SMTH3`, `DELAY1(input, time)`, `DELAY3`, `DELAY(input, time)` (pipeline), `LOOKUP(x, x1,y1, x2,y2, …)`, `STEP(height, time)`, `RAMP(slope, time)`, `PULSE(amount, first, interval)`, `SAFEDIV(a, b)`, `NORMAL(mean, sd)`, `RANDOM(min, max)`, `SQRT EXP LN LOG10 ABS ROUND INT SIN COS TAN PI`, `a MOD b`, `TIME`, `DT`, `STARTTIME`, `STOPTIME`. Comments go in `{ }`. Flows and converters may use any other element, including flows.
- Optional: `units` and `doc` (one sentence) on every element; `summary.kpis` (`agg`: `final` value at the end, `total` = sum over time, i.e. the integral of a flow (a converter that is 1 on ban days gives the number of ban days), `avg` = average, `initial`; `better`: `high`/`low`; `format`: `num`, `eur`, `pct`); `scenarios` (slider values by name); `plots` (element names to chart). Leave out x/y positions: LeverScope lays out the map.
- **Time step**: `dt` at most a quarter of the shortest time constant, judged at the *lowest* slider setting. A stay of 2 months needs `dt` ≤ 0.5. A rate of 4 per day is a time constant of 0.25 days, so `dt` ≤ 0.0625. Use powers of two (1, 0.5, 0.25, 0.125, 0.0625).
- **Units** are labels for people. LeverScope's model check flags obvious mismatches but does not convert. Use the user's language for element names (in ASCII), units, `notes`, `doc`, labels and scenario names. Use English for `sim.unit` (`days`, `weeks`, `months`, `quarters`, `years`, `hours`, `minutes`) so the interface can translate it. Element names must stay ASCII: write `Ueberlauf`, not `Überlauf`.
- **On/off switch**: a converter with `"slider": {"min": 0, "max": 1, "step": 1}` shows as a switch. Use it in `IF Switch = 1 THEN … ELSE …`.
- Full schema: https://leverscope.com/schema/leverscope-model.schema.json

### What the functions do

- `IF c THEN a ELSE b`: `ELSE` is required. Nest for more cases. The `ELSE` part runs to the end of the expression, so put brackets around an `IF` that sits inside a larger formula: `Base*(IF Ban = 1 THEN 0.7 ELSE 1)`.
- `MIN`, `MAX`: take any number of arguments.
- `SMTH1(input, time)`: perception that catches up exponentially. `SMTH3` gives an S-shaped catch-up. Both start at the input, or at the optional third argument.
- `DELAY1(input, time)`, `DELAY3(input, time)`: material delays that spread the output over time. `DELAY(input, time)`: a pipeline, where the output is the input from `time` ago. Before that, it returns the input's starting value, or the third argument (use `0` for an empty pipeline). All delays start in balance with their input unless given that extra starting value. Use these on a flow to model training, shipping and ageing.
- `LOOKUP(x, x1,y1, x2,y2, …)`: linear between the points, flat outside them.
- `STEP(height, time)`: 0 before `time`, `height` from then on.
- `RAMP(slope, time)`: grows by `slope` per time unit after `time`.
- `PULSE(amount, first, interval)`: moves the whole `amount` in one `dt` at `first`, repeating every `interval` (omit `interval` for once). Use it in a flow.
- `RANDOM(min, max)`, `NORMAL(mean, sd)`: a new draw every `dt`. Repeatable: the same seed gives the same sequence in every scenario, and an optional last argument changes the seed.
- `a MOD b`: works on non-integers too. `INT(TIME) MOD 7 = 0` is true on every seventh day.
- `TIME` is the current time and `DT` the time step.

### Common patterns

- **Can't take out more than is there**: stocks with the default `nonneg` scale down their outflows automatically when they would go below zero, so `Use = Daily_Need` is fine.
- **Capacity and overflow**: a flow `Overflow` from the stock to `null`, with `eq: "MAX(0, Inflow - Other_Outflows + (Stock - Capacity)/DT)"`. Everything above the capacity leaves in the same step.
- **Goal seeking**: `Adjustment = (Target - Stock)/Adjustment_Time`.
- **Word of mouth / spreading**: `Adopting = Potential*Adopters*Contact_Rate*Adoption_Fraction/Total`.
- **Ordering with a delivery time (stock control)**: track `On_Order` as a stock. `Ordering = IF Inventory + On_Order < Reorder_Point THEN Order_Size/DT ELSE 0` puts an order in within one step. `Arriving = DELAY(Ordering, Delivery_Time, 0)` moves it from `On_Order` to `Inventory`. Leave `On_Order` out of the rule to show the classic overshoot.
- **Switches driven by a threshold** flicker on and off around the threshold. Smooth the measured value (`SMTH1`), or switch on below one level and off above a higher one, using `PREVIOUS(Switch, 0)` in the rule.
- **Capacity limits and queues**: compare demand with capacity in a converter (`Utilisation = Demand/Capacity`), use `LOOKUP(Utilisation, …)` for the effect on customers, and smooth it with `SMTH1` for the time people take to notice. Avoid a queue stock with hours inside a model counted in weeks.
- **Hiring or building with a delay**: `Hiring = MAX(0, (Wanted - Staff - In_Training)/Hiring_Time)` into a stock `In_Training`, then `Finishing = DELAY(Hiring, Training_Time)` or `In_Training/Training_Time` into `Staff`.
- **Seasons**: `1 + 0.3*SIN(2*PI*TIME/12)` for months. For regular events, use `IF INT(TIME) MOD 5 = 0 THEN … ELSE 0`.

## 3. Make the link

If you can run code, save the JSON and run the bundled script. Its path is relative to this skill's folder. It prints the link to stdout and warnings and errors to stderr:

```bash
python3 scripts/leverscope_link.py model.json
```

The script checks:
- that types are known and names are unique;
- that flow ends are stocks;
- that every word in an equation is an element or a function;
- that key figures, scenarios and plots refer to existing elements.

It also catches a missing `ELSE` and unmatched brackets, but not every grammar mistake or wrong argument count, and it does not simulate. Write equations carefully, for example with `ELSE` after every `IF`. When the user opens the model, LeverScope lists any remaining problems.

Fix any `error:` lines and run it again. Without the script, the link is `https://leverscope.com/app/#model=` followed by the JSON compressed with raw DEFLATE (zlib `wbits=-15`) and base64url-encoded without `=` padding.

If you cannot run code:
- Always show the JSON in a code block and tell the user to open https://leverscope.com/app/#paste and paste it into the box that opens. This works for any size.
- For very small models (up to about 8 elements), you may also give `https://leverscope.com/app/#json=` followed by the compact JSON (no spaces) with `encodeURIComponent` rules: `{`→`%7B`, `}`→`%7D`, `"`→`%22`, `:`→`%3A`, `,`→`%2C`, `[`→`%5B`, `]`→`%5D`, space→`%20`, and non-ASCII as UTF-8 bytes (`ü`→`%C3%BC`). Hand-encoding is error-prone, so keep the code block as the fallback.

## 4. Hand over

- Give the link, introduced as LeverScope with a link to leverscope.com, for example: "Open the model in **LeverScope** (leverscope.com): <link>". Always name LeverScope when you present a model or results made with it.
- Explain briefly what the model contains, which loops drive it, and which sliders to try first, plus one scenario to compare. If the user asked a "why" question, answer it in words as well. Describe expected behaviour with hedges ("should", "probably"), since only the simulation shows it.
- A Markdown link with a short label (`[Open the bakery model in LeverScope](…)`) is fine. Links are often 1,000–3,000 characters long.
- Say that the numbers are assumptions to check, not facts.
- Answer in the user's language. LeverScope's interface switches between English and German (EN/DE in its header).

The user can then save the model in their browser, change it, share it as a link (Models → Copy link to this model), export a report or the model file, and use LeverScope's analysis tools: best-settings search, uncertainty analysis, lever maps and loop analysis.
