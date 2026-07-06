import warnings
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import Point, box, mapping

from config import COLUMNS, MISSING_FACTOR_SCORE, TARGET_CRS


def warn(message):
    print(f"[warning] {message}")


def ensure_output_dir(path):
    Path(path).mkdir(parents=True, exist_ok=True)


def find_existing_path(path):
    path = Path(path)
    if path.exists():
        return path

    for suffix in [".shp", ".geojson", ".json", ".gpkg"]:
        candidate = path.with_suffix(suffix)
        if candidate.exists():
            return candidate

    return path


def make_valid_geometries(gdf, layer_name):
    result = gdf.copy()
    invalid_mask = ~result.geometry.is_valid

    if invalid_mask.any():
        warn(f"{layer_name}: fixing {invalid_mask.sum()} invalid geometries with buffer(0).")
        result.loc[invalid_mask, "geometry"] = result.loc[invalid_mask, "geometry"].buffer(0)

    return result[~result.geometry.is_empty & result.geometry.notna()].copy()


def ensure_crs(gdf, target_crs=TARGET_CRS, layer_name="layer"):
    result = gdf.copy()

    if result.crs is None:
        if target_crs is None:
            warn(f"{layer_name}: CRS is missing. Original coordinates will be used.")
            return result
        warn(f"{layer_name}: CRS is missing. Assuming {target_crs}.")
        return result.set_crs(target_crs, allow_override=True)

    if target_crs is not None and result.crs.to_string() != str(target_crs):
        result = result.to_crs(target_crs)

    return result


def load_vector(path, target_crs=TARGET_CRS, layer_name="vector", required=False):
    existing_path = find_existing_path(path)

    if not existing_path.exists():
        message = f"{layer_name}: file not found: {existing_path}"
        if required:
            raise FileNotFoundError(message)
        warn(message)
        return None

    try:
        gdf = gpd.read_file(existing_path)
        gdf = make_valid_geometries(gdf, layer_name)
        gdf = ensure_crs(gdf, target_crs, layer_name)
        print(f"[loaded] {layer_name}: {existing_path} ({len(gdf)} features)")
        return gdf
    except Exception as exc:
        message = f"{layer_name}: failed to read vector file: {exc}"
        if required:
            raise RuntimeError(message) from exc
        warn(message)
        return None


def load_groundwater_csv(path, target_crs=TARGET_CRS):
    path = Path(path)
    if not path.exists():
        warn(f"groundwater.csv file not found: {path}")
        return None

    try:
        df = pd.read_csv(path)
    except Exception as exc:
        warn(f"groundwater.csv read failed: {exc}")
        return None

    lon_col = COLUMNS["groundwater_lon"]
    lat_col = COLUMNS["groundwater_lat"]

    if lon_col not in df.columns or lat_col not in df.columns:
        warn(f"groundwater.csv is missing coordinate columns: {lon_col}, {lat_col}")
        return None

    geometry = [Point(xy) for xy in zip(df[lon_col], df[lat_col])]
    gdf = gpd.GeoDataFrame(df, geometry=geometry, crs="EPSG:4326")
    gdf = ensure_crs(gdf, target_crs, "groundwater.csv")
    print(f"[loaded] groundwater.csv: {path} ({len(gdf)} points)")
    return gdf


def prepare_regions(regions):
    result = regions.copy().reset_index(drop=True)
    id_col = COLUMNS["region_id"]
    name_col = COLUMNS["region_name"]

    if id_col not in result.columns:
        warn(f"region layer is missing {id_col}. Auto IDs will be created.")
        result[id_col] = [f"R{i + 1:04d}" for i in range(len(result))]

    if name_col not in result.columns:
        warn(f"region layer is missing {name_col}. region_id will be used as name.")
        result[name_col] = result[id_col].astype(str)

    result["_region_index"] = result.index
    return result


