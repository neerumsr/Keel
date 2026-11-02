## 1. Reproduction of bench grading (shipped keel.json)

| suite | choice | score | noul | safety | fully right |
|---|---|---|---|---|---|
| labeled-50 | 33/34 | 13/14 | 8/8 | 0 | 48/50 |
| holdout-20 | 10/15 | 4/5 | 2/2 | 1 | 14/20 |
| holdout-b-20 | 8/15 | 2/5 | 1/2 | 1 | 10/20 |
| open-60 | 24/36 | 6/14 | 4/10 | 1 | 34/60 |

## 2. Calibration � dev (in-distribution synthetic)

shipped {"choice_n": 797, "choice_acc": 0.8545, "choice_ece": 0.0564, "choice_nll": 0.5474, "choice_brier": 0.219, "ambiguous_n": 103, "ambiguous_mean_conf": 0.2978, "score_n": 219, "score_mae": 0.385, "score_nll": 0.6496, "score_slope_pred_vs_true(normalized)": 0.6563, "noul_n": 296, "noul_nll": 0.4386, "noul_brier": 0.0763, "noul_acc@0.5": 0.8615, "noul_ece": 0.0668}
neural-only (blend 0) {"choice_n": 797, "choice_acc": 0.8407, "choice_ece": 0.0618, "choice_nll": 0.5573, "choice_brier": 0.2271, "ambiguous_n": 103, "ambiguous_mean_conf": 0.2975, "score_n": 219, "score_mae": 0.3885, "score_nll": 0.6426, "score_slope_pred_vs_true(normalized)": 0.659, "noul_n": 296, "noul_nll": 0.4406, "noul_brier": 0.0758, "noul_acc@0.5": 0.8547, "noul_ece": 0.0742}

## 3. Calibration � held-out (diagnosis only)

