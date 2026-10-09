# Kitchen Workshop

## Interactive 2D designer milestone

The **Full design** view now includes a locally served Streamlit v1 component
with an SVG canvas. There are no CDN, JavaScript package or new Python dependency
requirements. Click to select, drag to move, rotate 90° or delete after confirmation.
Arrow keys move by 10 mm (Shift: 1 mm). Changes are sent only when a gesture ends;
Python checks the current scene fingerprint and validates every mutation. A stale
event is rejected rather than overwriting a newer edit. Canvas events use 0.001 mm
precision; numerical forms retain entered dimensions and coordinates.

Use the precise editor to change width, depth, height, elevation, XY position and
rotation, or place a unit against a named wall using an exact offset. Wall placement
turns cabinet fronts into the room. Optional snapping has a 20 mm tolerance, aligning
footprint bounds with walls and neighbouring units sharing a span and elevation.
For arbitrary rotations, snapping uses axis-aligned footprint bounds; collision
checks use the actual rotated rectangle with a separating-axis test. Touching edges
are permitted. Cabinet collisions also require overlapping vertical extents, so wall
units can sit above base units.

The catalogue keeps existing base units and adds Wall, Corner and Tall categories.
New entries are single/double wall cabinets, a rectangular **blind corner base**,
tall pantry and tall appliance housing. Elevation is adjustable. L-shaped and diagonal
corner cabinets, custom room polygons, service fixtures and arbitrary curved shapes
are not supported. These new entries are 2D footprints with placeholder volumes
in existing 3D views; no new 3D renderer or production costing was added.

Opening warnings use a door keep-clear strip extending inward by the opening width
(up to 1000 mm), or a 100 mm strip at a window's measured sill and height. This
approximation does not know hinge side, opening direction, actual door swing or
required installation clearance. Invalid units remain repairable in the table and
do not hide valid units. Plan SVG exports now use the authoritative unit footprints,
not the panel geometry of the 3D presentation.

**Approve and lock layout** is available after units are valid and no collision or
opening warnings remain. Approval freezes a deep copy of room dimensions, openings
and all unit rows with a fingerprint and timestamp. Room controls, measurement
imports, placement table, canvas mutations and AI application are blocked while
locked. To revise, explicitly check **I intend to revise this approved layout** and
click **Unlock approved layout**. Save a quotation revision to persist the lock.
Old revisions open without migration, and previous approved revisions remain intact.
This is an accidental-edit guard, not role-based authorisation or a legally binding
approval signature. Users with app access can deliberately unlock a layout.

The AI assistant may suggest optional wall/offset or XY/rotation/elevation values.
All proposals require explicit user application, geometry validation and a collision
check; a conflicting batch is rejected completely. AI can answer questions about
approved designs but cannot apply changes while locked. Live requests still require
an OpenAI API key and billing. Service integration tests use simulated responses.

Saving jobs retains exact room geometry, openings, placements and approval data.
Viewing the single-cabinet presentation no longer discards the full design on save.
**Export 2D design and approval JSON** is an additional portable backup; job-history
exports remain the complete quotation archive. **Restore a downloaded job history**
restores a complete exported job archive, preserving IDs, revisions and approvals;
conflicting revisions are rejected and identical imports do nothing. The separate
2D-only scene export does not support re-import in this milestone. Free Streamlit storage is still temporary: export important history and
supplier prices before a redeployment.

Validation: `python -m unittest discover -s tests -v`. Browser checks require
Playwright plus Chromium and run against a separately started local app; those
are development-only tools. The component uses the standard Streamlit message
protocol and supported iframe bridge. Streamlit reruns on completed edits, so it
is intended for a desktop, single-editor workflow of up to 30 units. True concurrent
editing, shared durable storage, authentication roles and CAD-level interaction
would require a dedicated frontend and transactional backend in a later milestone.

## Unit library and AI design assistant

