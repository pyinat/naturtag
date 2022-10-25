# History

## 0.8.0 (Unreleased)
* Add tab for basic observation details
* When an observation is selected, show a summary of basic observation details on main screen
* Display observation count and leaf taxon count on taxon info cards
* In refresh mode, check for taxonomy changes and update tags with the new taxon (1:1 changes only)
* Add support for alternate XMP sidecar path format, if it already exists (`basename.ext.xmp` instead of `basename.xmp`)

## 0.7.0 (2022-07-29)
* Rebuilt UI from scratch using Qt
* Build local taxon and observation database for partial online access and better performance
* Build local taxon text search database for fully offline (and much faster) taxon autocomplete
* Add CLI taxon autocomplete search
* Add fullscreen image viewer
* Add full bi-directional conversion between iNat API results and Darwin Core XMP metadata
* Add recent and favorite image directories
* Build Windows installer, macOS `.dmg`, and PyInstaller artifacts for all platforms
* Add GPS metadata
* Many performance improvements, bugfixes, etc.

## 0.6.0 (2021-06-16)
* Improved image drag-and-drop, and support recursively adding images from subdirectories
* Initial packaging with PyInstaller
* Add tab for user-observed taxa
* CLI improvements and options
* Add more data models and move these to pyinaturalist
* Add caching improvements and merge into requests-cache
* Add progress bar for loading taxon data and images
* Multithreading for better performance with loading taxon data and images
* Update to Kivy 2
* Improvements for docs, CI/project config, bugfixes, etc.

## 0.5.0 (2020-06-03)
* Add a full taxon search with filters and search results tab
* Add tabs for recently viewed, frequently, viewed, and favorite taxa
* Add context menus for local images
* Add keyboard shortcuts
* Add a thumbnail atlas
* Add a Taxon data model
* Performance improvements, bugfixes, etc.

## 0.4.0 (2020-05-25)
* Add scrollable list of taxon children and ancestors
* Add caching for API requests and thumbnails
* UI cleanup, bugfixes, docs

## 0.3.0 (2020-05-24)
* Add a taxon info display
* Add a basic taxon name search with autocomplete

## 0.2.0 (2020-05-19)
* Add a basic GUI made with Kivy

## 0.1.0 (2020-05-14)
* Initial release; CLI tool with basic tagging functionality
