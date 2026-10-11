import json

from tally import live

AB = {"abr": [
    {"tpabr": "uf", "cdabr": "ac", "s": {"ts": "3"}, "e": {}},
    {"tpabr": "mun", "cdabr": "01066", "dt": "04/10/2026", "ht": "18:49:26",
     "s": {"ts": "21", "st": "7"}, "e": {"te": "6336", "est": "2100"}},
    {"tpabr": "mun", "cdabr": "01120", "dt": "", "ht": "", "s": {"ts": "10", "st": "0"}, "e": {"te": "3000", "est": "0"}},
]}
U = {"dg": "04/10/2026", "hg": "18:50:00", "s": {"ts": "21", "st": "7"}, "v": {"vb": "12", "tvn": "30", "vv": "900"},
     "carg": [{"cd": "1", "agr": [{"par": [{"cand": [{"n": "22", "vap": "500"}]}]},
                                  {"par": [{"cand": [{"n": "13", "vap": "350"}, {"n": "70", "vap": "50"}]}]}]},
              {"cd": "3", "agr": [{"par": [{"cand": [{"n": "99", "vap": "1"}]}]}]}]}


def test_parse_progress_keeps_municipalities_only():
    ab = live.parse_ab(AB, "ac")
    assert list(ab["CD_MUNICIPIO"]) == ["1066", "1120"]
    r = ab.iloc[0]
    assert (r.sections_total, r.sections_counted, r.electorate_counted) == (21, 7, 2100)


def test_parse_results_reads_president_only():
    u = live.parse_u(U)
    assert u["votes"] == {"22": 500, "13": 350, "70": 50}
    assert (u["blank"], u["null"], u["sections_counted"]) == (12, 30, 7)


class FakeCollector(live.Collector):
    """Collector with the network replaced by a dict of url -> body; counts requests."""

    def __init__(self, tmp_path, responses):
        self.responses, self.calls = responses, []
        self.failing = set()
        super().__init__("6257", archive=tmp_path, uf_list=["ac"], log=lambda *_: None)

    def _resolve_pleito(self):
        return "3220"

    def _get(self, url, conditional=True):
        self.calls.append(url)
        if url in self.failing:
            return 503, None
        body = json.dumps(self.responses.get(url, {})).encode()
        import hashlib
        import gzip
        sha = hashlib.sha256(body).hexdigest()
        (self.blobs / f"{sha}.json.gz").write_bytes(gzip.compress(body))
        self.latest[url] = sha
        self._append({"t_utc": "2026-10-25T20:00:00", "url": url, "status": 200, "sha256": sha})
        return 200, body


def test_cycle_fetches_changed_municipalities_and_retries_failures(tmp_path):
    c = FakeCollector(tmp_path, {})
    c.responses = {c.url_ab("ac"): AB, c.url_u("ac", "1066"): U, c.url_u("br"): U, c.url_u("ac"): U}
    c.failing = {c.url_u("ac", "1066")}
    c.cycle(with_cs=False)
    assert c.url_u("ac", "1066") in c.calls and c.url_u("ac", "1120") not in c.calls   # 1120 has nothing counted
    c.calls.clear()
    c.failing.clear()
    c.cycle(with_cs=False)
    assert c.url_u("ac", "1066") in c.calls          # retried after the failure
    c.calls.clear()
    c.cycle(with_cs=False)
    assert c.url_u("ac", "1066") not in c.calls      # unchanged progress: not fetched again


def test_state_is_rebuilt_from_the_archive_alone(tmp_path):
    c = FakeCollector(tmp_path, {})
    c.responses = {c.url_ab("ac"): AB, c.url_u("ac", "1066"): U, c.url_u("br"): U, c.url_u("ac"): U}
    c.cycle(with_cs=False)
    st = live.load_state(tmp_path)
    assert st["br"]["votes"]["22"] == 500 and "AC" in st["uf"]
    row = st["municipal"].set_index("CD_MUNICIPIO").loc["1066"]
    assert (row["v_22"], row["v_13"]) == (500, 350)
    assert len(st["ab"]) == 2
