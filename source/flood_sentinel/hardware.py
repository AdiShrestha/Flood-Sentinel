"""Host hardware profiling and sustained inference benchmarking utilities.

Measures actual CPU runtime, latency percentiles, sustained inference throughput,
and peak memory consumption across hydrological model architectures.
"""
from __future__ import annotations

import os
import platform
import resource
import subprocess
import sys
import time
from typing import Any, Callable, Sequence

import numpy as np
import torch


def get_host_hardware_info() -> dict[str, Any]:
    """Retrieve host hardware specifications and runtime environment details."""
    cpu_model = platform.processor() or "Unknown CPU"
    if sys.platform == "darwin":
        try:
            res = subprocess.run(
                ["sysctl", "-n", "machdep.cpu.brand_string"],
                capture_output=True,
                text=True,
                check=False,
            )
            if res.returncode == 0 and res.stdout.strip():
                cpu_model = res.stdout.strip()
        except Exception:
            pass

    return {
        "platform": platform.system(),
        "platform_release": platform.release(),
        "architecture": platform.machine(),
        "cpu_model": cpu_model,
        "python_version": sys.version.split()[0],
        "torch_version": torch.__version__,
        "torch_threads": torch.get_num_threads(),
        "device": "cpu",
    }


def get_current_rss_mb() -> float:
    """Retrieve peak resident set size in megabytes (MB) for the current process."""
    maxrss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if sys.platform == "darwin":
        return float(maxrss / (1024.0 * 1024.0))
    return float(maxrss / 1024.0)


def count_parameters(model: Any) -> int:
    """Count trainable and total parameters for a model."""
    if isinstance(model, torch.nn.Module):
        return sum(p.numel() for p in model.parameters())
    if isinstance(model, tuple):
        total = 0
        for m in model:
            if isinstance(m, torch.nn.Module):
                total += sum(p.numel() for p in m.parameters())
        return total
    if hasattr(model, "weights") and hasattr(model.weights, "size"):
        return int(model.weights.size)
    if hasattr(model, "coef_"):
        return int(model.coef_.size)
    return 0


def benchmark_inference(
    predict_fn: Callable[[], Any],
    n_samples: int,
    warmup_trials: int = 10,
    measured_trials: int = 50,
) -> dict[str, float]:
    """Execute timed inference trials and measure latency and sustained throughput.

    Parameters:
        predict_fn: Zero-argument callable executing forward inference.
        n_samples: Number of samples processed per invocation.
        warmup_trials: Number of untimed warmup invocations.
        measured_trials: Number of timed invocations.

    Returns:
        Dictionary with latency statistics (ms), throughput (samples/s), and memory (MB).
    """
    for _ in range(warmup_trials):
        predict_fn()

    latencies_ms: list[float] = []
    for _ in range(measured_trials):
        t0 = time.perf_counter()
        predict_fn()
        t1 = time.perf_counter()
        latencies_ms.append((t1 - t0) * 1000.0)

    latencies = np.array(latencies_ms, dtype=np.float64)
    mean_lat_ms = float(np.mean(latencies))
    std_lat_ms = float(np.std(latencies))
    p50_ms = float(np.percentile(latencies, 50))
    p95_ms = float(np.percentile(latencies, 95))
    min_ms = float(np.min(latencies))
    max_ms = float(np.max(latencies))

    # Throughput calculation based on mean batch latency
    mean_lat_sec = mean_lat_ms / 1000.0
    throughput = float(n_samples / mean_lat_sec) if mean_lat_sec > 0 else 0.0

    return {
        "mean_latency_ms": mean_lat_ms,
        "std_latency_ms": std_lat_ms,
        "p50_latency_ms": p50_ms,
        "p95_latency_ms": p95_ms,
        "min_latency_ms": min_ms,
        "max_latency_ms": max_ms,
        "throughput_samples_per_sec": throughput,
        "peak_rss_mb": get_current_rss_mb(),
    }
