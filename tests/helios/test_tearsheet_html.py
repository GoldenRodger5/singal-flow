"""Tests for the HTML tearsheet renderer."""
from __future__ import annotations

from helios.ops.tearsheet import render_tearsheet


def test_render_empty(tmp_path):
    out = render_tearsheet(output_path=tmp_path / "ts.html")
    assert out.exists()
    html = out.read_text()
    assert "Helios" in html
    assert "no signals yet" in html


def test_render_with_data(tmp_path):
    out = render_tearsheet(
        n_observations=500,
        n_outcomes=120,
        n_fills=10,
        realized_pnl_sol=0.0345,
        strategy_attribution=[
            {"name": "A2", "signals": 80, "win_rate": 0.18, "mean_r": 1.5, "status": "shadow"},
            {"name": "A3", "signals": 40, "win_rate": 0.55, "mean_r": 0.3, "status": "shadow"},
        ],
        recent_fills=[
            {"timestamp_iso": "2026-05-25T15:00:00+00:00", "strategy": "A2",
             "mint": "AbCd1234", "action": "entry", "pnl_sol": 0.0},
            {"timestamp_iso": "2026-05-25T15:30:00+00:00", "strategy": "A2",
             "mint": "AbCd1234", "action": "exit_target", "pnl_sol": 0.06},
        ],
        output_path=tmp_path / "ts.html",
    )
    html = out.read_text()
    assert "500" in html      # n_observations
    assert "+0.0345" in html  # PnL
    assert "A2" in html
    assert "exit_target" in html
