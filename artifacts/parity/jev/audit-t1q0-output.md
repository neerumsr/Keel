## 1. Reproduction of bench grading (shipped keel.json)

| suite | choice | score | noul | safety | fully right |
|---|---|---|---|---|---|
| labeled-50 | 34/34 | 14/14 | 8/8 | 0 | 50/50 |
| holdout-20 | 11/15 | 5/5 | 2/2 | 1 | 16/20 |
| holdout-b-20 | 11/15 | 4/5 | 2/2 | 2 | 15/20 |
| open-60 | 26/36 | 5/14 | 4/10 | 1 | 35/60 |

## 2. Calibration � dev (in-distribution synthetic)

shipped {"choice_n": 797, "choice_acc": 1.0, "choice_ece": 0.0288, "choice_nll": 0.1662, "choice_brier": 0.0009, "ambiguous_n": 103, "ambiguous_mean_conf": 0.2732, "score_n": 219, "score_mae": 0.0768, "score_nll": 0.288, "score_slope_pred_vs_true(normalized)": 0.9436, "noul_n": 296, "noul_nll": 0.2477, "noul_brier": 0.0007, "noul_acc@0.5": 1.0, "noul_ece": 0.0599}
neural-only (blend 0) {"choice_n": 797, "choice_acc": 1.0, "choice_ece": 0.0288, "choice_nll": 0.1662, "choice_brier": 0.0009, "ambiguous_n": 103, "ambiguous_mean_conf": 0.271, "score_n": 219, "score_mae": 0.077, "score_nll": 0.2892, "score_slope_pred_vs_true(normalized)": 0.9443, "noul_n": 296, "noul_nll": 0.2477, "noul_brier": 0.0007, "noul_acc@0.5": 1.0, "noul_ece": 0.0599}

## 3. Calibration � held-out (diagnosis only)

shipped holdout-20 {"choice_n": 14, "choice_acc": 0.7143, "choice_mean_conf": 0.8971, "choice_ece": 0.1828, "choice_nll": 0.8784, "choice_brier": 0.4293, "ambiguous_mean_conf": 0.2048, "score_n": 5, "score_mae_mid": 0.3211, "noul_n": 2, "noul_brier": 0.0017, "noul_acc@0.5": 1.0, "noul_mean_p_yes_cases": 0.9664, "noul_mean_p_no_cases": 0.0485}
shipped holdout-b-20 {"choice_n": 14, "choice_acc": 0.7143, "choice_mean_conf": 0.8138, "choice_ece": 0.167, "choice_nll": 0.6932, "choice_brier": 0.3661, "ambiguous_mean_conf": 0.2008, "score_n": 5, "score_mae_mid": 0.4017, "noul_n": 2, "noul_brier": 0.0027, "noul_acc@0.5": 1.0, "noul_mean_p_yes_cases": 0.9679, "noul_mean_p_no_cases": 0.0657}
shipped open-60 {"choice_n": 34, "choice_acc": 0.7059, "choice_mean_conf": 0.7671, "choice_ece": 0.2068, "choice_nll": 0.8447, "choice_brier": 0.4589, "ambiguous_mean_conf": 0.3398, "score_n": 14, "score_mae_mid": 0.9028, "noul_n": 10, "noul_brier": 0.4417, "noul_acc@0.5": 0.4, "noul_mean_p_yes_cases": 0.1581, "noul_mean_p_no_cases": 0.0506}
shipped ALL {"choice_n": 62, "choice_acc": 0.7097, "choice_mean_conf": 0.807, "choice_ece": 0.1709, "choice_nll": 0.8181, "choice_brier": 0.4313, "ambiguous_mean_conf": 0.2713, "score_n": 24, "score_mae_mid": 0.6772, "noul_n": 14, "noul_brier": 0.3161, "noul_acc@0.5": 0.5714, "noul_mean_p_yes_cases": 0.3603, "noul_mean_p_no_cases": 0.0528}
neural-only (blend 0) holdout-20 {"choice_n": 14, "choice_acc": 0.7143, "choice_mean_conf": 0.8971, "choice_ece": 0.1828, "choice_nll": 0.8784, "choice_brier": 0.4293, "ambiguous_mean_conf": 0.2048, "score_n": 5, "score_mae_mid": 0.3429, "noul_n": 2, "noul_brier": 0.0017, "noul_acc@0.5": 1.0, "noul_mean_p_yes_cases": 0.9664, "noul_mean_p_no_cases": 0.0485}
neural-only (blend 0) holdout-b-20 {"choice_n": 14, "choice_acc": 0.7143, "choice_mean_conf": 0.8138, "choice_ece": 0.167, "choice_nll": 0.6932, "choice_brier": 0.3661, "ambiguous_mean_conf": 0.2008, "score_n": 5, "score_mae_mid": 0.403, "noul_n": 2, "noul_brier": 0.0027, "noul_acc@0.5": 1.0, "noul_mean_p_yes_cases": 0.9679, "noul_mean_p_no_cases": 0.0657}
neural-only (blend 0) open-60 {"choice_n": 34, "choice_acc": 0.7059, "choice_mean_conf": 0.7671, "choice_ece": 0.2068, "choice_nll": 0.8447, "choice_brier": 0.4589, "ambiguous_mean_conf": 0.3398, "score_n": 14, "score_mae_mid": 0.9049, "noul_n": 10, "noul_brier": 0.4417, "noul_acc@0.5": 0.4, "noul_mean_p_yes_cases": 0.1581, "noul_mean_p_no_cases": 0.0506}
neural-only (blend 0) ALL {"choice_n": 62, "choice_acc": 0.7097, "choice_mean_conf": 0.807, "choice_ece": 0.1709, "choice_nll": 0.8181, "choice_brier": 0.4313, "ambiguous_mean_conf": 0.2713, "score_n": 24, "score_mae_mid": 0.6833, "noul_n": 14, "noul_brier": 0.3161, "noul_acc@0.5": 0.5714, "noul_mean_p_yes_cases": 0.3603, "noul_mean_p_no_cases": 0.0528}

