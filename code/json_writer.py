import json
import logging
import os
import tempfile
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def write_collections_json(collections, output_path):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    payload = {
        "last_fetched": datetime.now(timezone.utc).isoformat(),
        "collections": sorted(
            [{"date": dt.strftime("%Y-%m-%d"), "bin_type": label} for dt, label in collections],
            key=lambda c: (c["date"], c["bin_type"]),
        ),
    }

    tmp_fd = None
    try:
        tmp_fd = tempfile.NamedTemporaryFile(
            mode="w", dir=os.path.dirname(output_path),
            suffix=".tmp", delete=False,
        )
        json.dump(payload, tmp_fd, indent=2)
        tmp_fd.write("\n")
        tmp_fd.flush()
        os.fsync(tmp_fd.fileno())
        tmp_fd.close()
        os.replace(tmp_fd.name, output_path)
        os.chmod(output_path, 0o644)
        logger.info("Wrote %d collections to %s", len(collections), output_path)
    except Exception:
        logger.exception("Failed to write JSON output to %s", output_path)
        if tmp_fd is not None:
            try:
                os.unlink(tmp_fd.name)
            except OSError:
                pass
