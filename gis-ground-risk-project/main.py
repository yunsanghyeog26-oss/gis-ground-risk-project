import warnings

from config import (
    AUTO_CREATE_GRID_IF_REGION_MISSING,
    AUTO_GRID_MAX_CELLS,
    COLUMNS,
    GEOLOGY_RISK_MAP,
    GRID_SIZE_M,
    INPUT_FILES,
    OUTPUT_DIR,
    OUTPUT_FILES,
    RISK_COLUMNS,
    SOIL_RISK_MAP,
    TARGET_CRS,
    WEATHERING_RISK_MAP,
    WEIGHTS,
)

try:
    from risk_model import (
        add_grade_and_recommendation,
        calculate_final_risk,
        score_categorical,
        score_fault_by_distance,
        score_groundwater,
        score_slope,
    )
    from utils import (
        create_grid_from_layer,
        dominant_attribute_by_overlay,
        ensure_output_dir,
        extract_raster_mean_by_regions,
        fill_missing_scores,
        load_groundwater_csv,
        load_vector,
        numeric_attribute_mean_by_region,
        prepare_regions,
        warn,
    )
    from visualize import create_grade_summary_chart, create_risk_map
except ModuleNotFoundError as exc:
    print(f"[error] Missing Python package: {exc.name}")
    print("Install dependencies first: pip install -r requirements.txt")
    raise SystemExit(1) from exc


warnings.simplefilter("default")


def load_soil_layer():
    soil = load_vector(INPUT_FILES["soil"], TARGET_CRS, "soil", required=False)
    if soil is not None:
        return soil
    return load_vector(INPUT_FILES["jiban_strata"], TARGET_CRS, "jiban_strata_as_soil", required=False)


def load_groundwater_layer():
    groundwater = load_vector(INPUT_FILES["groundwater_vector"], TARGET_CRS, "groundwater", required=False)
    if groundwater is not None:
        return groundwater

    groundwater = load_groundwater_csv(INPUT_FILES["groundwater_csv"], TARGET_CRS)
    if groundwater is not None:
        return groundwater

    return load_vector(INPUT_FILES["jiban_strata"], TARGET_CRS, "jiban_strata_as_groundwater", required=False)


def load_or_create_regions(soil_layer):
    regions = load_vector(INPUT_FILES["region"], TARGET_CRS, "region", required=False)
    if regions is not None:
        return prepare_regions(regions)

    if AUTO_CREATE_GRID_IF_REGION_MISSING and soil_layer is not None:
        warn("region.shp is missing. Temporary grid regions will be created from jiban_strata.")
        grid = create_grid_from_layer(soil_layer, GRID_SIZE_M, AUTO_GRID_MAX_CELLS)
        return prepare_regions(grid)

    raise FileNotFoundError(f"region file is required: {INPUT_FILES['region']}")


def main():
    print("Starting GIS ground stability decision model.")
    print("This is an exploratory model, not an official engineering judgement.")

    ensure_output_dir(OUTPUT_DIR)

    faults = load_vector(INPUT_FILES["fault"], TARGET_CRS, "fault", required=False)
    geology = load_vector(INPUT_FILES["geology"], TARGET_CRS, "geology", required=False)
    soil = load_soil_layer()
    groundwater = load_groundwater_layer()
    weathering = load_vector(INPUT_FILES["weathering"], TARGET_CRS, "weathering", required=False)
    regions = load_or_create_regions(soil)

    result = regions.copy()
    result = score_fault_by_distance(result, faults, RISK_COLUMNS["fault"])

    result = dominant_attribute_by_overlay(result, geology, COLUMNS["geology_type"], "geology_type_joined", "geology")
    result[RISK_COLUMNS["geology"]] = score_categorical(result["geology_type_joined"], GEOLOGY_RISK_MAP)

    result = dominant_attribute_by_overlay(result, soil, COLUMNS["soil_type"], "soil_type_joined", "soil")
    result[RISK_COLUMNS["soil"]] = score_categorical(result["soil_type_joined"], SOIL_RISK_MAP)

    result = numeric_attribute_mean_by_region(
        result,
        groundwater,
        COLUMNS["groundwater_value"],
        "groundwater_mean",
        "groundwater",
    )
    result[RISK_COLUMNS["groundwater"]] = score_groundwater(result["groundwater_mean"])

    result = extract_raster_mean_by_regions(result, INPUT_FILES["slope"], "slope_mean")
    result[RISK_COLUMNS["slope"]] = score_slope(result["slope_mean"])

    result = dominant_attribute_by_overlay(
        result,
        weathering,
        COLUMNS["weathering_grade"],
        "weathering_joined",
        "weathering",
    )
    result[RISK_COLUMNS["weathering"]] = score_categorical(result["weathering_joined"], WEATHERING_RISK_MAP)

    result = fill_missing_scores(result, list(WEIGHTS.keys()))
    result = calculate_final_risk(result, WEIGHTS, RISK_COLUMNS["final"])
    result = add_grade_and_recommendation(
        result,
        RISK_COLUMNS["final"],
        RISK_COLUMNS["grade"],
        RISK_COLUMNS["recommendation"],
    )

    result.to_file(OUTPUT_FILES["geojson"], driver="GeoJSON", encoding="utf-8")
    print(f"[saved] GeoJSON: {OUTPUT_FILES['geojson']}")

    csv_columns = [
        COLUMNS["region_id"],
        COLUMNS["region_name"],
        "fault_distance_m",
        "fault_intersects",
        "geology_type_joined",
        "soil_type_joined",
        "groundwater_mean",
        "slope_mean",
        "weathering_joined",
        RISK_COLUMNS["fault"],
        RISK_COLUMNS["geology"],
        RISK_COLUMNS["soil"],
        RISK_COLUMNS["groundwater"],
        RISK_COLUMNS["slope"],
        RISK_COLUMNS["weathering"],
        "active_weight_sum",
        RISK_COLUMNS["final"],
        RISK_COLUMNS["grade"],
        RISK_COLUMNS["recommendation"],
    ]
    csv_columns = [col for col in csv_columns if col in result.columns]
    result[csv_columns].to_csv(OUTPUT_FILES["csv"], index=False, encoding="utf-8-sig")
    print(f"[saved] CSV: {OUTPUT_FILES['csv']}")

    create_risk_map(
        result,
        OUTPUT_FILES["map"],
        grade_col=RISK_COLUMNS["grade"],
        score_col=RISK_COLUMNS["final"],
        name_col=COLUMNS["region_name"],
    )
    create_grade_summary_chart(result, OUTPUT_FILES["chart"], grade_col=RISK_COLUMNS["grade"])

    summary = result[RISK_COLUMNS["grade"]].value_counts(dropna=False).rename_axis("risk_grade").reset_index(name="count")
    print("\nRisk grade summary")
    print(summary.to_string(index=False))
    print("\nDone.")


if __name__ == "__main__":
    try:
        main()
    except FileNotFoundError as exc:
        warn(str(exc))
        print("Add region.shp or jiban_strata_WGS84.shp, then run again.")
    except Exception as exc:
        warn(f"Unexpected error: {exc}")
        raise
