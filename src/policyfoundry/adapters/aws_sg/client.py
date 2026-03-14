"""Thin boto3 EC2 wrapper for AWS Security Group rule operations."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

import boto3
from botocore.exceptions import ClientError

from policyfoundry.exceptions import AdapterAuthenticationError, AdapterError

if TYPE_CHECKING:
    from mypy_boto3_ec2.client import EC2Client

_AUTH_ERROR_CODES = frozenset({"AuthFailure", "UnauthorizedAccess", "AccessDeniedException"})


class AwsSgClient:
    """Async wrapper around boto3 EC2 describe_security_group_rules.

    Provides a single async method to fetch security group rules,
    wrapping the synchronous boto3 call via asyncio.to_thread.
    """

    def __init__(self, security_group_id: str, region: str | None = None) -> None:
        self._sg_id = security_group_id
        self._client: EC2Client = boto3.client(
            "ec2",
            region_name=region,
        )

    async def describe_rules(self) -> list[dict[str, Any]]:
        """Fetch security group rules for the configured SG ID.

        Returns:
            List of AWS SecurityGroupRule dicts.

        Raises:
            AdapterAuthenticationError: On AWS auth failures.
            AdapterError: On other AWS API errors.
        """
        try:
            response = await asyncio.to_thread(
                self._client.describe_security_group_rules,
                Filters=[
                    {
                        "Name": "group-id",
                        "Values": [self._sg_id],
                    }
                ],
            )
            return response["SecurityGroupRules"]
        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code", "")
            details = {
                "sg_id": self._sg_id,
                "region": self._client.meta.region_name,
                "error_code": error_code,
            }
            if error_code in _AUTH_ERROR_CODES:
                msg = (
                    f"Authentication failed for security group '"
                    f"{self._sg_id}': {exc}"
                )
                raise AdapterAuthenticationError(
                    msg,
                    error_code=error_code,
                    details=details,
                ) from exc
            else:
                msg = (
                    f"AWS API error for security group '"
                    f"{self._sg_id}': {exc}"
                )
                raise AdapterError(
                    msg,
                    error_code=error_code,
                    details=details,
                ) from exc
