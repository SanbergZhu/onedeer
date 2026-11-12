# ONEDeer website

A dependency-free, responsive English website based on the supplied ONEDeer service catalog.

Open index.html directly, or run `python3 -m http.server 8080` in this directory and visit http://localhost:8080.

Contents: five service descriptions, engagement process, pricing, progressive commission estimator, terms, FAQ and email contact. Contact opens the visitor's mail application; there is no form submission backend.

The PDF's unfinished response-time placeholder has been omitted. Compliance content describes coordination and document review, not certification. Prices are reproduced from the supplied catalog and should be reviewed before publication.

This is a standalone replacement homepage. Original template demonstration pages and unrelated welding product images are not included. LICENSE.txt is retained from the provided source repository.

## Product directory

`search.html` loads `data/products.json`. Search supports English/Chinese product keywords, city names, supplier-location filtering, price sorting and incremental results. Run the HTTP server above to preview this page; opening it through `file://` cannot load JSON reliably.

The directory is a manually refreshed snapshot, not a live connection. Only sanitized product titles, city-level supplier locations and widened CNY price bounds are published. Order numbers, customer records, barcodes, supplier company/contact details, Unit Cost, source-sheet links and original price fields are not included in the public dataset.

The agreed price source is **Unit Price (CNY)** from the **Products** tab, not Unit Cost. Bounds are 85% and 115% of the recorded unit price, rounded outward to two decimals. Slash-separated price options use the lowest and highest values. Identical product titles at the same recorded location are grouped; their displayed range covers all priced variants. A missing price/location is shown as available on request. FOB terms still need confirmation for a quotation.

### Refresh on request

Ask Codex to “同步产品目录” and provide/retain access to the private source spreadsheet. It should read current metadata and the Products headers, retrieve only the necessary columns into a private working file outside this repository, regenerate the public snapshot, check the result, and push only the sanitized snapshot to GitHub.

For a manual CSV refresh, export the **Products** tab to a file **outside the repository** and run:

```sh
python3 scripts/build_catalog.py --input /absolute/private/path/products-source.csv --output data/products.json
python3 -m unittest discover -s tests
```

The builder also accepts connector range JSON (`values` with the original header row). Do not copy the raw CSV/JSON into the website or commit it. Review missing fields and product grouping after every refresh, then commit only `data/products.json`. The original Sheet’s sharing settings do not need to change. There is no scheduled sync or service-account credential.
