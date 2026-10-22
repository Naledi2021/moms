"""Wall centre lines and rectilinear worktop designs, in millimetres."""
import math
from rendering import Box

WALL_COLUMNS=['Name','Start X (mm)','Start Y (mm)','End X (mm)','End Y (mm)','Thickness (mm)']
RECT_COLUMNS=['X (mm)','Y (mm)','Width (mm)','Depth (mm)']

def wall_box(wall,height):
    x,y,ex,ey,t=(float(wall[k]) for k in WALL_COLUMNS[1:]);length=math.hypot(ex-x,ey-y);angle=math.degrees(math.atan2(ey-y,ex-x));r=math.radians(angle)
    return Box(str(wall['Name']),(x+t/2*math.sin(r),y-t/2*math.cos(r),0),(length,t,height),'wall',angle)

def validate_walls(walls,layout):
    if not isinstance(walls,list) or len(walls)>40:raise ValueError('Use at most 40 drawn wall segments.')
    for wall in walls:
        if not isinstance(wall.get('Name'),str) or not wall['Name'].strip():raise ValueError('Name each wall.')
        values=[float(wall[k]) for k in WALL_COLUMNS[1:]]
        if not all(math.isfinite(v) for v in values):raise ValueError('Wall measurements must be finite.')
        x,y,ex,ey,t=values
        if math.hypot(ex-x,ey-y)<50 or not 20<=t<=500:raise ValueError('Walls need length at least 50 mm and thickness 20–500 mm.')
        if not all(0<=a<=layout['length'] and 0<=b<=layout['width'] for a,b in ((x,y),(ex,ey))):raise ValueError('Wall centre-line endpoints must be inside the room boundary.')
    return walls

def room_wall_boxes(layout):
    """Outer walls are outside the measured clear room, with genuine opening gaps."""
    boxes=[];L,D,H=layout['length'],layout['width'],layout['height'];t=float(layout.get('wall_thickness',110))
    for wall,span in (('Front',L),('Back',L),('Left',D),('Right',D)):
        openings=[o for o in layout['openings'] if o['Wall']==wall]
        xs=sorted({0,span,*[float(o['Offset (mm)']) for o in openings],*[float(o['Offset (mm)'])+float(o['Width (mm)']) for o in openings]})
        zs=sorted({0,H,*[float(o['Sill (mm)']) for o in openings],*[float(o['Sill (mm)'])+float(o['Height (mm)']) for o in openings]})
        for x1,x2 in zip(xs,xs[1:]):
            for z1,z2 in zip(zs,zs[1:]):
                if any(float(o['Offset (mm)'])<(x1+x2)/2<float(o['Offset (mm)'])+float(o['Width (mm)']) and float(o['Sill (mm)'])<(z1+z2)/2<float(o['Sill (mm)'])+float(o['Height (mm)']) for o in openings):continue
                if wall in ('Front','Back'):origin=(x1,-t if wall=='Front' else D,z1);size=(x2-x1,t,z2-z1)
                else:origin=(-t if wall=='Left' else L,x1,z1);size=(t,x2-x1,z2-z1)
                boxes.append(Box(wall+' room wall',origin,size,'wall'))
    return boxes+[wall_box(w,H) for w in layout.get('walls',[])]

def worktop_rectangles(width,depth,config):
    """Subtract validated rectangular cut-outs from a union of rectangular sections."""
    sections=config.get('sections',[{'X (mm)':0,'Y (mm)':0,'Width (mm)':width,'Depth (mm)':depth}])
    holes=config.get('cutouts',[])
    if not sections or not isinstance(sections,list) or not isinstance(holes,list) or len(sections)>12 or len(holes)>8:raise ValueError('Use up to 12 worktop sections and 8 cut-outs.')
    def rectangle(item):
        x,y,w,d=(float(item[k]) for k in RECT_COLUMNS)
        if not all(math.isfinite(v) for v in (x,y,w,d)) or min(x,y)<0 or min(w,d)<=0 or x+w>width+.001 or y+d>depth+.001:raise ValueError('Worktop sections and cut-outs must fit inside its width and depth.')
        return x,y,x+w,y+d
    outer=[rectangle(r) for r in sections];inner=[rectangle(r) for r in holes]
    # Cross-sections across all edges create disjoint solid tiles; overlaps are not double-counted.
    xs=sorted({v for r in outer+inner for v in (r[0],r[2])});ys=sorted({v for r in outer+inner for v in (r[1],r[3])})
    solid=[]
    for y1,y2 in zip(ys,ys[1:]):
        runs=[]
        for x1,x2 in zip(xs,xs[1:]):
            cx,cy=(x1+x2)/2,(y1+y2)/2
            contained=lambda rs:any(a<cx<b and c<cy<d for a,c,b,d in rs)
            in_outer=contained(outer);in_hole=contained(inner)
            if in_hole and not in_outer:raise ValueError('Each cut-out must be completely inside the worktop sections.')
            if in_outer and not in_hole:
                if runs and abs(runs[-1][2]-x1)<.001:runs[-1]=(runs[-1][0],y1,x2,y2)
                else:runs.append((x1,y1,x2,y2))
        solid.extend(runs)
    if not solid:raise ValueError('Worktop must contain some solid material.')
    if len(solid)>250:raise ValueError('Simplify the worktop geometry.')
    return solid
