from dataclasses import asdict
from io import BytesIO
from pathlib import Path
import json
from datetime import datetime, timezone
from price_watch import CATALOG, refresh
from supplier_upload_ui import render_supplier_uploads
from jobs_ui import render_saved_jobs, render_save_job
from render_ui import render_views
from layout_ui import render_room_layout
from plan_import_ui import render_plan_import
from supplier_updates import load as load_updates, current_products, material_rate
from zoneinfo import ZoneInfo
from hardware_ui import select_unit_price, supplier_accessories
import pandas as pd
import streamlit as st
from reportlab.pdfgen import canvas
from calculator import Part, cabinet_parts, estimate, single_door, edged_cut_size, carcass_cut_size, EDGE_RULES, sheet_rate

LOGO=Path(__file__).with_name('assets')/'mkp-logo.png'
st.set_page_config(page_title='MKP | Kitchen Design Studio', page_icon=str(LOGO), layout='wide')
from app_access import require_access
require_access()
st.logo(str(LOGO),size='large')


def job_supplier_products():
    return st.session_state['_job_supplier_snapshot'] if '_job_supplier_snapshot' in st.session_state else current_products(load_updates(),datetime.now(ZoneInfo('Africa/Johannesburg')).date())

def supplier_price(label, key):
    products=[p for p in job_supplier_products() if p['unit'] in ('sheet','m2')]
    if products:
        source=st.selectbox(label+' price source',['Manual entry','Uploaded supplier prices'],key=key+'_source')
        if source=='Uploaded supplier prices':
            choices={f"{p['supplier']} · {p['sku']} · {p['product']}":p for p in products}
            selected=st.selectbox(label+' supplier product',list(choices),key=key+'_product')
            product=choices[selected]
            st.caption(f"Effective {product['effective_date']}; listed R {product['price']:,.2f} per {product['unit']}; VAT {product['vat_basis'].lower()}. Thickness: {product['thickness_mm'] or 'not specified'} mm. Confirm material and thickness match this job.")
            try:
                rate=material_rate(product)
            except ValueError as error:
                st.warning(str(error));return None
            st.caption(f'Applied rate excluding VAT: R {rate:,.2f} / m². Job tax is added separately.')
            return rate
    basis = st.selectbox(label + ' price basis', ['Per m²', 'Per sheet / panel'], key=key+'_basis')
    if basis == 'Per m²':
        return st.number_input(label + ' price (R / m²)', min_value=0.0, value=0.0, key=key+'_rate')
    sheet_price = st.number_input(label + ' sheet / panel price (R)', min_value=0.0, value=None, key=key+'_price')
    length = st.number_input(label + ' sheet / panel length (mm)', min_value=1.0, value=None, key=key+'_length')
    width = st.number_input(label + ' sheet / panel width (mm)', min_value=1.0, value=None, key=key+'_width')
    try:
        rate = sheet_rate(sheet_price, length, width)
    except ValueError as error:
        st.warning(str(error))
        return None
    st.caption(f'Equivalent material rate: R {rate:,.2f} / m². This does not calculate how many sheets to buy.')
    return rate


brand_icon,brand_title=st.columns([1,7])
with brand_icon:st.image(str(LOGO),width=120)
with brand_title:
    st.title('Moms Kitchens and Projects')
    st.caption('Design • Renovate • Build | Kitchen design, costing and cutting lists')
render_saved_jobs()
render_supplier_uploads()
from default_prices_ui import render_shared_defaults,save_current_defaults
render_shared_defaults()
render_plan_import()
room_layout=render_room_layout()
if room_layout is None:
    st.stop()
with st.expander('Online supplier prices — sources and freshness'):
    st.caption('Public observations, not trade quotations. Confirm VAT, exact variant, stock and set contents. Prices are not silently applied to your estimate. Daily checks run only while the price worker and environment are running.')
    if st.button('Check tracked online prices now'):
        with st.spinner('Checking supplier product pages…'):
            refresh()
    catalogue = json.loads(CATALOG.read_text())
    price_rows = []
    for product in catalogue['products']:
        timestamp = product.get('last_verified_utc')
        age = (datetime.now(timezone.utc)-datetime.fromisoformat(timestamp)).total_seconds()/86400 if timestamp else None
        status = 'Stale — over 7 days' if age is not None and age > 7 else product['check_status']
        price_rows.append({'Supplier':product['supplier'], 'Product':product['name'], 'Price (R)':product.get('price_zar'), 'Basis':product['price_basis'], 'VAT':product['vat_basis'], 'Last verified (UTC)':timestamp, 'Status':status, 'Source':product['source_url']})
    st.dataframe(pd.DataFrame(price_rows), hide_index=True, width='stretch', column_config={'Source':st.column_config.LinkColumn()})
    st.caption('PG Bison July 2026 availability list: many ranges use 2750 × 1840 mm. SupaWood raw MDF includes 16, 18 and 22 mm, not a verified 22.5 mm specification. Do not substitute board thickness automatically. Seno SA, BoardCity and Blum retail prices remain unresolved.')
    st.download_button('Download supplier price observations', json.dumps(catalogue,indent=2), 'supplier_prices.json','application/json')
