import pandas as pd

from data_tools.gdc_manifest import _slide_id_from_filename, _submitter_id_from_filename


def test_submitter_id_from_tcga_filename():
    fn = "TCGA-CF-A9FM-01A-01-TSA.A8A47050-75B5-42BE-ABF0-70AAA85EA88C.svs"
    assert _submitter_id_from_filename(fn) == "TCGA-CF-A9FM"
    assert _slide_id_from_filename(fn) == "TCGA-CF-A9FM-01A-01-TSA"
