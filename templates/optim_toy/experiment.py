"""Baseline: two-layer ReLU MLP trained with plain mini-batch SGD on two synthetic
2-D classification datasets (moons, circles). Pure numpy, runs on CPU in seconds.

Contract (AI-Scientist template):
  python experiment.py --out_dir=run_i
writes run_i/final_info.json  ->  {dataset: {"means": {...}, "stds": {...}}}
and    run_i/all_results.json  ->  per-dataset, per-seed training curves for plot.py
and    run_i/checkpoint.npz   ->  final weights for independent evaluation
"""
import argparse
import json
import os
import time

import numpy as np


from benchmark_evaluator import BATCH_SIZE, DATASETS, HIDDEN, SEEDS, STEPS, split_data


# ----------------------------------------------------------------------------- model
class MLP:
    def __init__(self, d_in, d_hidden, d_out, rng):
        self.params = {
            "W1": rng.normal(0, np.sqrt(2 / d_in), (d_in, d_hidden)),
            "b1": np.zeros(d_hidden),
            "W2": rng.normal(0, np.sqrt(2 / d_hidden), (d_hidden, d_out)),
            "b2": np.zeros(d_out),
        }

    def forward(self, X):
        p = self.params
        h = X @ p["W1"] + p["b1"]
        a = np.maximum(h, 0)
        return a @ p["W2"] + p["b2"], (X, h, a)

    def loss_and_grads(self, X, y):
        logits, (X, h, a) = self.forward(X)
        z = logits - logits.max(1, keepdims=True)
        probs = np.exp(z) / np.exp(z).sum(1, keepdims=True)
        n = len(y)
        loss = -np.log(probs[np.arange(n), y] + 1e-12).mean()
        d = probs.copy()
        d[np.arange(n), y] -= 1
        d /= n
        p = self.params
        grads = {"W2": a.T @ d, "b2": d.sum(0)}
        da = d @ p["W2"].T
        dh = da * (h > 0)
        grads["W1"] = X.T @ dh
        grads["b1"] = dh.sum(0)
        return loss, grads

    def accuracy(self, X, y):
        return float((self.forward(X)[0].argmax(1) == y).mean())


# ----------------------------------------------------------------------------- optimiser
class SGD:
    def __init__(self, lr):
        self.lr = lr

    def step(self, params, grads, t):
        for k in params:
            params[k] -= self.lr * grads[k]


# ----------------------------------------------------------------------------- training
def train(dataset, seed, cfg):
    rng = np.random.default_rng(seed)
    Xtr, ytr = split_data(dataset, seed, "train")
    Xva, yva = split_data(dataset, seed, "validation")

    model = MLP(2, HIDDEN, 2, rng)
    opt = SGD(cfg["lr"])
    log = {"step": [], "train_loss": [], "validation_acc": []}
    steps_to_target = cfg["steps"]
    t0 = time.time()
    for t in range(1, cfg["steps"] + 1):
        b = rng.integers(0, len(ytr), cfg["batch_size"])
        _, grads = model.loss_and_grads(Xtr[b], ytr[b])
        opt.step(model.params, grads, t)
        if t % cfg["eval_every"] == 0 or t == cfg["steps"]:
            loss, _ = model.loss_and_grads(Xtr, ytr)
            acc = model.accuracy(Xva, yva)
            log["step"].append(t)
            log["train_loss"].append(float(loss))
            log["validation_acc"].append(acc)
            if acc >= cfg["target_acc"] and steps_to_target == cfg["steps"]:
                steps_to_target = t
    final = {
        "final_train_loss": log["train_loss"][-1],
        "final_validation_acc": log["validation_acc"][-1],
        "steps_to_target_acc": steps_to_target,
        "train_time_s": time.time() - t0,
    }
    return final, log, model.params


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out_dir", type=str, default="run_0")
    args = ap.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)

    cfg = dict(lr=0.1, batch_size=BATCH_SIZE, steps=STEPS,
               eval_every=50, target_acc=0.95)

    final_info, all_results, checkpoints = {}, {}, {}
    for ds in DATASETS:
        finals, logs = [], []
        for s in SEEDS:
            f, log, params = train(ds, s, cfg)
            checkpoints.update({f"{ds}_{s}_{key}": value for key, value in params.items()})
            finals.append(f)
            logs.append(log)
        keys = finals[0].keys()
        final_info[ds] = {
            "means": {k: float(np.mean([f[k] for f in finals])) for k in keys},
            "stds": {k: float(np.std([f[k] for f in finals])) for k in keys},
        }
        all_results[ds] = logs

    with open(os.path.join(args.out_dir, "final_info.json"), "w") as f:
        json.dump(final_info, f, indent=2)
    np.savez(os.path.join(args.out_dir, "checkpoint.npz"), **checkpoints)
    with open(os.path.join(args.out_dir, "all_results.json"), "w") as f:
        json.dump(all_results, f)


if __name__ == "__main__":
    main()