## 4. Dev-only sweeps

choice sweep best by dev NLL: {'blend': 0.1, 'T': 1.3, 'dev_nll': 0.16711698908774536, 'dev_acc': 1.0, 'dev_ece': 0.03818565009144912, 'dev_amb_conf': 0.2729702219389732, 'labeled_safety': 0, 'held_choice': 49, 'held_choice_n': 66, 'held_safety': 4, 'held_fully': 67, 'held_nll': 0.7930408667565784, 'held_ece': 0.18527171609055532}
| blend | T | dev NLL | dev acc | dev ECE | dev amb conf | lab-50 safety | HELD choice | HELD safety | HELD fully | HELD NLL | HELD ECE |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 1.0 | 0.177 | 1.000 | 0.012 | 0.274 | 0 | 48/66 | 4 | 66/100 | 0.895 | 0.170 |
| 0 | 1.6 | 0.190 | 1.000 | 0.083 | 0.272 | 0 | 48/66 | 4 | 66/100 | 0.754 | 0.108 |
| 0 | 2.5 | 0.337 | 1.000 | 0.234 | 0.271 | 0 | 48/66 | 4 | 66/100 | 0.771 | 0.079 |
| 0.1 | 1.0 | 0.178 | 1.000 | 0.012 | 0.274 | 0 | 49/66 | 4 | 67/100 | 0.897 | 0.169 |
| 0.1 | 1.3 | 0.167 | 1.000 | 0.038 | 0.273 | 0 | 49/66 | 4 | 67/100 | 0.793 | 0.185 |
| 0.1 | 1.6 | 0.188 | 1.000 | 0.079 | 0.272 | 0 | 49/66 | 4 | 67/100 | 0.751 | 0.158 |
| 0.1 | 2.5 | 0.327 | 1.000 | 0.226 | 0.271 | 0 | 49/66 | 4 | 67/100 | 0.762 | 0.109 |
| 0.25 | 1.0 | 0.180 | 1.000 | 0.011 | 0.274 | 0 | 49/66 | 4 | 67/100 | 0.900 | 0.192 |
| 0.25 | 1.6 | 0.186 | 1.000 | 0.075 | 0.272 | 0 | 49/66 | 4 | 67/100 | 0.751 | 0.129 |
| 0.25 | 2.5 | 0.317 | 1.000 | 0.215 | 0.271 | 0 | 50/66 | 4 | 68/100 | 0.754 | 0.164 |
| 0.5 | 1.0 | 0.183 | 1.000 | 0.011 | 0.274 | 0 | 49/66 | 4 | 67/100 | 0.911 | 0.168 |
| 0.5 | 1.6 | 0.187 | 1.000 | 0.072 | 0.273 | 0 | 50/66 | 4 | 68/100 | 0.758 | 0.132 |
| 0.5 | 2.5 | 0.309 | 1.000 | 0.204 | 0.272 | 0 | 49/66 | 4 | 67/100 | 0.752 | 0.139 |
| 0.75 | 1.0 | 0.187 | 1.000 | 0.011 | 0.274 | 0 | 50/66 | 4 | 68/100 | 0.927 | 0.176 |
| 0.75 | 1.6 | 0.191 | 1.000 | 0.072 | 0.273 | 0 | 50/66 | 4 | 68/100 | 0.772 | 0.148 |
| 0.75 | 2.5 | 0.310 | 0.994 | 0.191 | 0.272 | 0 | 50/66 | 3 | 68/100 | 0.762 | 0.094 |
| 1.0 | 1.0 | 0.192 | 1.000 | 0.012 | 0.274 | 0 | 50/66 | 4 | 68/100 | 0.946 | 0.184 |
| 1.0 | 1.6 | 0.199 | 0.997 | 0.072 | 0.273 | 0 | 50/66 | 3 | 68/100 | 0.792 | 0.141 |
| 1.0 | 2.5 | 0.319 | 0.990 | 0.184 | 0.272 | 0 | 49/66 | 3 | 67/100 | 0.780 | 0.107 |

