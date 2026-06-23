"""
CropScan AI — train_model.py
════════════════════════════
Trains a ResNet-50 on the PlantVillage dataset and saves the weights to
  model/cropscan_resnet50.pth
along with the ordered class list at
  model/class_names.txt

═══════ QUICK START ═════════════════════════════════════════════════════════

1.  Install dependencies
    pip install torch torchvision pillow tqdm

2.  Download the PlantVillage dataset (choose ONE option):

    Option A — Kaggle  (recommended, full colour dataset)
      kaggle datasets download -d abdallahalidev/plantvillage-dataset
      unzip plantvillage-dataset.zip -d data/

    Option B — Manual
      Download from https://github.com/spMohanty/PlantVillage-Dataset
      and place it so the folder structure looks like:

        data/
          plantvillage dataset/
            color/
              Apple___Apple_scab/
                image1.JPG
                ...
              Apple___Black_rot/
                ...

3.  Run training
    python train_model.py

    Key flags:
      --data_dir   Path to the colour folder   (default: data/plantvillage dataset/color)
      --epochs     Max epochs                  (default: 25)
      --batch      Batch size                  (default: 32)
      --lr         Initial learning rate       (default: 1e-4)
      --data_fraction  Fraction of data to use, e.g. 0.25  (default: 0.1 = 10%)
      --workers        DataLoader workers               (default: 4)
      --resume     Path to checkpoint to resume from

    Example with custom paths:
      python train_model.py --data_dir /path/to/color --epochs 30 --batch 64

4.  After training, copy model/ into your Flask project root and start:
      python app.py

═════════════════════════════════════════════════════════════════════════════
"""

import argparse
import os
import copy
import json
import time

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, random_split
from torchvision import datasets, models, transforms
from tqdm import tqdm

# ─────────────────────────────────────────────────────────────────────────────
#  Hyperparameters  (overridden by CLI flags)
# Data source file loaction
# ─────────────────────────────────────────────────────────────────────────────
DEFAULTS = dict(
    data_dir      = os.path.join("data", "plantvillage dataset", "color"),
    output_dir    = "model",
    epochs        = 25,
    batch         = 32,
    lr            = 1e-4,
    weight_decay  = 1e-4,
    val_split     = 0.15,   # 15 % held out for validation
    data_fraction = 0.1,    # use 1.0 for full dataset, 0.1 for 10%, etc.
    workers       = 4,
    patience      = 5,      # early-stopping patience (epochs without improvement)
    seed          = 42,
    resume        = None,
)

# ─────────────────────────────────────────────────────────────────────────────
#  Image transforms
# ─────────────────────────────────────────────────────────────────────────────
IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD  = [0.229, 0.224, 0.225]

TRAIN_TRANSFORM = transforms.Compose([
    transforms.RandomResizedCrop(224, scale=(0.7, 1.0)),
    transforms.RandomHorizontalFlip(),
    transforms.RandomVerticalFlip(),
    transforms.ColorJitter(brightness=0.3, contrast=0.3, saturation=0.2, hue=0.05),
    transforms.RandomRotation(15),
    transforms.ToTensor(),
    transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
])

VAL_TRANSFORM = transforms.Compose([
    transforms.Resize(256),
    transforms.CenterCrop(224),
    transforms.ToTensor(),
    transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
])


# ─────────────────────────────────────────────────────────────────────────────
#  Dataset helpers
# ─────────────────────────────────────────────────────────────────────────────

def find_image_folder(data_dir: str) -> str:
    """
    ImageFolder requires a directory whose DIRECT children are the class folders
    (each sub-folder = one class, containing images).

    The PlantVillage Kaggle zip unpacks like this:
      plantvillage dataset/
        color/          <-- 38 class folders HERE  ✔
          Apple___Apple_scab/
            img.JPG
          ...
        grayscale/      <-- also 38 class folders
        segmented/      <-- also 38 class folders

    Naively stopping at the first level with >= 2 image-dirs would pick
    'plantvillage dataset/' and see only 3 "classes" (color, grayscale,
    segmented).  Instead we search every candidate level and return the one
    with the MOST image-containing sub-directories — that will be 38, not 3.
    """
    import os

    IMG_EXTS = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'}

    def _count_class_dirs(path):
        """Count sub-dirs of path that contain at least one image file."""
        count = 0
        try:
            for entry in os.scandir(path):
                if not entry.is_dir():
                    continue
                try:
                    for f in os.scandir(entry.path):
                        if os.path.splitext(f.name)[1].lower() in IMG_EXTS:
                            count += 1
                            break
                except PermissionError:
                    pass
        except PermissionError:
            pass
        return count

    # Build a list of (candidate_path, class_count) for up to 4 levels deep
    best_path  = data_dir
    best_count = _count_class_dirs(data_dir)

    queue = [data_dir]
    for _ in range(4):                         # search up to 4 levels deep
        next_queue = []
        for current in queue:
            try:
                subdirs = [e.path for e in os.scandir(current) if e.is_dir()]
            except PermissionError:
                continue
            for sd in subdirs:
                n = _count_class_dirs(sd)
                if n > best_count:             # strictly more classes = better
                    best_count = n
                    best_path  = sd
                next_queue.append(sd)
        queue = next_queue
        if not queue:
            break

    return best_path