st.info('First version: a base carcass with two 100 mm top rails and a full bottom panel. Sides are full height; rails and bottom fit between them. A 3 mm PG Bison Masonite back covers the full rear. One door uses a 4 mm total deduction from both cabinet width and height. Door board cuts deduct selected edging from finished sizes. Drawer units, legs, worktops, and sheet nesting are not calculated yet.')

with st.sidebar:
    st.header('Job details')
    if 'job_name' not in st.session_state: st.session_state['job_name']='New kitchen'
    customer = st.text_input('Job name',key='job_name')
    customer_name = st.text_input('Customer name',key='customer_name')
    customer_phone = st.text_input('Customer phone',key='customer_phone')
    customer_email = st.text_input('Customer email',key='customer_email')
    customer_address = st.text_area('Installation address',key='customer_address')
    job_notes = st.text_area('Job notes',key='job_notes')
    job_status = st.selectbox('Job status',['Enquiry','Quotation','Confirmed','In production','Completed'],key='job_status')
    material = st.selectbox('Material', ['Melamine', 'MDF', 'Solid wood'], key='job_material')
    thickness = st.selectbox('Board thickness (mm)', [16.0, 18.0, 22.5], index=1, key='job_thickness')
    units = st.number_input('Identical cabinets', min_value=1, max_value=100, value=1, step=1, key='job_units')

left, right = st.columns(2)
with left:
    st.subheader('Cabinet dimensions')
    width = st.number_input('External width (mm)', min_value=1.0, value=600.0, step=1.0, key='job_width')
    height = st.number_input('Carcass height (mm), excluding legs and worktop', min_value=1.0, value=720.0, step=1.0, key='job_height')
    depth = st.number_input('Panel depth (mm), excluding door and back', min_value=1.0, value=500.0, step=1.0, key='job_depth')
    st.caption('Rear-fixed Masonite back: 3 mm. Overall depth before doors = panel depth + 3 mm.')
    shelves = st.number_input('Internal shelves per cabinet', min_value=0, max_value=20, value=1, step=1, key='job_shelves')
    clearance = st.number_input('Total shelf width clearance (mm)', min_value=0.0, value=0.0, step=0.5, key='job_clearance')
    st.caption('Clearance is subtracted once from shelf width only. Dimensions are panel cut sizes before any edging adjustment. Grain direction requires workshop review.')
    carcass_edging = st.selectbox('Carcass edging thickness (mm)', [1, 2], key='job_carcass_edging')
    st.caption('Sides: 1 long + 1 short edge. Shelves: 1 long edge. Bases: none. Rails: 1 long edge. Long means the longer finished dimension.')
    st.subheader('Single door')
    door_height = height - 4
    st.caption(f'Door: {width-4:g} mm wide × {door_height:g} mm high (4 mm total deduction in each direction).')
    door_material = st.selectbox('Door material', ['Melamine', 'MDF', 'Solid wood'], key='job_door_material')
    door_thickness = st.selectbox('Door thickness (mm)', [16.0, 18.0, 22.5], index=1, key='job_door_thickness')
    edging = st.selectbox('Door edging thickness (mm)', [1, 2], key='job_door_edging')
    door_edges = st.multiselect('Door edges to finish', ['Top', 'Bottom', 'Left', 'Right'], default=[] if door_material == 'Solid wood' else ['Top', 'Bottom', 'Left', 'Right'], key='job_door_edges')
    st.caption('Door dimensions above are finished sizes including edging. Cut dimensions deduct edging on selected edges only.')
