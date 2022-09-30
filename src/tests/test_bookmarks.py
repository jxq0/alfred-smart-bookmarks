#!/usr/bin/env python3
import unittest
import os
from smart_bookmarks import BookmarkRepo
from pathlib import Path
import sys
import logging
import logging.handlers

import mistletoe
from mistletoe import Document


class TestBookmark(unittest.TestCase):
    def config_logger(self):
        logger = logging.getLogger("smart_bookmarks")

        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler(sys.stderr)
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            "[%(asctime)s][%(filename)s:%(lineno)d][%(levelname)s] %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    def setUp(self):
        self.config_logger()

    def test_markdown(self):
        file_path = str(Path("tests/test-bookmarks.md").resolve())
        repo = BookmarkRepo(file_path, "tests")
        bookmarks = repo.read_markdown_file(file_path)
        print(bookmarks)

    def test_misltetoe(self):
        file_path = str(Path("tests/test-bookmarks.md").resolve())
        with open(file_path, "r") as fd:
            doc = Document(fd)
            print(doc.children[1].children[0].target)
            print(doc.children[1].children[0].children[0].content)

    def test_update_store(self):
        file_path = str(Path("tests/test-bookmarks.md").resolve())
        repo = BookmarkRepo(file_path, "tests")
        repo.update_store()


if __name__ == "__main__":

    unittest.main()