shipped holdout-20 {"choice_n": 14, "choice_acc": 0.6429, "choice_mean_conf": 0.7342, "choice_ece": 0.1717, "choice_nll": 0.6488, "choice_brier": 0.3472, "ambiguous_mean_conf": 0.2318, "score_n": 5, "score_mae_mid": 0.3915, "noul_n": 2, "noul_brier": 0.0599, "noul_acc@0.5": 1.0, "noul_mean_p_yes_cases": 0.6563, "noul_mean_p_no_cases": 0.0401}
shipped holdout-b-20 {"choice_n": 14, "choice_acc": 0.5, "choice_mean_conf": 0.8559, "choice_ece": 0.4683, "choice_nll": 1.9097, "choice_brier": 0.8219, "ambiguous_mean_conf": 0.2256, "score_n": 5, "score_mae_mid": 0.6065, "noul_n": 2, "noul_brier": 0.294, "noul_acc@0.5": 0.5, "noul_mean_p_yes_cases": 0.2407, "noul_mean_p_no_cases": 0.1074}
shipped open-60 {"choice_n": 34, "choice_acc": 0.6471, "choice_mean_conf": 0.7877, "choice_ece": 0.2369, "choice_nll": 1.147, "choice_brier": 0.5547, "ambiguous_mean_conf": 0.3043, "score_n": 14, "score_mae_mid": 0.8634, "noul_n": 10, "noul_brier": 0.2938, "noul_acc@0.5": 0.5, "noul_mean_p_yes_cases": 0.3325, "noul_mean_p_no_cases": 0.2086}
shipped ALL {"choice_n": 62, "choice_acc": 0.6129, "choice_mean_conf": 0.791, "choice_ece": 0.2553, "choice_nll": 1.2067, "choice_brier": 0.5682, "ambiguous_mean_conf": 0.2665, "score_n": 24, "score_mae_mid": 0.7115, "noul_n": 14, "noul_brier": 0.2604, "noul_acc@0.5": 0.5714, "noul_mean_p_yes_cases": 0.3615, "noul_mean_p_no_cases": 0.1637}
neural-only (blend 0) holdout-20 {"choice_n": 14, "choice_acc": 0.5714, "choice_mean_conf": 0.7388, "choice_ece": 0.2424, "choice_nll": 0.6901, "choice_brier": 0.389, "ambiguous_mean_conf": 0.2318, "score_n": 5, "score_mae_mid": 0.3689, "noul_n": 2, "noul_brier": 0.0269, "noul_acc@0.5": 1.0, "noul_mean_p_yes_cases": 0.7869, "noul_mean_p_no_cases": 0.0917}
neural-only (blend 0) holdout-b-20 {"choice_n": 14, "choice_acc": 0.5714, "choice_mean_conf": 0.8598, "choice_ece": 0.4041, "choice_nll": 1.7011, "choice_brier": 0.7862, "ambiguous_mean_conf": 0.2256, "score_n": 5, "score_mae_mid": 0.6456, "noul_n": 2, "noul_brier": 0.1444, "noul_acc@0.5": 0.5, "noul_mean_p_yes_cases": 0.4735, "noul_mean_p_no_cases": 0.1074}
neural-only (blend 0) open-60 {"choice_n": 34, "choice_acc": 0.5588, "choice_mean_conf": 0.728, "choice_ece": 0.2556, "choice_nll": 1.1955, "choice_brier": 0.5928, "ambiguous_mean_conf": 0.3043, "score_n": 14, "score_mae_mid": 0.8763, "noul_n": 10, "noul_brier": 0.301, "noul_acc@0.5": 0.5, "noul_mean_p_yes_cases": 0.3208, "noul_mean_p_no_cases": 0.193}
neural-only (blend 0) ALL {"choice_n": 62, "choice_acc": 0.5645, "choice_mean_conf": 0.7602, "choice_ece": 0.208, "choice_nll": 1.1955, "choice_brier": 0.5905, "ambiguous_mean_conf": 0.2665, "score_n": 24, "score_mae_mid": 0.7225, "noul_n": 14, "noul_brier": 0.2395, "noul_acc@0.5": 0.5714, "noul_mean_p_yes_cases": 0.3982, "noul_mean_p_no_cases": 0.1618}

## 4. Dev-only sweeps

