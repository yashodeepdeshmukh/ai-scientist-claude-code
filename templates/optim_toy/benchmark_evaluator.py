"""Fixed data protocol and independent scoring for optim_toy."""
import argparse
import json
from pathlib import Path

import numpy as np

SEEDS = (0, 1, 2)
HIDDEN = 32
STEPS = 3000
BATCH_SIZE = 32
SIZES = {"train": 800, "validation": 400, "test": 400}
SPLIT_SEEDS = {"train": 100, "validation": 200, "test": 300}


def make_moons(n, noise, rng):
    n1 = n // 2
    t1 = rng.uniform(0, np.pi, n1)
    t2 = rng.uniform(0, np.pi, n - n1)
    a = np.stack([np.cos(t1), np.sin(t1)], 1)
    b = np.stack([1 - np.cos(t2), 0.5 - np.sin(t2)], 1)
    X = np.concatenate([a, b]) + rng.normal(0, noise, (n, 2))
    y = np.concatenate([np.zeros(n1, int), np.ones(n - n1, int)])
    return X, y


def make_circles(n, noise, rng, factor=0.5):
    n1 = n // 2
    t = rng.uniform(0, 2 * np.pi, n)
    r = np.concatenate([np.ones(n1), factor * np.ones(n - n1)])
    X = np.stack([r * np.cos(t), r * np.sin(t)], 1) + rng.normal(0, noise, (n, 2))
    y = np.concatenate([np.zeros(n1, int), np.ones(n - n1, int)])
    return X, y


DATASETS = {"moons": make_moons, "circles": make_circles}


def split_data(dataset, seed, split):
    rng = np.random.default_rng(SPLIT_SEEDS[split] + seed)
    return DATASETS[dataset](SIZES[split], 0.15, rng)


def score(checkpoint, split):
    shapes = {"W1": (2, HIDDEN), "b1": (HIDDEN,), "W2": (HIDDEN, 2), "b2": (2,)}
    scores = {}
    with np.load(checkpoint, allow_pickle=False) as arrays:
        expected = {f"{dataset}_{seed}_{key}" for dataset in DATASETS for seed in SEEDS for key in shapes}
        if set(arrays.files) != expected or len(arrays.files) != len(expected):
            raise ValueError("Unexpected checkpoint fields")
        for dataset in DATASETS:
            scores[dataset] = {}
            for seed in SEEDS:
                params = {key: arrays[f"{dataset}_{seed}_{key}"] for key in shapes}
                for key, array in params.items():
                    if array.shape != shapes[key] or array.dtype.kind != "f" or not np.isfinite(array).all():
                        raise ValueError("Invalid model weights")
                X, y = split_data(dataset, seed, split)
                with np.errstate(over="raise", invalid="raise"):
                    hidden = np.maximum(X @ params["W1"] + params["b1"], 0)
                    predicted = (hidden @ params["W2"] + params["b2"]).argmax(axis=1)
                scores[dataset][str(seed)] = float((predicted == y).mean())
    return scores


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkpoint", type=Path)
    parser.add_argument("--split", choices=("validation", "test"), required=True)
    args = parser.parse_args()
    print(json.dumps(score(args.checkpoint, args.split)))


if __name__ == "__main__":
    main()
