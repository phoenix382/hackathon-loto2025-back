import datetime
from typing import Dict, List, Tuple, Iterable
import requests
import imghdr
import hashlib

DEFAULT_TIMEOUT = 8
def _is_image_bytes(b: bytes) -> str:
    """
    Возвращает формат ('jpeg', 'png', 'gif', 'webp', ...) если распознан,
    иначе пустую строку.
    """
    kind = imghdr.what(None, h=b)
    return kind or ""

def _fetch(url: str) -> Tuple[bytes, Dict[str, str]]:
    resp = requests.get(url, timeout=DEFAULT_TIMEOUT, headers={"User-Agent": "loto-rng/1.0"})
    resp.raise_for_status()
    headers = {k.lower(): v for k, v in resp.headers.items()}
    return resp.content, headers

def _is_jpeg(content: bytes, headers: Dict[str, str]) -> bool:
    ct = headers.get("content-type", "").lower()
    sig = content[:3]
    return (ct.startswith("image/jpeg") or ct.startswith("image/jpg")) and sig == b"\xff\xd8\xff"

def _worldview_snapshot_url(layer: str,
                            date: datetime.date,
                            width: int = 1024,
                            height: int = 512,
                            bbox: str = "-180,-90,180,90",
                            fmt: str = "image/jpeg") -> str:
    """
    Формирование URL для NASA Worldview Snapshots API (GIBS), без ключа.
    Документация: https://wvs.earthdata.nasa.gov/
    """
    day = date.isoformat()
    base = "https://wvs.earthdata.nasa.gov/api/v1/snapshot"
    params = (
        "REQUEST=GetSnapshot",
        f"FORMAT={fmt}",
        f"LAYERS={layer}",
        "CRS=EPSG:4326",
        f"BBOX={bbox}",
        f"WIDTH={width}",
        f"HEIGHT={height}",
        f"TIME={day}",
    )
    return f"{base}?" + "&".join(params)

def _goes_geocolor(sat: str, sector: str) -> str:
    # sat: "GOES19" (East), "GOES18" (West); sector: "FD" (full disk), "CONUS"
    return f"https://cdn.star.nesdis.noaa.gov/{sat}/ABI/{sector}/GEOCOLOR/latest.jpg"

def _goes_band(sat: str, band: int, size: str = "678x678.jpg", sector: str = "FD") -> str:
    # stable “latest” symlinks exist per size inside each band directory
    return f"https://cdn.star.nesdis.noaa.gov/{sat}/ABI/{sector}/{band:02d}/{size}"

def get_meteo_sat_images(validate: bool = True,min_bytes: int = 10_000,
                         dedup: bool = True) -> List[Tuple[str, bytes, Dict[str, str]]]:
    """Получить небольшую, но разнообразную подборку актуальных спутниковых снимков.

    Источники:
      - GOES-19 (East) и GOES-18 (West): GeoColor (FD) + CONUS (для GOES-18)
      - GOES-19/18: каналы 02 (Red VIS), 08 (WV 6.2µm), 13 (Clean IR) — Full Disk, 678x678
      - NASA Worldview VIIRS NOAA-20 Global TrueColor (текущая дата)

    Возвращает: список кортежей (source_name, image_bytes, response_headers)
    """
    today = datetime.date.today()

    urls: List[Tuple[str, str]] = [
        # GeoColor full disk
        ("goes19_geocolor_fd", _goes_geocolor("GOES19", "FD")),
        ("goes18_geocolor_fd", _goes_geocolor("GOES18", "FD")),
        # Геоcolor регион США (на CDN путь CONUS, это и есть PACUS для GOES-18)
        ("goes18_conus_geocolor", _goes_geocolor("GOES18", "CONUS")),
        # Отдельные каналы (Full Disk) — стабильные «latest» файлы по размеру
        ("goes19_band02_fd", _goes_band("GOES19", 2)),
        ("goes18_band02_fd", _goes_band("GOES18", 2)),
        ("goes19_band08_fd", _goes_band("GOES19", 8)),
        ("goes18_band08_fd", _goes_band("GOES18", 8)),
        ("goes19_band13_fd", _goes_band("GOES19", 13)),
        ("goes18_band13_fd", _goes_band("GOES18", 13)),
        ("goes16_geocolor_fd", "https://cdn.star.nesdis.noaa.gov/GOES16/ABI/FD/GEOCOLOR/latest.jpg"),
        # NASA Worldview — глобальный TrueColor (без ключа)
         ("nasa_viirs_noaa20_truecolor",
         _worldview_snapshot_url("VIIRS_NOAA20_CorrectedReflectance_TrueColor", today)),
        ("nasa_viirs_snpp_truecolor",
         _worldview_snapshot_url("VIIRS_SNPP_CorrectedReflectance_TrueColor", today)),
        ("nasa_modis_terra_truecolor",
         _worldview_snapshot_url("MODIS_Terra_CorrectedReflectance_TrueColor", today)),
        ("nasa_modis_aqua_truecolor",
         _worldview_snapshot_url("MODIS_Aqua_CorrectedReflectance_TrueColor", today)),
    ]

    out: List[Tuple[str, bytes, Dict[str, str]]] = []
    seen_hashes: set[str] = set()

    for name, url in urls:
        try:
            content, headers = _fetch(url)

            if validate:
                ok, meta = _validate_image(name, content, headers, min_bytes=min_bytes)
                # прикрепим метаданные в headers с префиксом (не ломаем сигнатуру возврата)
                headers = dict(headers)
                for k, v in meta.items():
                    headers[f"x-validate-{k}"] = v
                if not ok:
                    continue  # отбрасываем неподходящее

                if dedup:
                    digest = meta["sha256"]
                    if digest in seen_hashes:
                        # дубликат — пропускаем
                        continue
                    seen_hashes.add(digest)

            out.append((name, content, headers))

        except Exception:
            # Best-effort: любые падения источников просто пропускаем
            continue

    return out

