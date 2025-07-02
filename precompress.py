#!/usr/bin/env python3
import argparse
import gzip
import logging
import pathlib
import subprocess

COMPRESSED_SUFFIXES = {".gz", ".br"}

logging.basicConfig(level=logging.INFO)

parser = argparse.ArgumentParser(
    prog="precompress",
    description="Precompress files to be efficiently served over the web",
)
parser.add_argument("dirname")
parser.add_argument(
    "--clobber",
    action=argparse.BooleanOptionalAction,
    help="whether to silently overwrite existing .gz and .br files (default: no)",
)
args = parser.parse_args()
dirname, clobber = args.dirname, args.clobber

write_mode = "wb" if clobber else "xb"


def compress(
    path: pathlib.Path, compress_fn, name: str, compressed_suffix: str, orig_size
) -> None:
    compressed = compress_fn(path)
    compressed_size = len(compressed)
    logging.info("%s-compressed size is %s", name, compressed_size)

    if compressed_size >= orig_size:
        logging.info("Not writing %s-compressed output", name)
        return

    compressed_path = path.with_suffix(path.suffix + compressed_suffix)
    with open(compressed_path, write_mode) as f:
        f.write(compressed)
    logging.info("Wrote %s-compressed output to %s", name, compressed_path)


def gzip_compress(path):
    with open(path, "rb") as f:
        return gzip.compress(f.read(), 9)


def brotli_compress(path):
    result = subprocess.run(
        [
            "brotli",
            "-9",
            "--stdout",
            *(["--force"] if clobber else []),
            "--",
            str(path),
        ],
        capture_output=True,
    )
    if result.returncode != 0:
        raise RuntimeError("brotli returned nonzero exit code")
    return result.stdout


dirname = pathlib.Path(dirname).resolve(True)
for path in dirname.rglob("*"):
    if not path.is_file() or path.is_symlink() or path.suffix in COMPRESSED_SUFFIXES:
        continue
    logging.info("Processing file %s", path)
    orig_size = path.stat().st_size
    logging.info("Original size is %s bytes", orig_size)

    compress(path, gzip_compress, "gzip", ".gz", orig_size)
    compress(path, brotli_compress, "brotli", ".br", orig_size)
