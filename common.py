"""
Common utilities for logging, config loading, output writing, and shared resource base class for extractors.
"""
import logging
import yaml
import json
from typing import Any, Dict
from dataclasses import dataclass, asdict
from azure.identity import DefaultAzureCredential
from tenacity import retry, stop_after_attempt, wait_exponential



def setup_logging(config: dict):
    level = config.get('logging', {}).get('level', 'INFO')
    fmt = config.get('logging', {}).get('format', '%(asctime)s %(levelname)s %(name)s %(message)s')
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format=fmt
    )


def load_config(config_path: str) -> Dict[str, Any]:
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def write_json_output(data: Dict[str, Any], output_path: str, output_cfg: Dict[str, Any]):
    with open(output_path, 'w', encoding='utf-8') as f:
        if output_cfg.get('json_pretty', True):
            json.dump(data, f, indent=2, ensure_ascii=False)
        else:
            json.dump(data, f, ensure_ascii=False)





def retry_on_exception(config: dict = None):
    retry_cfg = (config or {}).get('retry', {})
    max_attempts = retry_cfg.get('max_attempts', 5)
    backoff_factor = retry_cfg.get('backoff_factor', 2)
    min_wait = retry_cfg.get('min_wait', 2)
    max_wait = retry_cfg.get('max_wait', 10)
    return retry(stop=stop_after_attempt(max_attempts), wait=wait_exponential(multiplier=backoff_factor, min=min_wait, max=max_wait))

@dataclass
class ResourceBase:
    name: str
    id: str
    type: str
    location: str
    tags: dict

    def to_dict(self):
        return asdict(self)
