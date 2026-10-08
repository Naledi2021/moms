# Kitchen Workshop

Initial cabinet calculator for melamine, MDF and finished solid wood panels.

Run from this directory:

```sh
/workspace/.venvs/church_streamlit/bin/python -m streamlit run app.py --server.address 127.0.0.1 --server.port 8502 --server.headless true --browser.gatherUsageStats false
```

For a separate Python 3.12 environment, create a virtual environment and install requirements.txt. The current workspace already contains compatible dependencies.

Construction: full-height sides; two 100 mm finished-width top rails and bottom between sides. Internal width and height subtract twice the board thickness. Shelf width optionally subtracts total clearance. A 3 mm PG Bison Masonite back covers the full rear (external height by width), adds 3 mm to panel depth, and is priced separately per m² with the material waste allowance. Single-door width and height each subtract 4 mm total from external cabinet dimensions (600 × 720 mm gives a 596 × 716 mm door). Door dimensions recalculate when cabinet dimensions change; material, thickness and price are separately selectable. No automatic edging deductions, legs, worktop or sheet nesting. Solid wood uses finished-panel area pricing rather than rough timber volume. Prices default to zero and must be supplied by the business. Cost markup and tax are separate sequential calculations.

CSV cutting list and preliminary PDF estimate exports are included. No AI service is connected yet.

Door sizes include edging. Select 1 mm (default) or 2 mm and the edges receiving it. A finished 596 × 716 mm door edged all round cuts at 594 × 714 mm with 1 mm edging or 592 × 712 mm with 2 mm. CSV shows cut and finished dimensions and edges. Door panel costing uses cut area; edging cost stays in the manual allowance. Solid wood defaults to no applied edging. Carcass edging remains pending.

Carcass edging defaults: sides one long and one short edge; shelves and rails one long edge; bottom bases and drawer bases none. Carcass edging selectable at 1 or 2 mm. Long edge means the longer finished dimension; its edging reduces the shorter cut dimension. Two top rails are generated and edged on one long edge. Drawer base rules are registered but drawer components are not generated yet.

Supplier pricing: carcass, Masonite and door material each accept either R/m² or sheet/panel price with explicitly entered dimensions. Sheet pricing converts to an area rate; incomplete entries block the estimate instead of silently treating them as zero. It does not calculate purchasing sheet quantities or nesting.

## Regular online price checks

Run `python price_watch.py` using this project's Python environment for one check, or `python -u price_watch.py --loop --interval-hours 24` as a managed service for daily checks. The worker checks exact public Gelmar product SKUs and a Roco product page, and stores observations atomically in supplier_prices.json. A failed check retains the previous price and last successful timestamp, while exposing failure status. Ambiguous product offers, non-ZAR prices and ranges are rejected. Roco's current listing is a FROM price and is labelled accordingly. No prices are silently applied to quotes. VAT remains unverified.

The app shows source links, verification times and stale warnings after 7 days, and supports manual refresh. Live services stop when the cloud environment stops; restart the worker in future tasks. An always-on daily schedule has not been deployed. For unattended operation, deploy this worker on an always-on host with a persistent data volume and one daily scheduled invocation. The app button and worker share a lock to avoid simultaneous catalogue writes.

## Upload supplier updates

Open **Upload supplier price updates**, choose supplier, effective date and VAT basis, then upload CSV or .xlsx. Choose a worksheet for Excel and map SKU/code, product description, numeric price and price unit; optionally map panel dimensions and thickness. Download the CSV template for an example. Sheet prices require length and width. Units: sheet/panel, m2, each, set, metre. PDF lists are not automatically extracted; convert to a spreadsheet first. Decimal points are required without currency symbols or thousands separators. Limits: 10 MB upload, 5000 rows, 40 columns, 50 MB unpacked workbook.

Review the validated preview and click **Save supplier price update**. Data persists in data/supplier_updates.json, protected by a write lock and atomic replacement. All revisions are retained; duplicate identical imports are ignored. Updates merge by supplier and SKU, keeping products absent from a partial update. Effective dates govern current prices, so future updates do not replace current prices early. Supplier price data is separate from online observations.

