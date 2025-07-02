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

dirname = pathlib.Path(dirname).resolve(True)
for path in dirname.rglob("*"):
    if not path.is_file() or path.is_symlink() or path.suffix in COMPRESSED_SUFFIXES:
        continue
    logging.info("Processing file %s", path)
    orig_size = path.stat().st_size
    logging.info("Original size is %s bytes", orig_size)

    with open(path, "rb") as f:
        gzipped = gzip.compress(f.read(), 9)
    gzipped_size = len(gzipped)
    logging.info("Gzipped size is %s", gzipped_size)
    if len(gzipped) >= orig_size:
        logging.info("Not writing gzipped output")
        continue
    gzipped_path = path.with_suffix(path.suffix + ".gz")
    with open(gzipped_path, write_mode) as f:
        f.write(gzipped)
    logging.info("Wrote gzipped output to %s", gzipped_path)

    result = subprocess.run(
        ["brotli", "-9", "--squash", *(["--force"] if clobber else []), "--", str(path)]
    )
    if result.returncode != 0:
        raise OSError("Brotli returned nonzero exit code: %s", result.returncode)
    logging.info("Ran brotli on the file")