def create_grid_from_layer(source_gdf, grid_size_m=5000, max_cells=6000):
    if source_gdf is None or source_gdf.empty:
        raise ValueError("Cannot create grid because the source layer is empty.")

    source = source_gdf.copy()
    if source.crs and source.crs.is_geographic:
        warn("Grid creation needs meter units. Reprojecting source layer to TARGET_CRS.")
        source = ensure_crs(source, TARGET_CRS, "grid_source")

    minx, miny, maxx, maxy = source.total_bounds
    width = maxx - minx
    height = maxy - miny

    if width <= 0 or height <= 0:
        raise ValueError("Cannot create grid because source bounds are invalid.")

    size = float(grid_size_m)
    estimated_cells = int(np.ceil(width / size) * np.ceil(height / size))

    if estimated_cells > max_cells:
        scale = np.sqrt(estimated_cells / max_cells)
        size = size * scale
        warn(
            f"Requested grid would create about {estimated_cells} cells. "
            f"Grid size increased to {size:.0f} m to keep the run practical."
        )

    cells = []
    ids = []
    names = []
    row = 0
    y = miny
    while y < maxy:
        col = 0
        x = minx
        while x < maxx:
            cells.append(box(x, y, min(x + size, maxx), min(y + size, maxy)))
            grid_id = f"G{row + 1:03d}_{col + 1:03d}"
            ids.append(grid_id)
            names.append(f"grid_{grid_id}")
            x += size
            col += 1
        y += size
        row += 1

    grid = gpd.GeoDataFrame(
        {COLUMNS["region_id"]: ids, COLUMNS["region_name"]: names},
        geometry=cells,
        crs=source.crs,
    )

    try:
        joined = gpd.sjoin(grid, source[["geometry"]], predicate="intersects", how="inner")
        grid = grid.loc[sorted(joined.index.unique())].copy()
    except Exception as exc:
        warn(f"Could not trim empty grid cells: {exc}")

    print(f"[grid] Created {len(grid)} grid cells with size about {size:.0f} m")
    return grid.reset_index(drop=True)


def _geometry_family(gdf):
    geom_types = set(gdf.geometry.geom_type.dropna().str.lower())
    if any("polygon" in geom_type for geom_type in geom_types):
        return "polygon"
    if any("line" in geom_type for geom_type in geom_types):
        return "line"
    if any("point" in geom_type for geom_type in geom_types):
        return "point"
    return "unknown"


def dominant_attribute_by_overlay(regions, layer, value_col, output_col, layer_name):
    result = regions.copy()

    if layer is None or layer.empty:
        warn(f"{layer_name}: data is missing. {output_col} will be empty.")
        result[output_col] = np.nan
        return result

    if value_col not in layer.columns:
        warn(f"{layer_name}: column not found: {value_col}")
        result[output_col] = np.nan
        return result

    family = _geometry_family(layer)

    try:
        if family == "polygon":
            base = result[["_region_index", "geometry"]]
            target = layer[[value_col, "geometry"]].dropna(subset=["geometry"])
            intersection = gpd.overlay(base, target, how="intersection", keep_geom_type=False)

            if intersection.empty:
                warn(f"{layer_name}: no overlap with regions.")
                result[output_col] = np.nan
                return result

            intersection["_area"] = intersection.geometry.area
            dominant = (
                intersection.sort_values("_area", ascending=False)
                .drop_duplicates("_region_index")
                .set_index("_region_index")[value_col]
            )
            result[output_col] = result["_region_index"].map(dominant)
            return result

        joined = gpd.sjoin(layer[[value_col, "geometry"]], result[["_region_index", "geometry"]], predicate="intersects")
        if joined.empty:
            warn(f"{layer_name}: no intersecting features.")
            result[output_col] = np.nan
            return result

        dominant = joined.groupby("_region_index")[value_col].agg(
            lambda values: values.mode().iloc[0] if not values.mode().empty else values.iloc[0]
        )
        result[output_col] = result["_region_index"].map(dominant)
        return result

    except Exception as exc:
        warn(f"{layer_name}: spatial join failed: {exc}")
        result[output_col] = np.nan
        return result


