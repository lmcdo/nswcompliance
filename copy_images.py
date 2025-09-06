#!/usr/bin/env python3
import os
import shutil
from pathlib import Path

def copy_all_images():
    output_dir = Path("output")
    images_dir = Path("images")
    
    # Create images directory if it doesn't exist
    images_dir.mkdir(exist_ok=True)
    
    copied_count = 0
    
    # Walk through all subdirectories in output
    for root, dirs, files in os.walk(output_dir):
        root_path = Path(root)
        
        # Only process directories that contain "images"
        if root_path.name == "images":
            parent_folder = root_path.parent.name
            
            # Clean up the parent folder name for use in filenames
            clean_name = parent_folder.replace(" ", "_").replace("-", "_").replace("(", "").replace(")", "")
            clean_name = clean_name.replace(".", "_").replace(",", "")[:50]  # Limit length
            
            print(f"Processing images from: {parent_folder}")
            
            # Copy each image file
            for image_file in files:
                if image_file.lower().endswith(('.jpg', '.jpeg', '.png', '.gif')):
                    source = root_path / image_file
                    
                    # Create descriptive filename
                    file_ext = Path(image_file).suffix
                    new_name = f"{clean_name}_{copied_count:03d}{file_ext}"
                    destination = images_dir / new_name
                    
                    try:
                        shutil.copy2(source, destination)
                        print(f"  Copied: {new_name}")
                        copied_count += 1
                        
                        # Limit to reasonable number for testing
                        if copied_count >= 50:
                            print(f"Reached limit of 50 images for testing")
                            return copied_count
                            
                    except Exception as e:
                        print(f"  Error copying {image_file}: {e}")
    
    return copied_count

if __name__ == "__main__":
    print("Copying images from output folders...")
    total = copy_all_images()
    print(f"Total images copied: {total}")