"""Async task supervisor — runs N independent strategy loops in one process
with per-task auto-restart on crash.

Why this exists:
  Helios has 4+ strategies that each need a long-running async loop. Running
  them as 4 separate Railway services is wasteful (4x base cost, 4x volumes,
  4x deploy churn). Running them as 4 tasks in one event loop is cheaper —
  IF one task crashing doesn't bring down the others.

  This supervisor wraps each task in a watchdog that catches exceptions and
  restarts the task with exponential backoff. The bot can survive arbitrary
  per-strategy failures (bad API call, parse error, OOM in one branch) without
  dropping the others.

Design:
  - Each task is a coroutine factory (callable that returns a fresh coroutine)
    so we can re-create it after a crash. We don't reuse a single coroutine
    object because once it raises it's "used up."
  - Backoff: 1s → 2s → 4s → ... capped at 5 min. Reset to 1s after 5 min of
    healthy uptime.
  - Logging: every restart logged with stack trace.
"""
from __future__ import annotations

import asyncio
import time
import traceback
from collections.abc import Callable, Coroutine
from dataclasses import dataclass

from helios.ops import get_logger

log = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class SupervisedTask:
    name: str
    factory: Callable[[], Coroutine]
    # Initial backoff seconds; doubles per consecutive failure
    initial_backoff: float = 1.0
    max_backoff: float = 300.0
    # If task survives this many seconds without crashing, reset backoff
    healthy_uptime_reset_seconds: float = 300.0


async def run_supervised(task: SupervisedTask) -> None:
    """Run a single supervised task forever, restarting on every exception.

    NEVER raises — designed to be passed to asyncio.gather alongside siblings
    that should keep running even if this one fails.
    """
    backoff = task.initial_backoff
    while True:
        start_time = time.monotonic()
        try:
            log.info("supervised_task_starting", name=task.name)
            await task.factory()
            # Task returned cleanly (rare — most are infinite loops). Treat as
            # done and exit.
            log.info("supervised_task_returned_cleanly", name=task.name)
            return
        except asyncio.CancelledError:
            log.info("supervised_task_cancelled", name=task.name)
            raise
        except Exception as e:  # noqa: BLE001
            uptime = time.monotonic() - start_time
            tb = traceback.format_exc()
            log.warning(
                "supervised_task_crashed",
                name=task.name,
                error=str(e),
                uptime_seconds=int(uptime),
                next_retry_in_seconds=backoff,
            )
            # Also print the traceback so it shows up in stdout / Railway logs
            print(f"\n[supervisor] task {task.name!r} crashed after {uptime:.0f}s — restart in {backoff:.0f}s")
            print(tb, flush=True)

            await asyncio.sleep(backoff)
            # If the task lasted longer than the reset threshold, treat this
            # as an isolated incident and don't accelerate backoff
            if uptime >= task.healthy_uptime_reset_seconds:
                backoff = task.initial_backoff
            else:
                backoff = min(task.max_backoff, backoff * 2.0)


async def run_all(tasks: list[SupervisedTask]) -> None:
    """Run all supervised tasks in parallel. Returns only when ALL tasks
    cleanly exit (rare) or when SIGINT cancels the gather.
    """
    log.info("supervisor_starting", n_tasks=len(tasks), names=[t.name for t in tasks])
    await asyncio.gather(*(run_supervised(t) for t in tasks))
