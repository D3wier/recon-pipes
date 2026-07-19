"""Pipeline data models."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class NotifyConfig:
    webhook: str = ""
    on: list = field(default_factory=lambda: ["complete", "error"])


@dataclass
class PipelineOptions:
    rate_limit: str = "100/s"
    dedup: bool = True
    parallel: int = 2
    resume: bool = True
    output_dir: str = "./results"
    notify: Optional[NotifyConfig] = None


@dataclass
class Step:
    name: str
    tool: str
    args: str = ""
    input: Optional[str] = None
    output: Optional[str] = None
    notify: bool = False
    rate_limit: Optional[str] = None
    timeout: int = 300
    depends_on: list = field(default_factory=list)
    status: str = "pending"


@dataclass
class Pipeline:
    name: str
    target: str
    steps: list = field(default_factory=list)
    options: PipelineOptions = field(default_factory=PipelineOptions)
