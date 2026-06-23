"""
CropScan AI — app.py
════════════════════
Flask backend for the CropScan AI plant-disease detector.

Run:
    python app.py

Expects the model/ folder (produced by train_model.py) to sit next to this file:
    model/
      cropscan_resnet50.pth   <- trained weights
      class_names.json        <- ["Apple___Apple_scab", ...]
"""

import json
import logging
import os
import io

import torch
import torch.nn as nn
from torchvision import models, transforms
from PIL import Image
from flask import Flask, request, jsonify, render_template

# ─────────────────────────────────────────────────────────────────────────────
#  Logging
# ─────────────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
#  Paths  — everything is relative to THIS file's directory
# ─────────────────────────────────────────────────────────────────────────────
BASE_DIR        = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR       = os.path.join(BASE_DIR, "model")
WEIGHTS_PATH    = os.path.join(MODEL_DIR, "cropscan_resnet50.pth")
CLASS_JSON_PATH = os.path.join(MODEL_DIR, "class_names.json")
CLASS_TXT_PATH  = os.path.join(MODEL_DIR, "class_names.txt")

# ─────────────────────────────────────────────────────────────────────────────
#  Treatment database  (keyword -> advice)
# ─────────────────────────────────────────────────────────────────────────────
TREATMENTS = {
    "Apple_scab":                   "Apply fungicides containing captan or myclobutanil at bud break. Rake and destroy fallen leaves. Prune for better air circulation. Use scab-resistant apple varieties in future plantings.",
    "Black_rot":                    "Prune and destroy all infected wood, fruit, and leaves. Apply copper-based or captan fungicide. Ensure good drainage. Remove mummified fruits from the tree and ground.",
    "Cedar_apple_rust":             "Apply fungicides (myclobutanil or propiconazole) from pink bud stage through cover sprays. Remove nearby juniper/cedar host trees if possible. Use resistant apple varieties.",
    "Powdery_mildew":               "Apply neem oil, potassium bicarbonate, or sulfur-based fungicide. Improve air circulation by pruning. Water at the base — avoid wetting foliage. Remove heavily infected shoots.",
    "Cercospora":                   "Apply chlorothalonil or copper fungicide. Rotate crops — avoid planting corn in the same field for 1-2 seasons. Bury crop residue after harvest.",
    "Common_rust":                  "Apply azoxystrobin or propiconazole fungicide early. Plant rust-resistant hybrid varieties. Monitor crops closely during warm, humid weather.",
    "Northern_Leaf_Blight":         "Apply fungicides (azoxystrobin, propiconazole) at early tasselling. Use resistant hybrids. Rotate crops and till infected residue into the soil.",
    "Esca":                         "No effective chemical cure. Prune infected wood 10-15 cm below visible symptoms. Seal wounds with wound protectant. Remove and destroy severely infected vines.",
    "Leaf_blight":                  "Apply copper oxychloride or mancozeb fungicide. Improve canopy airflow via pruning. Avoid overhead irrigation. Remove and destroy infected leaves promptly.",
    "Haunglongbing":                "No cure exists for citrus greening (HLB). Remove and destroy infected trees. Control Asian citrus psyllid vector with insecticides. Use certified disease-free nursery stock.",
    "Bacterial_spot":               "Apply copper hydroxide + mancozeb sprays preventively. Use disease-free transplants. Avoid overhead irrigation. Practice 2-3 year crop rotation.",
    "Early_blight":                 "Remove infected lower leaves immediately. Apply chlorothalonil or copper fungicide every 7-10 days. Avoid overhead watering. Rotate crops annually.",
    "Late_blight":                  "Apply mancozeb or chlorothalonil at first sign. Destroy all infected plant material (do NOT compost). Avoid overhead irrigation. Plant resistant varieties.",
    "Leaf_Mold":                    "Improve greenhouse ventilation to reduce humidity below 85%. Apply chlorothalonil or copper fungicide. Remove infected leaves. Avoid wetting foliage when watering.",
    "Septoria_leaf_spot":           "Apply chlorothalonil, mancozeb, or copper fungicide. Remove infected leaves. Avoid working with wet plants. Mulch base to prevent soil splash.",
    "Spider_mites":                 "Apply miticide (abamectin or bifenazate) or insecticidal soap. Increase humidity around plants. Introduce predatory mites (Phytoseiulus persimilis) as biological control.",
    "Target_Spot":                  "Apply azoxystrobin or chlorothalonil fungicide. Remove infected plant material. Ensure good air circulation. Avoid excessive nitrogen fertilisation.",
    "Tomato_Yellow_Leaf_Curl_Virus":"No chemical cure. Remove and destroy infected plants immediately. Control whitefly vectors with yellow sticky traps, insecticidal soap, or neem oil. Use virus-resistant varieties.",
    "Tomato_mosaic_virus":          "No cure. Remove and destroy infected plants. Disinfect tools with 10% bleach solution. Control aphid vectors. Plant mosaic-resistant varieties.",
    "Leaf_scorch":                  "Remove and destroy infected leaves. Apply copper-based fungicide in early spring. Avoid overhead irrigation. Ensure good drainage and air circulation.",
    "healthy":                      "No disease detected! Maintain regular watering, balanced fertilisation, and periodic neem oil spray (every 3-4 weeks) as prevention.",
}