with right:
    from default_prices import seed_defaults
    seed_defaults(st.session_state,st.session_state['_job_default_prices'])
    st.subheader('Your prices and allowances')
    price = supplier_price('Carcass material', 'carcass_supplier')
    back_price = supplier_price('3 mm PG Bison Masonite', 'back_supplier')
    door_price = supplier_price('Door material', 'door_supplier')
    waste = st.number_input('Material waste allowance (%)', min_value=0.0, value=10.0, key='job_waste')
    st.subheader('Soft-close hinges')
    hinge_brand = st.selectbox('Hinge brand', ['Roco', 'Blum', 'Gelmar'], key='job_hinge_brand')
    hinges_per_door = st.number_input('Hinges per door', min_value=1, value=2, step=1, key='job_hinges_per_door')
    hinge_price_input, hinge_record = select_unit_price('Soft-close hinge price each (R)', 'hinge_price')
    plates_included = st.checkbox('Mounting plates included in hinge price', key='plates_included')
    if plates_included:
        plate_price_input, plate_record = 0.0, None
    else:
        plate_price_input, plate_record = select_unit_price('Mounting plate price each (R); enter 0 if included', 'plate_price')
    st.caption('Two hinges per door is your default. Confirm hinge model, overlay and plate compatibility for the selected door thickness. Supplier prices have not been verified.')
    hardware = st.number_input('Other hardware / edging allowance per cabinet (R)', min_value=0.0, value=0.0, key='job_hardware')
    labour = st.number_input('Labour per cabinet (R)', min_value=0.0, value=0.0, key='job_labour')
    transport = st.number_input('Transport for this job (R)', min_value=0.0, value=0.0, key='job_transport')
    markup = st.number_input('Markup on cost (%)', min_value=0.0, value=0.0, key='job_markup')
    tax = st.number_input('Tax (%)', min_value=0.0, value=0.0, key='job_tax')
    if material == 'Solid wood':
        st.caption('Solid wood currently uses a finished-panel price per m² at the chosen thickness. Rough timber volume, machining loss, and board selection need a later costing model.')

design_views=render_views(width,height,depth,thickness,shelves,clearance,door_thickness,hinges_per_door,room_layout)

uploaded_items, invalid_accessories = supplier_accessories()
if invalid_accessories or (hinge_record is not None and hinge_price_input is None) or (plate_record is not None and plate_price_input is None):
    st.info('Complete the selected supplier VAT information before using these hardware prices.')
    st.stop()

st.subheader('Additional manually priced Blum accessories for this job')
st.caption('Enter complete-set prices from your supplier. These are optional costing lines, not a verified catalogue or installation specification. Quantities apply to the whole job.')
if '_job_manual_accessories' not in st.session_state:
    items=[{'Accessory':k[10:],'Quantity':0,'Unit price (R)':v} for k,v in st.session_state['_job_default_prices']['prices'].items() if k.startswith('accessory|')]
    if items:st.session_state['_job_manual_accessories']=items
accessories = st.data_editor(pd.DataFrame(st.session_state.get('_job_manual_accessories', [
    {'Accessory': 'AVENTOS lift system (complete set)', 'Quantity': 0, 'Unit price (R)': 0.0},
    {'Accessory': 'LEGRABOX drawer system (complete set)', 'Quantity': 0, 'Unit price (R)': 0.0},
    {'Accessory': 'TANDEMBOX drawer system (complete set)', 'Quantity': 0, 'Unit price (R)': 0.0},
    {'Accessory': 'MOVENTO runner pair', 'Quantity': 0, 'Unit price (R)': 0.0},
    {'Accessory': 'TANDEM runner pair', 'Quantity': 0, 'Unit price (R)': 0.0},
    {'Accessory': 'SERVO-DRIVE kit (specify components)', 'Quantity': 0, 'Unit price (R)': 0.0},
])), hide_index=True, num_rows='dynamic', key='blum_accessories', column_config={
    'Quantity': st.column_config.NumberColumn(min_value=0, step=1, required=True),
    'Unit price (R)': st.column_config.NumberColumn(min_value=0, required=True),
})
if accessories[['Quantity', 'Unit price (R)']].isna().any().any() or (accessories[['Quantity', 'Unit price (R)']] < 0).any().any() or ((accessories['Quantity'] % 1) != 0).any():
    st.error('Accessory quantities must be whole nonnegative numbers and prices must be nonnegative.')
    st.stop()
uploaded_accessory_cost = sum(item['total_ex_vat'] for item in uploaded_items)
accessory_cost = float((accessories['Quantity'] * accessories['Unit price (R)']).sum()) + uploaded_accessory_cost
hinge_price = hinge_price_input or 0
plate_price = plate_price_input or 0
hinge_cost = hinges_per_door * (hinge_price + plate_price)
unpriced = hinge_price_input is None or plate_price_input is None or ((accessories['Quantity'] > 0) & (accessories['Unit price (R)'] == 0)).any()
if unpriced:
    st.warning('Preliminary estimate: missing hinge/plate prices or selected accessories priced at zero. Unpriced amounts are excluded from totals.')