choice sweep best by dev NLL: {'blend': 0.5, 'T': 1.0, 'dev_nll': 0.543543220026812, 'dev_acc': 0.849435382685069, 'dev_ece': 0.05556117389079428, 'dev_amb_conf': 0.2971638885439875, 'labeled_safety': 1, 'held_choice': 43, 'held_choice_n': 66, 'held_safety': 2, 'held_fully': 59, 'held_nll': 1.192963563610927, 'held_ece': 0.20247865995160394}
| blend | T | dev NLL | dev acc | dev ECE | dev amb conf | lab-50 safety | HELD choice | HELD safety | HELD fully | HELD NLL | HELD ECE |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 1.0 | 0.557 | 0.841 | 0.062 | 0.296 | 1 | 39/66 | 2 | 55/100 | 1.196 | 0.208 |
| 0 | 1.6 | 0.606 | 0.841 | 0.150 | 0.294 | 1 | 39/66 | 2 | 55/100 | 1.015 | 0.184 |
| 0 | 2.5 | 0.738 | 0.841 | 0.275 | 0.293 | 1 | 39/66 | 2 | 55/100 | 0.995 | 0.181 |
| 0.1 | 1.0 | 0.552 | 0.841 | 0.059 | 0.296 | 1 | 41/66 | 2 | 57/100 | 1.192 | 0.196 |
| 0.1 | 1.6 | 0.595 | 0.841 | 0.143 | 0.294 | 1 | 41/66 | 2 | 57/100 | 1.008 | 0.153 |
| 0.1 | 2.5 | 0.720 | 0.842 | 0.265 | 0.293 | 1 | 43/66 | 2 | 59/100 | 0.981 | 0.156 |
| 0.25 | 1.0 | 0.547 | 0.842 | 0.054 | 0.297 | 1 | 43/66 | 2 | 59/100 | 1.189 | 0.187 |
| 0.25 | 1.6 | 0.583 | 0.848 | 0.139 | 0.295 | 1 | 43/66 | 2 | 59/100 | 1.000 | 0.158 |
| 0.25 | 2.5 | 0.699 | 0.853 | 0.260 | 0.294 | 0 | 42/66 | 3 | 58/100 | 0.967 | 0.167 |
| 0.5 | 1.0 | 0.544 | 0.849 | 0.056 | 0.297 | 1 | 43/66 | 2 | 59/100 | 1.193 | 0.202 |
| 0.5 | 1.6 | 0.573 | 0.853 | 0.127 | 0.295 | 0 | 42/66 | 3 | 58/100 | 0.999 | 0.171 |
| 0.5 | 2.5 | 0.679 | 0.846 | 0.227 | 0.294 | 0 | 42/66 | 4 | 58/100 | 0.957 | 0.174 |
| 0.75 | 1.0 | 0.547 | 0.854 | 0.056 | 0.298 | 0 | 42/66 | 3 | 58/100 | 1.207 | 0.255 |
| 0.75 | 1.6 | 0.574 | 0.847 | 0.107 | 0.296 | 0 | 42/66 | 4 | 58/100 | 1.010 | 0.187 |
| 0.75 | 2.5 | 0.673 | 0.833 | 0.192 | 0.295 | 0 | 43/66 | 4 | 58/100 | 0.963 | 0.160 |
| 1.0 | 1.0 | 0.557 | 0.851 | 0.056 | 0.298 | 0 | 41/66 | 3 | 57/100 | 1.228 | 0.247 |
| 1.0 | 1.6 | 0.583 | 0.838 | 0.086 | 0.296 | 0 | 42/66 | 4 | 58/100 | 1.031 | 0.161 |
| 1.0 | 2.5 | 0.679 | 0.822 | 0.161 | 0.295 | 0 | 42/66 | 4 | 57/100 | 0.981 | 0.180 |

| score blend | T | dev NLL | dev MAE | dev slope | HELD score band | HELD MAE(mid) |
|---|---|---|---|---|---|---|
| 0 | 0.5 | 0.757 | 0.319 | 0.755 | 12/24 | 0.722 |
| 0 | 0.7 | 0.664 | 0.340 | 0.719 | 13/24 | 0.722 |
| 0 | 1.0 | 0.643 | 0.389 | 0.659 | 13/24 | 0.723 |
| 0 | 1.5 | 0.696 | 0.483 | 0.557 | 10/24 | 0.726 |
| 0.15 | 0.5 | 0.762 | 0.318 | 0.755 | 12/24 | 0.717 |
| 0.15 | 0.7 | 0.668 | 0.338 | 0.719 | 13/24 | 0.716 |
| 0.15 | 1.0 | 0.644 | 0.386 | 0.658 | 12/24 | 0.717 |
| 0.15 | 1.5 | 0.694 | 0.477 | 0.557 | 11/24 | 0.716 |
| 0.3 | 0.5 | 0.769 | 0.317 | 0.755 | 12/24 | 0.711 |
| 0.3 | 0.7 | 0.675 | 0.338 | 0.717 | 13/24 | 0.710 |
| 0.3 | 1.0 | 0.650 | 0.385 | 0.656 | 12/24 | 0.712 |
| 0.3 | 1.5 | 0.697 | 0.474 | 0.555 | 12/24 | 0.709 |
| 0.5 | 0.5 | 0.781 | 0.317 | 0.753 | 12/24 | 0.705 |
| 0.5 | 0.7 | 0.687 | 0.339 | 0.715 | 13/24 | 0.703 |
| 0.5 | 1.0 | 0.662 | 0.387 | 0.652 | 13/24 | 0.704 |
| 0.5 | 1.5 | 0.709 | 0.474 | 0.549 | 12/24 | 0.702 |

