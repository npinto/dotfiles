#!/usr/bin/env bash
#
# ig-dl.sh - Download Instagram posts (images + videos) using instaloader
#
# Usage:
#   ig-dl.sh <instagram_url_or_shortcode>
#   ig-dl.sh https://www.instagram.com/p/DNoevj6NFop/
#   ig-dl.sh DNoevj6NFop
#

set -euo pipefail

# Uncomment for debugging:
# set -x

usage() {
    cat <<EOF
Usage: $(basename "$0") <instagram_url_or_shortcode>

Download Instagram posts (images + videos) to current directory.

Examples:
    $(basename "$0") https://www.instagram.com/p/DNoevj6NFop/
    $(basename "$0") DNoevj6NFop

Options:
    -h, --help    Show this help message
EOF
    exit "${1:-0}"
}

# Check arguments
if [[ $# -eq 0 ]] || [[ "$1" == "-h" ]] || [[ "$1" == "--help" ]]; then
    usage
fi

# Check dependencies
if ! command -v instaloader &>/dev/null; then
    echo "Error: instaloader not found. Install with: brew install instaloader" >&2
    exit 1
fi

# Extract shortcode from URL or use as-is
input="$1"
code="${input%/}"        # Remove trailing slash
code="${code##*/}"       # Remove everything before last slash (gets shortcode from URL)

# Validate shortcode format (alphanumeric, dash, underscore)
if [[ ! "$code" =~ ^[A-Za-z0-9_-]+$ ]]; then
    echo "Error: Invalid shortcode format: $code" >&2
    exit 1
fi

echo "Downloading Instagram post: $code"

instaloader \
    --no-metadata-json \
    --no-captions \
    --dirname-pattern . \
    --filename-pattern "{date_utc}_{shortcode}" \
    -- -"$code"
