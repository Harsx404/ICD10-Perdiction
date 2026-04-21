import os


# Keep tests deterministic and fast even when the repo-root .env enables full-model mode.
os.environ["ENABLE_MEDGEMMA"] = "false"
os.environ["ENABLE_ICD_MODEL"] = "false"
