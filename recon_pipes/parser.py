"""YAML pipeline parser."""

import yaml
from pathlib import Path
from .models import Pipeline, Step, PipelineOptions, NotifyConfig


def parse_pipeline(path: str) -> Pipeline:
    """Parse a YAML pipeline file into a Pipeline object."""
    content = Path(path).read_text()
    data = yaml.safe_load(content)

    options_data = data.get("options", {}) or {}
    notify_data = options_data.pop("notify", None)
    notify = None
    if notify_data and isinstance(notify_data, dict):
        notify = NotifyConfig(
            webhook=str(notify_data.get("webhook", "")),
            on=notify_data.get("on", ["complete", "error"]),
        )

    valid_option_fields = {"rate_limit", "dedup", "parallel", "resume", "output_dir"}
    filtered_options = {k: v for k, v in options_data.items() if k in valid_option_fields}
    options = PipelineOptions(**filtered_options, notify=notify)

    steps = []
    for step_data in data.get("steps", []):
        valid_step_fields = {"name", "tool", "args", "input", "output", "notify", "rate_limit", "timeout", "depends_on"}
        filtered_step = {k: v for k, v in step_data.items() if k in valid_step_fields}
        steps.append(Step(**filtered_step))

    return Pipeline(
        name=data.get("name", "unnamed"),
        target=data.get("target", ""),
        steps=steps,
        options=options,
    )


def validate_pipeline(path: str) -> list:
    """Validate pipeline YAML and return list of errors."""
    errors = []
    try:
        pipeline = parse_pipeline(path)
    except Exception as e:
        return [f"Parse error: {e}"]

    if not pipeline.target:
        errors.append("Missing 'target' field")

    if not pipeline.steps:
        errors.append("No steps defined")

    step_names = set()
    for step in pipeline.steps:
        if step.name in step_names:
            errors.append(f"Duplicate step name: {step.name}")
        step_names.add(step.name)

        if not step.tool:
            errors.append(f"Step '{step.name}' missing 'tool' field")

        for dep in step.depends_on:
            if dep not in step_names:
                errors.append(f"Step '{step.name}' depends on unknown step '{dep}'")

    return errors
