#!/usr/bin/python3
from multiprocessing import Process
import subprocess
import time
import sys
import os
import fcntl
import json
import logging
from pathlib import Path
from smart_bookmarks import (
    config_logger,
    logger,
    bookmark_decode,
    BookmarkEncoder,
)


def load_browser_bookmarks(browser):
    res = subprocess.run(
        ["./browser-bookmarks.js", browser], capture_output=True, text=True
    )

    if res.returncode == 0:
        return json.loads(res.stderr, object_hook=bookmark_decode)
    else:
        return None


def main():
    config_logger()
    logger.info("load browser bookmarks")

    use_chrome = os.getenv("use_chrome") == "1"
    use_edge = os.getenv("use_edge") == "1"
    browser_store = {}

    if use_chrome:
        ret = load_browser_bookmarks("com.google.chrome")
        if ret:
            browser_store["com.google.chrome"] = ret

    browser_store_path = Path(os.getenv("alfred_workflow_cache")).joinpath(
        "browser_bookmarks.json"
    )

    browser_store_lock = (
        Path(os.getenv("alfred_workflow_cache"))
        .joinpath("browser_bookmarks.lock")
        .open("w")
    )

    fcntl.flock(browser_store_lock, fcntl.LOCK_EX)

    json.dump(
        browser_store,
        browser_store_path.open("w"),
        cls=BookmarkEncoder,
        ensure_ascii=False,
    )

    fcntl.flock(browser_store_lock, fcntl.LOCK_UN)


if __name__ == "__main__":
    main()
