SEARCH_SPACE = [
    ("learning_rate", 0.0005, "Lower the learning rate to make each update more cautious."),
    ("learning_rate", 0.002, "Raise the learning rate to explore faster parameter updates."),
    ("batch_size", 64, "Use smaller batches for noisier, potentially better generalization."),
    ("batch_size", 256, "Use larger batches for steadier gradient estimates."),
    ("hidden_units", 64, "Try a compact hidden layer to reduce model capacity."),
    ("hidden_units", 256, "Give the model more capacity to learn visual patterns."),
    ("dropout", 0.0, "Remove dropout to test whether regularization is limiting learning."),
    ("dropout", 0.25, "Increase dropout to test stronger regularization."),
    ("optimizer", "SGD", "Compare Adam with momentum SGD."),
    ("optimizer", "Adam", "Return to adaptive Adam updates."),
]


def propose(best, runs):
    config = dict(best["config"])
    tried = {(key, run["config"].get(key)) for run in runs for key, _, _ in SEARCH_SPACE}
    candidates = []
    for key, value, why in SEARCH_SPACE:
        if config.get(key) != value and (key, value) not in tried:
            candidates.append((key, value, why))
    if not candidates:
        # Search is finite: revisit the least recently attempted valid change.
        for key, value, why in SEARCH_SPACE:
            if config.get(key) != value:
                candidates.append((key, value, why))
    if not candidates:
        return None
    key, value, rationale = candidates[0]
    config[key] = value
    note = f"{key.replace('_', ' ')}: {best['config'][key]} → {value}"
    return config, note, rationale
