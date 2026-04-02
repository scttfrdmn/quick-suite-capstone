#!/usr/bin/env python3
"""
Quick Suite Shared Infrastructure — CDK entry point.

Three stacks:
  QuickSuiteSharedGuardrail  — Bedrock Guardrail + SSM export
  QuickSuiteSharedDiscover   — qs-discover unified Lambda
  QuickSuiteSharedIdentity   — Shared Cognito User Pool + GroupMetadataTable

Deploy all together (CDK handles ordering via add_dependency):
  uv run cdk deploy --all

Deploy with target Lambda ARNs for qs-discover:
  uv run cdk deploy QuickSuiteSharedDiscover \\
    --context roda_search_arn=arn:aws:lambda:... \\
    --context s3_browse_arn=arn:aws:lambda:... \\
    --context claws_discover_arn=arn:aws:lambda:...

Override Cognito domain prefix (must be globally unique):
  uv run cdk deploy QuickSuiteSharedIdentity \\
    --context cognito_domain_prefix=quicksuite-myuniversity
"""

import aws_cdk as cdk

from stacks.discover_stack import QuickSuiteSharedDiscover
from stacks.guardrail_stack import QuickSuiteSharedGuardrail
from stacks.identity_stack import QuickSuiteSharedIdentity

app = cdk.App()

guardrail_stack = QuickSuiteSharedGuardrail(app, "QuickSuiteSharedGuardrail")

discover_stack = QuickSuiteSharedDiscover(
    app,
    "QuickSuiteSharedDiscover",
    guardrail_id=guardrail_stack.guardrail_id,
)
discover_stack.add_dependency(guardrail_stack)

identity_stack = QuickSuiteSharedIdentity(app, "QuickSuiteSharedIdentity")

app.synth()