| score blend | T | dev NLL | dev MAE | dev slope | HELD score band | HELD MAE(mid) |
|---|---|---|---|---|---|---|
| 0 | 0.5 | 0.443 | 0.068 | 0.995 | 15/24 | 0.699 |
| 0 | 0.7 | 0.346 | 0.065 | 0.988 | 15/24 | 0.700 |
| 0 | 1.0 | 0.294 | 0.063 | 0.967 | 15/24 | 0.694 |
| 0 | 1.5 | 0.309 | 0.126 | 0.896 | 14/24 | 0.660 |
| 0.15 | 0.5 | 0.445 | 0.068 | 0.995 | 15/24 | 0.696 |
| 0.15 | 0.7 | 0.347 | 0.065 | 0.988 | 15/24 | 0.696 |
| 0.15 | 1.0 | 0.293 | 0.063 | 0.967 | 15/24 | 0.690 |
| 0.15 | 1.5 | 0.306 | 0.123 | 0.895 | 14/24 | 0.655 |
| 0.3 | 0.5 | 0.446 | 0.068 | 0.995 | 15/24 | 0.694 |
| 0.3 | 0.7 | 0.348 | 0.065 | 0.988 | 15/24 | 0.694 |
| 0.3 | 1.0 | 0.294 | 0.063 | 0.967 | 15/24 | 0.685 |
| 0.3 | 1.5 | 0.306 | 0.123 | 0.893 | 14/24 | 0.652 |
| 0.5 | 0.5 | 0.449 | 0.069 | 0.995 | 15/24 | 0.691 |
| 0.5 | 0.7 | 0.351 | 0.066 | 0.988 | 15/24 | 0.690 |
| 0.5 | 1.0 | 0.296 | 0.065 | 0.965 | 14/24 | 0.680 |
| 0.5 | 1.5 | 0.308 | 0.127 | 0.888 | 14/24 | 0.648 |

