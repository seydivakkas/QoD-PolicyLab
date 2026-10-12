# Three Labs — Optional integrated SYNTHETIC research demo

The three research repos remain independent. This directory is only a bridging **prototype**; it is not a verified backend acceptance system, automotive controller, or 5G API client.

## Installation and development (Windows PowerShell)

Clone the three repositories as sibling directories under one `Projects` folder. From `Projects`:

```powershell
py -m pip install -e ./KalmanTrackLab -e ./BEV-MotionLab -e ./QoD-PolicyLab fastapi uvicorn
py ./QoD-PolicyLab/integrations/three_labs/run_pipeline.py --frames 120 --out synthetic-demo.jsonl
py ./QoD-PolicyLab/integrations/three_labs/server.py
```

Use a second terminal:

```powershell
cd ./QoD-PolicyLab/integrations/three_labs/frontend
npm install
npm run dev
```

UI: http://127.0.0.1:5173; localhost WebSocket: 127.0.0.1:8787. The application requires no network provider or subscription while running. The initial Python/Node dependency installation may require internet unless wheel/npm caches are provided. Windows packaging is NOT yet an offline installer. No user-provided video has been tested. `THREE_LABS_WS_TOKEN` is an optional local-only extra guard; a client passing that secret through a query URL must be configured explicitly.

## Canonical stream contract

- Driver -> Kalman: `{"schema_version":"1.0","type":"frame","timestamp_s":0.1,"detections":[{"u":100,"v":150,"confidence":0.9}]}`
- Kalman -> BEV: pixel XY, 2x2 covariance, track identity, tracking validity.
- BEV -> QoD: calibrated XY metres, 2x2 metric covariance, speed, valid/invalid flags.
- QoD -> UI: synthetic TTC lower bound, decision, cost, state and warnings.
- All transfers: UTF-8 JSONL, one bounded object per line; errors emitted as explicit records.

**Deliberate boundaries:** default homography is a synthetic scale, not a physical calibration. Instantaneous speed noise assumes uncorrelated successive positions and may underestimate uncertainty when filter correlations matter; treat as demonstration only. QoD activated state is a visual mock and not the full accepted session FSM. The local failsafe state is a warning and does NOT apply physical brakes. There are no guarantees of 60 FPS tracking/UI, zero identity switches, measured collision risk or improved real-world QoD.

## Future final-stage-only driver

`driver/video_driver.py` is an **opt-in skeleton** requiring a user-provided licensed local YOLOv8 weight file, permitted MP4/RTSP source and explicit `--enable-real-video`. It intentionally does not fetch model weights. Raw RTSP video timestamps and codec provenance are **not** independently validated by the skeleton: do not treat as an accepted field driver. No real imagery is used during the synthetic stage.
