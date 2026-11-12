"""
Telemetry and publisher metrics tracker for Amazon Kinesis streaming.
"""
import time
from typing import Dict, List


class StreamingMetricsTracker:
    """Tracks streaming publishing throughput, latency, and error counts."""

    def __init__(self):
        self.start_time = time.time()
        self.total_records = 0
        self.successful_records = 0
        self.failed_records = 0
        self.total_batches = 0
        self.total_bytes = 0
        self.batch_latencies: List[float] = []

    def record_batch(self, success_count: int, failed_count: int, num_bytes: int, latency_sec: float):
        self.total_batches += 1
        self.successful_records += success_count
        self.failed_records += failed_count
        self.total_records += (success_count + failed_count)
        self.total_bytes += num_bytes
        self.batch_latencies.append(latency_sec)

    def summary(self) -> Dict:
        elapsed = max(0.001, time.time() - self.start_time)
        tps = self.successful_records / elapsed
        kbps = (self.total_bytes / 1024.0) / elapsed
        avg_latency = (sum(self.batch_latencies) / len(self.batch_latencies)) if self.batch_latencies else 0.0

        return {
            "total_batches": self.total_batches,
            "total_records": self.total_records,
            "successful_records": self.successful_records,
            "failed_records": self.failed_records,
            "total_bytes": self.total_bytes,
            "elapsed_seconds": round(elapsed, 2),
            "records_per_second": round(tps, 2),
            "throughput_kbps": round(kbps, 2),
            "average_batch_latency_ms": round(avg_latency * 1000.0, 2)
        }
