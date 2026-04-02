"""
QuickSuiteSharedDiscover — qs-discover unified Lambda + IAM wiring.

Creates the qs-discover Lambda and grants it invoke permission on the
three discovery target Lambdas (roda-search, s3-browse, claws-discover).
Their ARNs are passed as CDK context variables at deploy time, after the
sub-project stacks have been deployed and written them to SSM.

Required CDK context vars (cdk deploy --context key=value):
  roda_search_arn       — ARN of quick-suite-data roda-search Lambda
  s3_browse_arn         — ARN of quick-suite-data s3-browse Lambda
  claws_discover_arn    — ARN of quick-suite-claws discover Lambda

Exports:
  CfnOutput DiscoverFunctionArn  — for AgentCore Gateway registration
"""

import aws_cdk as cdk
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_ssm as ssm
from constructs import Construct


class QuickSuiteSharedDiscover(cdk.Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        guardrail_id: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Resolve target ARNs from CDK context (set at deploy time)
        roda_search_arn = self.node.try_get_context("roda_search_arn") or ""
        s3_browse_arn = self.node.try_get_context("s3_browse_arn") or ""
        claws_discover_arn = self.node.try_get_context("claws_discover_arn") or ""

        # qs-discover Lambda
        discover_fn = lambda_.Function(
            self,
            "QsDiscoverFunction",
            function_name="qs-shared-discover",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="handler.handler",
            code=lambda_.Code.from_asset("lambdas/qs-discover"),
            timeout=cdk.Duration.seconds(30),
            memory_size=256,
            description=(
                "Unified discovery: fans out to roda-search, s3-browse, "
                "and claws-discover in parallel and returns ranked results."
            ),
            environment={
                "GUARDRAIL_ID": guardrail_id,
            },
        )

        # SSM read permissions for target ARN lookup
        discover_fn.add_to_role_policy(
            iam.PolicyStatement(
                actions=["ssm:GetParameter"],
                resources=[
                    self.format_arn(
                        service="ssm",
                        resource="parameter",
                        resource_name="quick-suite/lambdas/*",
                    )
                ],
            )
        )

        # Lambda invoke permissions on all three discovery targets
        target_arns = [a for a in [roda_search_arn, s3_browse_arn, claws_discover_arn] if a]
        if target_arns:
            discover_fn.add_to_role_policy(
                iam.PolicyStatement(
                    actions=["lambda:InvokeFunction"],
                    resources=target_arns,
                )
            )

        # CloudFormation output for AgentCore Gateway registration
        cdk.CfnOutput(
            self,
            "DiscoverFunctionArn",
            value=discover_fn.function_arn,
            description="qs-discover Lambda ARN — register as AgentCore Gateway Lambda target",
            export_name="QuickSuiteSharedDiscoverArn",
        )

        self.discover_fn = discover_fn
