"""OPTIONAL final-stage-only MP4/RTSP driver. NOT run during synthetic acceptance.
Requires user-supplied local YOLO weights and rights to video/model.
No pretrained weight downloading or remote inference is performed by this script.
"""
from __future__ import annotations
import argparse,json,sys

def main(argv=None):
    p=argparse.ArgumentParser()
    p.add_argument('--source',required=True,help='Local MP4 or authorized RTSP URL')
    p.add_argument('--weights',required=True,help='Existing local Ultralytics YOLOv8 .pt weights')
    p.add_argument('--enable-real-video',action='store_true')
    p.add_argument('--max-frames',type=int,default=1000)
    a=p.parse_args(argv)
    if not a.enable_real_video:raise SystemExit('REAL_VIDEO_DISABLED_UNTIL_FINAL_EVALUATION')
    from pathlib import Path
    if not Path(a.weights).is_file():raise SystemExit('WEIGHTS_MUST_EXIST_LOCALLY')
    import cv2
    from ultralytics import YOLO
    model=YOLO(a.weights)
    cap=cv2.VideoCapture(a.source)
    if not cap.isOpened():raise SystemExit('VIDEO_OPEN_FAILED')
    last=-1.
    try:
        for i in range(a.max_frames):
            ok,frame=cap.read()
            if not ok:break
            pos_ms=cap.get(cv2.CAP_PROP_POS_MSEC)
            timestamp=pos_ms/1000. if pos_ms>0 else None
            if timestamp is None or timestamp<=last:
                raise RuntimeError('NON_MONOTONIC_OR_UNVERIFIABLE_VIDEO_PTS: do not guess FPS')
            last=timestamp
            results=model.predict(frame,verbose=False)
            detections=[]
            for box in results[0].boxes:
                axy=box.xyxy[0].cpu().numpy().tolist()
                detections.append({'u':(axy[0]+axy[2])/2.,'v':axy[3],
                                   'confidence':float(box.conf[0]),
                                   'bbox_xywh':[axy[0],axy[1],axy[2]-axy[0],axy[3]-axy[1]]})
            print(json.dumps({'schema_version':'1.0','type':'frame','source':'REAL_UNVALIDATED',
                              'frame':i,'timestamp_s':timestamp,'detections':detections}),flush=True)
    finally:cap.release()
if __name__=='__main__':main()