def get_treatment(class_name: str) -> str:
    """Match predicted class name to a treatment suggestion."""
    for keyword, suggestion in TREATMENTS.items():
        if keyword.lower() in class_name.lower():
            return suggestion
    if "healthy" in class_name.lower():
        return TREATMENTS["healthy"]
    return (
        "Isolate affected plants immediately. Remove visibly infected tissue. "
        "Consult your local agricultural extension office for region-specific "
        "treatment protocols tailored to this disease."
    )

# ─────────────────────────────────────────────────────────────────────────────
#  Built-in fallback — full 38-class PlantVillage list
#  Used when model/class_names.json is missing (prevents "class_12" output)
# ─────────────────────────────────────────────────────────────────────────────
BUILTIN_CLASS_NAMES = [
    "Apple___Apple_scab",
    "Apple___Black_rot",
    "Apple___Cedar_apple_rust",
    "Apple___healthy",
    "Blueberry___healthy",
    "Cherry_(including_sour)___Powdery_mildew",
    "Cherry_(including_sour)___healthy",
    "Corn_(maize)___Cercospora_leaf_spot Gray_leaf_spot",
    "Corn_(maize)___Common_rust_",
    "Corn_(maize)___Northern_Leaf_Blight",
    "Corn_(maize)___healthy",
    "Grape___Black_rot",
    "Grape___Esca_(Black_Measles)",
    "Grape___Leaf_blight_(Isariopsis_Leaf_Spot)",
    "Grape___healthy",
    "Orange___Haunglongbing_(Citrus_greening)",
    "Peach___Bacterial_spot",
    "Peach___healthy",
    "Pepper,_bell___Bacterial_spot",
    "Pepper,_bell___healthy",
    "Potato___Early_blight",
    "Potato___Late_blight",
    "Potato___healthy",
    "Raspberry___healthy",
    "Soybean___healthy",
    "Squash___Powdery_mildew",
    "Strawberry___Leaf_scorch",
    "Strawberry___healthy",
    "Tomato___Bacterial_spot",
    "Tomato___Early_blight",
    "Tomato___Late_blight",
    "Tomato___Leaf_Mold",
    "Tomato___Septoria_leaf_spot",
    "Tomato___Spider_mites Two-spotted_spider_mite",
    "Tomato___Target_Spot",
    "Tomato___Tomato_Yellow_Leaf_Curl_Virus",
    "Tomato___Tomato_mosaic_virus",
    "Tomato___healthy",
]