def load_datasets(data_dir: str, val_split: float, seed: int, data_fraction: float = 1.0):
    """
    Load PlantVillage from ImageFolder, optionally sub-sample a fraction of
    images (stratified per class), then split into train / val.

    data_fraction=0.10  use 10% of images from each class (balanced).
    data_fraction=1.0   use the full dataset.
    """
    # ── Auto-detect the correct subfolder level ───────────────────────────────
    resolved_dir = find_image_folder(data_dir)
    if resolved_dir != data_dir:
        print(f"\n  [INFO] data_dir auto-resolved:")
        print(f"         given    : {data_dir}")
        print(f"         resolved : {resolved_dir}")

    full_dataset = datasets.ImageFolder(resolved_dir)
    class_names  = full_dataset.classes

    # ── Sanity-check: must find more than 1 class ─────────────────────────────
    if len(class_names) < 2:
        print("\n" + "!" * 60)
        print(f"  ERROR: Only {len(class_names)} class(es) found in:\n  {resolved_dir}")
        print("\n  ImageFolder expects this structure:")
        print("    <data_dir>/")
        print("      Apple___Apple_scab/   <- one folder per disease")
        print("        image1.JPG")
        print("        image2.JPG")
        print("      Apple___Black_rot/")
        print("        ...")
        print("\n  Actual contents of your data_dir:")
        try:
            entries = sorted(os.listdir(resolved_dir))
            for e in entries[:20]:
                full = os.path.join(resolved_dir, e)
                kind = "DIR " if os.path.isdir(full) else "FILE"
                print(f"    [{kind}] {e}")
            if len(entries) > 20:
                print(f"    ... and {len(entries)-20} more")
        except Exception as ex:
            print(f"    (could not list: {ex})")
        print("!" * 60 + "\n")
        raise SystemExit(1)

    print(f"\n  ✔ Found {len(class_names)} classes in {resolved_dir}")

    # Optional stratified sub-sampling
    if data_fraction < 1.0:
        from collections import defaultdict
        import random as _random
        _random.seed(seed)

        # Group indices by class
        class_indices = defaultdict(list)
        for idx, (_, label) in enumerate(full_dataset.samples):
            class_indices[label].append(idx)

        # Keep data_fraction of each class (at least 1 image)
        kept_indices = []
        for label, indices in sorted(class_indices.items()):
            k = max(1, int(len(indices) * data_fraction))
            kept_indices.extend(_random.sample(indices, k))

        full_dataset = torch.utils.data.Subset(full_dataset, kept_indices)
        n_total = len(kept_indices)
        print(f"\n  Using {data_fraction*100:.0f}% of dataset -> {n_total:,} images (stratified across {len(class_names)} classes)")
    else:
        n_total = len(full_dataset)

    # Train / val split
    n_val   = int(n_total * val_split)
    n_train = n_total - n_val

    generator = torch.Generator().manual_seed(seed)
    train_subset, val_subset = random_split(full_dataset, [n_train, n_val], generator=generator)

    train_dataset = TransformSubset(train_subset, TRAIN_TRANSFORM)
    val_dataset   = TransformSubset(val_subset,   VAL_TRANSFORM)

    print(f"  Dataset  : {resolved_dir}")
    print(f"  Classes  : {len(class_names)}")
    print(f"  Fraction : {data_fraction*100:.0f}%")
    print(f"  Train    : {n_train:,} images")
    print(f"  Val      : {n_val:,} images\n")

    return train_dataset, val_dataset, class_names


class TransformSubset(torch.utils.data.Dataset):
    """Thin wrapper that applies a transform to a Subset."""

    def __init__(self, subset, transform):
        self.subset    = subset
        self.transform = transform

    def __getitem__(self, idx):
        img, label = self.subset[idx]
        if self.transform:
            img = self.transform(img)
        return img, label

    def __len__(self):
        return len(self.subset)


# ─────────────────────────────────────────────────────────────────────────────
#  Model
# ─────────────────────────────────────────────────────────────────────────────

def build_model(num_classes: int, device: torch.device) -> nn.Module:
    """
    ResNet-50 pretrained on ImageNet, final FC replaced for num_classes.
    Only the classifier head is trained for the first few epochs (feature
    extraction warm-up), then the full network is fine-tuned.
    """
    model = models.resnet50(weights=models.ResNet50_Weights.IMAGENET1K_V2)

    # Freeze all layers initially
    for param in model.parameters():
        param.requires_grad = False

    # Replace final FC
    in_features = model.fc.in_features
    model.fc = nn.Sequential(
        nn.Dropout(0.4),
        nn.Linear(in_features, num_classes),
    )

    return model.to(device)


