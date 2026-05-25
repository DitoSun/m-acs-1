"""GPU metrics. Swappable provider: currently file_provider, future socket/sqlite."""

from services.metrics_provider import file_provider
from config import config

get_gpu_metrics = file_provider(config.GPU_METRICS_FILE, config.METRICS_STALE_SECONDS)