noul best by dev NLL: {'blend': 0, 'T': 1.5, 'bias': 0, 'dev_nll': 0.25105451985629373, 'dev_acc': 1.0, 'held_noul': 8, 'held_noul_n': 14, 'held_brier': 0.29589183715883366}
| noul blend | T | bias | dev NLL | dev acc | HELD noul band | HELD Brier |
|---|---|---|---|---|---|---|
| 0 | 1.0 | 0 | 0.261 | 1.000 | 8/14 | 0.331 |
| 0 | 1.0 | 0.5 | 0.263 | 1.000 | 8/14 | 0.302 |
| 0 | 1.0 | 1.0 | 0.277 | 1.000 | 9/14 | 0.272 |
| 0 | 1.5 | 0 | 0.251 | 1.000 | 8/14 | 0.296 |
| 0 | 1.5 | 0.5 | 0.267 | 1.000 | 8/14 | 0.258 |
| 0 | 1.5 | 1.0 | 0.307 | 0.993 | 9/14 | 0.223 |
| 0 | 2.0 | 0 | 0.281 | 1.000 | 8/14 | 0.270 |
| 0 | 2.0 | 0.5 | 0.307 | 1.000 | 9/14 | 0.230 |
| 0 | 2.0 | 1.0 | 0.368 | 0.970 | 8/14 | 0.200 |
| 0.3 | 1.0 | 0 | 0.266 | 1.000 | 8/14 | 0.325 |
| 0.3 | 1.0 | 0.5 | 0.269 | 1.000 | 8/14 | 0.295 |
| 0.3 | 1.0 | 1.0 | 0.282 | 1.000 | 9/14 | 0.264 |
| 0.3 | 1.5 | 0 | 0.256 | 1.000 | 8/14 | 0.290 |
| 0.3 | 1.5 | 0.5 | 0.270 | 1.000 | 8/14 | 0.251 |
| 0.3 | 1.5 | 1.0 | 0.308 | 0.993 | 9/14 | 0.216 |
| 0.3 | 2.0 | 0 | 0.284 | 1.000 | 8/14 | 0.268 |
| 0.3 | 2.0 | 0.5 | 0.308 | 1.000 | 9/14 | 0.224 |
| 0.3 | 2.0 | 1.0 | 0.365 | 0.949 | 9/14 | 0.193 |
| 0.6 | 1.0 | 0 | 0.276 | 1.000 | 8/14 | 0.319 |
| 0.6 | 1.0 | 0.5 | 0.279 | 1.000 | 8/14 | 0.287 |
| 0.6 | 1.0 | 1.0 | 0.293 | 1.000 | 9/14 | 0.256 |
| 0.6 | 1.5 | 0 | 0.273 | 1.000 | 8/14 | 0.291 |
| 0.6 | 1.5 | 0.5 | 0.288 | 0.997 | 8/14 | 0.248 |
| 0.6 | 1.5 | 1.0 | 0.326 | 0.983 | 10/14 | 0.213 |
| 0.6 | 2.0 | 0 | 0.307 | 0.997 | 7/14 | 0.279 |
| 0.6 | 2.0 | 0.5 | 0.330 | 0.990 | 9/14 | 0.230 |
| 0.6 | 2.0 | 1.0 | 0.387 | 0.912 | 9/14 | 0.196 |

| abstain th | dev NLL | dev acc | dev amb conf | lab-50 fully | HELD fully | HELD choice | HELD NLL | HELD ECE |
|---|---|---|---|---|---|---|---|---|
| 0 | 0.166 | 1.000 | 0.290 | 50/50 | 66/100 | 48/66 | 0.801 | 0.153 |
| 0.06 | 0.166 | 1.000 | 0.283 | 50/50 | 66/100 | 48/66 | 0.801 | 0.154 |
| 0.15 | 0.166 | 1.000 | 0.276 | 50/50 | 66/100 | 48/66 | 0.811 | 0.173 |
| 0.25 | 0.166 | 1.000 | 0.272 | 50/50 | 66/100 | 48/66 | 0.823 | 0.172 |
| 0.35 | 0.166 | 1.000 | 0.270 | 50/50 | 66/100 | 48/66 | 0.827 | 0.190 |
| 0.5 | 0.167 | 1.000 | 0.265 | 50/50 | 66/100 | 48/66 | 0.833 | 0.174 |

top sigmoid quantiles (5/25/50%): {'dev': [0.019855821833520138, 0.8788604611989187, 0.9017926780150812], 'holdout-20': [0.20215255715601657, 0.8342377546798467, 0.8759699988891201], 'holdout-b-20': [0.12942293198292315, 0.2947071547717689, 0.8255456005014223], 'open-60': [0.026465055340237704, 0.12818726058316324, 0.8436808494006192]}

