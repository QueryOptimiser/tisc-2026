#!/usr/bin/env python3
"""TISC 2026 - REDACTED (Level 1).
Decode the base64 string recovered from the PDF's text layer.
"""
import base64

encoded = "VElTQ3tCUk8hUmVkYWN0UERGc1Byb3Blcmx5TGFoISEhfQ=="
print(base64.b64decode(encoded).decode())
