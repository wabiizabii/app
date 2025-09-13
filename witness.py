# This is the witness file. Its purpose is to report the absolute truth.
import sys
import os
import pprint

print("\n================ WITNESS REPORT ================")

print("\n[1] PYTHON EXECUTABLE:")
print(f"    -> {sys.executable}")

print("\n[2] CURRENT WORKING DIRECTORY:")
print(f"    -> {os.getcwd()}")

print("\n[3] PYTHON SEARCH PATHS (sys.path):")
# Using a loop for cleaner output
for i, path in enumerate(sys.path):
    print(f"    [{i}] {path}")

print("\n[4] ATTEMPTING TO LOCATE 'core.mt5_handler'...")
try:
    # We temporarily add the current directory to the path to ensure it can be found
    # if the environment is misconfigured. This helps in diagnosis.
    if os.getcwd() not in sys.path:
        sys.path.insert(0, os.getcwd())

    from core import mt5_handler
    print("\n    [SUCCESS] Module found.")
    print(f"    -> ABSOLUTE PATH: {os.path.abspath(mt5_handler.__file__)}")

    # Verification check
    with open(mt5_handler.__file__, 'r') as f:
        content = f.read()
        if "KEYERROR_FIX" in content:
            print("    -> [VERIFIED] The file contains the 'KEYERROR_FIX' version.")
        else:
            print("    -> [CRITICAL WARNING] The file found is an OLD VERSION without the fix!")

except ImportError as e:
    print(f"\n    [FAILURE] Could not import the module.")
    print(f"    -> ERROR: {e}")
except Exception as e:
    print(f"\n    [UNEXPECTED FAILURE] An error occurred.")
    print(f"    -> ERROR: {e}")

print("\n================ END OF REPORT ================\n")