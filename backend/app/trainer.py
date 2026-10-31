import os
import random
import time
from pathlib import Path

import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader, Subset
from torchvision import datasets, transforms

from . import db

DATA_DIR = db.DATA_DIR
CHECKPOINT_DIR = DATA_DIR / "checkpoints"
TRAIN_SIZE = 12000
VALID_SIZE = 3000


class FashionMLP(nn.Module):
    def __init__(self, hidden_units=128, dropout=0.1):
        super().__init__()
        self.net = nn.Sequential(nn.Flatten(), nn.Linear(28 * 28, hidden_units), nn.ReLU(),
                                 nn.Dropout(dropout), nn.Linear(hidden_units, 10))

    def forward(self, x):
        return self.net(x)


def train(run_id, config):
    seed = int(config.get("seed", 42))
    random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)
    torch.set_num_threads(max(1, min(4, os.cpu_count() or 1)))
    start = time.time()
    db.update_run(run_id, status="running")
    try:
        allow_download = os.getenv("LOOPLAB_ALLOW_DOWNLOAD", "1") != "0"
        transform = transforms.ToTensor()
        root = DATA_DIR / "fashion-mnist"
        train_data = datasets.FashionMNIST(root, train=True, download=allow_download, transform=transform)
        # Stable, shared split for fair comparisons.
        train_set = Subset(train_data, range(TRAIN_SIZE))
        valid_set = Subset(train_data, range(TRAIN_SIZE, TRAIN_SIZE + VALID_SIZE))
        generator = torch.Generator().manual_seed(seed)
        train_loader = DataLoader(train_set, batch_size=config["batch_size"], shuffle=True, generator=generator)
        valid_loader = DataLoader(valid_set, batch_size=512, shuffle=False)
        model = FashionMLP(config["hidden_units"], config["dropout"])
        optimizer_cls = torch.optim.Adam if config["optimizer"] == "Adam" else torch.optim.SGD
        optimizer_args = {"lr": config["learning_rate"]}
        if config["optimizer"] == "SGD":
            optimizer_args["momentum"] = 0.9
        optimizer = optimizer_cls(model.parameters(), **optimizer_args)
        criterion = nn.CrossEntropyLoss()
        for _ in range(config["epochs"]):
            model.train()
            for images, labels in train_loader:
                optimizer.zero_grad(set_to_none=True)
                loss = criterion(model(images), labels)
                loss.backward(); optimizer.step()
        model.eval()
        correct = total = 0
        loss_sum = 0.0
        with torch.no_grad():
            for images, labels in valid_loader:
                logits = model(images)
                loss_sum += criterion(logits, labels).item() * labels.size(0)
                correct += (logits.argmax(1) == labels).sum().item()
                total += labels.size(0)
        accuracy = correct / total
        CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
        checkpoint = CHECKPOINT_DIR / f"{run_id}.pt"
        torch.save({"state_dict": model.state_dict(), "config": config, "accuracy": accuracy}, checkpoint)
        current = db.best_run()
        promoted = current is None or accuracy > current["accuracy"]
        if promoted:
            db.set_promoted(run_id)
        db.update_run(run_id, status="completed", accuracy=accuracy, loss=loss_sum / total,
                      duration_seconds=round(time.time() - start, 2), is_best=int(promoted), promoted=int(promoted),
                      finished_at=db.now(), checkpoint=str(checkpoint))
    except Exception as exc:
        db.update_run(run_id, status="failed", error=str(exc), duration_seconds=round(time.time() - start, 2), finished_at=db.now())