# ─────────────────────────────────────────────────────────────────────────────
#  Class names  — loaded from model/class_names.json (saved by train_model.py)
# ─────────────────────────────────────────────────────────────────────────────
def load_class_names() -> list:
    """
    Load class names from the JSON file saved by train_model.py.
    Tries .json first, then .txt. Raises FileNotFoundError if neither exists.
    """
    if os.path.isfile(CLASS_JSON_PATH):
        with open(CLASS_JSON_PATH, "r") as f:
            names = json.load(f)
        log.info(f"Loaded {len(names)} class names from {CLASS_JSON_PATH}")
        return names

    if os.path.isfile(CLASS_TXT_PATH):
        with open(CLASS_TXT_PATH, "r") as f:
            names = [line.strip() for line in f if line.strip()]
        log.warning(f"class_names.json not found — loaded {len(names)} classes from .txt fallback")
        return names

    log.warning(
        f"class_names.json not found in {MODEL_DIR} — using built-in 38-class list."
    )
    return BUILTIN_CLASS_NAMES

# ─────────────────────────────────────────────────────────────────────────────
#  Model — num_classes is read FROM THE CHECKPOINT ITSELF, never hardcoded
# ─────────────────────────────────────────────────────────────────────────────
def load_model(weights_path: str, device: torch.device):
    """
    Load the ResNet-50 model.

    FIX: We inspect the saved fc.1.weight tensor shape to get num_classes
    dynamically — so app.py always matches whatever train_model.py produced,
    even if the number of classes changes between training runs.
    """
    if not os.path.isfile(weights_path):
        raise FileNotFoundError(
            f"Model weights not found at: {weights_path}\n"
            f"  Run train_model.py first."
        )

    # Load raw state_dict to read the output dimension
    state_dict = torch.load(weights_path, map_location=device)

    # Find the FC weight key — handles both nn.Linear and nn.Sequential(Dropout, Linear)
    fc_key = None
    for candidate in ("fc.1.weight", "fc.weight"):
        if candidate in state_dict:
            fc_key = candidate
            break
    if fc_key is None:
        # Last-resort search
        fc_key = next((k for k in state_dict if "fc" in k and "weight" in k), None)
    if fc_key is None:
        raise KeyError(
            "Cannot locate FC layer weight in checkpoint.\n"
            "Keys found: " + ", ".join(list(state_dict.keys())[:15])
        )

    # shape is [num_classes, in_features]
    num_classes = state_dict[fc_key].shape[0]
    log.info(f"Checkpoint: {num_classes} output classes (from '{fc_key}')")

    # Build architecture to match checkpoint exactly
    model = models.resnet50(weights=None)       # offline safe — no download
    in_features = model.fc.in_features
    model.fc = nn.Sequential(
        nn.Dropout(0.4),
        nn.Linear(in_features, num_classes),
    )

    model.load_state_dict(state_dict)
    model.to(device)
    model.eval()
    log.info(f"Model loaded successfully ({num_classes} classes, device={device})")
    return model, num_classes

# ─────────────────────────────────────────────────────────────────────────────
#  Image pre-processing  (must match VAL_TRANSFORM in train_model.py)
# ─────────────────────────────────────────────────────────────────────────────
INFER_TRANSFORM = transforms.Compose([
    transforms.Resize(256),
    transforms.CenterCrop(224),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std =[0.229, 0.224, 0.225],
    ),
])

# ─────────────────────────────────────────────────────────────────────────────
#  Startup — load everything once at import time
# ─────────────────────────────────────────────────────────────────────────────
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
log.info(f"Device: {device}")

# Load class names — never empty; falls back to BUILTIN_CLASS_NAMES if JSON missing
CLASS_NAMES = load_class_names()

