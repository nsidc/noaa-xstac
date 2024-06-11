import sys
from datetime import datetime
import argparse
import json
import fsspec
import xarray as xr
from pathlib import Path
import earthpy as et

import xstac
import pystac
import shapely.geometry

BBOX = {
    "north": [31.1, -180, 89.84, 180],
    "south": [-89.84, -180, -39.36, 180]
}

DESC = {
    "daily":"",
    "monthly":"",
    "aggregate":"",
}
CITATION_URLS = {
    "daily": "https://doi.org/10.7265/efmz-2t65",
    "monthly": "https://doi.org/10.7265/efmz-2t65",
    "annual": "https://doi.org/10.7265/efmz-2t65",
}

CITATION = {("Meier, W. N., F. Fetterer, A. K. Windnagel, and S. Stewart. 2021. NOAA/NSIDC Climate Data Record of Passive Microwave Sea Ice Concentration, Version 4."
             "[Indicate subset used]. Boulder, Colorado, USA. NSIDC: National Snow and Ice Data Center https://doi.org/10.7265/efmz-2t65.")}

FREQUENCIES = ["daily", "monthly"]
# TODO: Add aggregate later

REGIONS = ["north", "south"]

# Unsure if this is correct
NETCDF_MEDIA_TYPE = pystac.MediaType.HDF


# Generate list of years
start_year = (datetime(1978, 1, 1).year)
current_year = (datetime.now()).year
years = list(range(start_year, 1 + current_year))
str_years = [str(year) for year in years]

months = ["01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12"]

doys = list(range(1, 366))
str_doys = [str(doy) for doy in doys]
doys1 = [ "00"+doy for doy in str_doys if len(doy)==1]
doys2 = [ "0"+doy for doy in str_doys if len(doy)==2]
doys3 = [doy for doy in str_doys  if len(doy)==3]
full_doys = doys1 + doys2 + doys3


def parse_args(args=None):
    parser = argparse.ArgumentParser(usage=__doc__)
    parser.add_argument(
        "--region", type=str, choices=["both", "north", "south"], default="both"
    )
    parser.add_argument(
        "--frequency",
        type=str,
        choices=["all", "daily", "monthly", "aggregate"],
        default="all",
    )
    return parser.parse_args(args)

def generate(frequency, region, year):

    collection_template = {
        "id": f"seaiceClimateDataRecordV4-{frequency}-{region}",
        "stac_extensions": [
            "https://stac-extensions.github.io/scientific/v1.0.0/schema.json"
        ],
        "description": "{{ collection.description }}",
        "type": "Collection",
        "title": f"NOAA/NSIDC passive microwave sea ice concentration climate data record {frequency.title()} {FULL_REGIONS[region]}",
        "license": "proprietary",
        "keywords": [
            "EARTH SCIENCE",
            "CRYOSPHERE",
            "SEA ICE",
            "SEA ICE CONCENTRATION",
            "Polar",
        ],
        "stac_version": "1.0.0",
        "links": [
            {
                "rel": "license",
                "title": "EOSDIS Data Use Policy",
                "href": "https://science.nasa.gov/earth-science/earth-science-data/data-information-policy",
            },
            {"rel": "cite-as", "href": CITATION},
        ],
        "extent": {
            "spatial": {"bbox": [BBOX[region]]},
            },
        "providers": [
            {
                "name": "NOAA at the National Snow and Ice Data Center",
                "roles": ["licensor", "host", "processor"],
                "url": "https://nsidc.org/data",
            },
        ],
        "assets": {
            "netcdf-https": {
                "href": f"https://noaadata.apps.nsidc.org/NOAA/G02202_V4/{region}/{frequency}.nc",
                "type": "application/x-hdf",
                "roles": ["data", "netcdf4", "https"]},
               #  "xarray:open_kwargs": {"consolidated": True},
        },
        "sci:doi": DOI_NAMES[frequency],
        "sci:citation": CITATIONS[frequency],
    }

    
    if region == "north":
        region_sn = "nh"
    else:
        region_sn = "sh"

    if frequency == "daily":
        # for doy in doys: 
        filepath_url = f"https://noaadata.apps.nsidc.org/NOAA/G02202_V4/{region}/{frequency}/{year}" # /seaice_conc_daily_{region_sn}_{year}{doy}_n07_v04r00.nc"
    elif frequency == "monthly":
        # for month in months:
        filepath_url = f"https://noaadata.apps.nsidc.org/NOAA/G02202_V4/{region}/{frequency}" # /seaice_conc_monthly_{region_sn}_{year}{month}_n07_v04r00.nc" 

    fs = fsspec.filesystem('https') #, host=host)
    url = filepath_url
    files = [f for f in fs.find(url) if f.endswith('.nc')]
    with fs.open(files[0]) as f:
        ds = xr.open_dataset(f)

    collection = xstac.xarray_to_stac(
        ds,
        collection_template,
        temporal_dimension="time",
        x_dimension="x",
        y_dimension="y",
    )
    collection.remove_links(pystac.RelType.SELF)
    collection.remove_links(pystac.RelType.ROOT)
    collection_result = collection.to_dict(include_self_link=False)
    
    item_template = {
        "id": f"cdr-{frequency}-{region}",
        "type": "Feature",
        "links": [],
        "bbox": BBOX[region],
        "geometry": shapely.geometry.mapping(shapely.geometry.box(*BBOX[region])),
        "stac_version": "1.0.0",
        "properties": {"start_datetime": None, "end_datetime": None},
        "assets": {
            "hdf-https": {
                "href": f"https://noaadata.apps.nsidc.org/NOAA/G02202_V4/{region}/{frequency}.nc",
                "type": "application/x-hdf",
                "title": f"{frequency.title()} {region} CDR HTTPS NetCDF root",
                "description": f"HTTPS URI of the {frequency} {region} Climate Data Record.",  # noqa: E501
                "roles": ["data", "hdf", "https"],
                "xarray:open_kwargs": {"consolidated": True},
            },
        },
    }
    item = xstac.xarray_to_stac(
        ds, item_template, temporal_dimension="time", x_dimension="x", y_dimension="y"
    )
    
    item_result = item.to_dict(include_self_link=False)
    return collection_result, item_result

def main(args=None):
    args = parse_args(args)
    region = args.region
    frequency = args.frequency
    year = 

    if region == "all":
        regions = list(REGIONS)
    else: 
        regions = [region]

    if frequency == "all":
        frequencies = FREQUENCIES
    else:
        frequencies = [frequency]

    for region in regions:
        for frequency in frequencies:
            collection, item = general(frequency, region)
            outfile = Path(__file__).parent/f"{frequency}{region}collection.json"
            outfile.parent.mkdir(exist_ok=True, parents=True)
            with open(outfile, "w") as f:
                json.dump(collection, f, indent=2)
            outfile = Path(__file__).parent / f"{frequency}/{region}/{year}/item.json"
            with open(outfile, "w") as f:
                json.dump(item, f, indent=2)

    if __name__ == "__main__":
        sys.exit(main())
