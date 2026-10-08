"""Local cabinet turntable videos, encoded to H.264 MP4 without external services."""
import hashlib
import json
import math
from pathlib import Path
import shutil
import subprocess
import tempfile
import numpy as np
from PIL import Image, ImageDraw
from rendering import cabinet_geometry,FACES,rgb,Box

ROOT=Path(__file__).with_name('data')/'videos'
FORMATS={'Square':(640,640),'Portrait':(480,720),'Landscape':(800,450)}
FPS=24

def cache_key(settings):
    return hashlib.sha256(json.dumps(settings,sort_keys=True,allow_nan=False).encode()).hexdigest()

def video_path(settings):
    return ROOT/(cache_key(settings)+'.mp4')

def frame_image(boxes,settings,angle):
    width,height=FORMATS[settings['format']]
    image=Image.new('RGB',(width,height),'#f6f4ef');draw=ImageDraw.Draw(image)
    points=np.vstack([b.vertices() for b in boxes]);centre=(points.min(axis=0)+points.max(axis=0))/2
    radius=float(np.linalg.norm(points.max(axis=0)-points.min(axis=0))/2)
    eye=np.array([math.cos(angle),math.sin(angle),.65]);eye/=np.linalg.norm(eye)
    forward=-eye;right=np.cross(forward,[0,0,1]);right/=np.linalg.norm(right);up=np.cross(right,forward)
    scale=min(width*.42,height*.36)/radius
    colours={'carcass':settings['carcass_colour'],'door':settings['door_colour'],'back':'#bfa27b','metal':'#aab3bd','appliance':'#7a8791','panel':settings['door_colour'],'floor':'#d9d2c3','wall':'#eeeae2'}
    polygons=[]
    for box in boxes:
        verts=box.vertices()
        for face in FACES:
            vertices=verts[list(face)]
            normal=np.cross(vertices[1]-vertices[0],vertices[2]-vertices[1]);normal/=max(np.linalg.norm(normal),1e-9)
            light=np.array([-.4,-.6,.7]);light/=np.linalg.norm(light)
            shade=.55+.45*abs(float(np.dot(normal,light)))
            polygons.append((float(np.mean((vertices-centre)@forward)),vertices,box.colour or colours[box.kind],shade,box.kind))
    draw.ellipse((width*.16,height*.75,width*.84,height*.87),fill='#e2ded5')
    def screen(vertices):
        local=vertices-centre
        return list(zip(width/2+local@right*scale,height*.49-local@up*scale))
    for _,vertices,colour,shade,kind in sorted(polygons,key=lambda p:p[0],reverse=True):
        tint=tuple(np.clip(rgb(colour)*shade,0,255).astype(int));draw.polygon(screen(vertices),fill=tint)
        if settings['finish']=='Wood grain' and kind in ('door','carcass'):
            for i in range(16):
                a=i/16;b=(i+1)/16
                stripe=np.array([vertices[0]*(1-a)+vertices[1]*a,vertices[0]*(1-b)+vertices[1]*b,vertices[3]*(1-b)+vertices[2]*b,vertices[3]*(1-a)+vertices[2]*a])
                c=tuple(np.clip(rgb(colour)*shade*(.89+.1*math.sin(i*1.8)),0,255).astype(int))
                draw.polygon(screen(stripe),fill=c)
        draw.line(screen(np.vstack([vertices,vertices[0]])),fill=tuple(np.clip(np.array(tint)*.8,0,255).astype(int)),width=1)
    draw.text((20,18),'KITCHEN WORKSHOP | DESIGN TURNTABLE',fill='#213547')
    draw.text((20,height-36),'Design presentation | dimensions in mm',fill='#213547')
    return image


def create_video(settings):
    if settings['format'] not in FORMATS or settings['seconds'] not in range(3,13):
        raise ValueError('Choose a 3–12 second video and a supported format.')
    if not shutil.which('ffmpeg'):raise ValueError('Video generation requires FFmpeg installed on the server.')
    output=video_path(settings)
    if output.exists():return output
    boxes=[Box(**b) for b in settings['scene']] if settings.get('scene') else cabinet_geometry(settings['width'],settings['height'],settings['depth'],settings['thickness'],settings['shelves'],settings['clearance'],settings['door_thickness'],settings['open_door'])
    if settings.get('hardware') and not settings.get('scene'):
        for i in range(min(settings['hinges'],12)):
            z=settings['height']*(i+1)/(settings['hinges']+1)
            boxes.append(Box('Illustrative hinge',(settings['thickness'],5,z-10),(24,35,20),'metal'))
    output.parent.mkdir(parents=True,exist_ok=True)
    width,height=FORMATS[settings['format']]
    with tempfile.TemporaryDirectory(dir=output.parent) as directory:
        temp=Path(directory)/'video.mp4';log=Path(directory)/'ffmpeg.log'
        command=['ffmpeg','-hide_banner','-loglevel','error','-f','rawvideo','-pix_fmt','rgb24','-s',f'{width}x{height}','-r',str(FPS),'-i','pipe:0','-an','-c:v','libx264','-threads','2','-preset','veryfast','-crf','21','-pix_fmt','yuv420p','-movflags','+faststart','-y',str(temp)]
        with log.open('w') as errors:
            process=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=errors)
            try:
                frames=settings['seconds']*FPS
                for i in range(frames):
                    image=frame_image(boxes,settings,math.radians(-55)+i/frames*math.tau)
                    process.stdin.write(image.tobytes())
                process.stdin.close()
                code=process.wait(timeout=60)
                if code or not temp.exists() or temp.stat().st_size<1000:raise ValueError('Video encoding failed.')
                temp.replace(output)
            except BaseException:
                process.kill();process.wait();raise
    return output
