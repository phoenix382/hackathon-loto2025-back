#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import datetime
import hashlib
import imghdr
from typing import Dict, List, Tuple, Iterable

import requests


DEFAULT_TIMEOUT = 8
UA = "loto-rng/1.1 (+entropy images; contact: none)"


def _fetch(url: str) -> Tuple[bytes, Dict[str, str]]:
    resp = requests.get(url, timeout=DEFAULT_TIMEOUT, headers={"User-Agent": UA})
    resp.raise_for_status()
    headers = {k.lower(): v for k, v in resp.headers.items()}
    return resp.content, headers


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


def _is_image_bytes(b: bytes) -> str:
    """
    Возвращает формат ('jpeg', 'png', 'gif', 'webp', ...) если распознан,
    иначе пустую строку.
    """
    kind = imghdr.what(None, h=b)
    return kind or ""


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


def _sources(today: datetime.date) -> List[Tuple[str, str]]:
    """
    Подборка источников, дающих варьирующийся во времени контент (проверяемые факты):
      - GOES-16/18 (GEOCOLOR + разные каналы)
      - Himawari-8/9 (NICT true color)
      - SDO (Солнце, несколько длин волн)
      - NASA Worldview (VIIRS/MODIS, разные платформы)
    Все — без ключей и с устойчивых публичных хостов.
    """
    urls: List[Tuple[str, str]] = [
        # NOAA/NESDIS STAR CDN — GOES Full Disk (устойчивый публичный CDN)
        ("goes16_geocolor_fd", "https://cdn.star.nesdis.noaa.gov/GOES16/ABI/FD/GEOCOLOR/latest.jpg"),
        ("goes18_geocolor_fd", "https://cdn.star.nesdis.noaa.gov/GOES18/ABI/FD/GEOCOLOR/latest.jpg"),
        ("goes16_band02_fd",   "https://cdn.star.nesdis.noaa.gov/GOES16/ABI/FD/Channel/02/latest.jpg"),  # Red Vis
        ("goes18_band02_fd",   "https://cdn.star.nesdis.noaa.gov/GOES18/ABI/FD/Channel/02/latest.jpg"),
        ("goes16_band08_fd",   "https://cdn.star.nesdis.noaa.gov/GOES16/ABI/FD/Channel/08/latest.jpg"),  # WV 6.2µm
        ("goes18_band08_fd",   "https://cdn.star.nesdis.noaa.gov/GOES18/ABI/FD/Channel/08/latest.jpg"),
        # Региональные композиции (обычно есть; если нет — просто пропустим)
        ("goes16_conus_geocolor", "https://cdn.star.nesdis.noaa.gov/GOES16/ABI/CONUS/GEOCOLOR/latest.jpg"),
        ("goes18_pacus_geocolor", "https://cdn.star.nesdis.noaa.gov/GOES18/ABI/PACUS/GEOCOLOR/latest.jpg"),

        # Himawari-8/9 true color (NICT публичное зеркало)
        ("himawari_geocolor_fd", "https://himawari8.nict.go.jp/img/D531106/2d/550/latest.jpg"),

        # NASA Worldview (GIBS) — разные платформы/датчики, TrueColor, текущая дата
        ("nasa_viirs_noaa20_truecolor",
         _worldview_snapshot_url("VIIRS_NOAA20_CorrectedReflectance_TrueColor", today)),
        ("nasa_viirs_snpp_truecolor",
         _worldview_snapshot_url("VIIRS_SNPP_CorrectedReflectance_TrueColor", today)),
        ("nasa_modis_terra_truecolor",
         _worldview_snapshot_url("MODIS_Terra_CorrectedReflectance_TrueColor", today)),
        ("nasa_modis_aqua_truecolor",
         _worldview_snapshot_url("MODIS_Aqua_CorrectedReflectance_TrueColor", today)),
    ]
    return urls


def get_meteo_sat_images(validate: bool = True,
                         min_bytes: int = 10_000,
                         dedup: bool = True) -> List[Tuple[str, bytes, Dict[str, str]]]:
    """
    Скачивает набор разнородных космических/метео-изображений, пригодных для энтропии.
    По умолчанию проводит валидацию и дедупликацию. Возвращает
    [(source_name, image_bytes, response_headers), ...]
    """
    today = datetime.date.today()
    urls = _sources(today)

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


# Если хотите быстрый отчёт по валидации без изменения внешней логики:
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