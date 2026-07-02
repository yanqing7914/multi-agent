.PHONY: validate fast full package verify-packages release-check

validate:
	python3 -V
	python3 scripts/validate_all_adapters.py

fast:
	python3 -V
	python3 scripts/validate_all_adapters.py
	python3 adapters/codex/scripts/prepare_native_plan.py --self-check
	python3 adapters/codex/scripts/finalize_native_run.py --self-check
	python3 scripts/install_native_skills.py --self-check
	python3 scripts/verify_release_packages.py --self-check

full: fast
	python3 adapters/openclaw/scripts/validate_all.py
	python3 adapters/openclaw/scripts/run_local_demo.py --out /tmp/openclaw-demo-ci --keep

package:
	python3 scripts/build_skill_packages.py --version 0.0.0-local

verify-packages:
	python3 scripts/verify_release_packages.py --version 0.0.0-local

release-check: full package verify-packages
