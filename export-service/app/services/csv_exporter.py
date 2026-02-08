"""CSV exporter for audit logs."""

import csv
from io import BytesIO, StringIO


# Column headers for the audit log CSV export.
AUDIT_COLUMNS = [
    "Timestamp",
    "User ID",
    "Action",
    "Resource Type",
    "Resource ID",
    "Workspace ID",
    "Details",
    "IP Address",
]


class CsvExporter:
    """Exports audit log entries as a CSV file."""

    def export_audit_logs(self, logs: list[dict]) -> BytesIO:
        """Generate a CSV file from audit log records.

        Args:
            logs: List of audit log dicts, each containing keys matching
                  the column headers (snake_case).

        Returns:
            BytesIO buffer containing the generated CSV (UTF-8 encoded).
        """
        text_buffer = StringIO()
        writer = csv.writer(text_buffer)

        # Header row
        writer.writerow(AUDIT_COLUMNS)

        # Data rows
        for entry in logs:
            writer.writerow([
                entry.get("timestamp", ""),
                entry.get("user_id", ""),
                entry.get("action", ""),
                entry.get("resource_type", ""),
                entry.get("resource_id", ""),
                entry.get("workspace_id", ""),
                entry.get("details", ""),
                entry.get("ip_address", ""),
            ])

        # Convert text -> bytes
        csv_bytes = text_buffer.getvalue().encode("utf-8")
        buffer = BytesIO(csv_bytes)
        buffer.seek(0)
        return buffer
