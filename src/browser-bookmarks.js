#!/usr/bin/env osascript -l JavaScript

function walk(folder, path, isApp, result) {
  let pathStr = path.join("/");

  if (!isApp) {
    let itemCount = folder.bookmarkItems.url().length;
    for (let i = 0; i < itemCount; i++) {
      let item = {
        name: folder.bookmarkItems.at(i).name(),
        url: folder.bookmarkItems.at(i).url(),
        "__bm__": true
      };

      if (pathStr in result) {
        result[pathStr].push(item);
      } else {
        result[pathStr] = [item];
      }
    }
  }

  let childCount = folder.bookmarkFolders.name().length;
  for (let i = 0; i < childCount; i++) {
    let currDirName = folder.bookmarkFolders.at(i).name();

    walk(
      folder.bookmarkFolders.at(i),
      path.concat([currDirName]),
      false,
      result
    );
  }
}

function run(args) {
  let bundleId = args[0];
  let initPath = [];

  if (bundleId == "com.google.chrome") {
    initPath = ["Chrome"];
  } else if (bundleId == "com.microsoft.edgemac") {
    initPath = ["Edge"];
  } else {
    throw 'Invalid bundleId.';
  }

  app = Application(bundleId);
  app.includeStandardAdditions = true;

  var result = {};
  walk(app, initPath, true, result);

  console.log(JSON.stringify(result));
}
