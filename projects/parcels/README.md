# Parcel land use

How is a county's parcel layer divided between land uses, by area and by assessed value?

`data/parcels.gdb.zip` is a file geodatabase zipped on Windows, with three feature classes:
Parcels (2,000 polygons), Roads and Hydrants. It is synthetic, in Web Mercator (EPSG:3857),
so areas are inflated by about 1/cos²(latitude).

`layer` reads the Parcels feature class from the zip with GDAL in the browser, `areas`
drops slivers below `min_area_m2`, and `summary` adds area and assessed value up per land
use (downloadable as CSV). Replace the data on the overview with another county's zip and
Run.
