#!/usr/bin/env python3
"""
Remove ALL emojis from codebase
Following TECHNICAL_ROLLOUT_FAILURE_PREVENTION_GUIDE.md - NO EMOJIS rule
"""

import os
import re
import sys
from pathlib import Path

def remove_emojis_from_file(file_path):
    """Remove emojis from a single file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content

        # Common emoji patterns to remove
        emoji_patterns = [
            r'[🎉✅❌🏠📊🔨📍🏗️⚠️🚨💡📝🔧🌟💯🎯🚀📈📉💭🔍📋✨🎨🛠️💪🎊🎈🎁🔥💎⭐🌈🎭🎪🎵🎶🎼🎸🎹🎺🎻🥁🎤🎧🎬🎥📸📹📽️🎮🕹️🎲🎰🎳🏆🥇🥈🥉🏅🎖️🏵️🎗️🎫🎟️🎪🎨🎭🎬🎤🎧🎼🎵🎶🎹🎸🎻🥁🎺🎷🎭🎪🎯🎲🎰🎳]',
            r'[😀😃😄😁😆😅🤣😂🙂🙃😉😊😇🥰😍🤩😘😗☺️😚😙🥲😋😛😜🤪😝🤑🤗🤭🤫🤔🤐🤨😐😑😶😏😒🙄😬🤥😌😔😪🤤😴😷🤒🤕🤢🤮🤧🥵🥶🥴😵🤯🤠🥳🥸😎🤓🧐]',
            r'[👍👎👌🤏✌️🤞🤟🤘🤙👈👉👆🖕👇☝️👍👎👊✊🤛🤜👏🙌👐🤲🤝🙏✍️💅🤳💪🦾🦿🦵🦶👂🦻👃🧠🫀🫁🦷🦴👀👁️👅👄💋🩸]'
        ]

        # Remove emoji patterns
        for pattern in emoji_patterns:
            content = re.sub(pattern, '', content)

        # Remove any remaining Unicode emoji ranges
        # Basic emoticons and symbols
        content = re.sub(r'[\U0001F600-\U0001F64F]', '', content)  # emoticons
        content = re.sub(r'[\U0001F300-\U0001F5FF]', '', content)  # symbols & pictographs
        content = re.sub(r'[\U0001F680-\U0001F6FF]', '', content)  # transport & map
        content = re.sub(r'[\U0001F1E0-\U0001F1FF]', '', content)  # flags
        content = re.sub(r'[\U00002600-\U000027BF]', '', content)  # misc symbols
        content = re.sub(r'[\U0001F900-\U0001F9FF]', '', content)  # supplemental symbols

        # Clean up any double spaces left by emoji removal
        content = re.sub(r'  +', ' ', content)

        # Only write if content changed
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True

        return False

    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def main():
    project_root = Path(__file__).parent.parent

    # File extensions to process
    extensions = ['.tsx', '.ts', '.js', '.jsx', '.py', '.md', '.txt']

    # Directories to skip
    skip_dirs = {
        'node_modules',
        '.next',
        '.git',
        '__pycache__',
        'backup',
        'migratePRPs'  # Skip backup directories
    }

    files_processed = 0
    files_changed = 0

    print("Removing ALL emojis from codebase...")
    print(f"Project root: {project_root}")

    for root, dirs, files in os.walk(project_root):
        # Skip unwanted directories
        dirs[:] = [d for d in dirs if d not in skip_dirs]

        for file in files:
            if any(file.endswith(ext) for ext in extensions):
                file_path = Path(root) / file
                files_processed += 1

                if remove_emojis_from_file(file_path):
                    files_changed += 1
                    print(f"Cleaned: {file_path}")

    print(f"\nCompleted!")
    print(f"Files processed: {files_processed}")
    print(f"Files changed: {files_changed}")

    if files_changed > 0:
        print("\nNOTE: All emojis have been removed from the codebase.")
        print("Following TECHNICAL_ROLLOUT_FAILURE_PREVENTION_GUIDE.md NO EMOJIS rule.")

if __name__ == "__main__":
    main()