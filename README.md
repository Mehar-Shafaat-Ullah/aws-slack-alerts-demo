# AWS Slack Alerts Demo (Source + Build Only)

A tiny Node.js web app + Dockerfile, designed to demonstrate **AWS CodePipeline** (Source → Build) 
and **Slack alerts** (pipeline start/finish, stage start/finish, build success/fail) without any deploy stage.

## Quickstart (Local)

```bash
# 1) Run with Node
npm ci
npm start
# open http://localhost:3000

# 2) Or run with Docker
docker build -t aws-slack-alerts-demo:local .
docker run -d -p 3000:3000 --name web -e COMMIT_SHA=local aws-slack-alerts-demo:local
# open http://localhost:3000 and http://localhost:3000/version
```

## Repo Layout

```
aws-slack-alerts-demo/
├─ server.js
├─ package.json
├─ Dockerfile
├─ .dockerignore
├─ buildspec.yml
├─ public/
│  ├─ index.html
│  └─ style.css
├─ scripts/
│  └─ smoke-test.js
└─ infra/
   ├─ lambda_slack_notify/
   │  └─ index.py
   └─ eventbridge/
      └─ pipeline-rule.json
```

## Step 1 — Push to GitHub

1. Create a new repo on GitHub (public or private).
2. In this folder run:

```bash
git init
git add .
git commit -m "init: AWS Slack Alerts demo"
git branch -M main
git remote add origin https://github.com/<your-username>/<your-repo>.git
git push -u origin main
```

## Step 2 — Create CodeBuild Project (Docker-in-Docker enabled)

- Environment image: `aws/codebuild/standard:7.0` (or newer)
- Runtime: Ubuntu, compute small/medium is fine
- **Enable privileged mode** (needed to run Docker in buildspec)
- Service role needs permissions for CloudWatch logs (default is fine)

No artifacts bucket is required by CodeBuild itself, but CodePipeline needs artifacts, so we emit a small folder in `buildspec.yml`.

## Step 3 — Create CodePipeline (Source → Build only)

- **Source**: GitHub (connect to your repo), output artifact: `SourceOutput`
- **Build**: choose the CodeBuild project above, input artifact: `SourceOutput`
- No **Deploy** stage (skip it)

Every push to `main` (or manual “Release change”) will trigger the pipeline. The build will:
- Install Node deps
- Build a Docker image
- Run the container and **curl** health endpoints
- Emit `build_artifacts/build_info.txt`

## Step 4 — Slack Alerts (2 Options)

### Option A — *No-code* using **AWS Chatbot + CodeStar Notifications** (Recommended)

1. **Create SNS topic** for notifications:
   ```bash
   aws sns create-topic --name codepipeline-alerts
   # Save the TopicArn output
   ```

2. **Create CodeStar Notification rule** for your **CodePipeline** (replace ARNs/names):
   ```bash
   PIPELINE_ARN=$(aws codepipeline get-pipeline --name <your-pipeline-name> --query 'metadata.pipelineArn' --output text)
   TOPIC_ARN=<your-sns-topic-arn>

   aws codestar-notifications create-notification-rule      --name PipelineLifecycleAlerts      --resource $PIPELINE_ARN      --event-type-ids        codepipeline-pipeline-pipeline-execution-started        codepipeline-pipeline-pipeline-execution-succeeded        codepipeline-pipeline-pipeline-execution-failed        codepipeline-pipeline-stage-execution-started        codepipeline-pipeline-stage-execution-succeeded        codepipeline-pipeline-stage-execution-failed      --targets TargetType=SNS,TargetAddress=$TOPIC_ARN      --detail-type FULL
   ```

   (Optional) A second rule for your **CodeBuild** project:
   ```bash
   PROJECT_ARN=$(aws codebuild batch-get-projects --names <your-codebuild-project> --query 'projects[0].arn' --output text)
   aws codestar-notifications create-notification-rule      --name BuildStateAlerts      --resource $PROJECT_ARN      --event-type-ids        codebuild-project-build-state-succeeded        codebuild-project-build-state-failed        codebuild-project-build-state-in-progress      --targets TargetType=SNS,TargetAddress=$TOPIC_ARN      --detail-type FULL
   ```

3. **Connect Slack via AWS Chatbot** (Console steps):
   - AWS Chatbot → Slack → “Configure client” → *Add workspace* (one-time OAuth)
   - “Configure new channel” → pick your Slack workspace + channel
   - Select the **SNS topic** you created above
   - Save. Post a test message from Chatbot to verify

You will now get Slack messages on:
- Pipeline started/succeeded/failed
- Stage started/succeeded/failed
- Build in-progress/succeeded/failed

### Option B — *Custom* **EventBridge → Lambda → Slack Webhook**

Only use this if your org prefers webhooks over Chatbot.

1. Create an **Incoming Webhook** in Slack (URL looks like `https://hooks.slack.com/services/...`).  
2. Create the Lambda function from `infra/lambda_slack_notify/index.py` with env var `SLACK_WEBHOOK_URL`.
3. Create an EventBridge rule using `infra/eventbridge/pipeline-rule.json` and set the Lambda as the target:
   ```bash
   aws events put-rule --name pipeline-state-change --event-pattern file://infra/eventbridge/pipeline-rule.json
   RULE_ARN=$(aws events describe-rule --name pipeline-state-change --query Arn --output text)
   LAMBDA_ARN=<your-lambda-arn>
   aws lambda add-permission --function-name <your-lambda-name>      --statement-id allow-events      --action "lambda:InvokeFunction"      --principal events.amazonaws.com      --source-arn $RULE_ARN
   aws events put-targets --rule pipeline-state-change --targets "Id"="1","Arn"="$LAMBDA_ARN"
   ```

---

## Triggering a Demo Run

Edit `public/index.html` (change the heading) → commit → push to `main`.  
Watch CodePipeline run; Slack should receive the notifications.

---

## Troubleshooting

- **Build fails at Docker step:** Make sure CodeBuild project has **Privileged mode** enabled.
- **Slack receives nothing:** Check the SNS topic subscription inside **AWS Chatbot**. Try the “Send test message” button.
- **Pipeline has no artifacts error:** Ensure `buildspec.yml` outputs to `build_artifacts/**`.
- **Webhook path blocked by proxy:** If using Option B, confirm your VPC egress or place Lambda out of VPC.