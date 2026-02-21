"""Export DataFrame to file formats."""

import os
from pathlib import Path

import pandas as pd


def export_dataframe(
    df: pd.DataFrame, *, out_dir: str, format: str, filename: str
) -> str:
    """
    Export DataFrame to file.

    Args:
        df: DataFrame to export
        out_dir: Output directory path
        format: Format ("parquet" or "csv")
        filename: Filename (without extension)

    Returns:
        Full path to exported file

    Raises:
        ValueError: If format is not supported
    """
    # Create output directory if it doesn't exist
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    # Determine file extension and full path
    if format == "parquet":
        file_path = out_path / f"{filename}.parquet"
        df.to_parquet(file_path, engine="pyarrow", index=False)
    elif format == "csv":
        file_path = out_path / f"{filename}.csv"
        df.to_csv(file_path, index=False)
    else:
        raise ValueError(f"Unsupported format: {format}")

    return str(file_path)
