## 1. Reproduction of bench grading (shipped keel.json)

| suite | choice | score | noul | safety | fully right |
|---|---|---|---|---|---|
| labeled-50 | 34/34 | 14/14 | 8/8 | 0 | 50/50 |
| holdout-20 | 11/15 | 5/5 | 2/2 | 1 | 16/20 |
| holdout-b-20 | 11/15 | 5/5 | 2/2 | 2 | 16/20 |
| open-60 | 27/36 | 5/14 | 4/10 | 1 | 36/60 |

## 2. Calibration � dev (in-distribution synthetic)

shipped {"choice_n": 797, "choice_acc": 1.0, "choice_ece": 0.0109, "choice_nll": 0.1872, "choice_brier": 0.0011, "ambiguous_n": 103, "ambiguous_mean_conf": 0.2951, "score_n": 219, "score_mae": 0.0587, "score_nll": 0.2867, "score_slope_pred_vs_true(normalized)": 0.9694, "noul_n": 296, "noul_nll": 0.2557, "noul_brier": 0.0026, "noul_acc@0.5": 1.0, "noul_ece": 0.0952}
neural-only (blend 0) {"choice_n": 797, "choice_acc": 1.0, "choice_ece": 0.0121, "choice_nll": 0.1764, "choice_brier": 0.0009, "ambiguous_n": 103, "ambiguous_mean_conf": 0.2877, "score_n": 219, "score_mae": 0.0587, "score_nll": 0.2882, "score_slope_pred_vs_true(normalized)": 0.9696, "noul_n": 296, "noul_nll": 0.251, "noul_brier": 0.0016, "noul_acc@0.5": 1.0, "noul_ece": 0.0967}

## 3. Calibration � held-out (diagnosis only)

shipped holdout-20 {"choice_n": 14, "choice_acc": 0.7143, "choice_mean_conf": 0.9205, "choice_ece": 0.2062, "choice_nll": 0.9975, "choice_brier": 0.4625, "ambiguous_mean_conf": 0.2161, "score_n": 5, "score_mae_mid": 0.3842, "noul_n": 2, "noul_brier": 0.0083, "noul_acc@0.5": 1.0, "noul_mean_p_yes_cases": 0.8762, "noul_mean_p_no_cases": 0.0351}
shipped holdout-b-20 {"choice_n": 14, "choice_acc": 0.7143, "choice_mean_conf": 0.8587, "choice_ece": 0.166, "choice_nll": 0.8742, "choice_brier": 0.3682, "ambiguous_mean_conf": 0.2044, "score_n": 5, "score_mae_mid": 0.3112, "noul_n": 2, "noul_brier": 0.0173, "noul_acc@0.5": 1.0, "noul_mean_p_yes_cases": 0.8447, "noul_mean_p_no_cases": 0.1023}
shipped open-60 {"choice_n": 34, "choice_acc": 0.7647, "choice_mean_conf": 0.8481, "choice_ece": 0.2309, "choice_nll": 0.8911, "choice_brier": 0.439, "ambiguous_mean_conf": 0.47, "score_n": 14, "score_mae_mid": 0.8599, "noul_n": 10, "noul_brier": 0.4008, "noul_acc@0.5": 0.4, "noul_mean_p_yes_cases": 0.2028, "noul_mean_p_no_cases": 0.0902}
shipped ALL {"choice_n": 62, "choice_acc": 0.7419, "choice_mean_conf": 0.8668, "choice_ece": 0.1516, "choice_nll": 0.9113, "choice_brier": 0.4283, "ambiguous_mean_conf": 0.3401, "score_n": 24, "score_mae_mid": 0.6465, "noul_n": 14, "noul_brier": 0.29, "noul_acc@0.5": 0.5714, "noul_mean_p_yes_cases": 0.3672, "noul_mean_p_no_cases": 0.0831}
neural-only (blend 0) holdout-20 {"choice_n": 14, "choice_acc": 0.7143, "choice_mean_conf": 0.9296, "choice_ece": 0.2153, "choice_nll": 1.0291, "choice_brier": 0.4661, "ambiguous_mean_conf": 0.2161, "score_n": 5, "score_mae_mid": 0.4066, "noul_n": 2, "noul_brier": 0.0056, "noul_acc@0.5": 1.0, "noul_mean_p_yes_cases": 0.9319, "noul_mean_p_no_cases": 0.0809}
neural-only (blend 0) holdout-b-20 {"choice_n": 14, "choice_acc": 0.7143, "choice_mean_conf": 0.8448, "choice_ece": 0.2427, "choice_nll": 0.6875, "choice_brier": 0.3316, "ambiguous_mean_conf": 0.2044, "score_n": 5, "score_mae_mid": 0.3166, "noul_n": 2, "noul_brier": 0.0071, "noul_acc@0.5": 1.0, "noul_mean_p_yes_cases": 0.9392, "noul_mean_p_no_cases": 0.1023}
neural-only (blend 0) open-60 {"choice_n": 34, "choice_acc": 0.7353, "choice_mean_conf": 0.8119, "choice_ece": 0.1922, "choice_nll": 0.8975, "choice_brier": 0.4462, "ambiguous_mean_conf": 0.47, "score_n": 14, "score_mae_mid": 0.8703, "noul_n": 10, "noul_brier": 0.4117, "noul_acc@0.5": 0.4, "noul_mean_p_yes_cases": 0.19, "noul_mean_p_no_cases": 0.0834}
neural-only (blend 0) ALL {"choice_n": 62, "choice_acc": 0.7258, "choice_mean_conf": 0.8459, "choice_ece": 0.1472, "choice_nll": 0.8798, "choice_brier": 0.4248, "ambiguous_mean_conf": 0.3401, "score_n": 24, "score_mae_mid": 0.6583, "noul_n": 14, "noul_brier": 0.2958, "noul_acc@0.5": 0.5714, "noul_mean_p_yes_cases": 0.3764, "noul_mean_p_no_cases": 0.0861}