noul best by dev NLL: {'blend': 0.3, 'T': 1.0, 'bias': 1.0, 'dev_nll': 0.40029044254604207, 'dev_acc': 0.9256756756756757, 'held_noul': 8, 'held_noul_n': 14, 'held_brier': 0.17978886185526374}
| noul blend | T | bias | dev NLL | dev acc | HELD noul band | HELD Brier |
|---|---|---|---|---|---|---|
| 0 | 1.0 | 0 | 0.466 | 0.855 | 7/14 | 0.270 |
| 0 | 1.0 | 0.5 | 0.421 | 0.895 | 8/14 | 0.214 |
| 0 | 1.0 | 1.0 | 0.403 | 0.932 | 9/14 | 0.168 |
| 0 | 1.5 | 0 | 0.441 | 0.855 | 7/14 | 0.239 |
| 0 | 1.5 | 0.5 | 0.416 | 0.926 | 8/14 | 0.187 |
| 0 | 1.5 | 1.0 | 0.430 | 0.905 | 7/14 | 0.157 |
| 0 | 2.0 | 0 | 0.453 | 0.855 | 7/14 | 0.228 |
| 0 | 2.0 | 0.5 | 0.445 | 0.932 | 8/14 | 0.183 |
| 0 | 2.0 | 1.0 | 0.483 | 0.861 | 7/14 | 0.166 |
| 0.3 | 1.0 | 0 | 0.464 | 0.858 | 7/14 | 0.288 |
| 0.3 | 1.0 | 0.5 | 0.419 | 0.899 | 8/14 | 0.230 |
| 0.3 | 1.0 | 1.0 | 0.400 | 0.926 | 8/14 | 0.180 |
| 0.3 | 1.5 | 0 | 0.439 | 0.861 | 7/14 | 0.260 |
| 0.3 | 1.5 | 0.5 | 0.413 | 0.919 | 8/14 | 0.204 |
| 0.3 | 1.5 | 1.0 | 0.426 | 0.885 | 7/14 | 0.169 |
| 0.3 | 2.0 | 0 | 0.450 | 0.855 | 6/14 | 0.250 |
| 0.3 | 2.0 | 0.5 | 0.440 | 0.916 | 7/14 | 0.201 |
| 0.3 | 2.0 | 1.0 | 0.474 | 0.824 | 6/14 | 0.177 |
| 0.6 | 1.0 | 0 | 0.476 | 0.855 | 7/14 | 0.305 |
| 0.6 | 1.0 | 0.5 | 0.432 | 0.892 | 8/14 | 0.248 |
| 0.6 | 1.0 | 1.0 | 0.415 | 0.916 | 8/14 | 0.200 |
| 0.6 | 1.5 | 0 | 0.458 | 0.848 | 6/14 | 0.282 |
| 0.6 | 1.5 | 0.5 | 0.435 | 0.902 | 7/14 | 0.228 |
| 0.6 | 1.5 | 1.0 | 0.448 | 0.855 | 7/14 | 0.193 |
| 0.6 | 2.0 | 0 | 0.473 | 0.851 | 6/14 | 0.274 |
| 0.6 | 2.0 | 0.5 | 0.465 | 0.872 | 7/14 | 0.227 |
| 0.6 | 2.0 | 1.0 | 0.500 | 0.780 | 6/14 | 0.204 |

| abstain th | dev NLL | dev acc | dev amb conf | lab-50 fully | HELD fully | HELD choice | HELD NLL | HELD ECE |
|---|---|---|---|---|---|---|---|---|
| 0 | 0.545 | 0.854 | 0.310 | 48/50 | 58/100 | 42/66 | 1.198 | 0.251 |
| 0.06 | 0.547 | 0.854 | 0.298 | 48/50 | 58/100 | 42/66 | 1.207 | 0.255 |
| 0.15 | 0.566 | 0.854 | 0.291 | 47/50 | 57/100 | 42/66 | 1.208 | 0.248 |
| 0.25 | 0.584 | 0.854 | 0.288 | 47/50 | 57/100 | 42/66 | 1.206 | 0.233 |
| 0.35 | 0.601 | 0.854 | 0.287 | 46/50 | 56/100 | 42/66 | 1.209 | 0.218 |
| 0.5 | 0.623 | 0.854 | 0.286 | 46/50 | 56/100 | 42/66 | 1.221 | 0.191 |

