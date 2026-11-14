"""Fetch the PostgreSQL server subset (bin, lib, share and root files) of the official EDB
Windows x64 binaries archive by HTTP range requests, verifying each entry against the archive's
central directory (local header name, sizes and CRC-32) before writing it.

pgAdmin 4, StackBuilder, doc and include entries are deliberately not downloaded: pgAdmin alone
is ~82% of the archive and is not needed to run an owned local cluster. Because the full archive
is not downloaded, this tool cannot produce a whole-archive SHA-256; it records the archive's
Content-Length, ETag, Last-Modified and central-directory SHA-256 plus a SHA-256 for every
extracted file, so another checkout can reproduce and compare the exact subset.

Usage: python fetch_server_subset.py <destination-dir> <manifest-json>
Python 3.12 standard library only. No global configuration is changed.
"""
import hashlib
import json
import os
import struct
import sys
import urllib.request
import zlib
from concurrent.futures import ThreadPoolExecutor

URL = "https://get.enterprisedb.com/postgresql/postgresql-18.7-1-windows-x64-binaries.zip"
EXPECTED_LENGTH = 389_515_503
INCLUDE_PREFIXES = ("pgsql/bin/", "pgsql/lib/", "pgsql/share/")
GAP_MERGE = 256 * 1024


def fetch(start: int, end: int) -> bytes:
    request = urllib.request.Request(URL, headers={"Range": f"bytes={start}-{end}"})
    for attempt in range(5):
        try:
            with urllib.request.urlopen(request, timeout=300) as response:
                if response.status != 206:
                    raise RuntimeError(f"expected 206, got {response.status}")
                data = response.read()
                if len(data) != end - start + 1:
                    raise RuntimeError("short range read")
                return data
        except Exception:  # noqa: BLE001 - retried, then re-raised
            if attempt == 4:
                raise
    raise AssertionError("unreachable")