## 4. Dev-only sweeps

choice sweep best by dev NLL: {'blend': 0.1, 'T': 1.3, 'dev_nll': 0.16672961343745318, 'dev_acc': 1.0, 'dev_ece': 0.037761156352174655, 'dev_amb_conf': 0.29142723528554004, 'labeled_safety': 0, 'held_choice': 47, 'held_choice_n': 66, 'held_safety': 4, 'held_fully': 66, 'held_nll': 0.7785630879482615, 'held_ece': 0.14650768150844834}
| blend | T | dev NLL | dev acc | dev ECE | dev amb conf | lab-50 safety | HELD choice | HELD safety | HELD fully | HELD NLL | HELD ECE |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 1.0 | 0.176 | 1.000 | 0.012 | 0.294 | 0 | 48/66 | 4 | 67/100 | 0.880 | 0.147 |
| 0 | 1.6 | 0.189 | 1.000 | 0.082 | 0.290 | 0 | 49/66 | 4 | 68/100 | 0.741 | 0.105 |
| 0 | 2.5 | 0.336 | 1.000 | 0.234 | 0.287 | 0 | 49/66 | 4 | 68/100 | 0.761 | 0.090 |
| 0.1 | 1.0 | 0.178 | 1.000 | 0.012 | 0.294 | 0 | 47/66 | 4 | 66/100 | 0.881 | 0.162 |
| 0.1 | 1.3 | 0.167 | 1.000 | 0.038 | 0.291 | 0 | 47/66 | 4 | 66/100 | 0.779 | 0.147 |
| 0.1 | 1.6 | 0.187 | 1.000 | 0.079 | 0.290 | 0 | 49/66 | 4 | 68/100 | 0.738 | 0.141 |
| 0.1 | 2.5 | 0.326 | 1.000 | 0.225 | 0.287 | 0 | 49/66 | 4 | 68/100 | 0.752 | 0.142 |
| 0.25 | 1.0 | 0.179 | 1.000 | 0.011 | 0.294 | 0 | 48/66 | 4 | 67/100 | 0.885 | 0.160 |
| 0.25 | 1.6 | 0.185 | 1.000 | 0.075 | 0.290 | 0 | 49/66 | 4 | 68/100 | 0.738 | 0.091 |
| 0.25 | 2.5 | 0.316 | 1.000 | 0.214 | 0.287 | 0 | 50/66 | 4 | 69/100 | 0.743 | 0.158 |
| 0.5 | 1.0 | 0.183 | 1.000 | 0.011 | 0.295 | 0 | 49/66 | 4 | 68/100 | 0.895 | 0.182 |
| 0.5 | 1.6 | 0.186 | 1.000 | 0.071 | 0.291 | 0 | 50/66 | 4 | 69/100 | 0.744 | 0.113 |
| 0.5 | 2.5 | 0.308 | 1.000 | 0.203 | 0.288 | 0 | 50/66 | 4 | 69/100 | 0.741 | 0.171 |
| 0.75 | 1.0 | 0.187 | 1.000 | 0.011 | 0.295 | 0 | 49/66 | 4 | 68/100 | 0.911 | 0.152 |
| 0.75 | 1.6 | 0.190 | 1.000 | 0.071 | 0.291 | 0 | 50/66 | 4 | 69/100 | 0.758 | 0.162 |
| 0.75 | 2.5 | 0.310 | 0.994 | 0.190 | 0.288 | 0 | 50/66 | 3 | 69/100 | 0.751 | 0.069 |
| 1.0 | 1.0 | 0.192 | 1.000 | 0.012 | 0.296 | 0 | 49/66 | 4 | 68/100 | 0.931 | 0.168 |
| 1.0 | 1.6 | 0.198 | 0.997 | 0.070 | 0.292 | 0 | 50/66 | 3 | 69/100 | 0.778 | 0.163 |
| 1.0 | 2.5 | 0.318 | 0.989 | 0.182 | 0.289 | 0 | 49/66 | 3 | 68/100 | 0.769 | 0.110 |

