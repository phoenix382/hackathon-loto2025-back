import hashlib
import os
import time
from typing import List, Tuple
from app.parsers.solar_parser import get_solar_images


from .logging import StageLogger


def _bits_from_bytes(data: bytes) -> str:
    return ''.join(f'{b:08b}' for b in data)


def _hash_to_bits(*chunks: bytes, digest: str = 'sha256') -> str:
    h = hashlib.new(digest)
    for c in chunks:
        h.update(c)
    return _bits_from_bytes(h.digest())

def collect_entropy(sources: List[str], min_bits: int, logger: StageLogger) -> str:
    """Collects entropy bits from configured sources until min_bits bits are produced.

    Sources:
      - 'news': uses news_parser.get_rss_news
      - 'weather': uses weather_parser.OpenMeteoWeatherParser
      - 'meteo_sat': uses meteo_sat_parser.get_meteo_sat_images (GOES/Himawari/VIIRS)
      - 'os': uses os.urandom
      - 'time': samples perf_counter jitter
    """
    bits: List[str] = []
    logger.stage("entropy:start", {"sources": sources, "min_bits": min_bits})

    if 'news' in sources:
        try:
            logger.stage("entropy:news:fetch", {})
            # Lazy import to avoid hard dependency when not used
            from app.parsers.news_parser import get_rss_news
            news = get_rss_news(num_news=5)
            for item in news:
                payload = (
                    (item.get('source', '') + '|' + item.get('title', '') + '|' +
                     item.get('author', '') + '|' + item.get('date', '') + '|' + item.get('link', '')).encode('utf-8')
                )
                bits.append(_hash_to_bits(payload))
        except Exception as e:
            logger.stage("entropy:news:error", {"error": str(e)})

    if 'weather' in sources:
        try:
            logger.stage("entropy:weather:fetch", {})
            from app.parsers.weather_parser import OpenMeteoWeatherParser  # local module
            wp = OpenMeteoWeatherParser()
            cont = wp.get_continent_weather()
            for k, v in cont.items():
                payload = (k + '|' + str(sorted(v.items()))).encode('utf-8')
                bits.append(_hash_to_bits(payload))
        except Exception as e:
            logger.stage("entropy:weather:error", {"error": str(e)})

    if 'solar' in sources:
        try:
            logger.stage("entropy:solar:fetch", {})
            images = get_solar_images()
            for name, content, headers in images:
                # Mix bytes with HTTP metadata to diversify payload
                meta = (headers.get('last-modified', '') + '|' + headers.get('etag', '')).encode('utf-8')
                bits.append(_hash_to_bits(name.encode('utf-8'), meta, content))
        except Exception as e:
            logger.stage("entropy:solar:error", {"error": str(e)})

    if 'meteo_sat' in sources:
        try:
            logger.stage("entropy:meteo_sat:fetch", {})
            from app.parsers.meteo_sat_parser import get_meteo_sat_images
            images = get_meteo_sat_images()
            for name, content, headers in images:
                # Combine vantage/sensor id + HTTP metadata + raw bytes
                meta = (headers.get('last-modified', '') + '|' + headers.get('etag', '')).encode('utf-8')
                bits.append(_hash_to_bits(name.encode('utf-8'), meta, content))
        except Exception as e:
            logger.stage("entropy:meteo_sat:error", {"error": str(e)})

    if 'os' in sources:
        logger.stage("entropy:os:start", {})
        for _ in range(16):  # 16*32 bytes => 4096 bits potential after hashing
            rnd = os.urandom(32)
            bits.append(_hash_to_bits(rnd))

    if 'time' in sources:
        logger.stage("entropy:time:start", {})
        # Capture perf_counter jitter and hash batches
        accum: List[bytes] = []
        for _ in range(4096):
            t = time.perf_counter_ns()
            accum.append(t.to_bytes(8, 'little'))
        bits.append(_hash_to_bits(b''.join(accum)))

    # Concatenate and extend to minimum length
    bitstream = ''.join(bits)
    logger.stage("entropy:collected", {"bits": len(bitstream)})

    if len(bitstream) < min_bits:
        # expand deterministically by hashing cascading blocks
        logger.stage("entropy:expand", {"from_bits": len(bitstream)})
        seed = bitstream.encode('ascii')
        while len(bitstream) < min_bits:
            seed = hashlib.sha256(seed).digest()
            bitstream += _bits_from_bytes(seed)
        logger.stage("entropy:expanded", {"bits": len(bitstream)})

    return bitstream[:min_bits]


def von_neumann_extractor(bits: str, logger: StageLogger) -> str:
    logger.stage("whitening:von_neumann:start", {"in_bits": len(bits)})
    out = []
    it = iter(range(0, len(bits) - 1, 2))
    for i in it:
        a, b = bits[i], bits[i + 1]
        if a == b:
            continue
        out.append('1' if a == '0' and b == '1' else '0')
    res = ''.join(out)
    logger.stage("whitening:von_neumann:done", {"out_bits": len(res)})
    return res


def derive_seed_and_commitment(bits: str, logger: StageLogger) -> Tuple[bytes, str]:
    logger.stage("seed:start", {"bits": len(bits)})
    digest = hashlib.sha256(bits.encode('ascii')).digest()
    commit = hashlib.sha256(digest + b'|commit_v1').hexdigest()
    logger.stage("seed:done", {"seed_bytes": len(digest), "fingerprint": commit})
    return digest, commit
