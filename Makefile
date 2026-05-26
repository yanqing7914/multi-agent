.PHONY: validate

validate:
	python3 -V
	python3 scripts/validate_all_adapters.py
	python3 adapters/openclaw/scripts/validate_all.py
	python3 adapters/openclaw/scripts/run_local_demo.py --out /tmp/openclaw-demo-ci --keep
