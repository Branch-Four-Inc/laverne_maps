# -----------------------------------------------------------------------
# Name: Hudson County and NYC GeoJSON Pull
# Author: Sami Smalling
# -----------------------------------------------------------------------


library(tigris)
library(sf)
library(dplyr)

options(tigris_use_cache = TRUE)

# pull boundaries for New York and filter for NYC counties
nyc_counties <- counties(state = "NY", cb = TRUE) |>
    filter(COUNTYFP %in% c("061", "047", "081", "005", "085"))


# pull boundaries for New Jersey and filter for Hudson County (FIPS: 017)
nj_hudson <- counties(state = "NJ", cb = TRUE) |>
    filter(COUNTYFP == "017")

# combine the counties into a single dataset, keep ID and NAME
final_map_data <- rbind(nyc_counties, nj_hudson) |>
    select(GEOID, NAME)


# convert coordinates to  standard WGS84 (lat/long), which Leaflet expects
final_map_data <- st_transform(final_map_data, crs = 4326)

# write to boundaries.geojson file
st_write(
    final_map_data,
    "sliceofculture/growth_map/housing_growth_map/county_boundaries.geojson",
    driver = "GeoJSON",
    delete_dsn = TRUE
)

st_write(
    final_map_data,
    "sliceofculture/growth_map/demographic_growth_map/county_boundaries.geojson",
    driver = "GeoJSON",
    delete_dsn = TRUE
)
