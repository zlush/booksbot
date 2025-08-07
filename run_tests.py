import importlib
import inspect
import sys
import traceback

# Ensure package path
if "/workspace" not in sys.path:
    sys.path.insert(0, "/workspace")

modules = [
    "tests.test_acceptance",
]

failures = 0
ran = 0

for mod_name in modules:
    try:
        mod = importlib.import_module(mod_name)
    except Exception as e:
        print(f"ERROR importing {mod_name}: {e}")
        traceback.print_exc()
        failures += 1
        continue
    for name, obj in inspect.getmembers(mod):
        if name.startswith("test_") and inspect.isfunction(obj):
            try:
                obj()
                print(f"PASS {mod_name}:: {name}")
            except AssertionError:
                failures += 1
                print(f"FAIL {mod_name}:: {name}")
                traceback.print_exc()
            except Exception:
                failures += 1
                print(f"ERROR {mod_name}:: {name}")
                traceback.print_exc()
            finally:
                ran += 1

print(f"Ran {ran} tests; Failures: {failures}")
if failures:
    sys.exit(1)