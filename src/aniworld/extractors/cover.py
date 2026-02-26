import requests
from PIL import Image
from io import BytesIO

API_KEY = "382956036af4dcc39ae06e5c1a6083d9"
BASE_URL = "https://api.themoviedb.org/3"
IMAGE_BASE_URL = "https://image.tmdb.org/t/p/original"

def download_cover_2x3(title, output_path=None):
    def search(endpoint):
        url = f"{BASE_URL}/search/{endpoint}"
        params = {"api_key": API_KEY, "query": title}
        r = requests.get(url, params=params)
        r.raise_for_status()
        data = r.json()
        return data["results"][0] if data["results"] else None

    # Try movie first, then TV
    result = search("movie") or search("tv")
    if not result:
        raise ValueError("Title not found")

    poster_path = result.get("poster_path")
    if not poster_path:
        raise ValueError("No poster available")

    # Download image
    image_url = f"{IMAGE_BASE_URL}{poster_path}"
    img_response = requests.get(image_url)
    img_response.raise_for_status()
    img = Image.open(BytesIO(img_response.content)).convert("RGB")

    # Ensure 2:3 ratio (width:height)
    target_ratio = 2 / 3
    width, height = img.size
    current_ratio = width / height

    if abs(current_ratio - target_ratio) > 0.01:
        if current_ratio > target_ratio:
            # Too wide → crop width
            new_width = int(height * target_ratio)
            left = (width - new_width) // 2
            img = img.crop((left, 0, left + new_width, height))
        else:
            # Too tall → crop height
            new_height = int(width / target_ratio)
            top = (height - new_height) // 2
            img = img.crop((0, top, width, top + new_height))

    # Optional resize (example: 600x900)
    img = img.resize((600, 900), Image.Resampling.LANCZOS)

    if not output_path:
        safe_title = title.replace(" ", "_")
        output_path = f"{safe_title}.jpg"

    img.save(output_path, "JPEG", quality=95)

    return output_path