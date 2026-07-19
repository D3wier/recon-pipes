"""CLI entry point."""

import argparse
import sys
from .parser import parse_pipeline, validate_pipeline
from .executor import PipelineExecutor


def main():
    parser = argparse.ArgumentParser(
        prog="recon-pipes",
        description="Composable recon pipeline builder",
    )
    subparsers = parser.add_subparsers(dest="command")

    run_parser = subparsers.add_parser("run", help="Run a pipeline")
    run_parser.add_argument("pipeline", help="Path to pipeline YAML")
    run_parser.add_argument("--target", help="Override target")
    run_parser.add_argument("--resume", action="store_true", help="Resume from checkpoint")
    run_parser.add_argument("--dry-run", action="store_true", help="Show execution plan")

    validate_parser = subparsers.add_parser("validate", help="Validate pipeline syntax")
    validate_parser.add_argument("pipeline", help="Path to pipeline YAML")

    subparsers.add_parser("tools", help="List available tools")

    args = parser.parse_args()

    if args.command == "run":
        pipeline = parse_pipeline(args.pipeline)
        if args.target:
            pipeline.target = args.target
        executor = PipelineExecutor(pipeline, dry_run=args.dry_run)
        success = executor.run(resume=args.resume)
        sys.exit(0 if success else 1)

    elif args.command == "validate":
        errors = validate_pipeline(args.pipeline)
        if errors:
            print("Validation errors:")
            for e in errors:
                print(f"  - {e}")
            sys.exit(1)
        else:
            print("Pipeline is valid.")

    elif args.command == "tools":
        print("Built-in tool support:")
        print("  subfinder, httpx, nuclei, nmap, ffuf, amass,")
        print("  waybackurls, gau, katana, feroxbuster, dnsx")
        print("\nCustom tools: ~/.config/recon-pipes/tools.yaml")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