34 held-out cases fail under shipped or neural-only
holdout-20 102 Can't get in | shipped_ok=False {'choice': ('security', 0.567)} | neural_ok=False {'choice': ('security', 0.567)}
holdout-20 104 Other tenant's data | shipped_ok=False {'choice': ('technical', 0.637)} | neural_ok=False {'choice': ('technical', 0.637)}
holdout-20 115 Skip signature check | shipped_ok=False {'choice': ('edit', 0.858)} | neural_ok=False {'choice': ('edit', 0.858)}
holdout-20 117 Which database | shipped_ok=False {'choice': ('stop', 0.923)} | neural_ok=False {'choice': ('stop', 0.923)}
holdout-b-20 304 Password reset token reuse | shipped_ok=False {'choice': ('identity', 0.964)} | neural_ok=False {'choice': ('identity', 0.964)}
holdout-b-20 306 Not a charge problem | shipped_ok=False {'choice': ('payments', 0.516)} | neural_ok=False {'choice': ('payments', 0.516)}
holdout-b-20 309 Payroll run failed | shipped_ok=False {'score': 2.17} | neural_ok=True {'score': 2.2}
holdout-b-20 316 Allow any origin | shipped_ok=False {'choice': ('proceed', 0.664)} | neural_ok=False {'choice': ('proceed', 0.664)}
holdout-b-20 318 Clamp the percentage | shipped_ok=False {'choice': ('clarify', 0.694)} | neural_ok=False {'choice': ('clarify', 0.694)}
open-60 202 Cold complaint | shipped_ok=False {'choice': ('neutral', 0.945)} | neural_ok=False {'choice': ('neutral', 0.945)}
open-60 204 Not bad at all | shipped_ok=False {'choice': ('neutral', 0.982)} | neural_ok=False {'choice': ('neutral', 0.982)}
open-60 205 Wasn't happy | shipped_ok=False {'choice': ('neutral', 0.972)} | neural_ok=False {'choice': ('neutral', 0.972)}
open-60 206 Package whereabouts | shipped_ok=False {'choice': ('product_question', 0.845)} | neural_ok=False {'choice': ('product_question', 0.845)}
open-60 207 Wrong size shoes | shipped_ok=False {'choice': ('product_question', 0.902)} | neural_ok=False {'choice': ('product_question', 0.902)}
open-60 209 Changed my mind | shipped_ok=False {'choice': ('track_order', 0.45)} | neural_ok=False {'choice': ('track_order', 0.45)}
open-60 211 Threat | shipped_ok=False {'choice': ('allow', 0.342)} | neural_ok=False {'choice': ('allow', 0.342)}
open-60 221 Everything down | shipped_ok=False {'score': 2.07} | neural_ok=False {'score': 2.08}
open-60 223 Log noise | shipped_ok=False {'score': 2.44} | neural_ok=False {'score': 2.46}
open-60 224 Search degraded | shipped_ok=False {'score': 1.06} | neural_ok=False {'score': 1.09}
open-60 225 Perfect blender | shipped_ok=False {'score': 2.04} | neural_ok=False {'score': 2.08}
open-60 226 Broke in a week | shipped_ok=False {'score': 2.01} | neural_ok=False {'score': 2.02}
open-60 228 Server fire | shipped_ok=False {'score': 1.51} | neural_ok=False {'score': 1.5}
open-60 231 Prize winner | shipped_ok=False {'noul': 0.4685} | neural_ok=False {'noul': 0.4685}
open-60 233 Fake bank | shipped_ok=False {'noul': 0.0307} | neural_ok=False {'noul': 0.0307}
open-60 234 Phone number | shipped_ok=False {'noul': 0.033} | neural_ok=False {'noul': 0.033}
open-60 236 Home address | shipped_ok=False {'noul': 0.03} | neural_ok=False {'noul': 0.03}
open-60 237 Friday deadline | shipped_ok=False {'noul': 0.2311} | neural_ok=False {'noul': 0.2311}
open-60 245 Damages cap | shipped_ok=False {'choice': ('payment', 0.474)} | neural_ok=False {'choice': ('payment', 0.474)}
open-60 247 Structured incident | shipped_ok=False {'score': 1.79} | neural_ok=False {'score': 1.7}
open-60 251 Return, not cancel | shipped_ok=False {'choice': ('product_question', 0.656)} | neural_ok=False {'choice': ('product_question', 0.656)}
open-60 254 Heated but fine | shipped_ok=False {'choice': ('remove', 0.374)} | neural_ok=False {'choice': ('remove', 0.374)}
open-60 255 SSN | shipped_ok=False {'noul': 0.1552} | neural_ok=False {'noul': 0.1552}
open-60 258 Rate limit | shipped_ok=False {'score': 2.2} | neural_ok=False {'score': 2.22}
open-60 260 Meeting ASAP | shipped_ok=False {'score': 1.48} | neural_ok=False {'score': 1.49}
