#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "brotli",
# ]
# ///
import brotli

import argparse
import logging
import pathlib
import zlib

CHUNK_SIZE = 1024 * 1024
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


def streaming_compress(
    orig_path: pathlib.Path, out_path: pathlib.Path, compress_chunk, finish
) -> None:
    orig_size = orig_path.stat().st_size
    written_size = 0
    with open(orig_path, "rb") as orig_file:
        with open(out_path, write_mode) as out_file:
            while True:
                chunk = orig_file.read(CHUNK_SIZE)
                if chunk:
                    written_size += out_file.write(compress_chunk(chunk))
                    if written_size >= orig_size:
                        break
                else:
                    written_size += out_file.write(finish())
                    break
    if written_size >= orig_size:
        logging.info(
            "Compressed size not less than original size %s; not saving",
            orig_size,
        )
        out_path.unlink()
    else:
        logging.info(
            "Compressed to %s bytes (%.1f%%, %s)",
            written_size,
            written_size / orig_size * 100,
            written_size - orig_size,
        )


dirname = pathlib.Path(dirname).resolve(True)
for path in dirname.rglob("*"):
    if not path.is_file() or path.is_symlink() or path.suffix in COMPRESSED_SUFFIXES:
        continue
    logging.info("Processing file %s", path)

    logging.info("Compressing with gzip")
    # Documented to write gzip-compatible output with this wbits value
    gzip_compressor = zlib.compressobj(9, wbits=zlib.MAX_WBITS + 16)
    streaming_compress(
        path,
        path.with_suffix(path.suffix + ".gz"),
        gzip_compressor.compress,
        gzip_compressor.flush,
    )

    logging.info("Compressing with brotli")
    brotli_compressor = brotli.Compressor(quality=11)
    streaming_compress(
        path,
        path.with_suffix(path.suffix + ".br"),
        brotli_compressor.process,
        brotli_compressor.finish,
    )
