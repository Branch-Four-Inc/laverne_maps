# -----------------------------------------------------------------------
# Name: La Verne GeoJSON Pull
# Updated by: Mieko Chun
# -----------------------------------------------------------------------

library(tigris)
library(sf)
library(dplyr)

options(tigris_use_cache = TRUE)

# pull tract boundaries for LA County and filter for La Verne tracts
lv_tracts <- tracts(state = "CA", county = "Los Angeles", year = 2020) |>
    filter(NAME %in% c("4002.07", "4002.08", "4002.09", "4015", "4016.01", "4016.02", "4089"))

# combine the tracts into a single dataset, keep ID and NAME
final_map_data <- lv_tracts |>
    select(GEOID, NAME)


# convert coordinates to  standard WGS84 (lat/long), which Leaflet expects
final_map_data <- st_transform(final_map_data, crs = 4326)

# write to tract boundaries.geojson file
st_write(
    final_map_data,
    "housing_maps/lv_housing_tract_boundaries.geojson",
    driver = "GeoJSON",
    delete_dsn = TRUE
)

st_write(
    final_map_data,
    "housing_maps/lv_population_tract_boundaries.geojson",
    driver = "GeoJSON",
    delete_dsn = TRUE
)
