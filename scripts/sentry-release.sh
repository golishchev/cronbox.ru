#!/bin/bash
set -e

# Sentry Release Tracking Script
# This script creates a new release in Sentry and associates it with commits
#
# Usage:
#   ./scripts/sentry-release.sh <component> <version>
#
# Example:
#   ./scripts/sentry-release.sh backend 0.1.0
#   ./scripts/sentry-release.sh frontend 0.1.0

COMPONENT=$1
VERSION=$2

if [ -z "$COMPONENT" ] || [ -z "$VERSION" ]; then
  echo "Usage: $0 <component> <version>"
  echo "Example: $0 backend 0.1.0"
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
echo "📦 Creating Sentry release: $RELEASE for project: $PROJECT"

# Create release
sentry-cli releases --project "$PROJECT" new "$RELEASE"

# Associate commits with release (auto-detect from git)
echo "🔗 Associating commits with release..."
sentry-cli releases --project "$PROJECT" set-commits "$RELEASE" --auto

# Finalize release
echo "✅ Finalizing release..."
sentry-cli releases --project "$PROJECT" finalize "$RELEASE"

echo "✨ Release $RELEASE created successfully!"
echo "   View at: https://sentry.serpdev.ru/organizations/sentry/releases/$RELEASE/"
