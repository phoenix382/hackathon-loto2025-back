import requests
from typing import List, Tuple, Dict


DEFAULT_TIMEOUT = 8


def _fetch(url: str) -> Tuple[bytes, Dict[str, str]]:
    resp = requests.get(url, timeout=DEFAULT_TIMEOUT, headers={"User-Agent": "loto-rng/1.0"})
    resp.raise_for_status()
    headers = {k.lower(): v for k, v in resp.headers.items()}
    return resp.content, headers


def get_solar_images() -> List[Tuple[str, bytes, Dict[str, str]]]:
    """Fetch a small set of current solar images from public endpoints.

    Returns list of tuples (source_name, image_bytes, response_headers)
    """
    urls = [
        # NASA SDO AIA latest images (no API key required)
        ("sdo_aia_0171", "https://sdo.gsfc.nasa.gov/assets/img/latest/latest_1024_0171.jpg"),
        ("sdo_aia_0193", "https://sdo.gsfc.nasa.gov/assets/img/latest/latest_1024_0193.jpg"),
        ("sdo_aia_0304", "https://sdo.gsfc.nasa.gov/assets/img/latest/latest_1024_0304.jpg"),
        # NOAA SWPC GOES SUVI latest images
        ("sdo_hmi_continuum", "https://sdo.gsfc.nasa.gov/assets/img/latest/latest_1024_HMIIF.jpg"),
        ("noaa_suvi_195", "https://services.swpc.noaa.gov/images/suvi/primary/195/latest.jpg"),
        ("noaa_suvi_304", "https://services.swpc.noaa.gov/images/suvi/primary/304/latest.jpg"),
        ("noaa_suvi_171", "https://services.swpc.noaa.gov/images/suvi/primary/171/latest.jpg"),
    ]

    out: List[Tuple[str, bytes, Dict[str, str]]] = []
    for name, url in urls:
        try:
            content, headers = _fetch(url)
            out.append((name, content, headers))
        except Exception:
            # Best-effort: skip failing sources
            continue
    return out

