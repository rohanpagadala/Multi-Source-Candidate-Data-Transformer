import argparse
import json
import os
import sys
from typing import List
from src.pipeline import run_pipeline

def main():
    parser = argparse.ArgumentParser(
        description="Multi-Source Candidate Data Transformer - Consolidate candidate profiles from multiple sources."
    )
    parser.add_argument(
        "--inputs", 
        nargs="+", 
        required=True, 
        help="Input files or directories containing candidate source data (Resumes, recruiter notes, ATS exports, profile JSONs)."
    )
    parser.add_argument(
        "--config", 
        help="Path to the custom projection configuration JSON file."
    )
    parser.add_argument(
        "--output", 
        default="candidate.json", 
        help="Path to write the merged and validated output candidate profiles JSON. (default: candidate.json)"
    )
    parser.add_argument(
        "--verbose", 
        action="store_true", 
        help="Print verbose logs of pipeline execution."
    )

    args = parser.parse_args()

    # Collect all input files
    input_files: List[str] = []
    for path in args.inputs:
        if os.path.isdir(path):
            for root, _, files in os.walk(path):
                for f in files:
                    # Ignore hidden files
                    if not f.startswith('.'):
                        input_files.append(os.path.join(root, f))
        elif os.path.isfile(path):
            input_files.append(path)
        else:
            print(f"Error: Input path is neither file nor directory: {path}", file=sys.stderr)
            sys.exit(1)

    if not input_files:
        print("Error: No input files found.", file=sys.stderr)
        sys.exit(1)

    if args.verbose:
        print(f"Collected {len(input_files)} input files:")
        for f in input_files:
            print(f"  - {f}")

    # Load configuration if provided
    config = {}
    if args.config:
        if not os.path.exists(args.config):
            print(f"Error: Configuration file not found: {args.config}", file=sys.stderr)
            sys.exit(1)
            
        try:
            with open(args.config, 'r') as f:
                config = json.load(f)
            if args.verbose:
                print(f"Loaded custom projection config from: {args.config}")
        except Exception as e:
            print(f"Error reading configuration file: {e}", file=sys.stderr)
            sys.exit(1)

    # Run the pipeline
    try:
        results = run_pipeline(input_files, config)
        
        # Save output to file
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2)
            
        print(f"Success! Processed {len(results)} candidate profiles and saved to {args.output}")
        
    except Exception as e:
        print(f"Pipeline Execution Failed: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