st.write(f'Hinges: {hinges_per_door * units} × {hinge_brand} soft-close. Hinges and plates: R {hinge_cost * units:,.2f}. Accessories: R {accessory_cost:,.2f}.')

if any(rate is None for rate in (price, back_price, door_price)):
    st.info('Complete the selected supplier pricing fields to calculate an estimate.')
    st.stop()

try:
    parts = cabinet_parts(width, height, depth, thickness, shelves, clearance)
    cut_parts = [carcass_cut_size(p, carcass_edging) for p in parts]
    door = single_door(width, door_height)
    door_cut = edged_cut_size(door, edging, door_edges)
except ValueError as error:
    st.error(str(error))
    st.stop()
rows = [dict(**asdict(p), material=material, thickness_mm=thickness) for p in cut_parts]
back = Part('Rear-fixed back', 1, height, width)
rows.append(dict(**asdict(back), material='PG Bison Masonite', thickness_mm=3.0))
rows.append(dict(**asdict(door_cut), material=door_material, thickness_mm=door_thickness))
for row in rows:
    row['finished_length_mm'] = row['length_mm']
    row['finished_width_mm'] = row['width_mm']
    row['edging_mm'] = 0
    row['edged_edges'] = ''
for row, finished in zip(rows, parts):
    counts = EDGE_RULES.get(finished.name)
    label = 'Pending' if counts is None else f'{counts[0]} long, {counts[1]} short'
    row.update(finished_length_mm=finished.length_mm, finished_width_mm=finished.width_mm, edging_mm=carcass_edging if counts and any(counts) else 0, edged_edges=label)
rows[-1].update(finished_length_mm=door.length_mm, finished_width_mm=door.width_mm, edging_mm=edging if door_edges else 0, edged_edges=', '.join(door_edges))
for row in rows:
    row['quantity'] *= units
frame = pd.DataFrame(rows)
door_cost = door_cut.area_m2 * (1+waste/100) * door_price
quote = estimate(cut_parts, price, waste, hardware + door_cost + hinge_cost + accessory_cost/units, labour, transport/units, markup, tax, back.area_m2, back_price)
quote['material'] += door_cost
quote['area'] += door_cut.area_m2
save_current_defaults(price,back_price,door_price,hinge_price_input,plate_price_input,accessories.to_dict(orient='records'))
st.subheader('Cutting list')
st.write(f'Internal width: **{width-2*thickness:g} mm** · Clear height below top rails: **{height-2*thickness:g} mm**')
st.write(f'Overall depth before doors: **{depth+3:g} mm**')
st.caption('length_mm and width_mm are board CUT sizes; finished columns show dimensions after edging. Rails are 100 mm wide when finished, including edging.')
st.dataframe(frame, hide_index=True, width='stretch')
st.download_button('Download cutting list CSV', frame.to_csv(index=False).encode(), 'cutting_list.csv', 'text/csv')
a, b, c = st.columns(3)
a.metric('Net panel area', f"{quote['area']*units:.3f} m²")
b.metric('Material estimate with waste', f"R {quote['material']*units:,.2f}")
c.metric('Job total including entered tax', f"R {quote['total']*units:,.2f}")
st.caption('Area plus waste is an estimate, not a sheet count or cutting optimisation. Enter all prices before using this estimate with customers.')

buffer = BytesIO()
pdf = canvas.Canvas(buffer)
pdf.setTitle('Kitchen cabinet estimate')
pdf.drawImage(str(LOGO),480,745,width=70,height=70,mask='auto')
lines = ['MKP — MOMS KITCHENS AND PROJECTS', customer,
         'Customer: '+customer_name, 'Phone: '+customer_phone, 'Email: '+customer_email,
         'Installation: '+customer_address.replace('\n',' '), 'Job status: '+job_status,
         f'{units} cabinet(s): {width:g} x {height:g} x {depth:g} mm',
         f'Material: {material}, {thickness:g} mm',
         'Back: 3 mm PG Bison Masonite, fixed onto rear',
         f'Overall depth before doors: {depth+3:g} mm',
         'Construction: two 100 mm top rails and bottom between full-height sides', '', 'CUTTING LIST']