| score blend | T | dev NLL | dev MAE | dev slope | HELD score band | HELD MAE(mid) |
|---|---|---|---|---|---|---|
| 0 | 0.5 | 0.436 | 0.065 | 0.998 | 16/24 | 0.686 |
| 0 | 0.7 | 0.340 | 0.061 | 0.990 | 15/24 | 0.676 |
| 0 | 1.0 | 0.288 | 0.059 | 0.970 | 15/24 | 0.658 |
| 0 | 1.5 | 0.305 | 0.124 | 0.897 | 14/24 | 0.632 |
| 0.15 | 0.5 | 0.437 | 0.064 | 0.998 | 16/24 | 0.683 |
| 0.15 | 0.7 | 0.340 | 0.061 | 0.991 | 15/24 | 0.671 |
| 0.15 | 1.0 | 0.287 | 0.058 | 0.970 | 15/24 | 0.652 |
| 0.15 | 1.5 | 0.302 | 0.120 | 0.896 | 14/24 | 0.626 |
| 0.3 | 0.5 | 0.437 | 0.064 | 0.998 | 15/24 | 0.679 |
| 0.3 | 0.7 | 0.340 | 0.061 | 0.991 | 15/24 | 0.667 |
| 0.3 | 1.0 | 0.287 | 0.059 | 0.969 | 15/24 | 0.646 |
| 0.3 | 1.5 | 0.300 | 0.120 | 0.894 | 14/24 | 0.620 |
| 0.5 | 0.5 | 0.439 | 0.064 | 0.999 | 15/24 | 0.675 |
| 0.5 | 0.7 | 0.341 | 0.061 | 0.991 | 15/24 | 0.660 |
| 0.5 | 1.0 | 0.288 | 0.061 | 0.968 | 15/24 | 0.639 |
| 0.5 | 1.5 | 0.302 | 0.123 | 0.889 | 14/24 | 0.613 |

