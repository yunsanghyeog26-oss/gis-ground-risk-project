from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data" / "raw"
OUTPUT_DIR = BASE_DIR / "outputs"
DOWNLOADS_DIR = Path.home() / "Downloads"

# Exploratory GIS decision model. This is not an official engineering judgement.
TARGET_CRS = "EPSG:5179"

INPUT_FILES = {
    "region": DATA_DIR / "region.shp",
    "fault": DATA_DIR / "fault.shp",
    "geology": DATA_DIR / "geology.shp",
    "soil": DATA_DIR / "soil.shp",
    "groundwater_vector": DATA_DIR / "groundwater.shp",
    "groundwater_csv": DATA_DIR / "groundwater.csv",
    "jiban_strata": DOWNLOADS_DIR / "jiban_strata_WGS84_shp" / "jiban_strata_WGS84.shp",
    "slope": DATA_DIR / "slope.tif",
    "weathering": DATA_DIR / "weathering.shp",
}

OUTPUT_FILES = {
    "geojson": OUTPUT_DIR / "final_result.geojson",
    "csv": OUTPUT_DIR / "final_result.csv",
    "map": OUTPUT_DIR / "risk_map.html",
    "chart": OUTPUT_DIR / "risk_grade_summary.png",
}

AUTO_CREATE_GRID_IF_REGION_MISSING = True
GRID_SIZE_M = 5000
AUTO_GRID_MAX_CELLS = 6000

COLUMNS = {
    "region_id": "region_id",
    "region_name": "region_name",
    "geology_type": "rock_type",
    "soil_type": "USCS_NM",
    "groundwater_value": "GWL_M",
    "groundwater_lon": "lon",
    "groundwater_lat": "lat",
    "weathering_grade": "weathering",
}

RISK_COLUMNS = {
    "fault": "fault_score",
    "geology": "geology_score",
    "soil": "soil_score",
    "groundwater": "groundwater_score",
    "slope": "slope_score",
    "weathering": "weathering_score",
    "final": "final_risk_score",
    "grade": "risk_grade",
    "recommendation": "land_use_recommendation",
}

WEIGHTS = {
    "fault_score": 0.25,
    "geology_score": 0.20,
    "soil_score": 0.20,
    "groundwater_score": 0.15,
    "slope_score": 0.10,
    "weathering_score": 0.10,
}

MISSING_FACTOR_SCORE = 0
UNKNOWN_CATEGORY_SCORE = 50
NORMALIZE_WEIGHTS_FOR_AVAILABLE_DATA = True
INACTIVE_FACTOR_UNIQUE_VALUE = MISSING_FACTOR_SCORE

FAULT_DISTANCE_SCORE_RULES = [
    {"max_distance_m": 0, "score": 100},
    {"max_distance_m": 500, "score": 90},
    {"max_distance_m": 1000, "score": 75},
    {"max_distance_m": 3000, "score": 50},
    {"max_distance_m": 5000, "score": 25},
    {"max_distance_m": float("inf"), "score": 0},
]

GEOLOGY_RISK_MAP = {
    "granite": 20,
    "gneiss": 25,
    "sandstone": 45,
    "shale": 65,
    "limestone": 60,
    "alluvium": 85,
    "fill": 90,
    "unknown": UNKNOWN_CATEGORY_SCORE,
}

SOIL_RISK_MAP = {
    "gw": 20,
    "gp": 25,
    "gm": 35,
    "gc": 45,
    "sw": 35,
    "sp": 40,
    "sm": 55,
    "sc": 65,
    "ml": 65,
    "cl": 75,
    "ol": 80,
    "mh": 80,
    "ch": 90,
    "oh": 90,
    "pt": 95,
    "wr": 35,
    "sr": 20,
    "mr": 15,
    "hr": 10,
    "rock": 15,
    "gravel": 25,
    "sand": 45,
    "silt": 65,
    "clay": 75,
    "soft_clay": 90,
    "fill": 85,
    "unknown": UNKNOWN_CATEGORY_SCORE,
}

WEATHERING_RISK_MAP = {
    "fresh": 10,
    "slightly weathered": 25,
    "moderately weathered": 50,
    "highly weathered": 75,
    "completely weathered": 90,
    "unknown": UNKNOWN_CATEGORY_SCORE,
}

GROUNDWATER_SCORE_MODE = "depth_to_water"
GROUNDWATER_DEPTH_RULES = [
    {"max_depth_m": 1, "score": 100},
    {"max_depth_m": 3, "score": 80},
    {"max_depth_m": 5, "score": 60},
    {"max_depth_m": 10, "score": 35},
    {"max_depth_m": float("inf"), "score": 10},
]

SLOPE_SCORE_RULES = [
    {"max_slope_degree": 5, "score": 10},
    {"max_slope_degree": 15, "score": 35},
    {"max_slope_degree": 30, "score": 65},
    {"max_slope_degree": 45, "score": 85},
    {"max_slope_degree": float("inf"), "score": 100},
]

RISK_GRADE_RULES = [
    {"min": 0, "max": 15, "grade": "very_low"},
    {"min": 15, "max": 30, "grade": "low"},
    {"min": 30, "max": 45, "grade": "slightly_low"},
    {"min": 45, "max": 60, "grade": "moderate"},
    {"min": 60, "max": 75, "grade": "high"},
    {"min": 75, "max": 90, "grade": "very_high"},
    {"min": 90, "max": 100.000001, "grade": "extreme"},
]

LAND_USE_RECOMMENDATIONS = {
    "very_low": "High-density development may be possible after standard site investigation.",
    "low": "Residential, public facilities, or industrial use may be possible.",
    "slightly_low": "General residential or small public facilities may be possible.",
    "moderate": "Medium-low density use is preferred; detailed ground investigation is recommended.",
    "high": "Low-rise buildings, parks, green areas, or buffer zones are recommended.",
    "very_high": "Large-scale development should be limited; disaster-prevention or green use is recommended.",
    "extreme": "Development should be avoided or strictly controlled; conservation or disaster-prevention use is preferred.",
    "unclassified": "More data is required before making a recommendation.",
}

MAP_COLORS = {
    "very_low": "#1a9850",
    "low": "#2ca25f",
    "slightly_low": "#91cf60",
    "moderate": "#fee08b",
    "high": "#fdae61",
    "very_high": "#f46d43",
    "extreme": "#b2182b",
    "unclassified": "#9e9e9e",
}
