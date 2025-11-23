#!/usr/bin/env python3
"""Build compressed IPA dictionary word list for kotoba-search."""

from __future__ import annotations

import csv
import datetime as dt
import gzip
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Iterable

ROOT_DIR = Path(__file__).resolve().parents[1]
PUBLIC_DIR = ROOT_DIR / "public"
WORDS_GZ = PUBLIC_DIR / "words.txt.gz"
COPYING_OUT = PUBLIC_DIR / "COPYING-ipadic.txt"
NOTICE_OUT = PUBLIC_DIR / "NOTICE.txt"
REPO_URL = "https://github.com/taku910/mecab.git"


def run_cmd(args: list[str]) -> None:
    subprocess.run(args, check=True)


def clone_repo(dest: Path) -> Path:
    print("Cloning mecab repository…")
    run_cmd(["git", "clone", "--depth", "1", REPO_URL, str(dest)])
    return dest / "mecab-ipadic"


KATAKANA_TO_HIRAGANA = {ordinal: ordinal - 0x60 for ordinal in range(ord("ァ"), ord("ヶ") + 1)}
ALLOWED_HIRAGANA = {chr(code) for code in range(ord("ぁ"), ord("ゟ"))} | {"ー"}


def katakana_to_hiragana(text: str) -> str:
    special = {
        "ヵ": "か",
        "ヶ": "け",
        "ヷ": "わ",
        "ヸ": "ゐ",
        "ヹ": "ゑ",
        "ヺ": "を",
        "ヴ": "ゔ",
    }
    result = []
    for ch in text:
        if ch in special:
            result.append(special[ch])
            continue
        ordinal = ord(ch)
        if ord("ァ") <= ordinal <= ord("ヶ"):
            result.append(chr(KATAKANA_TO_HIRAGANA[ordinal]))
        else:
            result.append(ch)
    return "".join(result)


def normalize_hiragana(text: str) -> str:
    converted = katakana_to_hiragana(text)
    return "".join(ch for ch in converted if ch in ALLOWED_HIRAGANA)


def iter_word_rows(ipadic_dir: Path) -> Iterable[list[str]]:
    for csv_path in ipadic_dir.rglob("*.csv"):
        if csv_path.suffix.lower() != ".csv":
            continue
        with csv_path.open(encoding="euc_jp", newline="") as handle:
            reader = csv.reader(handle)
            yield from reader


def extract_words(ipadic_dir: Path) -> list[str]:
    seen: set[str] = set()
    for row in iter_word_rows(ipadic_dir):
        if not row:
            continue
        reading = ""
        if len(row) > 11 and row[11]:
            reading = row[11].strip()
        elif row[0]:
            reading = row[0].strip()
        hira = normalize_hiragana(reading)
        if hira:
            seen.add(hira)
    return sorted(seen)


def write_wordlist(words: list[str]) -> None:
    PUBLIC_DIR.mkdir(parents=True, exist_ok=True)
    with gzip.open(WORDS_GZ, "wt", encoding="utf-8", newline="\n") as gz:
        for word in words:
            gz.write(word + "\n")


def write_notice(clone_dir: Path, ipadic_dir: Path) -> None:
    revision = subprocess.check_output(["git", "-C", str(clone_dir), "rev-parse", "HEAD"], text=True).strip()
    timestamp = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    shutil.copy(ipadic_dir / "COPYING", COPYING_OUT)
    NOTICE_OUT.write_text(
        (
            "This project bundles word data derived from the IPA dictionary (mecab-ipadic).\n\n"
            f"Source repository: {REPO_URL}\n"
            f"Source revision: {revision}\n"
            f"Build timestamp (UTC): {timestamp}\n\n"
            "The redistributed data is governed by the license terms in COPYING-ipadic.txt.\n"
        ),
        encoding="utf-8",
    )


def main() -> None:
    PUBLIC_DIR.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="kotoba-ipadic-") as tmp:
        clone_dir = Path(tmp) / "mecab"
        ipadic_dir = clone_repo(clone_dir)
        if not ipadic_dir.exists():
            print(f"Expected directory not found: {ipadic_dir}", file=sys.stderr)
            raise SystemExit(1)
        words = extract_words(ipadic_dir)
        write_wordlist(words)
        write_notice(clone_dir, ipadic_dir)
    print(f"Saved {len(words):,} entries to {WORDS_GZ}")


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as exc:
        print(f"Command failed: {exc}", file=sys.stderr)
        raise SystemExit(exc.returncode)