def unfreeze_all(model: nn.Module):
    """Unfreeze every layer for full fine-tuning."""
    for param in model.parameters():
        param.requires_grad = True


# ─────────────────────────────────────────────────────────────────────────────
#  Training loop
# ─────────────────────────────────────────────────────────────────────────────

def train_one_epoch(model, loader, criterion, optimizer, device, epoch):
    model.train()
    running_loss = 0.0
    correct      = 0
    total        = 0

    pbar = tqdm(loader, desc=f"Epoch {epoch:02d} [train]", leave=False)
    for images, labels in pbar:
        images, labels = images.to(device), labels.to(device)

        optimizer.zero_grad()
        outputs = model(images)
        loss    = criterion(outputs, labels)
        loss.backward()
        optimizer.step()

        running_loss += loss.item() * images.size(0)
        _, predicted  = outputs.max(1)
        correct += predicted.eq(labels).sum().item()
        total   += labels.size(0)

        pbar.set_postfix(loss=f"{loss.item():.4f}", acc=f"{100*correct/total:.1f}%")

    epoch_loss = running_loss / total
    epoch_acc  = correct / total
    return epoch_loss, epoch_acc


@torch.no_grad()
def evaluate(model, loader, criterion, device, epoch):
    model.eval()
    running_loss = 0.0
    correct      = 0
    total        = 0

    for images, labels in tqdm(loader, desc=f"Epoch {epoch:02d} [val  ]", leave=False):
        images, labels = images.to(device), labels.to(device)
        outputs = model(images)
        loss    = criterion(outputs, labels)

        running_loss += loss.item() * images.size(0)
        _, predicted  = outputs.max(1)
        correct += predicted.eq(labels).sum().item()
        total   += labels.size(0)

    epoch_loss = running_loss / total
    epoch_acc  = correct / total
    return epoch_loss, epoch_acc


# ─────────────────────────────────────────────────────────────────────────────
#  Main
# ─────────────────────────────────────────────────────────────────────────────

