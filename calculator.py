from dataclasses import dataclass

@dataclass(frozen=True)
class Part:
    name: str
    quantity: int
    length_mm: float
    width_mm: float

    @property
    def area_m2(self):
        return self.quantity * self.length_mm * self.width_mm / 1_000_000


def cabinet_parts(width, height, depth, thickness, shelves=1, clearance=0):
    if thickness not in (16, 18, 22.5):
        raise ValueError('Choose 16, 18, or 22.5 mm board.')
    if min(width, height) <= 2 * thickness or depth <= 0:
        raise ValueError('Cabinet dimensions must leave a positive internal space.')
    if shelves < 0 or int(shelves) != shelves or clearance < 0:
        raise ValueError('Shelf count and total shelf clearance must be nonnegative.')
    internal_width = width - 2 * thickness
    if clearance >= internal_width:
        raise ValueError('Shelf clearance must be less than internal width.')
    parts = [Part('Side', 2, height, depth),
             Part('Rail', 2, internal_width, 100),
             Part('Bottom', 1, internal_width, depth)]
    if shelves:
        parts.append(Part('Internal shelf', int(shelves), internal_width-clearance, depth))
    return parts


def estimate(parts, price_per_m2, waste_percent, hardware, labour, transport, markup_percent, tax_percent, back_area=0, back_price_per_m2=0):
    values = (price_per_m2, waste_percent, hardware, labour, transport, markup_percent, tax_percent, back_area, back_price_per_m2)
    if any(v < 0 for v in values):
        raise ValueError('Costs and percentages cannot be negative.')
    area = sum(p.area_m2 for p in parts)
    back_material = back_area * (1 + waste_percent / 100) * back_price_per_m2
    material = area * (1 + waste_percent / 100) * price_per_m2 + back_material
    cost = material + hardware + labour + transport
    subtotal = cost * (1 + markup_percent / 100)
    return dict(area=area + back_area, back_material=back_material, material=material, cost=cost, subtotal=subtotal,
                tax=subtotal * tax_percent / 100, total=subtotal * (1 + tax_percent / 100))


def single_door(width, door_height, width_deduction=4):
    if width_deduction < 0 or width <= width_deduction or door_height <= 0:
        raise ValueError('Door dimensions must be positive and width deduction nonnegative.')
    return Part('Single door', 1, door_height, width-width_deduction)


def edged_cut_size(finished, edging_mm, edges):
    allowed = {'Top', 'Bottom', 'Left', 'Right'}
    if edging_mm not in (1, 2) or not set(edges) <= allowed:
        raise ValueError('Choose 1 or 2 mm edging and valid edge names.')
    length = finished.length_mm - edging_mm * len(set(edges) & {'Top', 'Bottom'})
    width = finished.width_mm - edging_mm * len(set(edges) & {'Left', 'Right'})
    if min(length, width) <= 0:
        raise ValueError('Edging deductions must leave a positive board cut size.')
    return Part(finished.name, finished.quantity, length, width)


EDGE_RULES = {'Side': (1, 1), 'Internal shelf': (1, 0), 'Rail': (1, 0),
              'Bottom': (0, 0), 'Drawer base': (0, 0)}


def carcass_cut_size(finished, edging_mm):
    if edging_mm not in (1, 2):
        raise ValueError('Choose 1 or 2 mm edging.')
    long_count, short_count = EDGE_RULES.get(finished.name, (0, 0))
    # Edging a long edge reduces the shorter dimension, and vice versa.
    if finished.length_mm >= finished.width_mm:
        length = finished.length_mm - short_count * edging_mm
        width = finished.width_mm - long_count * edging_mm
    else:
        length = finished.length_mm - long_count * edging_mm
        width = finished.width_mm - short_count * edging_mm
    if min(length, width) <= 0:
        raise ValueError('Edging must leave positive board cut dimensions.')
    return Part(finished.name, finished.quantity, length, width)


def sheet_rate(sheet_price, length_mm, width_mm):
    if sheet_price is None or length_mm is None or width_mm is None:
        raise ValueError('Enter sheet price, length and width.')
    if sheet_price < 0 or min(length_mm, width_mm) <= 0:
        raise ValueError('Sheet dimensions must be positive and price nonnegative.')
    return sheet_price / (length_mm * width_mm / 1_000_000)
