"""Utils used for scripting"""

import time

import requests


def download_direct_link_with_progress(url, target_filename):
    """Downloads a direct link url to target_filename"""
    with requests.get(url, stream=True, timeout=3000) as r:
        r.raise_for_status()
        total_size = int(r.headers.get("Content-Length", 1))
        downloaded = 0
        last_log_time = time.time()

        with open(target_filename, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
                downloaded += len(chunk)

                current_time = time.time()
                if current_time - last_log_time >= 2:
                    progress_percent = (
                        (downloaded / total_size) * 100 if total_size > 0 else 0
                    )
                    print(
                        f"Progress: {downloaded}/{total_size} bytes ({progress_percent:.2f}%)"
                    )
                    last_log_time = current_time