def main(cfg):
    torch.manual_seed(cfg.seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"\n  Device   : {device}")
    if device.type == "cuda":
        print(f"  GPU      : {torch.cuda.get_device_name(0)}")

    # ── Datasets ─────────────────────────────────────────────────────────────
    train_ds, val_ds, class_names = load_datasets(cfg.data_dir, cfg.val_split, cfg.seed, cfg.data_fraction)
    num_classes = len(class_names)

    train_loader = DataLoader(
        train_ds, batch_size=cfg.batch, shuffle=True,
        num_workers=cfg.workers, pin_memory=(device.type == "cuda"),
    )
    val_loader = DataLoader(
        val_ds, batch_size=cfg.batch * 2, shuffle=False,
        num_workers=cfg.workers, pin_memory=(device.type == "cuda"),
    )

    # ── Model ─────────────────────────────────────────────────────────────────
    model = build_model(num_classes, device)

    # ── Loss & optimiser ──────────────────────────────────────────────────────
    criterion = nn.CrossEntropyLoss(label_smoothing=0.1)

    # Phase 1 — train only the new FC head (warm-up, 3 epochs)
    optimizer = optim.AdamW(model.fc.parameters(), lr=cfg.lr * 10, weight_decay=cfg.weight_decay)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=cfg.epochs)

    WARMUP_EPOCHS = 3

    # ── Resume from checkpoint ────────────────────────────────────────────────
    start_epoch   = 1
    best_val_acc  = 0.0
    best_weights  = None
    no_improve    = 0
    history       = []

    if cfg.resume:
        ckpt = torch.load(cfg.resume, map_location=device)
        model.load_state_dict(ckpt["model_state"])
        optimizer.load_state_dict(ckpt["optim_state"])
        start_epoch  = ckpt["epoch"] + 1
        best_val_acc = ckpt.get("best_val_acc", 0.0)
        no_improve   = ckpt.get("no_improve", 0)
        history      = ckpt.get("history", [])
        print(f"  Resumed from {cfg.resume} (epoch {ckpt['epoch']})\n")

    os.makedirs(cfg.output_dir, exist_ok=True)

    # ── Training loop ─────────────────────────────────────────────────────────
    print("  Starting training...\n")
    t0 = time.time()

    for epoch in range(start_epoch, cfg.epochs + 1):

        # Phase 2 — unfreeze all after warm-up
        if epoch == WARMUP_EPOCHS + 1:
            print("  ── Unfreezing full network for fine-tuning ──")
            unfreeze_all(model)
            # Lower LR now that backbone is trainable
            for g in optimizer.param_groups:
                g["lr"] = cfg.lr
            scheduler = optim.lr_scheduler.CosineAnnealingLR(
                optimizer, T_max=cfg.epochs - WARMUP_EPOCHS
            )

        train_loss, train_acc = train_one_epoch(model, train_loader, criterion, optimizer, device, epoch)
        val_loss,   val_acc   = evaluate(model, val_loader, criterion, device, epoch)
        scheduler.step()

        elapsed = (time.time() - t0) / 60
        print(
            f"  Epoch {epoch:02d}/{cfg.epochs}  "
            f"train_loss={train_loss:.4f}  train_acc={train_acc*100:.2f}%  "
            f"val_loss={val_loss:.4f}  val_acc={val_acc*100:.2f}%  "
            f"[{elapsed:.1f} min]"
        )

        history.append(dict(
            epoch=epoch, train_loss=train_loss, train_acc=train_acc,
            val_loss=val_loss, val_acc=val_acc,
        ))

        # ── Save best model ───────────────────────────────────────────────────
        if val_acc > best_val_acc:
            best_val_acc = val_acc
            best_weights = copy.deepcopy(model.state_dict())
            no_improve   = 0
            torch.save(best_weights, os.path.join(cfg.output_dir, "cropscan_resnet50.pth"))
            print(f"    ✔ New best val_acc={best_val_acc*100:.2f}% — model saved.")
        else:
            no_improve += 1
            if no_improve >= cfg.patience:
                print(f"\n  Early stopping after {no_improve} epochs without improvement.\n")
                break

        # ── Checkpoint (allows resuming) ──────────────────────────────────────
        torch.save(
            dict(
                epoch=epoch, model_state=model.state_dict(),
                optim_state=optimizer.state_dict(),
                best_val_acc=best_val_acc, no_improve=no_improve,
                history=history,
            ),
            os.path.join(cfg.output_dir, "checkpoint_last.pth"),
        )

    # ── Save class names ──────────────────────────────────────────────────────
    class_names_path = os.path.join(cfg.output_dir, "class_names.txt")
    with open(class_names_path, "w") as f:
        f.write("\n".join(class_names))

    # Also save as JSON for easier loading
    with open(os.path.join(cfg.output_dir, "class_names.json"), "w") as f:
        json.dump(class_names, f, indent=2)

    # ── Training summary ──────────────────────────────────────────────────────
    total_time = (time.time() - t0) / 60
    print("\n" + "═" * 60)
    print(f"  Training complete in {total_time:.1f} minutes")
    print(f"  Best validation accuracy : {best_val_acc*100:.2f}%")
    print(f"  Model saved to           : {cfg.output_dir}/cropscan_resnet50.pth")
    print(f"  Class names saved to     : {class_names_path}")
    print("═" * 60 + "\n")

    # ── Save training history ─────────────────────────────────────────────────
    with open(os.path.join(cfg.output_dir, "training_history.json"), "w") as f:
        json.dump(history, f, indent=2)

    print("  Next step: place the 'model/' folder in your Flask project root")
    print("  and run:   python app.py\n")


# ─────────────────────────────────────────────────────────────────────────────
#  CLI
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CropScan AI — ResNet-50 training")
    parser.add_argument("--data_dir",    default=DEFAULTS["data_dir"])
    parser.add_argument("--output_dir",  default=DEFAULTS["output_dir"])
    parser.add_argument("--epochs",      type=int,   default=DEFAULTS["epochs"])
    parser.add_argument("--batch",       type=int,   default=DEFAULTS["batch"])
    parser.add_argument("--lr",          type=float, default=DEFAULTS["lr"])
    parser.add_argument("--weight_decay",type=float, default=DEFAULTS["weight_decay"])
    parser.add_argument("--val_split",     type=float, default=DEFAULTS["val_split"])
    parser.add_argument("--data_fraction", type=float, default=DEFAULTS["data_fraction"],
                        help="Fraction of dataset to use, e.g. 0.25 for 25%% (default: 0.1 = 10%%)")
    parser.add_argument("--workers",     type=int,   default=DEFAULTS["workers"])
    parser.add_argument("--patience",    type=int,   default=DEFAULTS["patience"])
    parser.add_argument("--seed",        type=int,   default=DEFAULTS["seed"])
    parser.add_argument("--resume",      default=DEFAULTS["resume"],
                        help="Path to a checkpoint to resume training from")

    args = parser.parse_args()

    # Validate data directory
    if not os.path.isdir(args.data_dir):
        print(f"\n  ✗ Data directory not found: {args.data_dir}")
        print("  Please download the PlantVillage dataset and point --data_dir to")
        print("  the 'color' sub-folder that contains one sub-directory per class.\n")
        raise SystemExit(1)

    main(args)