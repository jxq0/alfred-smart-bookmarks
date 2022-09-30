#!/bin/bash

if [ -f "alfred-smart-bookmarks.alfredworkflow" ]; then
    echo "rm old file"
    rm alfred-smart-bookmarks.alfredworkflow
fi

cd src/

zip -r ../alfred-smart-bookmarks.alfredworkflow * -x "__pycache__*" "*/__pycache__*"
