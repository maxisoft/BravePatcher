from pathlib import Path, PurePath

from bravepatcher.pattern import PatternDownloader


class TestPatternDownloader:

    def test_download_latest_version(self):
        test_zip: Path = Path(__file__).parent / "BravePatcher-pattern.zip"

        downloader = PatternDownloader(url=test_zip.as_uri())
        pattern_data = downloader.download_latest_version()
        assert PurePath(pattern_data.program["path"]).parent.name == "88.1.20.100"

    def test_download_best_match_for_version(self):
        test_zip: Path = Path(__file__).parent / "BravePatcher-pattern.zip"

        downloader = PatternDownloader(url=test_zip.as_uri())

        # download existing version
        for v in ("88.1.20.100", "87.1.18.75", "87.1.18.77", "87.1.18.78", "88.1.19.87"):
            pattern_data = downloader.download_best_match_for_version(v)
            assert PurePath(pattern_data.program["path"]).parent.name == v

        # download closest version
        pattern_data = downloader.download_best_match_for_version("88.1.20.101")
        assert PurePath(pattern_data.program["path"]).parent.name == "88.1.20.100"

        pattern_data = downloader.download_best_match_for_version("87.1.18.74")
        assert PurePath(pattern_data.program["path"]).parent.name == "87.1.18.75"
