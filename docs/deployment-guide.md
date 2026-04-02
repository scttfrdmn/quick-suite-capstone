# Institutional Deployment Guide

This guide covers the complete setup process for deploying the Quick Suite extensions
at an institutional level — from the first CDK command to users seeing tools in their
Quick Suite workspace.

The deployment is done once by a cloud or IT team. Individual users don't install
anything. Once the administrator shares the integration with a user or group, the tools
appear automatically in their Quick Suite chat interface.

---

## Who Does What

| Role | Responsibilities |
|------|----------------|
| **Cloud / IT team** | Deploy CDK stacks, configure AgentCore Gateway, seed the data catalog |
| **Data steward / IT security** | Write Cedar policies defining which groups can access which data |
| **Quick Suite administrator** | Configure MCP Actions, share with users and groups |
| **Department data owners** | Identify which S3 buckets and Athena tables should be accessible |

In a smaller institution one person may cover all of these roles.

---

## Prerequisites

Before starting, you need:

- An AWS account with Bedrock enabled in your target region. Verify model access is
  granted for at least one Claude model family in the Bedrock console.
- AWS CDK v2 installed: `npm install -g aws-cdk`
- Python 3.12+ and [uv](https://docs.astral.sh/uv/) (or pip)
- AWS credentials configured with sufficient permissions to deploy IAM roles,
  Lambda functions, DynamoDB tables, S3 buckets, Step Functions, and Bedrock resources
- A Quick Suite instance where you have administrator access
- (For clAWS) At least one Athena database or S3 bucket containing institutional data
  that users should be able to query

If you plan to use the Router with external providers (Anthropic, OpenAI, Gemini), have
those API keys available. You'll add them to Secrets Manager during deployment.

---

## Step 1 — Deploy the Router (sets up the shared Gateway)

The Router is deployed first because it creates the AgentCore Gateway that all other
extensions will attach to.

```bash
git clone https://github.com/scttfrdmn/quick-suite-router.git
cd quick-suite-router

uv sync --extra cdk

cp config/routing_config.example.yaml config/routing_config.yaml
# Edit routing_config.yaml to set provider preferences for your institution
# At minimum, Bedrock works immediately with no changes needed

cdk bootstrap aws://YOUR_ACCOUNT_ID/YOUR_REGION   # first time only
cdk deploy
```

> **Important:** AgentCore Gateway's inbound authentication type (`AWS_IAM`, `CUSTOM_JWT`,
> or `NONE`) is immutable after the Gateway is created. If you need to change it, you
> must delete and recreate the Gateway. The Router stack creates a `CUSTOM_JWT` gateway
> backed by Cognito — this is the correct setting for Quick Suite MCP Actions and cannot
> be changed later without redeploying the stack.

When the deploy finishes, note these CloudFormation outputs — you'll need them in later steps:

```bash
aws cloudformation describe-stacks \
  --stack-name QuickSuiteRouterStack \
  --query 'Stacks[0].Outputs' \
  --output table
```

| Output Key | What it is | Used in |
|-----------|-----------|---------|
| `GatewayId` | AgentCore Gateway ID | Data, Compute, clAWS deploys |
| `GatewayArn` | Full Gateway ARN | clAWS policy attachment |
| `GatewayEndpointUrl` | HTTPS endpoint URL | Quick Suite MCP Actions (Step 6) |

If you're using external AI providers, add their credentials to Secrets Manager now:

```bash
# Only add the providers your institution has subscriptions for

aws secretsmanager put-secret-value \
  --secret-id qs-router/anthropic \
  --secret-string '{"api_key": "sk-ant-..."}'

aws secretsmanager put-secret-value \
  --secret-id qs-router/openai \
  --secret-string '{"api_key": "sk-...", "organization": "org-..."}'

aws secretsmanager put-secret-value \
  --secret-id qs-router/gemini \
  --secret-string '{"api_key": "AIza..."}'
```

Any provider without a configured secret is silently skipped — Bedrock is always
available as the fallback with no key needed.

