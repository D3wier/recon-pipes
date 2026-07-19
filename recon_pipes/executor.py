"""Pipeline execution engine."""

import subprocess
import time
import json
import re
import os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from .models import Pipeline, Step


class RateLimiter:
    """Token bucket rate limiter."""

    def __init__(self, rate_str: str):
        match = re.match(r"(\d+)/s", rate_str)
        self.rate = int(match.group(1)) if match else 100
        self.tokens = self.rate
        self.last_refill = time.time()

    def acquire(self):
        now = time.time()
        elapsed = now - self.last_refill
        self.tokens = min(self.rate, self.tokens + elapsed * self.rate)
        self.last_refill = now
        if self.tokens < 1:
            time.sleep(1.0 / self.rate)
            self.tokens = 1
        self.tokens -= 1


class PipelineExecutor:
    """Executes a parsed pipeline."""

    def __init__(self, pipeline: Pipeline, dry_run: bool = False):
        self.pipeline = pipeline
        self.dry_run = dry_run
        self.output_dir = Path(pipeline.options.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.state_file = self.output_dir / ".pipeline_state.json"
        self.rate_limiter = RateLimiter(pipeline.options.rate_limit)
        self.results = {}

    def interpolate(self, text: str) -> str:
        """Replace {{variable}} placeholders."""
        text = text.replace("{{target}}", self.pipeline.target)
        text = text.replace("{{date}}", time.strftime("%Y-%m-%d"))

        for key, val in os.environ.items():
            text = text.replace(f"{{{{env.{key}}}}}", val)

        for name, output_path in self.results.items():
            text = text.replace(f"{{{{{name}.output}}}}", str(output_path))

        return text

    def run_step(self, step: Step) -> bool:
        """Execute a single pipeline step."""
        print(f"  [{step.name}] Running: {step.tool}")

        args = self.interpolate(step.args)
        output_path = self.output_dir / step.output if step.output else None

        if step.input:
            input_path = self.output_dir / step.input
            if not input_path.exists():
                for name, res_path in self.results.items():
                    if res_path and res_path.name == step.input:
                        input_path = res_path
                        break

            if input_path.exists():
                args += f" -l {input_path}" if "-l" not in args else ""

        cmd = f"{step.tool} {args}"
        if self.dry_run:
            print(f"    [DRY RUN] Would execute: {cmd}")
            if output_path:
                output_path.write_text("")
                self.results[step.name] = output_path
            step.status = "complete"
            return True

        self.rate_limiter.acquire()

        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=step.timeout,
            )

            if output_path:
                output_lines = result.stdout.strip().split("\n")
                if self.pipeline.options.dedup:
                    output_lines = list(dict.fromkeys(output_lines))
                output_path.write_text("\n".join(output_lines) + "\n")
                self.results[step.name] = output_path
                print(f"    [{step.name}] → {len(output_lines)} results → {output_path}")
            else:
                print(f"    [{step.name}] Done (no output file)")

            step.status = "complete"
            self.save_state()
            return True

        except subprocess.TimeoutExpired:
            print(f"    [{step.name}] TIMEOUT after {step.timeout}s")
            step.status = "timeout"
            return False
        except Exception as e:
            print(f"    [{step.name}] ERROR: {e}")
            step.status = "error"
            return False

    def get_ready_steps(self) -> list:
        """Get steps whose dependencies are satisfied."""
        completed = {s.name for s in self.pipeline.steps if s.status == "complete"}
        ready = []
        for step in self.pipeline.steps:
            if step.status != "pending":
                continue
            deps_met = all(d in completed for d in step.depends_on)
            if step.input:
                input_available = any(
                    s.output == step.input and s.status == "complete"
                    for s in self.pipeline.steps
                ) or (self.output_dir / step.input).exists()
                deps_met = deps_met and input_available
            if deps_met:
                ready.append(step)
        return ready

    def save_state(self):
        """Save pipeline state for resume."""
        state = {
            "pipeline": self.pipeline.name,
            "target": self.pipeline.target,
            "steps": {s.name: s.status for s in self.pipeline.steps},
        }
        self.state_file.write_text(json.dumps(state, indent=2))

    def load_state(self):
        """Load pipeline state for resume."""
        if not self.state_file.exists():
            return
        state = json.loads(self.state_file.read_text())
        for step in self.pipeline.steps:
            if step.name in state.get("steps", {}):
                saved_status = state["steps"][step.name]
                if saved_status == "complete":
                    step.status = "complete"
                    if step.output:
                        self.results[step.name] = self.output_dir / step.output

    def run(self, resume: bool = False):
        """Execute the full pipeline."""
        print(f"Pipeline: {self.pipeline.name}")
        print(f"Target: {self.pipeline.target}")
        print(f"Steps: {len(self.pipeline.steps)}")
        print("-" * 40)

        if resume:
            self.load_state()
            skipped = sum(1 for s in self.pipeline.steps if s.status == "complete")
            if skipped:
                print(f"Resuming — skipping {skipped} completed steps")

        max_parallel = self.pipeline.options.parallel

        while True:
            ready = self.get_ready_steps()
            if not ready:
                break

            batch = ready[:max_parallel]
            if max_parallel == 1 or len(batch) == 1:
                for step in batch:
                    self.run_step(step)
            else:
                with ThreadPoolExecutor(max_workers=max_parallel) as pool:
                    futures = {pool.submit(self.run_step, s): s for s in batch}
                    for f in as_completed(futures):
                        f.result()

        failed = [s for s in self.pipeline.steps if s.status not in ("complete", "pending")]
        if failed:
            print(f"\n{'='*40}")
            print(f"Pipeline finished with {len(failed)} failed step(s):")
            for s in failed:
                print(f"  - {s.name}: {s.status}")
        else:
            print(f"\n{'='*40}")
            print("Pipeline complete!")

        self.save_state()
        return len(failed) == 0
