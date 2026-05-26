"""Tests for the async task supervisor."""
from __future__ import annotations

import asyncio

import pytest

from helios.ops.supervisor import SupervisedTask, run_supervised


@pytest.mark.asyncio
async def test_clean_return_exits_supervisor():
    """A task that returns cleanly should make the supervisor return."""
    called = 0

    async def factory():
        nonlocal called
        called += 1
        return

    task = SupervisedTask(name="t", factory=factory)
    await asyncio.wait_for(run_supervised(task), timeout=2.0)
    assert called == 1


@pytest.mark.asyncio
async def test_crashed_task_is_restarted():
    """A task that raises should be restarted by the supervisor with backoff."""
    starts = 0

    async def factory():
        nonlocal starts
        starts += 1
        if starts < 3:
            raise RuntimeError("simulated crash")
        # On the 3rd start, exit cleanly
        return

    task = SupervisedTask(name="crashy", factory=factory, initial_backoff=0.01, max_backoff=0.02)
    await asyncio.wait_for(run_supervised(task), timeout=3.0)
    assert starts == 3


@pytest.mark.asyncio
async def test_cancelled_propagates():
    """If a supervised task gets cancelled, the supervisor re-raises CancelledError
    so the parent gather can shut everything down."""
    async def factory():
        await asyncio.sleep(10)

    task = SupervisedTask(name="long", factory=factory)

    supervisor_task = asyncio.create_task(run_supervised(task))
    await asyncio.sleep(0.1)
    supervisor_task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await supervisor_task


@pytest.mark.asyncio
async def test_backoff_doubles_per_consecutive_failure():
    """Confirm backoff escalates when crashes are tight-loop (not enough uptime
    to reset)."""
    crash_times: list[float] = []
    crashes = 0

    async def factory():
        nonlocal crashes
        import time
        crash_times.append(time.monotonic())
        crashes += 1
        if crashes < 4:
            raise RuntimeError("boom")
        return

    task = SupervisedTask(
        name="escalate", factory=factory,
        initial_backoff=0.05, max_backoff=0.4,
        healthy_uptime_reset_seconds=60.0,  # never reset within this test
    )
    await asyncio.wait_for(run_supervised(task), timeout=5.0)
    # Consecutive gaps should grow
    if len(crash_times) >= 3:
        gap1 = crash_times[1] - crash_times[0]
        gap2 = crash_times[2] - crash_times[1]
        assert gap2 > gap1
