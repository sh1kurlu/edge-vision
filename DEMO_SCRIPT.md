# Demo Video Script (3–5 minutes)

Record a screen capture demonstrating the Document Scanner application.

## Preparation

```bash
cd document_scanner
source venv/bin/activate
python scripts/generate_examples.py   
python main.py
```

## Scene 1 — Launch (0:00–0:30)

- Show terminal: `python main.py`
- Application window opens with empty preview panels
- Briefly describe the purpose: automatic document detection and scanning

## Scene 2 — Upload & Scan (0:30–2:00)

Upload and scan at least three images from `examples/`:

1. `02_angle_25.jpg` — perspective distortion
2. `04_shadow.jpg` — uneven lighting
3. `06_noise.jpg` — image noise

For each image:
- Click **Upload Image**
- Show original in left panel
- Click **Scan Document**
- Show scanned result in right panel
- Mention status message and processing time

## Scene 3 — Settings (2:00–3:00)

- Switch **Enhancement** to **Otsu Threshold** and rescan one image
- Switch back to **Adaptive Threshold**
- Adjust **Canny Lower** threshold and show effect on a difficult image (optional)

## Scene 4 — Save Outputs (3:00–4:00)

- Click **Save Result**
- Save as PNG
- Scan another image and save as PDF
- Show saved files in file manager

## Scene 5 — Wrap-up (4:00–5:00)

- Summarize pipeline: edge detection → contour → perspective correction → enhancement
- Mention benchmark: 12/12 detection success on test images
- End

## Recording Tools

- **macOS:** QuickTime Player → File → New Screen Recording
- **Windows:** Xbox Game Bar (Win+G) or OBS Studio
- **Cross-platform:** [OBS Studio](https://obsproject.com/)

Save as `assets/demo.mp4` or include a link in your submission.
