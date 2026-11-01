"""Shared runtime state for uploaded datasets."""

from ocean_backend.services.upload_service import DatasetRegistry


# One registry shared by the upload and data-processing APIs.
#
# The registry lives for the lifetime of the backend process.
# Uploaded datasets are registered here and can then be accessed
# by their dataset_id from other API routes.
dataset_registry = DatasetRegistry()