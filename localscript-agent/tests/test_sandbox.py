import shutil

import pytest

from app.sandbox import run_lua_with_wf, run_lua_with_wf_capture_result

lua_bin = shutil.which("lua") or shutil.which("lua5.4")
pytestmark = pytest.mark.skipif(not lua_bin, reason="lua interpreter not installed")


def test_sandbox_return_last_email():
    wf = {"vars": {"emails": ["a", "b", "c"]}}
    code = "return wf.vars.emails[#wf.vars.emails]"
    ok, out, err = run_lua_with_wf(code, wf, lua_bin=lua_bin)
    assert ok
    assert out == "c"
    assert not err


def test_sandbox_capture_result_parses_array_of_objects():
    wf = {"vars": {"students": [{"name": "Ann", "score": 91}, {"name": "Bob", "score": 84}]}}
    code = """
local s = wf.vars.students
table.sort(s, function(a, b) return a.score > b.score end)
return {
  {name=s[1].name, score=s[1].score},
  {name=s[2].name, score=s[2].score}
}
"""
    ok, out, err, result = run_lua_with_wf_capture_result(code, wf, lua_bin=lua_bin)
    assert ok
    assert not err
    assert isinstance(out, str)
    assert isinstance(result, list)
    assert len(result) == 2
    assert result[0]["name"] == "Ann"
    assert result[0]["score"] == 91
