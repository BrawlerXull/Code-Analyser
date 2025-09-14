from pathlib import Path
from cq_agent.ingestion.fs_ingestor import FSIngestor
from cq_agent.ingestion.fs_ingestor import FSIngestor


def test_collect_files(tmp_path: Path):
    f = tmp_path / "test.py"
    f.write_text("print('hi')")
    ingestor = FSIngestor(tmp_path)
    files = ingestor.collect_files()
    assert len(files) == 1
    assert files[0]["lang"] == "python"
    assert "print" in files[0]["text"]
