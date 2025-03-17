"""CLI script for running codebase analysis."""

import argparse
import json
import sys
from pathlib import Path

from mcp_server_qdrant.analysis import CodebaseAnalyzer
from mcp_server_qdrant.analysis.config import AnalysisConfig
from mcp_server_qdrant.core.config import Settings

def main():
    """Run codebase analysis."""
    parser = argparse.ArgumentParser(description='Analyze codebase and store in Qdrant')
    parser.add_argument(
        '--root-dir',
        type=str,
        default='src',
        help='Root directory to analyze (default: src)'
    )
    parser.add_argument(
        '--collection',
        type=str,
        default='codebase',
        help='Qdrant collection name (default: codebase)'
    )
    parser.add_argument(
        '--config',
        type=str,
        help='Path to analysis configuration file (YAML or JSON)'
    )
    parser.add_argument(
        '--output',
        type=str,
        help='Output file for analysis results (default: stdout)'
    )
    parser.add_argument(
        '--save-config',
        type=str,
        help='Save default configuration to specified file'
    )
    
    args = parser.parse_args()
    
    try:
        # Save default config if requested
        if args.save_config:
            config = AnalysisConfig()
            path = Path(args.save_config)
            if path.suffix in {'.yml', '.yaml'}:
                import yaml
                with open(path, 'w') as f:
                    yaml.dump(config.dict(), f, default_flow_style=False)
            else:
                with open(path, 'w') as f:
                    json.dump(config.dict(), f, indent=2)
            print(f"Default configuration saved to {args.save_config}")
            return
        
        # Load configuration if specified
        config = None
        if args.config:
            config = AnalysisConfig.from_file(args.config)
        
        settings = Settings()
        analyzer = CodebaseAnalyzer(settings, config)
        
        print(f"Analyzing codebase in {args.root_dir}...")
        results = analyzer.analyze_codebase(
            root_dir=args.root_dir,
            collection_name=args.collection
        )
        
        output = json.dumps(results, indent=2)
        if args.output:
            with open(args.output, 'w') as f:
                f.write(output)
            print(f"Results written to {args.output}")
        else:
            print(output)
            
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main() 