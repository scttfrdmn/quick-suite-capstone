"""
QuickSuiteSharedIdentity — shared Cognito identity stack.

Single Cognito User Pool used by all Quick Suite sub-projects for both:
  1. AgentCore Gateway OAuth (M2M client_credentials flow)
  2. Department-level attribute enforcement (routing, budget, data access)

Department governance is stored in a GroupMetadataTable (DynamoDB):
  PK: group_name (str)
  Attributes:
    department              (str)  — display name
    max_monthly_budget_usd  (N)    — per-department compute budget
    approved_providers      (L)    — allowed model providers (e.g. ["bedrock","openai"])
    approved_sources        (S)    — allowed data source labels (e.g. "roda,s3-ir-data")

User Pool custom attribute:
  custom:department — set at sign-up to the Cognito group name; read by
  the router's _preferred_for() and compute_run's budget check.

SSM exports (no CloudFormation cross-stack deps):
  /quick-suite/shared/user_pool_id
  /quick-suite/shared/user_pool_client_id
  /quick-suite/shared/group_metadata_table
"""

import json

import aws_cdk as cdk
from aws_cdk import aws_cognito as cognito
from aws_cdk import aws_dynamodb as dynamodb
from aws_cdk import aws_ssm as ssm
from constructs import Construct


# Default department groups seeded into GroupMetadataTable at deploy time.
# Operators add real groups after deployment; these serve as reference entries.
_DEFAULT_GROUPS = [
    {
        "group_name": "default",
        "department": "General",
        "max_monthly_budget_usd": 50,
        "approved_providers": ["bedrock"],
        "approved_sources": "roda",
    },
    {
        "group_name": "research",
        "department": "Research Computing",
        "max_monthly_budget_usd": 200,
        "approved_providers": ["bedrock", "anthropic", "openai"],
        "approved_sources": "roda,s3-research",
    },
    {
        "group_name": "administrative",
        "department": "Administration",
        "max_monthly_budget_usd": 100,
        "approved_providers": ["bedrock", "openai"],
        "approved_sources": "s3-admin",
    },
]


