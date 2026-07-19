# recon-pipes

Composable recon pipeline builder for bug bounty and security testing. Define your reconnaissance workflows in YAML, chain tools together, and let recon-pipes handle orchestration, deduplication, rate-limiting, and notifications.

## Features

- **YAML-defined pipelines** — Declare your recon workflow as a simple YAML file
- **Tool chaining** — Pipe output from one tool into the next (subfinder → httpx → nuclei)
- **Built-in deduplication** — No duplicate targets across steps
- **Rate limiting** — Global and per-step rate limits to stay under the radar
- **Parallel execution** — Run independent steps concurrently
- **Notifications** — Slack, Discord, or webhook alerts on findings
- **Resumable** — Pipelines save state and can resume after interruption
- **Extensible** — Add custom tools via simple shell command definitions

## Installation

```bash
pip install recon-pipes
```

Or from source:

```bash
git clone https://github.com/D3wier/recon-pipes.git
cd recon-pipes
pip install -e .
```

## Quick Start

```yaml
# pipeline.yaml
name: full-recon
target: example.com

steps:
  - name: subdomains
    tool: subfinder
    args: "-d {{target}} -silent"
    output: subdomains.txt

  - name: live-hosts
    tool: httpx
    input: subdomains.txt
    args: "-silent -mc 200,301,302,403"
    output: live_hosts.txt

  - name: scan
    tool: nuclei
    input: live_hosts.txt
    args: "-t cves/ -severity medium,high,critical"
    output: findings.txt
    notify: true

options:
  rate_limit: 50/s
  dedup: true
  parallel: 2
  notify:
    webhook: "https://hooks.slack.com/services/XXX"
```

Run it:

```bash
recon-pipes run pipeline.yaml
```

## Pipeline Syntax

### Steps

Each step defines a tool to run:

```yaml
steps:
  - name: step-name        # Unique step identifier
    tool: tool-name        # CLI tool to execute
    args: "arguments"      # Arguments (supports {{variable}} interpolation)
    input: file.txt        # Input file (fed line-by-line or as argument)
    output: results.txt    # Output file to capture stdout
    notify: true           # Send notification on completion
    rate_limit: 10/s       # Per-step rate limit
    timeout: 300           # Step timeout in seconds
    depends_on:            # Explicit dependencies (auto-detected from input/output)
      - other-step
```

### Variables

Use `{{variable}}` syntax for interpolation:

- `{{target}}` — The pipeline target
- `{{step.output}}` — Reference another step's output file
- `{{env.VAR}}` — Environment variables
- `{{date}}` — Current date (YYYY-MM-DD)

### Options

```yaml
options:
  rate_limit: 100/s       # Global rate limit
  dedup: true             # Remove duplicate lines across outputs
  parallel: 4             # Max parallel steps
  resume: true            # Resume from last checkpoint
  output_dir: ./results   # Base output directory
  notify:
    webhook: "url"        # Slack/Discord webhook
    on: [complete, error] # When to notify
```

## CLI Usage

```bash
# Run a pipeline
recon-pipes run pipeline.yaml

# Run with target override
recon-pipes run pipeline.yaml --target other.com

# Resume interrupted pipeline
recon-pipes run pipeline.yaml --resume

# Validate pipeline syntax
recon-pipes validate pipeline.yaml

# List available tool definitions
recon-pipes tools

# Dry run (show execution plan)
recon-pipes run pipeline.yaml --dry-run
```

## Adding Custom Tools

Create a `tools.yaml` in your project or `~/.config/recon-pipes/tools.yaml`:

```yaml
tools:
  my-scanner:
    command: "/path/to/scanner"
    input_flag: "-l"      # How the tool accepts input files
    output_flag: "-o"     # How the tool writes output
    install: "go install github.com/user/scanner@latest"
```

## Examples

See the [examples/](examples/) directory for ready-to-use pipelines:

- `basic-recon.yaml` — Simple subdomain → live hosts → scan
- `full-recon.yaml` — Complete recon pipeline with JS analysis
- `continuous.yaml` — Continuous monitoring pipeline

## License

MIT License — see [LICENSE](LICENSE)
