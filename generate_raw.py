from pathlib import Path
import random

import pandas as pd


PLATES = ["SRC", "WORK", "OUT"]
ROWS = "ABCDEFGH"
COLS = range(1, 13)
WELLS = [f"{p}:{r}{c:02d}" for p in PLATES for r in ROWS for c in COLS]
START_WELLS = [f"SRC:{r}{c:02d}" for r in "ABCD" for c in range(1, 7)]
ACTIVE_WELLS = [f"WORK:{r}{c:02d}" for r in ROWS for c in range(1, 13)] + [
    f"OUT:{r}{c:02d}" for r in "ABCD" for c in range(1, 13)
]

LABELS = {
    "VOL_UP": "target volume increases the most",
    "VOL_DOWN": "target volume decreases the most",
    "A_UP": "antigen A percentage increases the most",
    "A_DOWN": "antigen A percentage decreases the most",
    "B_UP": "antigen B percentage increases the most",
    "B_DOWN": "antigen B percentage decreases the most",
    "BUFFER_UP": "buffer/rinse percentage increases the most",
    "NEAR_TIE": "no listed change clearly dominates",
}


def empty_well():
    return {"vol": 0.0, "a": 0.0, "b": 0.0, "buffer": 0.0, "carry": 0.0}


def add_payload(well, vol, a, b, buffer, carry):
    if vol <= 0:
        return
    old = well["vol"]
    new = old + vol
    well["a"] = (well["a"] * old + a * vol) / new
    well["b"] = (well["b"] * old + b * vol) / new
    well["buffer"] = (well["buffer"] * old + buffer * vol) / new
    well["vol"] = new
    well["carry"] = max(well["carry"], carry)


def remove_payload(well, vol):
    taken = min(max(float(vol), 0.0), well["vol"])
    payload = {
        "vol": taken,
        "a": well["a"],
        "b": well["b"],
        "buffer": well["buffer"],
        "carry": well["carry"],
    }
    well["vol"] -= taken
    if well["vol"] <= 1e-9:
        well.update(empty_well())
    return payload


def reagent_profile(name):
    if name == "ANTIGEN_A":
        return 1.0, 0.0, 0.0, 0.0
    if name == "ANTIGEN_B":
        return 0.0, 1.0, 0.0, 0.0
    if name == "BUFFER":
        return 0.0, 0.0, 1.0, 0.0
    if name == "RINSE":
        return 0.0, 0.0, 1.0, 0.03
    raise ValueError(name)


def execute(state, op):
    parts = op.split()
    cmd = parts[0]
    if cmd == "SEED":
        _, reagent, dst, vol = parts
        add_payload(state[dst], float(vol), *reagent_profile(reagent))
    elif cmd == "PIPET":
        _, src, dst, vol, loss = parts
        payload = remove_payload(state[src], float(vol))
        delivered = payload["vol"] * (1.0 - float(loss))
        add_payload(state[dst], delivered, payload["a"], payload["b"], payload["buffer"], payload["carry"])
    elif cmd == "FANOUT":
        _, src, dst1, dst2, dst3, vol, r1, r2, loss = parts
        payload = remove_payload(state[src], float(vol))
        delivered = payload["vol"] * (1.0 - float(loss))
        ratios = [float(r1), float(r2), max(0.0, 1.0 - float(r1) - float(r2))]
        for dst, ratio in zip([dst1, dst2, dst3], ratios):
            add_payload(state[dst], delivered * ratio, payload["a"], payload["b"], payload["buffer"], payload["carry"])
    elif cmd == "DILUTE":
        _, dst, reagent, vol = parts
        add_payload(state[dst], float(vol), *reagent_profile(reagent))
    elif cmd == "EVAP":
        _, dst, frac = parts
        state[dst]["vol"] *= max(0.0, 1.0 - float(frac))
    elif cmd == "DECAY":
        _, dst, a_frac, b_frac = parts
        state[dst]["a"] *= max(0.0, 1.0 - float(a_frac))
        state[dst]["b"] *= max(0.0, 1.0 - float(b_frac))
    elif cmd == "RINSE":
        _, dst, vol, retain = parts
        payload = remove_payload(state[dst], state[dst]["vol"])
        add_payload(state[dst], payload["vol"] * float(retain), payload["a"], payload["b"], payload["buffer"], payload["carry"])
        add_payload(state[dst], float(vol), *reagent_profile("RINSE"))
    elif cmd == "CARRY":
        _, src, dst, ppm = parts
        src_w = state[src]
        add_payload(
            state[dst],
            src_w["vol"] * float(ppm) / 1_000_000.0,
            src_w["a"],
            src_w["b"],
            src_w["buffer"],
            max(src_w["carry"], 0.10),
        )
    elif cmd == "CAP":
        _, dst, max_vol = parts
        state[dst]["vol"] = min(state[dst]["vol"], float(max_vol))


