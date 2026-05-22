import json
import re
import shutil
import subprocess
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parent
RESULTS_PATH = ROOT / "data_out" / "results.json"
RAW_UPLOAD_PATH = ROOT / "data_raw" / "retail" / "bike_sales_100k.csv"
STANDARDIZED_PATH = ROOT / "data_raw" / "retail" / "bike_standardized.csv"

PIPELINE_SCRIPTS = [
    ROOT / "src" / "merge_and_normalize.py",
    ROOT / "src" / "business_analysis.py",
    ROOT / "src" / "stat_analysis.py",
    ROOT / "src" / "pricing_ab_test.py",
    ROOT / "src" / "combine_json.py",
]


class PricingDashboardHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def do_GET(self):
        if self.path == "/api/results":
            self.send_json_file(RESULTS_PATH)
            return

        if self.path == "/":
            self.path = "/frontend/index.html"

        super().do_GET()

    def do_POST(self):
        if self.path != "/api/analyze":
            self.send_error(404, "Endpoint not found")
            return

        try:
            csv_bytes, filename = self.read_uploaded_csv()
            self.save_uploaded_csv(csv_bytes)
            self.run_existing_pipeline()
            with open(RESULTS_PATH, "r", encoding="utf-8") as f:
                results = json.load(f)
            self.send_json({
                "filename": filename,
                "results": results,
            })
        except Exception as exc:
            self.send_json({"error": str(exc)}, status=400)

    def read_uploaded_csv(self):
        content_type = self.headers.get("Content-Type", "")
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)

        if content_type.startswith("text/csv"):
            return body, "uploaded.csv"

        boundary_match = re.search(r"boundary=(.+)", content_type)
        if not boundary_match:
            raise ValueError("Upload must be a CSV file sent as multipart/form-data.")

        boundary = boundary_match.group(1).strip().strip('"').encode()
        for part in body.split(b"--" + boundary):
            part = part.strip()
            if not part or part == b"--":
                continue

            header_bytes, _, file_bytes = part.partition(b"\r\n\r\n")
            headers = header_bytes.decode("utf-8", errors="ignore")
            if "name=\"csvFile\"" not in headers:
                continue

            filename_match = re.search(r'filename="([^"]*)"', headers)
            filename = unquote(filename_match.group(1)) if filename_match else "uploaded.csv"
            file_bytes = file_bytes.rstrip(b"\r\n")
            if not file_bytes:
                raise ValueError("Uploaded CSV file is empty.")
            return file_bytes, filename

        raise ValueError("Could not find a csvFile upload field.")

    def save_uploaded_csv(self, csv_bytes):
        RAW_UPLOAD_PATH.parent.mkdir(parents=True, exist_ok=True)
        RAW_UPLOAD_PATH.write_bytes(csv_bytes)

    def run_existing_pipeline(self):
        self.ensure_absolute_path_compatibility()
        for script in PIPELINE_SCRIPTS:
            completed = subprocess.run(
                [sys.executable, str(script)],
                cwd=str(ROOT),
                capture_output=True,
                text=True,
                check=False,
            )
            if completed.returncode != 0:
                message = completed.stderr.strip() or completed.stdout.strip()
                raise RuntimeError(f"{script.name} failed: {message}")

    def ensure_absolute_path_compatibility(self):
        legacy_root = Path("/Users/zhihaoxu/Desktop/Project:Code/hotel-mvp")
        if legacy_root.exists():
            return

        legacy_raw = legacy_root / "data_raw" / "retail"
        legacy_out = legacy_root / "data_out"
        legacy_raw.mkdir(parents=True, exist_ok=True)
        legacy_out.mkdir(parents=True, exist_ok=True)
        shutil.copy2(RAW_UPLOAD_PATH, legacy_raw / "bike_sales_100k.csv")

        if STANDARDIZED_PATH.exists():
            shutil.copy2(STANDARDIZED_PATH, legacy_raw / "bike_standardized.csv")

    def send_json_file(self, path):
        if not path.exists():
            self.send_json({"error": f"{path.name} does not exist."}, status=404)
            return

        with open(path, "r", encoding="utf-8") as f:
            self.send_json(json.load(f))

    def send_json(self, payload, status=200):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def run(port=8000):
    server = ThreadingHTTPServer(("127.0.0.1", port), PricingDashboardHandler)
    print(f"Pricing dashboard server running at http://127.0.0.1:{port}/")
    server.serve_forever()


if __name__ == "__main__":
    selected_port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    run(selected_port)
