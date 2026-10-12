# Three Labs — Optional integrated SYNTHETIC research demo

The three research repos remain independent. This directory is only a bridging **prototype**; it is not a verified backend acceptance system, automotive controller, or 5G API client.

## Offline install (Windows PowerShell)

Install a compatible local Python 3.11+ and the checked-out branch of each repository, then from this folder:

```powershell
py -m pip install -e ..\..\KalmanTrackLab -e ..\..\BEV-MotionLab -e ..\..\QoD-PolicyLab scipy fastapi uvicorn
py run_pipeline.py --frames 120 --out synthetic-demo.jsonl
py server.py
```

The repository checkout paths above are illustrative: adjust to your actual folder layout. Install all dependencies ahead of time; then the demo itself needs no remote inference/API.

For the browser in a separate terminal:

```powershell
cd frontend
npm install
npm run dev
```

View http://127.0.0.1:5173. WebSocket connects to 127.0.0.1:8787, localhost only. For local usage set `THREE_LABS_WS_TOKEN` to a random secret and pass it in the client URL if needed; no secret is built into the sample. The UI control sliders are experimental runtime overrides; do **not** use these settings as proof of frozen acceptance. The frontend intentionally shows `BACKEND HOLD`.

## Canonical stream contract

- Driver -> Kalman: `{"schema_version":"1.0","type":"frame","timestamp_s":0.1,"detections":[{"u":100,"v":150,"confidence":0.9}]}`
- Kalman -> BEV: pixel XY, 2x2 covariance, track identity, tracking validity.
- BEV -> QoD: calibrated XY metres, 2x2 metric covariance, speed, valid/invalid flags.
- QoD -> UI: synthetic TTC lower bound, decision, cost, state and warnings.
- All transfers: UTF-8 JSONL, one bounded object per line; errors emitted as explicit records.

**Deliberate boundaries:** default homography is a synthetic scale, not a physical calibration. Instantaneous speed noise assumes uncorrelated successive positions and may underestimate uncertainty when filter correlations matter; treat as demonstration only. QoD activated state is a visual mock and not the full accepted session FSM. The local failsafe state is a warning and does NOT apply physical brakes. There are no guarantees of 60 FPS tracking/UI, zero identity switches, measured collision risk or improved real-world QoD.

## Future final-stage-only driver

`driver/video_driver.py` is an **opt-in skeleton** requiring a user-provided licensed local YOLOv8 weight file, permitted MP4/RTSP source and explicit `--enable-real-video`. It intentionally does not fetch model weights. Raw RTSP video timestamps and codec provenance are **not** independently validated by the skeleton: do not treat as an accepted field driver. No real imagery is used during the synthetic stage.
