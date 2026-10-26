#!/usr/bin/env python3
import os

import numpy as np

from astropy.time import Time
from astropy.io import ascii
from astropy.coordinates import AltAz
from astropy.coordinates import SkyCoord
from astropy.coordinates import EarthLocation
from astropy.coordinates import get_icrs_coordinates

def local_get_icrs_coordinates(source_name):
    # Set file path
    filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), "source_list.csv")

    # Read file
    data = ascii.read(filepath, format="csv", comment="#")
    
    # Select
    c = data["source_name"] == source_name
    data = data[c]
    
    # Fall back to astropy
    if len(data) == 0:
        return get_icrs_coordinates(source_name)
    else:
        return SkyCoord(ra=data["ra"][0], dec=data["dec"][0], unit=("hourangle", "deg"), frame="icrs")
    
def select_source(tstr, obstype, band):
    # Set file path
    filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), "automatic_source_list.csv")

    # Read file
    data = ascii.read(filepath, format="csv", comment="#")

    # Select
    c = (data["obstype"] == obstype) & (data["band"] == band)
    data = data[c]

    # Exit when no matches
    if len(data) == 0:
        return None, None

    # Time
    t = Time(tstr, format="isot", scale="utc")
    
    # Altaz
    loc = EarthLocation.of_site("LOFAR")
    p = SkyCoord(ra=data["ra"], dec=data["dec"], unit=("hourangle", "deg"), frame="icrs")
    a = p.transform_to(AltAz(obstime=t, location=loc))

    # Select highest
    idx = np.argmax(a.alt.degree)

    source_name = str(data["source_name"][idx])
        
    return source_name, p[idx]
