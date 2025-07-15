#!/bin/bash

set -e
#set -x

for file in *; do
  # Check if it's a regular file
  if [[ -f "$file" ]]; then
    # Get the modification date of the file in YYYY-MM-DD format
    file_date=$(date -r "$file" +%Y-%m-%d)
    
    # Get the base name of the file
    base_name=$(basename "$file")
    
    # Construct the new file name
    new_name="${file_date} ${base_name}"
    
    # Rename the file
    mv -vf "$file" "$new_name"
  fi
done
