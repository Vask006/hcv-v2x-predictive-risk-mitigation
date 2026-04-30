# Local Development

## Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
```

## Test

```bash
bash scripts/run_all_tests.sh
```

## Demo

```bash
python scripts/run_demo_end_to_end.py --skip-ingest
```
