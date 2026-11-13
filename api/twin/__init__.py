"""FIREWISE Digital Twin: shared scenario state, evidence twin, physics twin, persistence, reports.

The twin extends the FIREWISE API. It reads NASA evidence from the read-only scientific database
(build/firewise.sqlite) and keeps user scenarios in a separate writable state database (see state.py).
"""
