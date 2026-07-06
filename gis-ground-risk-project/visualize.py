import json
import warnings

from config import MAP_COLORS


def create_risk_map(gdf, output_path, grade_col="risk_grade", score_col="final_risk_score", name_col="region_name"):
    try:
        import folium
    except ImportError:
        warnings.warn("folium is not installed. risk_map.html was not created.")
        return False

    if gdf.empty:
        warnings.warn("No result data to map.")
        return False

    map_gdf = gdf.copy()
    if map_gdf.crs and map_gdf.crs.to_string() != "EPSG:4326":
        map_gdf = map_gdf.to_crs("EPSG:4326")

    bounds = map_gdf.total_bounds
    center = [(bounds[1] + bounds[3]) / 2, (bounds[0] + bounds[2]) / 2]
    m = folium.Map(location=center, zoom_start=8, tiles="CartoDB positron")

    def style_function(feature):
        grade = feature["properties"].get(grade_col, "unclassified")
        return {
            "fillColor": MAP_COLORS.get(grade, MAP_COLORS["unclassified"]),
            "color": "#444444",
            "weight": 0.8,
            "fillOpacity": 0.72,
        }

    tooltip_fields = [field for field in [name_col, score_col, grade_col, "land_use_recommendation"] if field in map_gdf.columns]
    tooltip_aliases = {
        name_col: "Region",
        score_col: "Final risk score",
        grade_col: "Risk grade",
        "land_use_recommendation": "Land-use recommendation",
    }

    folium.GeoJson(
        json.loads(map_gdf.to_json()),
        name="Ground stability risk",
        style_function=style_function,
        tooltip=folium.GeoJsonTooltip(
            fields=tooltip_fields,
            aliases=[tooltip_aliases.get(field, field) for field in tooltip_fields],
            localize=True,
            sticky=True,
        ),
    ).add_to(m)

    legend_html = """
    <div style="
        position: fixed;
        bottom: 30px;
        left: 30px;
        z-index: 9999;
        background: white;
        padding: 12px 14px;
        border: 1px solid #999;
        border-radius: 4px;
        font-size: 13px;
        box-shadow: 0 1px 5px rgba(0,0,0,0.25);
    ">
        <b>Risk grade</b><br>
        <span style="color:#1a9850;">&#9632;</span> very_low<br>
        <span style="color:#2ca25f;">&#9632;</span> low<br>
        <span style="color:#91cf60;">&#9632;</span> slightly_low<br>
        <span style="color:#fee08b;">&#9632;</span> moderate<br>
        <span style="color:#fdae61;">&#9632;</span> high<br>
        <span style="color:#f46d43;">&#9632;</span> very_high<br>
        <span style="color:#b2182b;">&#9632;</span> extreme<br>
        <span style="color:#9e9e9e;">&#9632;</span> unclassified
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))
    folium.LayerControl().add_to(m)
    m.save(output_path)
    print(f"[saved] Folium map: {output_path}")
    return True


def create_grade_summary_chart(gdf, output_path, grade_col="risk_grade"):
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        warnings.warn("matplotlib is not installed. Summary chart was not created.")
        return False

    if grade_col not in gdf.columns:
        warnings.warn(f"{grade_col} is missing. Summary chart was not created.")
        return False

    order = ["very_low", "low", "slightly_low", "moderate", "high", "very_high", "extreme", "unclassified"]
    counts = gdf[grade_col].value_counts().reindex(order, fill_value=0)
    colors = [MAP_COLORS.get(grade, MAP_COLORS["unclassified"]) for grade in counts.index]

    plt.figure(figsize=(9, 5))
    bars = plt.bar(counts.index, counts.values, color=colors, edgecolor="#333333", linewidth=0.7)
    plt.title("Risk grade count by grid")
    plt.xlabel("Risk grade")
    plt.ylabel("Grid count")
    plt.xticks(rotation=25, ha="right")
    plt.grid(axis="y", linestyle="--", alpha=0.35)

    for bar in bars:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width() / 2, height, f"{int(height)}", ha="center", va="bottom")

    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()
    print(f"[saved] Matplotlib chart: {output_path}")
    return True