# Дополнительно: быстрая самопроверка — вернёт (name, ok_bool, http_content_type)
def selftest_sources() -> List[Tuple[str, bool, str]]:
    results = []
    for name, url in [
        ("goes19_geocolor_fd", _goes_geocolor("GOES19", "FD")),
        ("goes18_geocolor_fd", _goes_geocolor("GOES18", "FD")),
        ("goes18_conus_geocolor", _goes_geocolor("GOES18", "CONUS")),
        ("goes19_band02_fd", _goes_band("GOES19", 2)),
        ("goes18_band02_fd", _goes_band("GOES18", 2)),
        ("goes19_band08_fd", _goes_band("GOES19", 8)),
        ("goes18_band08_fd", _goes_band("GOES18", 8)),
        ("goes19_band13_fd", _goes_band("GOES19", 13)),
        ("goes18_band13_fd", _goes_band("GOES18", 13)),
         ("nasa_viirs_noaa20_truecolor",
         _worldview_snapshot_url("VIIRS_NOAA20_CorrectedReflectance_TrueColor", datetime.date.today)),
        ("nasa_viirs_snpp_truecolor",
         _worldview_snapshot_url("VIIRS_SNPP_CorrectedReflectance_TrueColor", datetime.date.today)),
        ("nasa_modis_terra_truecolor",
         _worldview_snapshot_url("MODIS_Terra_CorrectedReflectance_TrueColor", datetime.date.today)),
        ("nasa_modis_aqua_truecolor",
         _worldview_snapshot_url("MODIS_Aqua_CorrectedReflectance_TrueColor", datetime.date.today)),
    ]:
        try:
            content, headers = _fetch(url)
            ok = _is_jpeg(content, headers)
            results.append((name, ok, headers.get("content-type", "")))
        except Exception:
            results.append((name, False, ""))
    return results

def _validate_image(name: str,
                    content: bytes,
                    headers: Dict[str, str],
                    min_bytes: int = 10_000,
                    allowed_mime_prefixes: Iterable[str] = ("image/",)) -> Tuple[bool, Dict[str, str]]:
    """
    Проверка скачанного ресурса:
      - по сигнатуре байтов это картинка
      - разумный размер (не tiny-плейсхолдер)
      - заголовок Content-Type начинается с image/
    Возвращает (ok, meta), где meta содержит полезную диагностику.
    """
    meta: Dict[str, str] = {"name": name, "ok": "false"}
    size = len(content)
    meta["size_bytes"] = str(size)

    img_kind = _is_image_bytes(content)
    meta["img_kind"] = img_kind or "unknown"

    ctype = headers.get("content-type", "")
    meta["content_type"] = ctype

    # Простая проверка MIME
    mime_ok = any(ctype.startswith(p) for p in allowed_mime_prefixes)
    meta["mime_ok"] = "true" if mime_ok else "false"

    size_ok = size >= min_bytes
    meta["size_ok"] = "true" if size_ok else "false"

    sig_ok = bool(img_kind)
    meta["sig_ok"] = "true" if sig_ok else "false"

    # Хеш — для дедупликации и аудита
    digest = hashlib.sha256(content).hexdigest()
    meta["sha256"] = digest

    ok = sig_ok and size_ok and mime_ok
    meta["ok"] = "true" if ok else "false"
    return ok, meta

def validate_report(items: List[Tuple[str, bytes, Dict[str, str]]]) -> List[Dict[str, str]]:
    """
    Извлекает x-validate-* поля из headers для краткого аудита.
    """
    report: List[Dict[str, str]] = []
    for name, content, headers in items:
        row = {"name": name}
        for k, v in headers.items():
            if k.startswith("x-validate-"):
                row[k[len("x-validate-"):]] = v
        # если не было встроенной валидации — проведём сейчас
        if "ok" not in row:
            ok, meta = _validate_image(name, content, headers)
            row |= meta
        report.append(row)
    return report