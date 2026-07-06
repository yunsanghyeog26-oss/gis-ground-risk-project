import math

import numpy as np
import pandas as pd

from config import (
    FAULT_DISTANCE_SCORE_RULES,
    GROUNDWATER_DEPTH_RULES,
    GROUNDWATER_SCORE_MODE,
    INACTIVE_FACTOR_UNIQUE_VALUE,
    LAND_USE_RECOMMENDATIONS,
    MISSING_FACTOR_SCORE,
    NORMALIZE_WEIGHTS_FOR_AVAILABLE_DATA,
    RISK_GRADE_RULES,
    SLOPE_SCORE_RULES,
    UNKNOWN_CATEGORY_SCORE,
    WEIGHTS,
)


def clamp_score(value):
    if pd.isna(value):
        return np.nan
    return max(0, min(100, float(value)))


def score_by_rules(value, rules, value_key):
    if pd.isna(value):
        return np.nan
    for rule in rules:
        if value <= rule[value_key]:
            return clamp_score(rule["score"])
    return np.nan


def score_fault_by_distance(regions, faults, score_col="fault_score"):
    result = regions.copy()

    if faults is None or faults.empty:
        print("[warning] Fault data is missing. fault_score will use the default value.")
        result[score_col] = MISSING_FACTOR_SCORE
        result["fault_distance_m"] = np.nan
        result["fault_intersects"] = False
        return result

    if result.crs and result.crs.is_geographic:
        print("[warning] Fault distance is being calculated in a geographic CRS. A meter CRS is recommended.")

    fault_union = faults.geometry.union_all() if hasattr(faults.geometry, "union_all") else faults.geometry.unary_union
    distances = []
    intersects = []
    scores = []

    for geom in result.geometry:
        if geom is None or geom.is_empty:
            distances.append(np.nan)
            intersects.append(False)
            scores.append(np.nan)
            continue

        is_intersecting = geom.intersects(fault_union)
        distance = 0.0 if is_intersecting else geom.distance(fault_union)
        distances.append(distance)
        intersects.append(is_intersecting)
        scores.append(score_by_rules(distance, FAULT_DISTANCE_SCORE_RULES, "max_distance_m"))

    result["fault_distance_m"] = distances
    result["fault_intersects"] = intersects
    result[score_col] = pd.Series(scores, index=result.index).fillna(MISSING_FACTOR_SCORE).map(clamp_score)
    return result


def score_categorical(series, risk_map, unknown_score=UNKNOWN_CATEGORY_SCORE):
    normalized_map = {str(key).strip().lower(): value for key, value in risk_map.items()}

    def _score(value):
        if pd.isna(value):
            return MISSING_FACTOR_SCORE
        key = str(value).strip().lower()
        return clamp_score(normalized_map.get(key, unknown_score))

    return series.apply(_score)


def score_groundwater(series):
    numeric = pd.to_numeric(series, errors="coerce")

    if GROUNDWATER_SCORE_MODE == "depth_to_water":
        numeric = numeric.abs()
        return numeric.apply(lambda value: score_by_rules(value, GROUNDWATER_DEPTH_RULES, "max_depth_m")).fillna(
            MISSING_FACTOR_SCORE
        )

    if GROUNDWATER_SCORE_MODE == "water_level":
        return normalize_numeric_score(numeric, higher_is_riskier=True).fillna(MISSING_FACTOR_SCORE)

    print(f"[warning] Unknown GROUNDWATER_SCORE_MODE={GROUNDWATER_SCORE_MODE}. Default score will be used.")
    return pd.Series(MISSING_FACTOR_SCORE, index=series.index)


def score_slope(series):
    numeric = pd.to_numeric(series, errors="coerce")
    return numeric.apply(lambda value: score_by_rules(value, SLOPE_SCORE_RULES, "max_slope_degree")).fillna(
        MISSING_FACTOR_SCORE
    )


def normalize_numeric_score(series, higher_is_riskier=True):
    numeric = pd.to_numeric(series, errors="coerce")
    valid = numeric.dropna()

    if valid.empty:
        return pd.Series(np.nan, index=series.index)

    min_value = valid.min()
    max_value = valid.max()

    if math.isclose(min_value, max_value):
        return pd.Series(50, index=series.index)

    score = (numeric - min_value) / (max_value - min_value) * 100
    if not higher_is_riskier:
        score = 100 - score

    return score.map(clamp_score)


def calculate_final_risk(gdf, weights=WEIGHTS, final_col="final_risk_score"):
    result = gdf.copy()
    result[final_col] = 0.0
    active_weight_sum = 0.0

    for score_col, weight in weights.items():
        if score_col not in result.columns:
            print(f"[warning] {score_col} is missing. Default score will be used.")
            result[score_col] = MISSING_FACTOR_SCORE

        result[score_col] = pd.to_numeric(result[score_col], errors="coerce").fillna(MISSING_FACTOR_SCORE).map(clamp_score)

        is_active = True
        if NORMALIZE_WEIGHTS_FOR_AVAILABLE_DATA:
            unique_values = result[score_col].dropna().unique()
            is_active = not (len(unique_values) == 1 and float(unique_values[0]) == float(INACTIVE_FACTOR_UNIQUE_VALUE))

        if is_active:
            active_weight_sum += weight
            result[final_col] += result[score_col] * weight

    if NORMALIZE_WEIGHTS_FOR_AVAILABLE_DATA and active_weight_sum > 0:
        result[final_col] = result[final_col] / active_weight_sum
        result["active_weight_sum"] = active_weight_sum
    else:
        result["active_weight_sum"] = sum(weights.values())

    result[final_col] = result[final_col].map(clamp_score)
    return result


def classify_risk(score):
    if pd.isna(score):
        return "unclassified"

    score = clamp_score(score)
    for rule in RISK_GRADE_RULES:
        if rule["min"] <= score < rule["max"]:
            return rule["grade"]
    return "unclassified"


def recommend_land_use(grade):
    return LAND_USE_RECOMMENDATIONS.get(grade, LAND_USE_RECOMMENDATIONS["unclassified"])


def add_grade_and_recommendation(
    gdf,
    final_col="final_risk_score",
    grade_col="risk_grade",
    recommendation_col="land_use_recommendation",
):
    result = gdf.copy()
    result[grade_col] = result[final_col].apply(classify_risk)
    result[recommendation_col] = result[grade_col].apply(recommend_land_use)
    return result
