# CropScan AI — Project Files

## File Overview

| File | Purpose |
|------|---------|
| `train_model.py` | Standalone training script — run this FIRST |
| `app.py` | Flask backend with full model integration |
| `home.html` | Home page template |
| `scan.html` | Scan / upload page template |
| `guide.html` | Disease guide page template |
| `script.js` | Shared frontend logic (EN/HI/MR i18n, scan flow) |
| `style.css` | All styles |

## Quickstart

### Step 1 — Install dependencies
```bash
pip install flask pillow torch torchvision tqdm
```

### Step 2 — Download PlantVillage dataset
```bash
kaggle datasets download -d abdallahalidev/plantvillage-dataset
unzip plantvillage-dataset.zip -d data/
```

### Step 3 — Train the model (creates model/ folder)
```bash
python train_model.py
# Optional flags:
# python train_model.py --epochs 30 --batch 64 --data_dir /path/to/color
```

### Step 4 — Organise into Flask project structure
```
project/
├── app.py
├── train_model.py
├── model/
│   ├── cropscan_resnet50.pth   ← created by train_model.py
│   └── class_names.json        ← created by train_model.py
├── templates/
│   ├── home.html
│   ├── scan.html
│   └── guide.html
└── static/
    ├── style.css
    └── script.js
```

### Step 5 — Run the app
```bash
python app.py
# Open http://localhost:5000
```

## How It Works
- **train_model.py** fine-tunes a pretrained ResNet-50 (ImageNet) on PlantVillage with data augmentation, cosine LR schedule, early stopping, and label smoothing.
- **app.py** loads `model/cropscan_resnet50.pth` at startup. If missing, it starts in "no-model" mode and returns HTTP 503 on `/predict` with a clear message.
- The `/status` endpoint reports model load state, class count, and device (CPU/GPU).