def zip64_values(extra: bytes, usize: int, csize: int, offset: int):
    position = 0
    while position < len(extra):
        header_id, size = struct.unpack("<HH", extra[position:position + 4])
        body = extra[position + 4:position + 4 + size]
        if header_id == 1:
            values = list(struct.unpack("<" + "Q" * (size // 8), body[:size // 8 * 8]))
            index = 0
            if usize == 0xFFFFFFFF:
                usize = values[index]; index += 1
            if csize == 0xFFFFFFFF:
                csize = values[index]; index += 1
            if offset == 0xFFFFFFFF:
                offset = values[index]; index += 1
        position += 4 + size
    return usize, csize, offset


def main(destination: str, manifest_path: str) -> int:
    head = urllib.request.urlopen(urllib.request.Request(URL, method="HEAD"), timeout=60)
    total = int(head.headers["Content-Length"])
    if total != EXPECTED_LENGTH:
        raise SystemExit(f"archive length changed: {total} != {EXPECTED_LENGTH}")

    tail = fetch(total - 65536, total - 1)
    eocd = tail.rfind(b"PK\x05\x06")
    _, _, _, _, entries, cd_size, cd_offset, _ = struct.unpack("<IHHHHIIH", tail[eocd:eocd + 22])
    if cd_offset == 0xFFFFFFFF or entries == 0xFFFF:
        locator = tail.rfind(b"PK\x06\x07")
        z64_offset = struct.unpack("<Q", tail[locator + 8:locator + 16])[0]
        z64 = fetch(z64_offset, z64_offset + 55)
        entries, = struct.unpack("<Q", z64[32:40])
        cd_size, = struct.unpack("<Q", z64[40:48])
        cd_offset, = struct.unpack("<Q", z64[48:56])
    central = fetch(cd_offset, cd_offset + cd_size - 1)

    selected = []
    position = 0
    while position < len(central):
        (signature, _, _, flags, method, _, _, crc, csize, usize, name_len, extra_len, comment_len,
         _, _, _, offset) = struct.unpack("<IHHHHHHIIIHHHHHII", central[position:position + 46])
        if signature != 0x02014B50:
            raise SystemExit("bad central directory signature")
        name = central[position + 46:position + 46 + name_len].decode("utf-8")
        extra = central[position + 46 + name_len:position + 46 + name_len + extra_len]
        usize, csize, offset = zip64_values(extra, usize, csize, offset)
        position += 46 + name_len + extra_len + comment_len
        included = name.startswith(INCLUDE_PREFIXES) or (name.count("/") == 1 and not name.endswith("/"))
        if included and not name.endswith("/"):
            if flags & 0x1:
                raise SystemExit(f"encrypted entry {name}")
            if method not in (0, 8):
                raise SystemExit(f"unsupported compression {method} for {name}")
            selected.append({"name": name, "method": method, "crc": crc, "csize": csize,
                             "usize": usize, "offset": offset})

    # Local header (30 bytes + name + extra) precedes data; allow 1 KiB for the local extra field.
    selected.sort(key=lambda e: e["offset"])
    ranges = []
    for entry in selected:
        start, end = entry["offset"], entry["offset"] + 30 + 1024 + entry["csize"]
        if ranges and start - ranges[-1][1] <= GAP_MERGE:
            ranges[-1][1] = max(ranges[-1][1], end)
            ranges[-1][2].append(entry)
        else:
            ranges.append([start, end, [entry]])

    files = []

    def process(block):
        start, end, block_entries = block
        end = min(end, cd_offset - 1)
        data = fetch(start, end)
        results = []
        for entry in block_entries:
            local = entry["offset"] - start
            sig, _, _, _, _, _, _, _, _, name_len, extra_len = struct.unpack("<IHHHHHIIIHH", data[local:local + 30])
            if sig != 0x04034B50:
                raise SystemExit(f"bad local header for {entry['name']}")
            local_name = data[local + 30:local + 30 + name_len].decode("utf-8")
            if local_name != entry["name"]:
                raise SystemExit(f"local/central name mismatch {local_name} != {entry['name']}")
            data_start = local + 30 + name_len + extra_len
            compressed = data[data_start:data_start + entry["csize"]]
            if len(compressed) != entry["csize"]:
                raise SystemExit(f"truncated data for {entry['name']}")
            content = compressed if entry["method"] == 0 else zlib.decompress(compressed, -15)
            if len(content) != entry["usize"] or (zlib.crc32(content) & 0xFFFFFFFF) != entry["crc"]:
                raise SystemExit(f"size/CRC mismatch for {entry['name']}")
            relative = entry["name"][len("pgsql/"):]
            target = os.path.normpath(os.path.join(destination, relative))
            if not target.startswith(os.path.normpath(destination) + os.sep):
                raise SystemExit(f"unsafe path {entry['name']}")
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with open(target, "wb") as handle:
                handle.write(content)
            results.append({"path": relative.replace("\\", "/"), "bytes": len(content),
                            "crc32": f"{entry['crc']:08x}", "sha256": hashlib.sha256(content).hexdigest()})
        return results

    with ThreadPoolExecutor(max_workers=4) as pool:
        for result in pool.map(process, ranges):
            files.extend(result)

    files.sort(key=lambda f: f["path"])
    manifest = {
        "source_url": URL,
        "official_route": "https://www.postgresql.org/download/windows/ -> https://www.enterprisedb.com/download-postgresql-binaries",
        "archive_content_length": total,
        "archive_etag": head.headers.get("ETag"),
        "archive_last_modified": head.headers.get("Last-Modified"),
        "central_directory_offset": cd_offset,
        "central_directory_size": cd_size,
        "central_directory_sha256": hashlib.sha256(central).hexdigest(),
        "archive_entries": entries,
        "included_prefixes": list(INCLUDE_PREFIXES) + ["pgsql/<root files>"],
        "extracted_file_count": len(files),
        "extracted_total_bytes": sum(f["bytes"] for f in files),
        "subset_manifest_sha256": hashlib.sha256(
            "\n".join(f"{f['sha256']}  {f['path']}" for f in files).encode()).hexdigest(),
        "whole_archive_sha256": "not computed: full archive (pgAdmin 4 ~82%) intentionally not downloaded",
        "files": files,
    }
    with open(manifest_path, "w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=1)
    print(json.dumps({k: v for k, v in manifest.items() if k != "files"}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