lines.append(f'Door FINISHED size: {door.width_mm:g} wide x {door.length_mm:g} high mm')
lines.append('Door edging: ' + str(edging) + ' mm on ' + (', '.join(door_edges) or 'no edges'))
lines.append('Dimensions below are board CUT sizes before edging.')
for row in rows:
    lines.append(f"{row['quantity']} x {row['name']}: {row['length_mm']:g} x {row['width_mm']:g} mm, {row['material']} {row['thickness_mm']:g} mm")
    lines.append(f"  Finished {row['finished_length_mm']:g} x {row['finished_width_mm']:g} mm; edging {row['edging_mm']:g} mm: {row['edged_edges'] or 'none'}")
lines += ['', f'Carcass rate: R {price:.2f} / m2; Masonite: R {back_price:.2f} / m2',
          f'Door rate: R {door_price:.2f} / m2', f"Material with {waste:g}% waste: R {quote['material']*units:.2f}",
          f"Masonite included in material total: R {quote['back_material']*units:.2f}",
          f'Door material included in material total: R {door_cost*units:.2f}',
          f'Other hardware / edging allowance: R {hardware*units:.2f}',
          f'{hinges_per_door*units} x {hinge_brand} soft-close hinges + plates: R {hinge_cost*units:.2f}',
          f'All accessories for job: R {accessory_cost:.2f}',
          f'Labour: R {labour*units:.2f}', f'Transport: R {transport:.2f}',
          f'Markup: {markup:g}%', f"Subtotal: R {quote['subtotal']*units:.2f}",
          f"Tax ({tax:g}%): R {quote['tax']*units:.2f}", f"Total: R {quote['total']*units:.2f}", '',
          'Excludes legs and worktops unless covered by your allowances.',
          'Confirm edging deductions, grain direction and fitting details before cutting.']
for label,key in [('Carcass','carcass_supplier'),('Back','back_supplier'),('Door','door_supplier')]:
    if st.session_state.get(key+'_source')=='Uploaded supplier prices':
        lines.append(label+' supplier product: '+str(st.session_state.get(key+'_product','')))
for component, record, applied in [('Hinge', hinge_record, hinge_price), ('Plate', plate_record, plate_price)]:
    if record:
        lines.append(f"{component}: {record['supplier']} SKU {record['sku']} - {record['product']}")
        lines.append(f"  Effective {record['effective_date']}; applied R {applied:.2f} each excluding VAT")
if plates_included:
    lines.append('Mounting plates included in hinge price; not charged separately.')
for item in uploaded_items:
    lines.append(f"{item['quantity']} x {item['supplier']} SKU {item['sku']} - {item['product']}")
    lines.append(f"  R {item['unit_price_ex_vat']:.2f} per {item['unit']} excluding VAT; effective {item['effective_date']}")
if unpriced or min(price,back_price,door_price)<=0:
    lines.append('INCOMPLETE PRICING: material, hinge/plate or selected accessory prices missing.')
lines.append('Supplier prices not independently verified; confirm VAT basis before quoting.')
for _, item in accessories[accessories['Quantity'] > 0].iterrows():
    lines.append(f"{item['Quantity']:g} x {item['Accessory']}: R {item['Unit price (R)']:.2f} each")
y = 800
for line in lines:
    if y < 50:
        pdf.showPage()
        y = 800
    pdf.drawString(40, y, line[:110])
    y -= 22
pdf.save()
st.download_button('Download estimate PDF', buffer.getvalue(), 'kitchen_estimate.pdf', 'application/pdf')
if st.session_state.get('render_scope')=='Single cabinet':
    from layout_ui import current_scene_rows
    design_views['scene_rows']=current_scene_rows()
snapshot = dict(
    total=quote['total']*units, subtotal=quote['subtotal']*units, tax=quote['tax']*units,
    pricing_status='Incomplete / preliminary' if unpriced or min(price,back_price,door_price)<=0 else 'Prices entered',
    material_rates=dict(carcass=price,back=back_price,door=door_price),
    hinge_record=hinge_record,plate_record=plate_record,
    hinge_price=hinge_price,plate_price=plate_price,
    supplier_products=job_supplier_products(),
    manual_accessories=accessories.to_dict(orient='records'),uploaded_accessories=uploaded_items,
    plan_import=st.session_state.get('_job_plan_import'),
    plan_pending_units=st.session_state.get('_job_import_units',[]),
    layout=room_layout,
    default_prices=st.session_state.get('_job_default_prices'),
    design_lock=st.session_state.get('_design_lock'),
    design_views=design_views,
    cutting_list=frame.to_dict(orient='records'),
)
render_save_job(customer,snapshot,buffer.getvalue(),frame.to_csv(index=False))
with st.expander('Design capabilities'):
    st.write('Use the base unit library and AI kitchen design assistant in Full design. Customer-facing chat, whole-room production costing and custom manufacturing rules remain to be developed.')