---

## Step 2 — Deploy the Data Extension

```bash
git clone https://github.com/scttfrdmn/quick-suite-data.git
cd quick-suite-data

uv sync --extra cdk

# Configure institutional S3 sources before deploying
cp config/sources.example.yaml config/sources.yaml
```

Edit `config/sources.yaml` to list the S3 buckets your institution wants to expose
through `s3_browse` and `s3_load`. This is the complete list — users can only reach
buckets explicitly configured here, regardless of their IAM permissions.

```yaml
sources:
  - label: financial-aid
    bucket: your-institutional-data-bucket
    prefix: financial-aid/
    description: Financial aid records and FAFSA processing data
    allowed_groups:
      - financial-aid-staff
      - institutional-research

  - label: student-outcomes
    bucket: your-institutional-data-bucket
    prefix: student-outcomes/
    description: Graduation, retention, and transfer tracking cohorts
    allowed_groups:
      - institutional-research
      - provost-office

  - label: alumni-giving
    bucket: your-advancement-bucket
    prefix: giving-records/
    description: Alumni donor history and engagement data
    allowed_groups:
      - advancement-office
```

Now deploy, passing the Gateway ID from Step 1:

```bash
cdk deploy \
  --context agentcore_gateway_id=agr-abc123 \
  --context quicksight_account_id=123456789012
```

After deploying, seed the RODA public dataset catalog immediately:

```bash
aws lambda invoke \
  --function-name qs-data-catalog-sync \
  /dev/null
```

This populates the DynamoDB catalog with 500+ public dataset entries. Without this,
`roda_search` returns empty results until the daily scheduled sync runs.

---

## Step 3 — Deploy Compute

```bash
git clone https://github.com/scttfrdmn/quick-suite-compute.git
cd quick-suite-compute

uv sync --extra cdk
```

Get the claws-resolver ARN from the Data stack — Compute needs it to resolve
`claws://` URIs at job execution time:

```bash
RESOLVER_ARN=$(aws cloudformation describe-stacks \
  --stack-name QuickSuiteData \
  --query 'Stacks[0].Outputs[?OutputKey==`ClawsResolverArn`].OutputValue' \
  --output text)
```

Deploy:

```bash
cdk deploy \
  --context agentcore_gateway_id=agr-abc123 \
  --context claws_resolver_arn=$RESOLVER_ARN \
  --context monthly_budget_usd=50        # per-user monthly spend limit
  --context max_concurrent_jobs=2        # max simultaneous jobs per user
```

To also enable the Spark profile for large-scale joins (requires EMR Serverless):

```bash
cdk deploy --context enable_emr=true  # add to the above
```

---

## Step 4 — Deploy clAWS

```bash
git clone https://github.com/scttfrdmn/claws.git
cd claws
uv sync --extra cdk

cd infra/cdk
```

Before deploying, decide which Athena databases and S3 paths should be accessible.
Tag each Glue table you want to expose with a `claws:space` tag:

```bash
aws glue tag-resource \
  --resource-arn arn:aws:glue:REGION:ACCOUNT:table/enrollment_db/student_cohorts \
  --tags-to-add "claws:space=enrollment"

aws glue tag-resource \
  --resource-arn arn:aws:glue:REGION:ACCOUNT:table/finance_db/aid_records \
  --tags-to-add "claws:space=financial-aid"
```

Deploy, attaching to the shared Gateway:

```bash
cdk deploy --all \
  -c CLAWS_GATEWAY_ID=agr-abc123 \
  -c quicksight_account_id=123456789012 \
  -c claws_lookup_table=qs-claws-lookup
```

---

## Step 5 — Write Cedar Policies for Each Department

Cedar policies define who can query what. They live in `policies/` in the clAWS repo
and are deployed as part of `ClawsPolicyStack`. You don't need to redeploy the Lambda
functions when you change policies — only the policy stack.

A minimal starting point for a university deployment:

