#!/usr/bin/python3
import sys
import os
from orgparse import load, loads
import re
from collections import defaultdict
import json
import logging
import logging.handlers
import hashlib
from pathlib import Path, PurePath
import pinyin
import subprocess
from timeit import default_timer as timer
import time
import fcntl

logger = logging.getLogger(__name__)


def config_logger():
    logger.setLevel(logging.INFO)
    handler = logging.handlers.RotatingFileHandler(
        Path(os.getenv("alfred_workflow_cache")).joinpath("smart_bookmarks.log")
    )
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        "[%(asctime)s][%(filename)s:%(lineno)d][%(levelname)s] %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)


class BookmarkRepo:
    def __init__(self, file_list_str, store_dir):
        self.file_list = file_list_str.split()
        self.store = {}
        self.browser_store_path = Path(
            os.getenv("alfred_workflow_cache")
        ).joinpath("browser_bookmarks.json")
        self.browser_store = {}
        self.browser_store_lock = (
            Path(os.getenv("alfred_workflow_cache"))
            .joinpath("browser_bookmarks.lock")
            .open("w")
        )

        self.md5sum = {}
        for org_file in self.file_list:
            self.md5sum[org_file] = hashlib.md5(
                open(org_file, "rb").read()
            ).hexdigest()

        self.store_dir = Path(store_dir)
        self.store_file = self.store_dir.joinpath("bookmarks.json")

        if not self.store_dir.exists():
            self.store_dir.mkdir(parents=True, exist_ok=True)

        if self.store_file.exists():
            self.store = json.load(
                self.store_file.open("r"), object_hook=bookmark_decode
            )

    def update_store(self):
        need_save_store = False

        # rm old store for files not in file_list
        files_to_rm = []
        for k in self.store:
            if k not in self.file_list:
                files_to_rm.append(k)
                need_save_store = True
                logger.info("%s not in file_list", k)

        for k in files_to_rm:
            self.store.pop(k)

        for org_file in self.file_list:
            need_reload = False

            if org_file in self.store:
                if self.store[org_file]["md5sum"] != self.md5sum[org_file]:
                    logger.info("file %s changed", org_file)
                    need_reload = True
            else:
                need_reload = True

            if need_reload:
                need_save_store = True
                self.store[org_file] = {
                    "data": self.read_org_file(org_file),
                    "md5sum": self.md5sum[org_file],
                }
            else:
                logger.info("file %s same, using cache", org_file)

        logger.debug("store:%s", self.store)
        if need_save_store:
            json.dump(
                self.store, self.store_file.open("w"), cls=BookmarkEncoder
            )

    def walk_node(self, node, bookmarks, headings):
        current_heading = ""
        if not node.is_root():
            current_heading = node.get_heading()
        else:
            current_heading = "/"

        heading_path = str(Path(*(headings + [current_heading])))

        for line in node.get_body(format="raw").split("\n"):
            for b in self.filter_bookmark(line):
                bookmarks[heading_path].append(b)

        for i in node.children:
            self.walk_node(i, bookmarks, headings + [current_heading])

    def read_org_file(self, file_path):
        bookmarks = defaultdict(list)

        root = load(file_path)
        self.walk_node(root, bookmarks, [])

        return bookmarks

    def filter_bookmark(self, line):
        bookmarks = []
        for m in re.findall(r"\[\[(\S*)\]\[(.*)\]\]", line):
            name = m[1]
            url = m[0]
            bookmark = Bookmark(name, url)
            bookmarks.append(bookmark)

        return bookmarks

    def match_query(self, b, query):
        if query in b.heading_path.lower():
            return True

        if query in pinyin.get(b.heading_path, format="strip"):
            return True

        if query in b.bookmark.url or query in b.bookmark.name.lower():
            return True

        if query in pinyin.get(b.bookmark.name, format="strip"):
            return True

        return False

    def load_browser_bookmarks(self):
        fcntl.flock(self.browser_store_lock, fcntl.LOCK_EX)
        self.browser_store = json.load(
            self.browser_store_path.open("r"), object_hook=bookmark_decode
        )
        fcntl.flock(self.browser_store_lock, fcntl.LOCK_UN)

        return

    def fetch(self, query_list, use_chrome, use_edge):
        self.update_store()

        self.load_browser_bookmarks()

        whole_list = []
        for v in self.store.values():
            for heading_path, bookmarks in v["data"].items():
                whole_list.append((heading_path, bookmarks))

        for v in self.browser_store.values():
            for heading_path, bookmarks in v.items():
                logger.debug(
                    "browser list: heading_path:%s, bookmarks:%s",
                    heading_path,
                    bookmarks,
                )
                whole_list.append((heading_path, bookmarks))

        result_list = []

        for heading_path, bookmarks in whole_list:
            for b in bookmarks:
                pathed_bookmark = PathedBookmark(heading_path, b)

                matched = True
                for query in query_list:
                    if not self.match_query(pathed_bookmark, query):
                        matched = False
                        break

                if matched:
                    result_list.append(pathed_bookmark)

        for i in result_list:
            logger.debug(
                "heading_path:%s, bookmark:%s", i.heading_path, i.bookmark
            )

        self.to_alfred(result_list)

    def to_alfred(self, result_list):
        items = []
        for b in result_list:
            item = {
                "type": "default",
                "title": b.title(),
                "subtitle": b.subtitle(),
                "uid": b.bookmark.url,
                "variables": {"url": b.bookmark.url},
            }

            items.append(item)

        result = {"items": items}
        print(json.dumps(result, ensure_ascii=False))


class PathedBookmark:
    def __init__(self, heading_path, bookmark):
        self.heading_path = heading_path
        self.bookmark = bookmark

    def title(self):
        return self.bookmark.name

    def subtitle(self):
        return "[%s] %s" % (self.heading_path, self.bookmark.url)


class Bookmark:
    def __init__(self, name, url):
        self.name = name
        self.url = url

    def __str__(self):
        return "Bookmark:" + self.name

    def __repr__(self):
        return self.__str__()


class BookmarkEncoder(json.JSONEncoder):
    def default(self, o):
        return {**(o.__dict__), "__bm__": True}


def bookmark_decode(d):
    if "__bm__" in d:
        return Bookmark(d["name"], d["url"])
    else:
        return d


def main():
    start = timer()
    config_logger()

    query = ""
    if len(sys.argv) > 1:
        query = list(map(str.lower, sys.argv[1:]))

    use_chrome = os.getenv("use_chrome") == "1"
    use_edge = os.getenv("use_edge") == "1"
    logger.info(
        "query:%s, use_chrome: %s, use_edge: %s", query, use_chrome, use_edge
    )

    file_list = os.getenv("org_files")

    repo = BookmarkRepo(file_list, os.getenv("alfred_workflow_cache"))
    repo.fetch(query, use_chrome, use_edge)

    end = timer()
    logger.info("done %.3f", end - start)


if __name__ == "__main__":
    main()