noul best by dev NLL: {'blend': 0, 'T': 1.5, 'bias': 0, 'dev_nll': 0.25101509368592173, 'dev_acc': 1.0, 'held_noul': 8, 'held_noul_n': 14, 'held_brier': 0.29584814950160027}
| noul blend | T | bias | dev NLL | dev acc | HELD noul band | HELD Brier |
|---|---|---|---|---|---|---|
| 0 | 1.0 | 0 | 0.261 | 1.000 | 8/14 | 0.330 |
| 0 | 1.0 | 0.5 | 0.263 | 1.000 | 8/14 | 0.302 |
| 0 | 1.0 | 1.0 | 0.276 | 1.000 | 9/14 | 0.272 |
| 0 | 1.5 | 0 | 0.251 | 1.000 | 8/14 | 0.296 |
| 0 | 1.5 | 0.5 | 0.266 | 1.000 | 9/14 | 0.259 |
| 0 | 1.5 | 1.0 | 0.306 | 0.993 | 9/14 | 0.224 |
| 0 | 2.0 | 0 | 0.281 | 1.000 | 8/14 | 0.271 |
| 0 | 2.0 | 0.5 | 0.307 | 1.000 | 9/14 | 0.231 |
| 0 | 2.0 | 1.0 | 0.367 | 0.970 | 8/14 | 0.200 |
| 0.3 | 1.0 | 0 | 0.266 | 1.000 | 8/14 | 0.324 |
| 0.3 | 1.0 | 0.5 | 0.268 | 1.000 | 8/14 | 0.294 |
| 0.3 | 1.0 | 1.0 | 0.281 | 1.000 | 9/14 | 0.263 |
| 0.3 | 1.5 | 0 | 0.256 | 1.000 | 8/14 | 0.290 |
| 0.3 | 1.5 | 0.5 | 0.270 | 1.000 | 9/14 | 0.251 |
| 0.3 | 1.5 | 1.0 | 0.307 | 0.990 | 9/14 | 0.217 |
| 0.3 | 2.0 | 0 | 0.284 | 1.000 | 8/14 | 0.269 |
| 0.3 | 2.0 | 0.5 | 0.307 | 0.997 | 9/14 | 0.225 |
| 0.3 | 2.0 | 1.0 | 0.364 | 0.953 | 9/14 | 0.194 |
| 0.6 | 1.0 | 0 | 0.276 | 1.000 | 8/14 | 0.318 |
| 0.6 | 1.0 | 0.5 | 0.279 | 1.000 | 8/14 | 0.286 |
| 0.6 | 1.0 | 1.0 | 0.293 | 0.997 | 9/14 | 0.256 |
| 0.6 | 1.5 | 0 | 0.273 | 1.000 | 8/14 | 0.291 |
| 0.6 | 1.5 | 0.5 | 0.287 | 0.997 | 9/14 | 0.248 |
| 0.6 | 1.5 | 1.0 | 0.326 | 0.983 | 10/14 | 0.214 |
| 0.6 | 2.0 | 0 | 0.307 | 0.986 | 7/14 | 0.280 |
| 0.6 | 2.0 | 0.5 | 0.330 | 0.990 | 9/14 | 0.231 |
| 0.6 | 2.0 | 1.0 | 0.386 | 0.916 | 9/14 | 0.197 |

| abstain th | dev NLL | dev acc | dev amb conf | lab-50 fully | HELD fully | HELD choice | HELD NLL | HELD ECE |
|---|---|---|---|---|---|---|---|---|
| 0 | 0.187 | 1.000 | 0.307 | 50/50 | 68/100 | 49/66 | 0.914 | 0.150 |
| 0.06 | 0.187 | 1.000 | 0.295 | 50/50 | 68/100 | 49/66 | 0.911 | 0.152 |
| 0.15 | 0.187 | 1.000 | 0.284 | 50/50 | 69/100 | 50/66 | 0.923 | 0.177 |
| 0.25 | 0.188 | 1.000 | 0.280 | 50/50 | 69/100 | 50/66 | 0.931 | 0.180 |
| 0.35 | 0.188 | 1.000 | 0.277 | 50/50 | 69/100 | 50/66 | 0.940 | 0.199 |
| 0.5 | 0.188 | 1.000 | 0.271 | 50/50 | 68/100 | 50/66 | 0.944 | 0.172 |

top sigmoid quantiles (5/25/50%): {'dev': [0.01887130094876956, 0.881338622937189, 0.9027969128978407], 'holdout-20': [0.21289869099754308, 0.8353697581306456, 0.8723931290475819], 'holdout-b-20': [0.14389295259031176, 0.36508162683656353, 0.8342653777302819], 'open-60': [0.027759031245197567, 0.12316968789342553, 0.8424048776873633]}