In Full design, use **Base unit library** to add single-door, double-door,
two- or three-drawer, sink, oven, pull-out and open-shelf bases. Adjust dimensions,
positions and rotation in the placement table. New units occupy the next free
footprint, rather than the same origin. Valid rows remain visible when another
row is incomplete or outside the room; the preview reports the skipped row and
overlap warnings. Rotation uses conservative bounding rectangles for overlap
warnings. Working aisles, openings and manufacturer clearances need review.

The catalogue-and-placement workflow is inspired by kitchen CAD tools. These
are illustrative presentation models, including drawer boxes and oven placeholders;
they do not add manufacturing rules or whole-scene costs. Positions are edited
numerically or by dragging on the new interactive 2D floor plan.

Expand **AI kitchen design assistant** after confirming the room. Set
`KITCHEN_AI_API_KEY` in Streamlit hosting Secrets (an OpenAI API key with API
billing). An existing `KITCHEN_VISION_API_KEY` can also be reused. Optional
`KITCHEN_AI_MODEL` defaults to `gpt-4.1-mini`. On explicit **Ask AI**, the request,
room, placed units and up to 80 current supplier products are sent to OpenAI;
contact information and raw documents are excluded. The assistant answers questions
and proposes supported units; review and click **Add proposed units to room**.
Existing units remain intact. Proposals are validated and placed in free space;
if the batch cannot fit, none of its units are added. AI does not calculate prices,
generate production cuts or certify installation clearances. Live AI calls require
a configured key and are not validated by the mocked service tests.

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

Prepare and confirm a measured rectangular room layout before cabinet controls or placement become available. Add doors and windows by wall, offset, width, height and sill. Changing these inputs invalidates confirmation. Irregular room outlines and service points are not implemented. The 2D designer checks cabinet collisions and opening clearance zones; it does not simulate actual door swing.

After confirmation, select **Full design**, add base cabinets, wardrobes, panels, worktops or appliance placeholders, then set their dimensions, positions and rotation. Up to 30 scene items are supported. The room floor can be shown. Wardrobes use a full top in the presentation model; their production construction rules are not yet configured. Items cannot extend outside the room bounds (small backing tolerance allowed). Review the automatic 2D warnings and check all service/access clearances manually.

Views: **Lines** provides the room plan with placed units (or front/side/top for a single cabinet), **Sketch** an isometric drawing, **3D** an interactive model, and **Ultra** detailed interactive finish shading/wood-grain with optional illustrative hinges. Door-open preview is available. SVG drawings and standalone interactive HTML can be exported.

Generate silent 3–12 second turntable MP4 videos of the entire selected scene in square, portrait or landscape format. The local Pillow/FFmpeg renderer produces stylised design presentations; it is not a photorealistic renderer. Matching video settings are cached in data/videos/. Videos are captured in saved quotation revisions when already generated. FFmpeg and ffprobe must be installed on the server; both are available in this instance.

**Pricing and cutting lists currently cover the configured base cabinet and its identical-unit quantity, not all independently placed scene items.** Full-scene production costing and irregular/custom furniture construction remain to be developed. Preview colours and hinge positions do not change prices or specify drilling.

## Sketch and PDF reading

Upload PNG/JPG sketches or PDFs up to 15 MB and 5 pages before room confirmation. Local reading uses embedded PDF text or Tesseract OCR on images/scanned pages; Poppler tools render PDF pages. Review and correct the transcript. Extracted dimension groups preserve their labels/context and units. Explicitly confirm the annotation, units and dimension order before applying room dimensions or staging a design item. Staged items can only be placed after confirming the room layout. Dimensions are never inferred from pixel scale. Handwriting is unreliable with local OCR.

Optional AI handwriting reading sends page images to OpenAI only on an explicit Read document action. It uses a secure KITCHEN_VISION_API_KEY binding for api.openai.com; a requirement was saved to the environment draft. It is not configured or validated yet. Add the credential securely in environment settings, review/save and publish the changes, then test an actual handwritten plan. Never place keys in project files. Reviewed text and source filename are retained in saved jobs; raw uploads remain in session memory.
