"""Plot training curves for every run listed in `labels`.

Only runs in `labels` are plotted, in the given order. The experimenter edits this dict
to include each meaningful run_i with a descriptive legend name.
Figures are written to the current folder: validation_acc_<dataset>.png, train_loss_<dataset>.png
"""
import json
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

labels = {
    "run_0": "Baseline (SGD, lr=0.1)",
}


def load(run):
    path = os.path.join(run, "all_results.json")
    if not os.path.exists(path):
        return None
    with open(path) as file:
        return json.load(file)


def main():
    runs = {r: load(r) for r in labels}
    runs = {r: v for r, v in runs.items() if v is not None}
    if not runs:
        raise SystemExit("No run folders with all_results.json found")
    datasets = list(next(iter(runs.values())).keys())
    cmap = plt.get_cmap("tab10")
    for metric, ylabel in (("validation_acc", "Validation accuracy"), ("train_loss", "Train loss")):
        for ds in datasets:
            plt.figure(figsize=(6, 4))
            for i, (run, res) in enumerate(runs.items()):
                logs = res[ds]
                steps = np.array(logs[0]["step"])
                vals = np.array([log[metric] for log in logs])
                mean, std = vals.mean(0), vals.std(0)
                plt.plot(steps, mean, label=labels[run], color=cmap(i))
                plt.fill_between(steps, mean - std, mean + std, alpha=0.2, color=cmap(i))
            plt.xlabel("Step")
            plt.ylabel(ylabel)
            plt.title(f"{ylabel} on {ds}")
            if metric == "train_loss":
                plt.yscale("log")
            plt.legend()
            plt.grid(alpha=0.3)
            plt.tight_layout()
            plt.savefig(f"{metric}_{ds}.png", dpi=150)
            plt.close()


if __name__ == "__main__":
    main()
