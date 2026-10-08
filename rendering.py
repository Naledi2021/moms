"""Cabinet geometry in millimetres; presentation models do not set drilling positions."""
from dataclasses import dataclass
import html
import math
import numpy as np
import plotly.graph_objects as go

@dataclass(frozen=True)
class Box:
    name: str
    origin: tuple
    size: tuple
    kind: str='carcass'
    angle: float=0
    colour: str | None=None

    def vertices(self):
        x,y,z=self.origin; a,b,c=self.size
        points=np.array([(0,0,0),(a,0,0),(a,b,0),(0,b,0),(0,0,c),(a,0,c),(a,b,c),(0,b,c)],dtype=float)
        theta=math.radians(self.angle)
        rotation=np.array([[math.cos(theta),-math.sin(theta),0],[math.sin(theta),math.cos(theta),0],[0,0,1]])
        return points@rotation.T + np.array([x,y,z])


def cabinet_geometry(width,height,depth,thickness,shelves,clearance,door_thickness,open_door=False):
    values=(width,height,depth,thickness,clearance,door_thickness)
    if not all(math.isfinite(v) for v in values) or min(width,height)<=2*thickness or depth<200 or door_thickness<=0 or clearance<0 or clearance>=width-2*thickness or shelves<0 or shelves>20:
        raise ValueError('Rendering needs valid cabinet dimensions, depth at least 200 mm for two 100 mm rails, and at most 20 shelves.')
    w=width-2*thickness
    boxes=[Box('Left side',(0,0,0),(thickness,depth,height)),
           Box('Right side',(width-thickness,0,0),(thickness,depth,height)),
           Box('Bottom',(thickness,0,0),(w,depth,thickness)),
           Box('Front top rail',(thickness,0,height-thickness),(w,100,thickness)),
           Box('Rear top rail',(thickness,depth-100,height-thickness),(w,100,thickness)),
           Box('3 mm Masonite back',(0,depth,0),(width,3,height),'back')]
    for index in range(shelves):
        z=thickness+(height-2*thickness)*(index+1)/(shelves+1)-thickness/2
        boxes.append(Box(f'Shelf {index+1}',(thickness+clearance/2,0,z),(w-clearance,depth,thickness)))
    boxes.append(Box('Door',(2,-2-door_thickness,2),(width-4,door_thickness,height-4),'door',-100 if open_door else 0))
    return boxes


FACES=[(0,1,2,3),(4,7,6,5),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)]
EDGES=[(0,1),(1,2),(2,3),(3,0),(4,5),(5,6),(6,7),(7,4),(0,4),(1,5),(2,6),(3,7)]


def technical_svg(width,height,depth,thickness,shelves,door_thickness):
    scale=min(620/(width+depth),570/(height+depth))
    x,y=65,65;w=width*scale;h=height*scale;d=depth*scale;t=thickness*scale
    side_x=x+w+95;plan_y=y+h+90
    pieces=['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 800" role="img" aria-label="Dimensioned cabinet front, side and top drawings">', '<rect width="900" height="800" fill="#fff"/>', '<g stroke="#213547" stroke-width="1.5" fill="none">']
    def rect(a,b,c,e,dashed=False):pieces.append(f'<rect x="{a}" y="{b}" width="{c}" height="{e}"'+(' stroke-dasharray="5 4"' if dashed else '')+'/>')
    def line(a,b,c,e):pieces.append(f'<path d="M {a} {b} L {c} {e}"/>')
    rect(x,y,w,h);rect(x+t,y,w-2*t,t,True);rect(x+t,y+h-t,w-2*t,t,True)
    line(x+t,y,x+t,y+h);line(x+w-t,y,x+w-t,y+h)
    rect(x+2*scale,y+2*scale,(width-4)*scale,(height-4)*scale)
    for index in range(shelves):
        z=thickness+(height-2*thickness)*(index+1)/(shelves+1)
        rect(x+t,y+h-z*scale,w-2*t,t,True)
    rect(side_x,y,d,h);rect(side_x+d,y,3*scale,h);rect(side_x-(door_thickness+2)*scale,y+2*scale,door_thickness*scale,(height-4)*scale)
    rect(x,plan_y,w,d);rect(x+t,plan_y,w-2*t,100*scale,True);rect(x+t,plan_y+d-100*scale,w-2*t,100*scale,True)
    rect(x,plan_y+d,w,3*scale)
    def dim(a,b,c,e,label):
        line(a,b,c,e)
        if b==e:line(a,b-5,a,b+5);line(c,e-5,c,e+5)
        else:line(a-5,b,a+5,b);line(c-5,e,c+5,e)
        pieces.append(f'<text x="{(a+c)/2+5}" y="{(b+e)/2-8}" stroke="none" fill="#213547" font-size="14">{label}</text>')
    dim(x,y-22,x+w,y-22,f'{width:g} mm')
    dim(x-22,y,x-22,y+h,f'{height:g} mm')
    dim(side_x,y-22,side_x+d,y-22,f'{depth:g} mm panel depth')
    pieces.append('</g><g fill="#213547" font-family="sans-serif" font-size="16">')
    pieces += [f'<text x="{x}" y="{y+h+28}">FRONT — door {width-4:g} × {height-4:g} mm finished</text>',f'<text x="{side_x}" y="{y+h+50}">SIDE — 3 mm rear back</text>',f'<text x="{x}" y="{plan_y+d+30}">TOP — two 100 mm rails</text>', '<text x="65" y="750">All dimensions in mm. Dashed lines show internal components.</text>', '<text x="65" y="775">Door offset is illustrative. Use the cutting list for board cuts before edging.</text>','</g></svg>']
    return ''.join(pieces)