def run_protocol(ops, target):
    state = {well: empty_well() for well in WELLS}
    for op in ops:
        execute(state, op)
    final = state[target]
    denom = max(final["a"] + final["b"] + final["buffer"], 1e-9)
    return {
        "volume": final["vol"],
        "a_pct": 100.0 * final["a"] / denom,
        "b_pct": 100.0 * final["b"] / denom,
        "buffer_pct": 100.0 * final["buffer"] / denom,
    }


def build_protocol(rng):
    ops = []
    state = {well: empty_well() for well in WELLS}
    active = rng.sample(ACTIVE_WELLS, rng.randint(8, 14))
    sources = rng.sample(START_WELLS, 4)
    for src, reagent in zip(sources, ["ANTIGEN_A", "ANTIGEN_B", "BUFFER", rng.choice(["ANTIGEN_A", "ANTIGEN_B"])]):
        op = f"SEED {reagent} {src} {rng.choice([70, 90, 110, 130])}"
        ops.append(op)
        execute(state, op)

    for _ in range(rng.randint(22, 42)):
        occupied = [w for w, s in state.items() if s["vol"] > 0.4]
        cmd = rng.choices(
            ["PIPET", "FANOUT", "DILUTE", "EVAP", "DECAY", "RINSE", "CARRY", "CAP"],
            weights=[7, 4, 3, 3, 3, 3, 2, 1],
        )[0]
        if cmd == "PIPET" and occupied:
            op = f"PIPET {rng.choice(occupied)} {rng.choice(active)} {rng.choice([3, 5, 8, 13, 21, 34])} {rng.choice([0.00, 0.03, 0.07, 0.11]):.2f}"
        elif cmd == "FANOUT" and occupied:
            src = rng.choice(occupied)
            dst1, dst2, dst3 = rng.sample(active, 3)
            r1 = rng.choice([0.17, 0.29, 0.41, 0.53])
            r2 = rng.choice([0.19, 0.31, 0.37])
            if r1 + r2 >= 0.92:
                r2 = 0.23
            op = f"FANOUT {src} {dst1} {dst2} {dst3} {rng.choice([7, 11, 17, 23, 29])} {r1:.2f} {r2:.2f} {rng.choice([0.01, 0.04, 0.09]):.2f}"
        elif cmd == "DILUTE":
            op = f"DILUTE {rng.choice(active)} {rng.choice(['BUFFER', 'RINSE', 'ANTIGEN_A', 'ANTIGEN_B'])} {rng.choice([4, 7, 12, 19, 31])}"
        elif cmd == "EVAP" and occupied:
            op = f"EVAP {rng.choice(occupied)} {rng.choice([0.03, 0.07, 0.13, 0.21]):.2f}"
        elif cmd == "DECAY" and occupied:
            op = f"DECAY {rng.choice(occupied)} {rng.choice([0.00, 0.06, 0.12, 0.19]):.2f} {rng.choice([0.00, 0.05, 0.11, 0.17]):.2f}"
        elif cmd == "RINSE" and occupied:
            op = f"RINSE {rng.choice(occupied)} {rng.choice([6, 10, 14, 22])} {rng.choice([0.01, 0.04, 0.08, 0.13]):.2f}"
        elif cmd == "CARRY" and occupied:
            op = f"CARRY {rng.choice(occupied)} {rng.choice(active)} {rng.choice([200, 900, 2400, 5200, 9500])}"
        else:
            op = f"CAP {rng.choice(active)} {rng.choice([18, 27, 41, 64, 88])}"
        ops.append(op)
        execute(state, op)
    target = rng.choice([w for w in active if state[w]["vol"] > 0.2] or active)
    return ops, target