class QuickSuiteSharedIdentity(cdk.Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        prefix = "qs-shared"

        # -----------------------------------------------------------------
        # Cognito User Pool
        # -----------------------------------------------------------------
        user_pool = cognito.UserPool(
            self,
            "UserPool",
            user_pool_name=f"{prefix}-identity",
            # Department stored as a custom attribute on each user token.
            # Populated at sign-up; read by router and compute_run.
            custom_attributes={
                "department": cognito.StringAttribute(mutable=True),
            },
            # Password policy — used for human users; M2M uses client secret
            password_policy=cognito.PasswordPolicy(
                min_length=12,
                require_uppercase=True,
                require_digits=True,
                require_symbols=True,
            ),
            self_sign_up_enabled=False,
            removal_policy=cdk.RemovalPolicy.RETAIN,
        )

        # Resource server — scopes mirror each tool plane
        resource_server = user_pool.add_resource_server(
            "ResourceServer",
            identifier="https://quicksuite.internal",
            scopes=[
                cognito.ResourceServerScope(
                    scope_name="router",
                    scope_description="Model router access",
                ),
                cognito.ResourceServerScope(
                    scope_name="data",
                    scope_description="Open data tool access",
                ),
                cognito.ResourceServerScope(
                    scope_name="compute",
                    scope_description="Compute tool access",
                ),
                cognito.ResourceServerScope(
                    scope_name="claws",
                    scope_description="clAWS data excavation access",
                ),
            ],
        )

        # M2M app client for AgentCore Gateway (client_credentials)
        app_client = user_pool.add_client(
            "AgentCoreClient",
            user_pool_client_name=f"{prefix}-agentcore",
            generate_secret=True,
            o_auth=cognito.OAuthSettings(
                flows=cognito.OAuthFlows(client_credentials=True),
                scopes=[
                    cognito.OAuthScope.resource_server(
                        resource_server,
                        cognito.ResourceServerScope(
                            scope_name="router",
                            scope_description="Model router access",
                        ),
                    ),
                    cognito.OAuthScope.resource_server(
                        resource_server,
                        cognito.ResourceServerScope(
                            scope_name="data",
                            scope_description="Open data tool access",
                        ),
                    ),
                    cognito.OAuthScope.resource_server(
                        resource_server,
                        cognito.ResourceServerScope(
                            scope_name="compute",
                            scope_description="Compute tool access",
                        ),
                    ),
                    cognito.OAuthScope.resource_server(
                        resource_server,
                        cognito.ResourceServerScope(
                            scope_name="claws",
                            scope_description="clAWS data excavation access",
                        ),
                    ),
                ],
            ),
            prevent_user_existence_errors=True,
        )

        # Cognito hosted domain — prefix configurable via CDK context
        cognito_domain_prefix = (
            self.node.try_get_context("cognito_domain_prefix")
            or f"quicksuite-identity-{cdk.Aws.ACCOUNT_ID}"
        )
        domain = user_pool.add_domain(
            "Domain",
            cognito_domain=cognito.CognitoDomainOptions(
                domain_prefix=cognito_domain_prefix,
            ),
        )

        # Pre-defined department Cognito groups
        for grp in _DEFAULT_GROUPS:
            cognito.CfnUserPoolGroup(
                self,
                f"Group{grp['group_name'].capitalize()}",
                user_pool_id=user_pool.user_pool_id,
                group_name=grp["group_name"],
                description=f"Department group: {grp['department']}",
            )

        # -----------------------------------------------------------------
        # GroupMetadataTable — department governance attributes
        # -----------------------------------------------------------------
        group_metadata_table = dynamodb.Table(
            self,
            "GroupMetadataTable",
            table_name=f"{prefix}-group-metadata",
            partition_key=dynamodb.Attribute(
                name="group_name",
                type=dynamodb.AttributeType.STRING,
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=cdk.RemovalPolicy.RETAIN,
        )

        # -----------------------------------------------------------------
        # SSM exports (avoid CloudFormation cross-stack dependencies)
        # -----------------------------------------------------------------
        ssm.StringParameter(
            self,
            "UserPoolIdParam",
            parameter_name="/quick-suite/shared/user_pool_id",
            string_value=user_pool.user_pool_id,
            description="Shared Quick Suite Cognito User Pool ID",
        )
        ssm.StringParameter(
            self,
            "UserPoolClientIdParam",
            parameter_name="/quick-suite/shared/user_pool_client_id",
            string_value=app_client.user_pool_client_id,
            description="AgentCore Gateway M2M app client ID",
        )
        ssm.StringParameter(
            self,
            "GroupMetadataTableParam",
            parameter_name="/quick-suite/shared/group_metadata_table",
            string_value=group_metadata_table.table_name,
            description="DynamoDB table name for department group metadata",
        )
        ssm.StringParameter(
            self,
            "TokenUrlParam",
            parameter_name="/quick-suite/shared/token_url",
            string_value=domain.base_url() + "/oauth2/token",
            description="Cognito OAuth token endpoint for AgentCore Gateway",
        )

        # CloudFormation outputs for post-deploy scripts
        cdk.CfnOutput(self, "UserPoolIdOutput", value=user_pool.user_pool_id)
        cdk.CfnOutput(self, "UserPoolClientIdOutput", value=app_client.user_pool_client_id)
        cdk.CfnOutput(self, "TokenUrlOutput", value=domain.base_url() + "/oauth2/token")
        cdk.CfnOutput(
            self, "GroupMetadataTableOutput", value=group_metadata_table.table_name
        )

        # Expose for downstream stacks (avoid SSM round-trip during synth)
        self.user_pool = user_pool
        self.user_pool_id = user_pool.user_pool_id
        self.app_client_id = app_client.user_pool_client_id
        self.group_metadata_table = group_metadata_table
