"""Service package marker.

Avoid eager service imports here; several services depend on each other through
engine modules and should be imported explicitly by their consumers.
"""