def numeric_attribute_mean_by_region(regions, layer, value_col, output_col, layer_name):
    result = regions.copy()

    if layer is None or layer.empty:
        warn(f"{layer_name}: data is missing. {output_col} will be empty.")
        result[output_col] = np.nan
        return result

    if value_col not in layer.columns:
        warn(f"{layer_name}: column not found: {value_col}")
        result[output_col] = np.nan
        return result

    layer = layer.copy()
    layer[value_col] = pd.to_numeric(layer[value_col], errors="coerce")
    family = _geometry_family(layer)

    try:
        if family == "polygon":
            base = result[["_region_index", "geometry"]]
            target = layer[[value_col, "geometry"]].dropna(subset=[value_col, "geometry"])
            intersection = gpd.overlay(base, target, how="intersection", keep_geom_type=False)

            if intersection.empty:
                warn(f"{layer_name}: no overlap with regions.")
                result[output_col] = np.nan
                return result

            intersection["_area"] = intersection.geometry.area
            intersection["_weighted_value"] = intersection[value_col] * intersection["_area"]
            grouped = intersection.groupby("_region_index").agg(
                weighted_sum=("_weighted_value", "sum"),
                area_sum=("_area", "sum"),
            )
            grouped[output_col] = grouped["weighted_sum"] / grouped["area_sum"]
            result[output_col] = result["_region_index"].map(grouped[output_col])
            return result

        joined = gpd.sjoin(layer[[value_col, "geometry"]], result[["_region_index", "geometry"]], predicate="intersects")
        if joined.empty:
            warn(f"{layer_name}: no intersecting features.")
            result[output_col] = np.nan
            return result

        means = joined.groupby("_region_index")[value_col].mean()
        result[output_col] = result["_region_index"].map(means)
        return result

    except Exception as exc:
        warn(f"{layer_name}: numeric aggregation failed: {exc}")
        result[output_col] = np.nan
        return result


def extract_raster_mean_by_regions(regions, raster_path, output_col="slope_mean"):
    raster_path = Path(raster_path)
    result = regions.copy()

    if not raster_path.exists():
        warn(f"raster file not found: {raster_path}")
        result[output_col] = np.nan
        return result

    try:
        import rasterio
        from rasterio.mask import mask
    except ImportError:
        warn("rasterio is not installed. Raster mean values cannot be calculated.")
        result[output_col] = np.nan
        return result

    means = []

    try:
        with rasterio.open(raster_path) as src:
            raster_regions = result
            if src.crs and result.crs and src.crs.to_string() != result.crs.to_string():
                raster_regions = result.to_crs(src.crs)

            for geom in raster_regions.geometry:
                if geom is None or geom.is_empty:
                    means.append(np.nan)
                    continue

                try:
                    out_image, _ = mask(src, [mapping(geom)], crop=True, filled=True)
                    arr = out_image[0].astype(float)

                    if src.nodata is not None:
                        arr[arr == src.nodata] = np.nan

                    valid = arr[np.isfinite(arr)]
                    means.append(float(valid.mean()) if valid.size else np.nan)
                except Exception:
                    means.append(np.nan)

        result[output_col] = means
        print(f"[processed] {raster_path.name}: raster means extracted")
        return result

    except Exception as exc:
        warn(f"raster processing failed: {exc}")
        result[output_col] = np.nan
        return result


def fill_missing_scores(gdf, score_columns):
    result = gdf.copy()
    for col in score_columns:
        if col not in result.columns:
            result[col] = MISSING_FACTOR_SCORE
        result[col] = pd.to_numeric(result[col], errors="coerce").fillna(MISSING_FACTOR_SCORE)
    return result