**`policies/institutional-research.cedar`** — IR can query enrollment and retention data,
aggregate only:
```cedar
permit(
  principal in Group::"institutional-research",
  action in [Action::"discover", Action::"probe", Action::"plan", Action::"excavate", Action::"refine"],
  resource
) when {
  context.source.space in ["enrollment", "student-outcomes", "retention"] &&
  context.constraints.read_only == true
};

permit(
  principal in Group::"institutional-research",
  action == Action::"export",
  resource
) when {
  context.destination.type in ["s3", "quicksight"]
};
```

**`policies/financial-aid.cedar`** — Financial aid staff can query aid records but not
export row-level data:
```cedar
permit(
  principal in Group::"financial-aid-staff",
  action in [Action::"discover", Action::"probe", Action::"plan", Action::"excavate"],
  resource
) when {
  context.source.space == "financial-aid" &&
  context.constraints.read_only == true &&
  context.constraints.max_cost_dollars <= 5.00
};
```

**`policies/public-data.cedar`** — Everyone can use public RODA data (no restrictions
needed on public datasets):
```cedar
permit(
  principal,
  action in [Action::"discover", Action::"probe", Action::"plan", Action::"excavate", Action::"refine", Action::"export"],
  resource
) when {
  context.source.space == "public"
};
```

Deploy updated policies without redeploying anything else:

```bash
cdk deploy ClawsPolicyStack
```

