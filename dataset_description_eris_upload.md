# Autodilution Protocol Counterfactual QA Dataset

## Overview

This synthetic dataset contains deterministic liquid-handling protocol traces for a mini assay deck. Each row is a counterfactual question: execute the original protocol, replace one specified operation, execute the mutated protocol, and determine which answer choice best describes the dominant change in a target well.

The dataset was generated locally using the included `generate_raw.py` script with a fixed random seed. It is intended for a from-scratch benchmark: participants should implement a protocol interpreter and counterfactual comparator rather than use external data or pretrained models.

## File Structure

The uploaded raw dataset zip contains exactly these top-level files:

| File | Description |
|---|---|
| `data.csv` | Raw generated counterfactual question rows. Each row contains an original protocol, target well, replacement operation, public metadata, answer choices, the correct answer label, and hidden diagnostic fields. |
| `generate_raw.py` | Deterministic Python script used to create `data.csv` from a fixed random seed. |

The challenge preparation step creates the files that participants use:

| Prepared File | Description |
|---|---|
| `train.csv` | Public training questions with `answer_label`. |
| `test.csv` | Public test questions without `answer_label`. |
| `sample_submission.csv` | Example submission with `question_id` and random valid answer labels. |
| `private/answers.csv` | Private answer labels and hidden grouping columns used only by the grader. |

## Raw Columns

| Column | Type | Description |
|---|---|---|
| `question_id` | string | Raw question identifier; remapped before public release. |
| `target_well` | string | Well whose final state is compared after the mutation. |
| `protocol_text` | string | Original semicolon-separated liquid-handling protocol. |
| `mutation_index` | int | One-based operation index to replace. |
| `replacement_operation` | string | Replacement operation for the counterfactual run. |
| `question_text` | string | Natural-language counterfactual question. |
| `question_type` | categorical | Question family; currently `counterfactual_dominant_shift`. |
| `difficulty_tier` | categorical | Difficulty level: `easy`, `medium`, or `hard`. |
| `mutation_family` | categorical | Mutated operation family such as `pipet`, `fanout`, `rinse`, `evap`, `decay`, `carry`, or `cap`. |
| `operation_count` | int | Number of operations in the original protocol. |
| `deck_format` | categorical | Deck layout context: `two_plate_bridge`, `source_to_assay`, or `three_zone_validation`. |
| `head_mode` | categorical | Pipette head mode: `single_tip`, `span8`, or `eight_channel`. |
| `stress_regime` | categorical | Protocol stress context: `low_loss`, `carryover_prone`, `evaporation_prone`, or `mixed_stress`. |
| `A` | string | Choice A text. |
| `B` | string | Choice B text. |
| `C` | string | Choice C text. |
| `D` | string | Choice D text. |
| `answer_label` | string | Correct answer label: `A`, `B`, `C`, or `D`. |
| `answer_key_private` | string | Hidden diagnostic category used only to audit answer balance; removed before public release. |

## Public Prepared Columns

| Column | Type | Public Train | Public Test | Description |
|---|---|---|---|---|
| `question_id` | string | yes | yes | Opaque remapped question identifier. |
| `target_well` | string | yes | yes | Requested final well. |
| `protocol_text` | string | yes | yes | Original DSL program. |
| `mutation_index` | int | yes | yes | Operation number to replace. |
| `replacement_operation` | string | yes | yes | Counterfactual replacement operation. |
| `question_text` | string | yes | yes | Natural-language prompt. |
| `question_type` | categorical | yes | yes | Question family. |
| `difficulty_tier` | categorical | yes | yes | Easy, medium, or hard tier. |
| `mutation_family` | categorical | yes | yes | Family of operation being changed. |
| `operation_count` | int | yes | yes | Number of original protocol operations. |
| `deck_format` | categorical | yes | yes | Public deck layout context. |
| `head_mode` | categorical | yes | yes | Public pipette head context. |
| `stress_regime` | categorical | yes | yes | Public stress context. |
| `A`, `B`, `C`, `D` | string | yes | yes | Candidate answer texts. |
| `answer_label` | string | yes | no | Correct choice label. |

The sample submission contains exactly `question_id` and `answer_label`.

## Data Characteristics

- 4,200 raw counterfactual questions.
- Protocols contain roughly 26 to 46 operations.
- Each question requires two executions of the DSL: one original and one mutated.
- Operations include `SEED`, `PIPET`, `FANOUT`, `DILUTE`, `EVAP`, `DECAY`, `RINSE`, `CARRY`, and `CAP`.
- Answer labels are randomized across `A`, `B`, `C`, and `D`.
- Hidden scoring groups check robustness across difficulty tiers, mutation families, stress regimes, and operation-count bands.
- Metadata alone is intentionally insufficient; the answer depends on protocol execution and counterfactual comparison.

## License and Source

The dataset is generated locally from the included script and is released as CC0 1.0 Public Domain. No external source data is used.