def sketch_svg(boxes):
    camera=np.array([1,-1,.8]); polygons=[];all_points=[]
    for box in boxes:
        vertices=box.vertices()
        for face in FACES:
            p=vertices[list(face)]
            projected=np.column_stack([.8*p[:,0]+.55*p[:,1],.3*p[:,0]-.4*p[:,1]-p[:,2]])
            polygons.append((float(np.mean(p@camera)),box.kind,projected));all_points.extend(projected)
    points=np.array(all_points);low=points.min(axis=0);high=points.max(axis=0)
    scale=min(760/(high[0]-low[0]),640/(high[1]-low[1]))
    pieces=['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 760" role="img" aria-label="Cabinet isometric sketch"><rect width="900" height="760" fill="#fffdf6"/>']
    colours={'carcass':'#f1eadb','back':'#d2bea0','door':'#e4d3b6','floor':'#f5f0e5','wall':'#ede7d9'}
    for _,kind,p in sorted(polygons,key=lambda a:a[0]):
        p=(p-low)*scale+np.array([65,35]);coords=' '.join(f'{a:.2f},{b:.2f}' for a,b in p)
        pieces.append(f'<polygon points="{coords}" fill="{colours.get(kind,"#d3d6db")}" stroke="#514940" stroke-width="1.3" stroke-linejoin="round"/>')
        shifted=p+np.array([.7,-.6]);coords=' '.join(f'{a:.2f},{b:.2f}' for a,b in shifted)
        pieces.append(f'<polygon points="{coords}" fill="none" stroke="#514940" stroke-width=".45" opacity=".4"/>')
    pieces.append('<text x="65" y="730" fill="#514940" font-family="sans-serif" font-size="15">Isometric design sketch — finished panel geometry</text></svg>')
    return ''.join(pieces)


def rgb(colour):
    return np.array([int(colour[i:i+2],16) for i in (1,3,5)],dtype=float)


def mesh(box,colour,ultra=False,finish='Matte'):
    vertices=box.vertices(); points=[];triangles=[];colors=[]
    for face in FACES:
        p=vertices[list(face)]
        steps=16 if ultra and finish=='Wood grain' and box.kind in ('door','carcass') else 1
        for index in range(steps):
            u=index/steps;v=(index+1)/steps
            stripe=[p[0]*(1-u)+p[1]*u,p[0]*(1-v)+p[1]*v,p[3]*(1-v)+p[2]*v,p[3]*(1-u)+p[2]*u]
            base=len(points);points.extend(stripe);triangles.extend([(base,base+1,base+2),(base,base+2,base+3)])
            shade=1
            if steps>1:shade=.86+.12*math.sin(index*1.8)+.03*math.sin(index*5.3)
            tint=np.clip(rgb(colour)*shade,0,255).astype(int)
            colors.extend([f'rgb({tint[0]},{tint[1]},{tint[2]})']*4)
    p=np.array(points);tri=np.array(triangles)
    return go.Mesh3d(x=p[:,0],y=p[:,1],z=p[:,2],i=tri[:,0],j=tri[:,1],k=tri[:,2],vertexcolor=colors,name=box.name,flatshading=True,
       hovertemplate=html.escape(box.name)+'<extra></extra>',showlegend=False,
       lighting=dict(ambient=.45 if ultra else .7,diffuse=.8,specular=.7 if finish=='Gloss' else .18,roughness=.18 if finish=='Gloss' else .8,fresnel=.15),lightposition=dict(x=-1500,y=-2500,z=2500))


def interactive_figure(boxes,carcass_colour='#eeeae2',door_colour='#b88a55',ultra=False,finish='Matte',hardware=False,hinges=2):
    traces=[]
    colours={'carcass':carcass_colour,'door':door_colour,'back':'#bfa27b','metal':'#aab3bd','appliance':'#7a8791','panel':door_colour,'floor':'#d9d2c3','wall':'#eeeae2'}
    for box in boxes:
        traces.append(mesh(box,box.colour or colours[box.kind],ultra,finish))
        if not ultra:
            p=box.vertices();coords=[]
            for a,b in EDGES:coords.extend([p[a],p[b],[None,None,None]])
            coords=np.array(coords,dtype=object)
            traces.append(go.Scatter3d(x=coords[:,0],y=coords[:,1],z=coords[:,2],mode='lines',line=dict(color='#354052',width=2),hoverinfo='skip',showlegend=False))
    if ultra and hardware:
        # Small schematic hinge bodies on the carcass; no drilling positions are specified.
        for side in [b for b in boxes if 'Left side' in b.name]:
            height=side.size[2];thickness=side.size[0];theta=math.radians(side.angle)
            for i in range(min(hinges,12)):
                z=height*(i+1)/(hinges+1)
                origin=(side.origin[0]+thickness*math.cos(theta)-5*math.sin(theta),side.origin[1]+thickness*math.sin(theta)+5*math.cos(theta),side.origin[2]+z-10)
                traces.append(mesh(Box(f'Hinge {i+1} — illustrative',origin,(24,35,20),'metal',side.angle),'#aab3bd',True,'Gloss'))
    figure=go.Figure(traces)
    figure.update_layout(height=650,margin=dict(l=0,r=0,t=0,b=0),paper_bgcolor='#f6f4ef' if ultra else '#fff',
        scene=dict(aspectmode='data',xaxis=dict(title='Width (mm)',visible=not ultra),yaxis=dict(title='Depth (mm)',visible=not ultra),zaxis=dict(title='Height (mm)',visible=not ultra),
                   camera=dict(eye=dict(x=1.7,y=-2.1,z=1.4)),bgcolor='#f6f4ef' if ultra else '#fff'),uirevision='cabinet-camera')
    return figure