See the [clAWS user guide](https://github.com/scttfrdmn/claws/blob/main/docs/user-guide.md)
for the full Cedar policy reference and more complex examples.

---

## Step 6 — Configure MCP Actions in Quick Suite

This step happens in the Quick Suite admin console, not the AWS console.

**Background — how the auth works:** Quick Suite MCP Actions supports two auth modes.
This deployment uses **Service Authentication** (service-to-service, also called 2LO),
which is the right choice for M2M connections to backend tools like AgentCore Gateway.
In this mode, Quick Suite calls the Cognito token endpoint using the client credentials
grant, receives a JWT, and presents it as a Bearer token on every MCP call to the
Gateway. The Gateway validates the token using OIDC — it was configured at deploy time
with Cognito's OIDC discovery URL, so it can verify signatures without any additional
setup. From the admin console you just fill in three fields.

The other mode, **User Authentication** (3LO / authorization code), is for integrations
where individual users must authorize access on their own behalf — for example, granting
Quick Suite access to a personal Google Drive. That is not what we're doing here.

Get all four required values from the Router stack at once:

```bash
aws cloudformation describe-stacks \
  --stack-name QuickSuiteRouterStack \
  --query 'Stacks[0].Outputs[?contains(OutputKey, `Cognito`) || OutputKey==`GatewayEndpointUrl`].{Key:OutputKey,Value:OutputValue}' \
  --output table
```

| Field in Quick Suite | CloudFormation Output Key | Example |
|---------------------|--------------------------|---------|
| Server URL | `GatewayEndpointUrl` | `https://abc123.execute-api.us-east-1.amazonaws.com/prod` |
| Client ID | `CognitoClientId` | `3abc123def456ghi` |
| Client secret | `CognitoClientSecret` | `...` |
| Token URL | `CognitoTokenUrl` | `https://qs-abc123.auth.us-east-1.amazoncognito.com/oauth2/token` |

In the Quick Suite admin console:

1. Open Quick Suite as an administrator
2. Go to **Settings → Integrations → MCP Actions**
3. Click **Add MCP Server**
4. Enter the `GatewayEndpointUrl` as the server URL
5. Choose **Service Authentication** as the authentication type
6. Enter the Client ID, Client Secret, and Token URL from the table above
7. Name the server — for example, "University Research Tools"
8. Save

Quick Suite connects to AgentCore Gateway and discovers all registered tools
automatically. You should see the full tool list appear: analyze, generate, research,
summarize, code, roda_search, roda_load, s3_browse, s3_preview, s3_load,
compute_profiles, compute_run, compute_status, discover, probe, plan, excavate,
refine, export.

> **Note:** MCP operations in Quick Suite have a 60-second timeout. Compute jobs that
> run longer (e.g., the Spark profile at ~8 minutes) use an async pattern — `compute_run`
> returns a job ID immediately and `compute_status` polls for completion, so the 60-second
> limit applies per tool call, not per job.

---

## Step 7 — Share with Users and Groups

With the integration saved, share it the same way you'd share any Quick Suite integration:

1. In the integration settings, open **Sharing**
2. Add users, groups, or domains as appropriate for your rollout

A few suggested sharing strategies:

**Pilot rollout** — Share with a small group first (IR office, one research group) to
validate Cedar policies and data access before opening broadly. This is the right
approach for any deployment involving sensitive institutional data.

**Department-by-department** — Share with each department as their Cedar policies are
written and validated. Advancement gets the integration when the alumni-giving policy is
ready; financial aid gets it when the financial-aid policy is validated.

**Broad rollout** — Once you're confident in the policies, share with your entire
institution. Public RODA data tools work for everyone; access to restricted data is
still gated by Cedar policies regardless of who has the integration.

From the user's perspective, there is nothing to install or configure. The tools
appear in their Quick Suite chat interface the next time they open it.

---

## Verifying the Deployment

### Check that tools are visible to users

Have a test user open Quick Suite and start a conversation. They should be able to ask:

> *"What public datasets are available related to enrollment?"*

If `roda_search` is working, they'll get a list of IPEDS and related datasets back.

> *"What analysis profiles are available for my data?"*

If `compute_profiles` is working, they'll see the list of ten profiles with descriptions.

### Check that access controls are working

Log in as a user who should *not* have access to financial aid data and try:

> *"Find data sources in the financial-aid domain."*

Cedar should deny this with a message indicating the user's policy doesn't permit access
to that data space. If it returns results instead, check the Cedar policy deployment.

### Check the CloudWatch dashboard

The Router stack deploys a CloudWatch dashboard named `qs-router-usage`. After a few
test conversations, verify that metrics are appearing for your active providers.

---

## Day-Two Operations

**Adding a new department's data source**

1. Tag the relevant Glue tables with `claws:space=new-space-name`
2. Write a Cedar policy for the new department
3. Add the S3 bucket to `sources.yaml` in the Data extension if needed
4. Run `cdk deploy ClawsPolicyStack` (policy update only — no Lambda redeployment)
5. If S3 sources changed, run `cdk deploy QuickSuiteData` as well
6. Share the Quick Suite integration with the new department's group

**Adjusting spend limits**

```bash
# Raise the per-user monthly budget
cdk deploy QuickSuiteCompute --context monthly_budget_usd=100

# Raise the concurrent job limit
cdk deploy QuickSuiteCompute --context max_concurrent_jobs=5
```

**Rotating an external provider API key**

```bash
aws secretsmanager put-secret-value \
  --secret-id qs-router/openai \
  --secret-string '{"api_key": "sk-new-key...", "organization": "org-..."}'
```

The Router Lambda fetches the secret at runtime — no redeployment needed. The response
cache won't automatically invalidate, so any cached responses from before the rotation
will still be served until their TTL expires.

**Onboarding a new AI provider**

Add credentials to Secrets Manager (see Step 1) and add the provider to
`routing_config.yaml`. Redeploy the Router stack:

```bash
cdk deploy QuickSuiteRouterStack
```

---

## Cost Summary

| Extension | Monthly Infrastructure | Per-Use Cost |
|-----------|----------------------|-------------|
| Router | ~$5 | LLM token costs at your provider rates |
| Data | ~$1 | < $0.01 per search or load |
| Compute | ~$5 | $0.01–$0.50 per analysis job |
| clAWS | ~$3 | Athena: $5/TB scanned (partition pruning keeps this low) |
| **Total** | **~$14/month** | Scales with usage |

Quick Sight SPICE ingestion costs apply when datasets are loaded — standard Quick Sight
pricing per GB of imported data.