def mutate_op(rng, op):
    parts = op.split()
    cmd = parts[0]
    family = cmd.lower()
    out = parts[:]
    if cmd == "PIPET":
        out[3] = str(max(1, int(round(float(out[3]) * rng.choice([0.45, 0.65, 1.55, 2.10])))))
        out[4] = f"{min(0.19, max(0.0, float(out[4]) + rng.choice([-0.04, 0.05, 0.09]))):.2f}"
    elif cmd == "FANOUT":
        out[5] = str(max(1, int(round(float(out[5]) * rng.choice([0.50, 0.75, 1.45, 1.95])))))
        out[6] = f"{rng.choice([0.13, 0.25, 0.47, 0.61]):.2f}"
        out[7] = f"{rng.choice([0.18, 0.27, 0.39]):.2f}"
    elif cmd == "DILUTE":
        out[2] = rng.choice(["BUFFER", "RINSE", "ANTIGEN_A", "ANTIGEN_B"])
        out[3] = str(max(1, int(round(float(out[3]) * rng.choice([0.40, 0.70, 1.60, 2.25])))))
    elif cmd == "EVAP":
        out[2] = f"{rng.choice([0.01, 0.05, 0.16, 0.28, 0.36]):.2f}"
    elif cmd == "DECAY":
        out[2] = f"{rng.choice([0.00, 0.04, 0.18, 0.31]):.2f}"
        out[3] = f"{rng.choice([0.00, 0.03, 0.16, 0.29]):.2f}"
    elif cmd == "RINSE":
        out[2] = str(max(1, int(round(float(out[2]) * rng.choice([0.35, 0.75, 1.65, 2.40])))))
        out[3] = f"{rng.choice([0.00, 0.02, 0.11, 0.22]):.2f}"
    elif cmd == "CARRY":
        out[3] = str(rng.choice([50, 400, 1800, 7000, 13000]))
    elif cmd == "CAP":
        out[2] = str(rng.choice([12, 24, 38, 53, 72]))
    else:
        family = "seed"
        out[3] = str(max(1, int(round(float(out[3]) * rng.choice([0.55, 1.75])))))
    return " ".join(out), family


def classify_delta(base, changed):
    deltas = {
        "VOL_UP": (changed["volume"] - base["volume"]) / 9.0,
        "VOL_DOWN": (base["volume"] - changed["volume"]) / 9.0,
        "A_UP": (changed["a_pct"] - base["a_pct"]) / 11.0,
        "A_DOWN": (base["a_pct"] - changed["a_pct"]) / 11.0,
        "B_UP": (changed["b_pct"] - base["b_pct"]) / 11.0,
        "B_DOWN": (base["b_pct"] - changed["b_pct"]) / 11.0,
        "BUFFER_UP": (changed["buffer_pct"] - base["buffer_pct"]) / 11.0,
    }
    best, value = max(deltas.items(), key=lambda item: item[1])
    ordered = sorted(deltas.values(), reverse=True)
    if value < 0.45 or (len(ordered) > 1 and ordered[0] - ordered[1] < 0.14):
        return "NEAR_TIE"
    return best


def build_row(rng, idx):
    while True:
        ops, target = build_protocol(rng)
        mutable = [i for i, op in enumerate(ops) if op.split()[0] != "SEED"]
        mutation_index = rng.choice(mutable)
        mutated_op, mutation_family = mutate_op(rng, ops[mutation_index])
        changed_ops = ops[:]
        changed_ops[mutation_index] = mutated_op
        base = run_protocol(ops, target)
        changed = run_protocol(changed_ops, target)
        answer_key = classify_delta(base, changed)
        if answer_key != "NEAR_TIE" or rng.random() < 0.35:
            break

    labels = list(LABELS)
    choices = [answer_key]
    hard_negatives = [k for k in labels if k != answer_key]
    rng.shuffle(hard_negatives)
    choices += hard_negatives[:3]
    rng.shuffle(choices)
    answer_label = "ABCD"[choices.index(answer_key)]
    difficulty_tier = "hard" if len(ops) >= 39 or mutation_family in {"fanout", "carry", "rinse"} else ("medium" if len(ops) >= 32 else "easy")
    deck_format = rng.choice(["two_plate_bridge", "source_to_assay", "three_zone_validation"])
    head_mode = rng.choice(["single_tip", "span8", "eight_channel"])
    stress_regime = rng.choice(["low_loss", "carryover_prone", "evaporation_prone", "mixed_stress"])

    return {
        "question_id": f"adlcf_{idx:06d}",
        "target_well": target,
        "protocol_text": " ; ".join(ops),
        "mutation_index": mutation_index + 1,
        "replacement_operation": mutated_op,
        "question_text": (
            f"Execute the protocol for {target}. Then replace operation {mutation_index + 1} "
            f"with `{mutated_op}` and execute again. Which listed effect best describes "
            "the changed final state compared with the original final state?"
        ),
        "question_type": "counterfactual_dominant_shift",
        "difficulty_tier": difficulty_tier,
        "mutation_family": mutation_family,
        "operation_count": len(ops),
        "deck_format": deck_format,
        "head_mode": head_mode,
        "stress_regime": stress_regime,
        "A": LABELS[choices[0]],
        "B": LABELS[choices[1]],
        "C": LABELS[choices[2]],
        "D": LABELS[choices[3]],
        "answer_label": answer_label,
        "answer_key_private": answer_key,
    }


def main():
    rng = random.Random(2026062807)
    rows = [build_row(rng, i) for i in range(4200)]
    out = Path("raw") / "data.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(out, index=False)
    print(f"Wrote {out} with {len(rows)} rows")


if __name__ == "__main__":
    main()