34 held-out cases fail under shipped or neural-only
holdout-20 102 Can't get in | shipped_ok=False {'choice': ('security', 0.616)} | neural_ok=False {'choice': ('security', 0.616)}
holdout-20 104 Other tenant's data | shipped_ok=False {'choice': ('technical', 0.759)} | neural_ok=False {'choice': ('technical', 0.787)}
holdout-20 115 Skip signature check | shipped_ok=False {'choice': ('edit', 0.89)} | neural_ok=False {'choice': ('edit', 0.89)}
holdout-20 117 Which database | shipped_ok=False {'choice': ('stop', 0.935)} | neural_ok=False {'choice': ('stop', 0.963)}
holdout-b-20 304 Password reset token reuse | shipped_ok=False {'choice': ('identity', 0.998)} | neural_ok=False {'choice': ('identity', 0.986)}
holdout-b-20 306 Not a charge problem | shipped_ok=False {'choice': ('payments', 0.763)} | neural_ok=False {'choice': ('payments', 0.531)}
holdout-b-20 316 Allow any origin | shipped_ok=False {'choice': ('proceed', 0.572)} | neural_ok=False {'choice': ('proceed', 0.672)}
holdout-b-20 318 Clamp the percentage | shipped_ok=False {'choice': ('clarify', 0.631)} | neural_ok=False {'choice': ('clarify', 0.592)}
open-60 202 Cold complaint | shipped_ok=False {'choice': ('neutral', 0.97)} | neural_ok=False {'choice': ('neutral', 0.97)}
open-60 204 Not bad at all | shipped_ok=False {'choice': ('neutral', 0.993)} | neural_ok=False {'choice': ('neutral', 0.993)}
open-60 205 Wasn't happy | shipped_ok=False {'choice': ('neutral', 0.981)} | neural_ok=False {'choice': ('neutral', 0.986)}
open-60 206 Package whereabouts | shipped_ok=False {'choice': ('product_question', 0.884)} | neural_ok=False {'choice': ('product_question', 0.884)}
open-60 207 Wrong size shoes | shipped_ok=False {'choice': ('product_question', 0.97)} | neural_ok=False {'choice': ('product_question', 0.97)}
open-60 209 Changed my mind | shipped_ok=True {'choice': ('cancel_order', 0.599)} | neural_ok=False {'choice': ('track_order', 0.485)}
open-60 211 Threat | shipped_ok=False {'choice': ('allow', 0.503)} | neural_ok=False {'choice': ('allow', 0.405)}
open-60 221 Everything down | shipped_ok=False {'score': 2.06} | neural_ok=False {'score': 2.08}
open-60 223 Log noise | shipped_ok=False {'score': 2.44} | neural_ok=False {'score': 2.47}
open-60 224 Search degraded | shipped_ok=False {'score': 1.03} | neural_ok=False {'score': 1.05}
open-60 225 Perfect blender | shipped_ok=False {'score': 2.04} | neural_ok=False {'score': 2.1}
open-60 226 Broke in a week | shipped_ok=False {'score': 2.06} | neural_ok=False {'score': 2.11}
open-60 228 Server fire | shipped_ok=False {'score': 1.52} | neural_ok=False {'score': 1.48}
open-60 231 Prize winner | shipped_ok=False {'noul': 0.48} | neural_ok=False {'noul': 0.48}
open-60 233 Fake bank | shipped_ok=False {'noul': 0.0594} | neural_ok=False {'noul': 0.0594}
open-60 234 Phone number | shipped_ok=False {'noul': 0.0567} | neural_ok=False {'noul': 0.0567}
open-60 236 Home address | shipped_ok=False {'noul': 0.0551} | neural_ok=False {'noul': 0.0551}
open-60 237 Friday deadline | shipped_ok=False {'noul': 0.3227} | neural_ok=False {'noul': 0.2808}
open-60 245 Damages cap | shipped_ok=False {'choice': ('payment', 0.881)} | neural_ok=True {'choice': ('liability', 0.491)}
open-60 247 Structured incident | shipped_ok=False {'score': 2.19} | neural_ok=False {'score': 2.1}
open-60 248 Mixed signals | shipped_ok=False {'choice': ('neutral', 0.689)} | neural_ok=False {'choice': ('neutral', 0.689)}
open-60 251 Return, not cancel | shipped_ok=True {'choice': ('return_item', 0.633)} | neural_ok=False {'choice': ('product_question', 0.65)}
open-60 254 Heated but fine | shipped_ok=False {'choice': ('remove', 0.49)} | neural_ok=False {'choice': ('remove', 0.49)}
open-60 255 SSN | shipped_ok=False {'noul': 0.2429} | neural_ok=False {'noul': 0.2082}
open-60 258 Rate limit | shipped_ok=False {'score': 2.15} | neural_ok=False {'score': 2.17}
open-60 260 Meeting ASAP | shipped_ok=False {'score': 1.42} | neural_ok=False {'score': 1.44}
