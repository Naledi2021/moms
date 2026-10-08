import streamlit as st
from dataclasses import asdict
from layout_ui import render_scene_editor,scene_boxes,plan_svg
from video_render import create_video, video_path
from rendering import cabinet_geometry,technical_svg,sketch_svg,interactive_figure


def render_views(width,height,depth,thickness,shelves,clearance,door_thickness,hinges,layout):
    st.subheader('Design views and videos')
    scope=st.radio('Design scope',['Full design','Single cabinet'],horizontal=True,key='render_scope')
    rows=render_scene_editor(layout,width,height,depth) if scope=='Full design' else []
    floor=st.checkbox('Show room floor',key='render_floor') if scope=='Full design' else False
    st.caption('Visualisations use finished dimensions. Scene placements are separate from the current single-cabinet quotation and cutting list.')
    mode=st.radio('Render view',['Lines','Sketch','3D','Ultra'],horizontal=True,key='render_mode')
    opened=st.checkbox('Show door open',key='render_door_open')
    with st.expander('Preview materials and details'):
        carcass_colour=st.color_picker('Carcass preview colour','#eeeae2',key='render_carcass_colour')
        door_colour=st.color_picker('Door preview colour','#b88a55',key='render_door_colour')
        finish=st.selectbox('Preview finish',['Matte','Gloss','Wood grain'],key='render_finish')
        hardware=st.checkbox('Show illustrative hinges in Ultra',key='render_hardware')
        st.caption('Colours and finish are presentation choices. They do not change material prices. Hinge positions are illustrative, not a drilling template.')
    try:
        boxes=scene_boxes(rows,layout,thickness,clearance,door_thickness,opened,floor) if scope=='Full design' else cabinet_geometry(width,height,depth,thickness,shelves,clearance,door_thickness,opened)
        lines=plan_svg(layout,boxes) if scope=='Full design' else technical_svg(width,height,depth,thickness,shelves,door_thickness)
        sketch=sketch_svg(boxes)
    except ValueError as error:
        st.info(str(error));return {'scene_rows':rows,'mode':mode}
    if mode=='Lines':
        st.image(lines,width='stretch')
        st.caption('Room plan with placed units.')
    elif mode=='Sketch':st.image(sketch,width='stretch')
    else:
        figure=interactive_figure(boxes,carcass_colour,door_colour,mode=='Ultra',finish,hardware,hinges)
        st.plotly_chart(figure,width='stretch',key='cabinet_3d')
        st.caption('Drag to rotate; scroll to zoom. Ultra adds finish shading, optional wood grain and hinge details.')
        st.download_button('Download interactive 3D view',figure.to_html(include_plotlyjs=True,full_html=True),'cabinet_3d.html','text/html')
    st.download_button('Download line drawing SVG',lines,'cabinet_lines.svg','image/svg+xml')
    st.download_button('Download sketch SVG',sketch,'cabinet_sketch.svg','image/svg+xml')
    st.subheader('Short design video')
    seconds=st.slider('Video length (seconds)',min_value=3,max_value=12,value=6,key='render_video_seconds')
    aspect=st.selectbox('Video format',['Square','Portrait','Landscape'],key='render_video_format')
    settings=dict(width=width,height=height,depth=depth,thickness=thickness,shelves=shelves,clearance=clearance,door_thickness=door_thickness,open_door=opened,carcass_colour=carcass_colour,door_colour=door_colour,finish=finish,hardware=hardware,hinges=hinges,seconds=seconds,format=aspect)
    if scope=='Full design':
        video_boxes=list(boxes)
        if hardware:
            from rendering import Box
            import math
            for side in [b for b in boxes if 'Left side' in b.name]:
                theta=math.radians(side.angle)
                for index in range(min(hinges,12)):
                    z=side.size[2]*(index+1)/(hinges+1)
                    t=side.size[0]
                    origin=(side.origin[0]+t*math.cos(theta)-5*math.sin(theta),side.origin[1]+t*math.sin(theta)+5*math.cos(theta),side.origin[2]+z-10)
                    video_boxes.append(Box('Illustrative hinge',origin,(24,35,20),'metal',side.angle))
        settings['scene']=[asdict(box) for box in video_boxes]
    path=video_path(settings)
    if st.button('Create short video',key='render_create_video'):
        try:
            with st.spinner('Rendering design turntable…'):
                create_video(settings)
        except (ValueError,OSError) as error:st.error(f'Could not create video: {error}')
    video=None
    if path.exists():
        video=path.read_bytes()
        st.video(video,format='video/mp4')
        st.download_button('Download design video MP4',video,'cabinet_turntable.mp4','video/mp4')
    st.caption('Silent turntable animation of the entire selected design. Hinge positions are illustrative; this is a design presentation, not an installation guide.')
    result={'mode':mode,'line_svg':lines,'sketch_svg':sketch,'scene_rows':rows}
    if video:
        import base64
        result['video_base64']=base64.b64encode(video).decode('ascii')
    return result