Choose **Uploaded supplier prices** as a material price source to use saved sheet or m² prices in the estimate. VAT-inclusive prices are converted to excluding VAT using the recorded rate; unknown VAT basis blocks automatic use. Verify the selected product matches the job material/thickness. Uploaded individually priced hinge and mounting-plate products can be selected in the hardware section. Uploaded accessories priced each or per set can be selected with quantities for the whole job. Imported prices are converted to excluding VAT before job markup and tax; unknown VAT blocks the estimate. Select the included-plates option when mounting plates are bundled with hinges. Confirm exact model, compatibility and set contents. Supplier, SKU and effective date are itemised in the PDF. Keep data/ on a persistent volume when deploying, and back up/export the catalogue. No authentication or multi-user access control has been added to this prototype.

Run importer checks from this directory: `python -m unittest discover -s tests -v`.

Hardware source selection defaults to manual pricing. Supplier accessories are added separately from the manual Blum accessories table; do not enter the same item twice. Job-level accessory quantities are not multiplied by the cabinet count. Uploaded hardware selections are retained in the current session, not saved as a job yet.

## Saved jobs and quotations

Enter the job name, customer contact details, installation address, notes and status. Use **Save new customer job** at the end of the estimate. Open it later from **Saved customer jobs and quotations**. Saving while editing adds an immutable quotation revision; previous PDFs, cutting lists, diagrams and any generated video remain available for download. Data persists in data/jobs.json. Reopening uses the saved supplier catalogue snapshot; **Use current supplier prices for this job** explicitly refreshes it. Starting a new job clears the active editing state. Supplier price uploads are retained separately.

## Room-first design and presentation

Prepare and confirm a measured rectangular room layout before cabinet controls or placement become available. Add doors and windows by wall, offset, width, height and sill. Changing these inputs invalidates confirmation. Irregular room outlines, service points and automatic collision/door-swing checks are not implemented.

After confirmation, select **Full design**, add base cabinets, wardrobes, panels, worktops or appliance placeholders, then set their dimensions, positions and rotation. Up to 30 scene items are supported. The room floor can be shown. Wardrobes use a full top in the presentation model; their production construction rules are not yet configured. Items cannot extend outside the room bounds (small backing tolerance allowed). Check overlaps and all service/access clearances manually.

Views: **Lines** provides the room plan with placed units (or front/side/top for a single cabinet), **Sketch** an isometric drawing, **3D** an interactive model, and **Ultra** detailed interactive finish shading/wood-grain with optional illustrative hinges. Door-open preview is available. SVG drawings and standalone interactive HTML can be exported.

Generate silent 3–12 second turntable MP4 videos of the entire selected scene in square, portrait or landscape format. The local Pillow/FFmpeg renderer produces stylised design presentations; it is not a photorealistic renderer. Matching video settings are cached in data/videos/. Videos are captured in saved quotation revisions when already generated. FFmpeg and ffprobe must be installed on the server; both are available in this instance.

**Pricing and cutting lists currently cover the configured base cabinet and its identical-unit quantity, not all independently placed scene items.** Full-scene production costing and irregular/custom furniture construction remain to be developed. Preview colours and hinge positions do not change prices or specify drilling.

## Sketch and PDF reading

Upload PNG/JPG sketches or PDFs up to 15 MB and 5 pages before room confirmation. Local reading uses embedded PDF text or Tesseract OCR on images/scanned pages; Poppler tools render PDF pages. Review and correct the transcript. Extracted dimension groups preserve their labels/context and units. Explicitly confirm the annotation, units and dimension order before applying room dimensions or staging a design item. Staged items can only be placed after confirming the room layout. Dimensions are never inferred from pixel scale. Handwriting is unreliable with local OCR.

Optional AI handwriting reading sends page images to OpenAI only on an explicit Read document action. It uses a secure KITCHEN_VISION_API_KEY binding for api.openai.com; a requirement was saved to the environment draft. It is not configured or validated yet. Add the credential securely in environment settings, review/save and publish the changes, then test an actual handwritten plan. Never place keys in project files. Reviewed text and source filename are retained in saved jobs; raw uploads remain in session memory.
