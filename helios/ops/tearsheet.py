"""Daily tearsheet HTML emitter.

Writes /data/logs/tearsheet.html every night with:
  - Total NAV trajectory
  - Per-strategy P&L attribution
  - Win rate, average R, Sharpe, max DD
  - Recent fills table
  - Drift monitor status

You read it by pulling the file from the Railway volume (or via a future
small Flask serving route).
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

TEARSHEET_PATH = Path(os.getenv("HELIOS_LOGS_DIR", "logs")) / "tearsheet.html"


HTML_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Helios — Daily Tearsheet</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
         background: #0e0e0e; color: #e0e0e0; padding: 30px; max-width: 1200px; margin: auto; }}
  h1, h2 {{ color: #ffd166; }}
  .card {{ background: #1a1a1a; padding: 20px; border-radius: 8px; margin: 16px 0; }}
  table {{ border-collapse: collapse; width: 100%; }}
  th, td {{ padding: 8px 12px; text-align: right; border-bottom: 1px solid #333; }}
  th {{ background: #222; }}
  td.label {{ text-align: left; }}
  .green {{ color: #06d6a0; }}
  .red {{ color: #ef476f; }}
  .meta {{ color: #888; font-size: 12px; }}
</style>
</head>
<body>
<h1>Helios — Daily Tearsheet</h1>
<p class="meta">Generated {generated_at}</p>

<div class="card">
  <h2>Portfolio</h2>
  <table>
    <tr><td class="label">Total observations logged</td><td>{n_observations}</td></tr>
    <tr><td class="label">Total outcomes harvested</td><td>{n_outcomes}</td></tr>
    <tr><td class="label">Live fills logged</td><td>{n_fills}</td></tr>
    <tr><td class="label">Realized P&amp;L (SOL)</td><td class="{pnl_color}">{realized_pnl_sol:+.4f}</td></tr>
  </table>
</div>

<div class="card">
  <h2>Per-strategy attribution</h2>
  <table>
    <tr><th>Strategy</th><th>Signals</th><th>Win-rate</th><th>Mean R</th><th>Status</th></tr>
    {strategy_rows}
  </table>
</div>

<div class="card">
  <h2>Recent fills</h2>
  <table>
    <tr><th>Time</th><th>Strategy</th><th>Symbol</th><th>Action</th><th>P&amp;L SOL</th></tr>
    {fill_rows}
  </table>
</div>

</body>
</html>
"""


def render_tearsheet(
    n_observations: int = 0,
    n_outcomes: int = 0,
    n_fills: int = 0,
    realized_pnl_sol: float = 0.0,
    strategy_attribution: list[dict] | None = None,
    recent_fills: list[dict] | None = None,
    output_path: Path = TEARSHEET_PATH,
) -> Path:
    """Render the tearsheet HTML to disk. Returns the path."""
    strategy_rows = ""
    for s in (strategy_attribution or []):
        strategy_rows += (
            f"<tr><td class='label'>{s.get('name','?')}</td>"
            f"<td>{s.get('signals',0)}</td>"
            f"<td>{s.get('win_rate',0):.1%}</td>"
            f"<td>{s.get('mean_r',0):+.2f}</td>"
            f"<td>{s.get('status','—')}</td></tr>"
        )
    if not strategy_rows:
        strategy_rows = "<tr><td colspan='5' class='meta'>no signals yet</td></tr>"

    fill_rows = ""
    for f in (recent_fills or [])[:20]:
        pnl = f.get("pnl_sol", 0.0)
        cls = "green" if pnl >= 0 else "red"
        fill_rows += (
            f"<tr><td class='label'>{f.get('timestamp_iso','')[:19]}</td>"
            f"<td>{f.get('strategy','')}</td>"
            f"<td>{(f.get('mint','') or f.get('symbol',''))[:12]}</td>"
            f"<td>{f.get('action','')}</td>"
            f"<td class='{cls}'>{pnl:+.4f}</td></tr>"
        )
    if not fill_rows:
        fill_rows = "<tr><td colspan='5' class='meta'>no fills yet</td></tr>"

    html = HTML_TEMPLATE.format(
        generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        n_observations=n_observations,
        n_outcomes=n_outcomes,
        n_fills=n_fills,
        realized_pnl_sol=realized_pnl_sol,
        pnl_color="green" if realized_pnl_sol >= 0 else "red",
        strategy_rows=strategy_rows,
        fill_rows=fill_rows,
    )
    parent = output_path.parent
    target = parent.resolve() if parent.is_symlink() else parent
    try:
        target.mkdir(parents=True, exist_ok=True)
    except FileExistsError:
        pass
    output_path.write_text(html, encoding="utf-8")
    return output_path
