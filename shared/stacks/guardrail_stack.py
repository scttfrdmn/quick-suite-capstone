"""
QuickSuiteSharedGuardrail — shared Bedrock Guardrail stack.

Creates a single Bedrock Guardrail with the superset policy of all
Quick Suite sub-projects (router + claws). Exports the guardrail ID
via CloudFormation output and SSM Parameter Store so sub-projects
can reference it without cross-stack CloudFormation dependencies.

SSM path: /quick-suite/shared/guardrail_id
"""

import aws_cdk as cdk
from aws_cdk import aws_bedrock as bedrock
from aws_cdk import aws_ssm as ssm
from constructs import Construct


class QuickSuiteSharedGuardrail(cdk.Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        guardrail = bedrock.CfnGuardrail(
            self,
            "SharedGuardrail",
            name="qs-shared-guardrail",
            description=(
                "Shared content guardrail for all Quick Suite extensions. "
                "Superset of router and claws guardrail policies."
            ),
            blocked_input_messaging=(
                "I'm unable to process this request due to content policy restrictions."
            ),
            blocked_outputs_messaging=(
                "The response was blocked due to content policy restrictions."
            ),
            content_policy_config=bedrock.CfnGuardrail.ContentPolicyConfigProperty(
                filters_config=[
                    bedrock.CfnGuardrail.ContentFilterConfigProperty(
                        type="SEXUAL",
                        input_strength="HIGH",
                        output_strength="HIGH",
                    ),
                    bedrock.CfnGuardrail.ContentFilterConfigProperty(
                        type="VIOLENCE",
                        input_strength="HIGH",
                        output_strength="HIGH",
                    ),
                    bedrock.CfnGuardrail.ContentFilterConfigProperty(
                        type="HATE",
                        input_strength="HIGH",
                        output_strength="HIGH",
                    ),
                    bedrock.CfnGuardrail.ContentFilterConfigProperty(
                        type="INSULTS",
                        input_strength="MEDIUM",
                        output_strength="MEDIUM",
                    ),
                    bedrock.CfnGuardrail.ContentFilterConfigProperty(
                        type="MISCONDUCT",
                        input_strength="HIGH",
                        output_strength="HIGH",
                    ),
                    bedrock.CfnGuardrail.ContentFilterConfigProperty(
                        type="PROMPT_ATTACK",
                        input_strength="HIGH",
                        output_strength="NONE",
                    ),
                ]
            ),
            sensitive_information_policy_config=bedrock.CfnGuardrail.SensitiveInformationPolicyConfigProperty(
                pii_entities_config=[
                    # Block: payment / credential PII
                    bedrock.CfnGuardrail.PiiEntityConfigProperty(
                        type="US_SOCIAL_SECURITY_NUMBER", action="BLOCK"
                    ),
                    bedrock.CfnGuardrail.PiiEntityConfigProperty(
                        type="CREDIT_DEBIT_CARD_NUMBER", action="BLOCK"
                    ),
                    bedrock.CfnGuardrail.PiiEntityConfigProperty(
                        type="CREDIT_DEBIT_CARD_CVV", action="BLOCK"
                    ),
                    bedrock.CfnGuardrail.PiiEntityConfigProperty(
                        type="CREDIT_DEBIT_CARD_EXPIRY", action="BLOCK"
                    ),
                    bedrock.CfnGuardrail.PiiEntityConfigProperty(
                        type="PIN", action="BLOCK"
                    ),
                    bedrock.CfnGuardrail.PiiEntityConfigProperty(
                        type="PASSWORD", action="BLOCK"
                    ),
                    bedrock.CfnGuardrail.PiiEntityConfigProperty(
                        type="AWS_ACCESS_KEY", action="BLOCK"
                    ),
                    bedrock.CfnGuardrail.PiiEntityConfigProperty(
                        type="AWS_SECRET_KEY", action="BLOCK"
                    ),
                    bedrock.CfnGuardrail.PiiEntityConfigProperty(
                        type="US_INDIVIDUAL_TAX_IDENTIFICATION_NUMBER", action="BLOCK"
                    ),
                    # Anonymize: identity / contact PII
                    bedrock.CfnGuardrail.PiiEntityConfigProperty(
                        type="EMAIL", action="ANONYMIZE"
                    ),
                    bedrock.CfnGuardrail.PiiEntityConfigProperty(
                        type="PHONE", action="ANONYMIZE"
                    ),
                    bedrock.CfnGuardrail.PiiEntityConfigProperty(
                        type="NAME", action="ANONYMIZE"
                    ),
                    bedrock.CfnGuardrail.PiiEntityConfigProperty(
                        type="ADDRESS", action="ANONYMIZE"
                    ),
                    bedrock.CfnGuardrail.PiiEntityConfigProperty(
                        type="AGE", action="ANONYMIZE"
                    ),
                    bedrock.CfnGuardrail.PiiEntityConfigProperty(
                        type="DATE_TIME", action="ANONYMIZE"
                    ),
                    bedrock.CfnGuardrail.PiiEntityConfigProperty(
                        type="IP_ADDRESS", action="ANONYMIZE"
                    ),
                    bedrock.CfnGuardrail.PiiEntityConfigProperty(
                        type="URL", action="ANONYMIZE"
                    ),
                ],
                regexes_config=[
                    # Anonymize project codes (PRJ-123456)
                    bedrock.CfnGuardrail.RegexConfigProperty(
                        name="ProjectCode",
                        pattern=r"PRJ-\d{6}",
                        action="ANONYMIZE",
                        description="Internal project codes",
                    ),
                    # Anonymize bare AWS account IDs (12-digit numbers)
                    bedrock.CfnGuardrail.RegexConfigProperty(
                        name="AwsAccountId",
                        pattern=r"\b\d{12}\b",
                        action="ANONYMIZE",
                        description="AWS account ID numbers",
                    ),
                    # Block medical record numbers
                    bedrock.CfnGuardrail.RegexConfigProperty(
                        name="MedicalRecordNumber",
                        pattern=r"MRN[-:]?\s?\d{6,10}",
                        action="BLOCK",
                        description="Medical record numbers",
                    ),
                ],
            ),
            word_policy_config=bedrock.CfnGuardrail.WordPolicyConfigProperty(
                words_config=[
                    bedrock.CfnGuardrail.WordConfigProperty(text="CONFIDENTIAL-INTERNAL"),
                    bedrock.CfnGuardrail.WordConfigProperty(text="TOP-SECRET"),
                ]
            ),
        )

        # SSM export — readable by sub-projects without CloudFormation dependency
        ssm.StringParameter(
            self,
            "GuardrailIdParam",
            parameter_name="/quick-suite/shared/guardrail_id",
            string_value=guardrail.attr_guardrail_id,
            description="Shared Bedrock Guardrail ID for all Quick Suite extensions",
        )

        # CloudFormation output
        cdk.CfnOutput(
            self,
            "GuardrailId",
            value=guardrail.attr_guardrail_id,
            description="Shared Bedrock Guardrail ID",
            export_name="QuickSuiteSharedGuardrailId",
        )

        # Expose for app.py dependency wiring
        self.guardrail_id = guardrail.attr_guardrail_id
