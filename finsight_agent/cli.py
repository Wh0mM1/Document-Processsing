import argparse
import json
import uuid
from pathlib import Path
from .graph import build_graph


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('source')
    parser.add_argument('--output', default='data/latest-run.json')
    args = parser.parse_args()
    run_id = str(uuid.uuid4())
    result = build_graph().invoke({'source_path': args.source, 'run_id': run_id}, {
        'configurable': {'thread_id': run_id}})
    destination = Path(args.output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(result, indent=2))
    print(
        f"{result['status']}: {len(result.get('claims',[]))} cited claims written to {destination}")


if __name__ == '__main__':
    main()
