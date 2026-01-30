#!/bin/bash
set -e

# Sentry Deploy Notification Script
# This script notifies Sentry about a deployment
#
# Usage:
#   ./scripts/sentry-deploy.sh <component> <version> <environment>
#
# Example:
#   ./scripts/sentry-deploy.sh backend 0.1.0 production
#   ./scripts/sentry-deploy.sh frontend 0.1.0 staging

COMPONENT=$1
VERSION=$2
ENVIRONMENT=$3

if [ -z "$COMPONENT" ] || [ -z "$VERSION" ] || [ -z "$ENVIRONMENT" ]; then
  echo "Usage: $0 <component> <version> <environment>"
  echo "Example: $0 backend 0.1.0 production"
  exit 1
fi

if [ "$COMPONENT" != "backend" ] && [ "$COMPONENT" != "frontend" ]; then
  echo "Error: component must be 'backend' or 'frontend'"
  exit 1
fi

# Check if sentry-cli is installed
if ! command -v sentry-cli &> /dev/null; then
  echo "Error: sentry-cli is not installed"
  echo "Install with: curl -sL https://sentry.io/get-cli/ | bash"
  exit 1
fi

# Set project based on component
if [ "$COMPONENT" = "backend" ]; then
  PROJECT="cronbox-backend"
else
  PROJECT="cronbox-frontend"
fi

RELEASE="cronbox-${COMPONENT}@${VERSION}"
echo "🚀 Notifying Sentry about deployment: $RELEASE to $ENVIRONMENT"

# Create deployment
sentry-cli releases --project "$PROJECT" deploys "$RELEASE" new -e "$ENVIRONMENT"

echo "✅ Deployment notification sent!"
echo "   View at: https://sentry.serpdev.ru/organizations/sentry/releases/$RELEASE/"