# Load model
MODEL             = None
MODEL_NUM_CLASSES = 0
try:
    MODEL, MODEL_NUM_CLASSES = load_model(WEIGHTS_PATH, device)

    # Cross-check class names vs model output size
    if CLASS_NAMES and len(CLASS_NAMES) != MODEL_NUM_CLASSES:
        log.warning(
            f"MISMATCH: class_names has {len(CLASS_NAMES)} entries "
            f"but model outputs {MODEL_NUM_CLASSES} classes. "
            f"Re-run train_model.py to regenerate class_names.json."
        )
        # Pad or trim so index lookups never crash
        if len(CLASS_NAMES) < MODEL_NUM_CLASSES:
            CLASS_NAMES += [f"class_{i}" for i in range(len(CLASS_NAMES), MODEL_NUM_CLASSES)]
        else:
            CLASS_NAMES = CLASS_NAMES[:MODEL_NUM_CLASSES]

except FileNotFoundError as e:
    log.error(str(e))
except Exception as e:
    log.error(f"Failed to load model: {e}")

# ─────────────────────────────────────────────────────────────────────────────
#  Flask app
# ─────────────────────────────────────────────────────────────────────────────
app = Flask(__name__, template_folder="templates", static_folder="static")
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024   # 10 MB limit

ALLOWED_MIMES = {"image/jpeg", "image/png", "image/webp"}


@app.route("/")
def index():
    return render_template("home.html")


@app.route("/scan")
def scan():
    return render_template("scan.html")


@app.route("/guide")
def guide():
    return render_template("guide.html")


@app.route("/status")
def status():
    """Health-check endpoint — open /status in your browser to debug."""
    return jsonify({
        "model_loaded"    : MODEL is not None,
        "num_classes"     : MODEL_NUM_CLASSES,
        "class_names_len" : len(CLASS_NAMES),
        "device"          : str(device),
        "weights_path"    : WEIGHTS_PATH,
        "class_json_path" : CLASS_JSON_PATH,
        "weights_exists"  : os.path.isfile(WEIGHTS_PATH),
        "json_exists"     : os.path.isfile(CLASS_JSON_PATH),
    })


@app.route("/predict", methods=["POST"])
def predict():
    # Guard: model must be loaded
    if MODEL is None:
        return jsonify({
            "error": (
                "Model is not loaded. "
                "Run train_model.py first to generate model/cropscan_resnet50.pth"
            )
        }), 503

    # Validate file
    if "image" not in request.files:
        return jsonify({"error": "No 'image' field found in request."}), 400
    file = request.files["image"]
    if file.filename == "":
        return jsonify({"error": "Empty filename."}), 400
    if file.mimetype not in ALLOWED_MIMES:
        return jsonify({"error": f"Unsupported type: {file.mimetype}. Use JPG, PNG, or WEBP."}), 400

    # Load and preprocess image
    try:
        img = Image.open(io.BytesIO(file.read())).convert("RGB")
        tensor = INFER_TRANSFORM(img).unsqueeze(0).to(device)   # [1, 3, 224, 224]
    except Exception as e:
        return jsonify({"error": f"Could not process image: {e}"}), 422

    # Inference
    with torch.no_grad():
        probs          = torch.softmax(MODEL(tensor), dim=1)
        confidence, idx = probs.max(dim=1)

    idx        = idx.item()
    confidence = round(confidence.item() * 100, 1)
    class_name = CLASS_NAMES[idx] if idx < len(CLASS_NAMES) else f"class_{idx}"
    suggestion = get_treatment(class_name)

    # Human-readable: "Apple___Apple_scab" -> "Apple — Apple Scab"
    display_name = class_name.replace("___", " — ").replace("_", " ").title()

    log.info(f"Prediction: {display_name} ({confidence}%)")

    return jsonify({
        "disease"   : display_name,
        "confidence": confidence,
        "suggestion": suggestion,
    })


# ─────────────────────────────────────────────────────────────────────────────
#  Entry point
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    port         = int(os.environ.get("PORT", 5000))
    model_status = "✔ loaded" if MODEL is not None else "✗ not loaded — run train_model.py first"
    print(f"\n  🌿  CropScan AI running at http://localhost:{port}")
    print(f"  Model status : {model_status}")
    if MODEL is not None:
        print(f"  Classes      : {MODEL_NUM_CLASSES}")
    print()
    app.run(host="0.0.0.0", port=port, debug=False)