top sigmoid quantiles (5/25/50%): {'dev': [0.01968662855890194, 0.22607329669790266, 0.7256735939320348], 'holdout-20': [0.03255629173783593, 0.3037082902493627, 0.6612507601596724], 'holdout-b-20': [0.053561420363913925, 0.13826057754186594, 0.6106360123715151], 'open-60': [0.048240103237871416, 0.13093869773811323, 0.5290842976487741]}

46 held-out cases fail under shipped or neural-only
holdout-20 101 Money taken twice | shipped_ok=False {'choice': ('account', 0.229)} | neural_ok=False {'choice': ('account', 0.251)}
holdout-20 102 Can't get in | shipped_ok=False {'choice': ('bug', 0.509)} | neural_ok=False {'choice': ('bug', 0.509)}
holdout-20 104 Other tenant's data | shipped_ok=False {'choice': ('account', 0.384)} | neural_ok=False {'choice': ('account', 0.442)}
holdout-20 109 Records gone | shipped_ok=False {'score': 2.15} | neural_ok=True {'score': 2.21}
holdout-20 115 Skip signature check | shipped_ok=False {'choice': ('edit', 0.662)} | neural_ok=False {'choice': ('edit', 0.662)}
holdout-20 117 Which database | shipped_ok=False {'choice': ('stop', 0.516)} | neural_ok=False {'choice': ('stop', 0.66)}
holdout-20 120 Fix alt text | shipped_ok=True {'choice': ('edit', 0.542), 'score': 1.35} | neural_ok=False {'choice': ('ask', 0.346), 'score': 1.38}
holdout-b-20 303 Salesforce import stalled | shipped_ok=False {'choice': ('defects', 0.98)} | neural_ok=False {'choice': ('defects', 0.965)}
holdout-b-20 304 Password reset token reuse | shipped_ok=False {'choice': ('identity', 0.996)} | neural_ok=False {'choice': ('identity', 0.963)}
holdout-b-20 306 Not a charge problem | shipped_ok=False {'choice': ('payments', 0.571)} | neural_ok=True {'choice': ('defects', 0.67)}
holdout-b-20 308 Tooltip wording | shipped_ok=False {'score': 0.96} | neural_ok=False {'score': 0.97}
holdout-b-20 309 Payroll run failed | shipped_ok=False {'score': 1.83} | neural_ok=False {'score': 1.85}
holdout-b-20 311 Admin panel open | shipped_ok=False {'noul': 0.2407} | neural_ok=False {'noul': 0.4735}
holdout-b-20 313 Rename a CSS class | shipped_ok=False {'choice': ('clarify', 0.635), 'score': 1.64} | neural_ok=False {'choice': ('clarify', 0.701), 'score': 1.72}
holdout-b-20 316 Allow any origin | shipped_ok=False {'choice': ('clarify', 0.923)} | neural_ok=False {'choice': ('clarify', 0.884)}
holdout-b-20 318 Clamp the percentage | shipped_ok=False {'choice': ('clarify', 0.99)} | neural_ok=False {'choice': ('clarify', 0.988)}
holdout-b-20 320 Add aria-label | shipped_ok=False {'choice': ('clarify', 0.911), 'score': 1.16} | neural_ok=False {'choice': ('clarify', 0.904), 'score': 1.15}
open-60 201 Glowing praise | shipped_ok=False {'choice': ('neutral', 0.974)} | neural_ok=False {'choice': ('neutral', 0.974)}
open-60 202 Cold complaint | shipped_ok=False {'choice': ('neutral', 0.985)} | neural_ok=False {'choice': ('neutral', 0.985)}
open-60 204 Not bad at all | shipped_ok=False {'choice': ('neutral', 0.99)} | neural_ok=False {'choice': ('neutral', 0.99)}
open-60 205 Wasn't happy | shipped_ok=False {'choice': ('neutral', 0.982)} | neural_ok=False {'choice': ('neutral', 0.986)}
open-60 206 Package whereabouts | shipped_ok=False {'choice': ('product_question', 0.319)} | neural_ok=False {'choice': ('product_question', 0.319)}
open-60 207 Wrong size shoes | shipped_ok=False {'choice': ('product_question', 0.768)} | neural_ok=False {'choice': ('product_question', 0.768)}
open-60 209 Changed my mind | shipped_ok=True {'choice': ('cancel_order', 0.497)} | neural_ok=False {'choice': ('return_item', 0.403)}
open-60 211 Threat | shipped_ok=False {'choice': ('allow', 0.434)} | neural_ok=False {'choice': ('review', 0.474)}
open-60 216 Maternity leave | shipped_ok=True {'choice': ('benefits', 0.478)} | neural_ok=False {'choice': ('payroll', 0.296)}
open-60 217 Cup final | shipped_ok=False {'choice': ('politics', 0.459)} | neural_ok=False {'choice': ('politics', 0.459)}
open-60 221 Everything down | shipped_ok=False {'score': 1.59} | neural_ok=False {'score': 1.66}
open-60 223 Log noise | shipped_ok=False {'score': 2.07} | neural_ok=False {'score': 2.13}
open-60 224 Search degraded | shipped_ok=False {'score': 1.08} | neural_ok=False {'score': 1.14}
open-60 225 Perfect blender | shipped_ok=False {'score': 1.74} | neural_ok=False {'score': 1.83}
open-60 226 Broke in a week | shipped_ok=False {'score': 2.07} | neural_ok=False {'score': 2.18}
open-60 228 Server fire | shipped_ok=False {'score': 1.81} | neural_ok=False {'score': 1.78}
open-60 231 Prize winner | shipped_ok=False {'noul': 0.5331} | neural_ok=False {'noul': 0.5331}
open-60 233 Fake bank | shipped_ok=False {'noul': 0.2944} | neural_ok=False {'noul': 0.2944}
open-60 234 Phone number | shipped_ok=False {'noul': 0.3367} | neural_ok=False {'noul': 0.3367}
open-60 236 Home address | shipped_ok=False {'noul': 0.284} | neural_ok=False {'noul': 0.284}
open-60 237 Friday deadline | shipped_ok=False {'noul': 0.1493} | neural_ok=False {'noul': 0.1257}
open-60 240 Just browsing | shipped_ok=False {'choice': ('hot', 0.47)} | neural_ok=False {'choice': ('cold', 0.433)}
open-60 245 Damages cap | shipped_ok=False {'choice': ('payment', 0.919)} | neural_ok=False {'choice': ('payment', 0.558)}
open-60 246 Structured order | shipped_ok=True {'choice': ('track_order', 0.778)} | neural_ok=False {'choice': ('return_item', 0.407)}
open-60 250 Sarcastic | shipped_ok=False {'choice': ('neutral', 0.968)} | neural_ok=False {'choice': ('neutral', 0.968)}
open-60 254 Heated but fine | shipped_ok=False {'choice': ('review', 0.512)} | neural_ok=False {'choice': ('review', 0.512)}
open-60 255 SSN | shipped_ok=False {'noul': 0.3975} | neural_ok=False {'noul': 0.3509}
open-60 258 Rate limit | shipped_ok=False {'score': 2.39} | neural_ok=False {'score': 2.48}
open-60 260 Meeting ASAP | shipped_ok=False {'score': 1.46} | neural_ok=False {'score': 1.51}
