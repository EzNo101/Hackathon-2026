from __future__ import annotations

MAIN_17: list[str] = [
    "R_mag_axis",
    "Z_mag_axis",
    "elongation",
    "triangularity",
    "triangularity_lower",
    "triangularity_upper",
    "a",
    "R_geom",
    "Z_geom",
    "R_x_point",
    "Z_x_point",
    "R_strike_point_1",
    "Z_strike_point_1",
    "R_strike_point_2",
    "Z_strike_point_2",
    "R_limiter",
    "Z_limiter",
]

EXTRA_TARGETS: list[str] = [
    "plasma_current",
    "R_top",
    "Z_top",
    "R_bottom",
    "Z_bottom",
    "R_outer",
    "Z_outer",
    "R_inner",
    "Z_inner",
    "squareness_upper_outer",
    "squareness_upper_inner",
    "squareness_lower_outer",
    "squareness_lower_inner",
]

DIVERTOR_FIELDS: list[str] = MAIN_17[9:15]
LIMITER_FIELDS: list[str] = MAIN_17[15:]

UNITS: dict[str, str] = {
    "R_mag_axis": "m",
    "Z_mag_axis": "m",
    "R_geom": "m",
    "Z_geom": "m",
    "a": "m",
    "R_x_point": "m",
    "Z_x_point": "m",
    "R_strike_point_1": "m",
    "Z_strike_point_1": "m",
    "R_strike_point_2": "m",
    "Z_strike_point_2": "m",
    "R_limiter": "m",
    "Z_limiter": "m",
    "R_top": "m",
    "Z_top": "m",
    "R_bottom": "m",
    "Z_bottom": "m",
    "R_outer": "m",
    "Z_outer": "m",
    "R_inner": "m",
    "Z_inner": "m",
    "plasma_current": "A",
    "elongation": "-",
    "triangularity": "-",
    "triangularity_lower": "-",
    "triangularity_upper": "-",
    "squareness_upper_outer": "-",
    "squareness_upper_inner": "-",
    "squareness_lower_outer": "-",
    "squareness_lower_inner": "-",
    "is_limited": "bool",
}

GROUPS: dict[str, str] = {}
for _target in MAIN_17[:9]:
    GROUPS[_target] = "position_shape"
for _target in DIVERTOR_FIELDS:
    GROUPS[_target] = "divertor"
for _target in LIMITER_FIELDS:
    GROUPS[_target] = "limiter"
for _target in EXTRA_TARGETS:
    GROUPS[_target] = "supplementary"
GROUPS["plasma_current"] = "plasma"
GROUPS["is_limited"] = "regime"

LABELS: dict[str, str] = {
    "R_mag_axis": "R magnetic axis",
    "Z_mag_axis": "Z magnetic axis",
    "elongation": "Elongation",
    "triangularity": "Triangularity",
    "triangularity_lower": "Lower triangularity",
    "triangularity_upper": "Upper triangularity",
    "a": "Minor radius",
    "R_geom": "R geometric centre",
    "Z_geom": "Z geometric centre",
    "R_x_point": "R X-point",
    "Z_x_point": "Z X-point",
    "R_strike_point_1": "R strike point 1",
    "Z_strike_point_1": "Z strike point 1",
    "R_strike_point_2": "R strike point 2",
    "Z_strike_point_2": "Z strike point 2",
    "R_limiter": "R limiter contact",
    "Z_limiter": "Z limiter contact",
    "plasma_current": "Plasma current",
    "R_top": "R top point",
    "Z_top": "Z top point",
    "R_bottom": "R bottom point",
    "Z_bottom": "Z bottom point",
    "R_outer": "R outer point",
    "Z_outer": "Z outer point",
    "R_inner": "R inner point",
    "Z_inner": "Z inner point",
    "squareness_upper_outer": "Squareness upper outer",
    "squareness_upper_inner": "Squareness upper inner",
    "squareness_lower_outer": "Squareness lower outer",
    "squareness_lower_inner": "Squareness lower inner",
    "is_limited": "Limited configuration",
}
