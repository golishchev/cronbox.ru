"""Task Chains API endpoints."""

from datetime import datetime
from uuid import UUID

import pytz
from croniter import croniter
from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import DB, ActiveSubscriptionWorkspace, CurrentWorkspace, UserPlan
from app.db.repositories.chain_executions import ChainExecutionRepository
from app.db.repositories.task_chains import ChainStepRepository, TaskChainRepository
from app.db.repositories.workspaces import WorkspaceRepository
from app.models.task_chain import ChainStep, TriggerType
from app.schemas.task_chain import (
    ChainExecutionDetailResponse,
    ChainExecutionListResponse,
    ChainExecutionResponse,
    ChainRunRequest,
    ChainStepCreate,
    ChainStepResponse,
    ChainStepUpdate,
    PaginationMeta,
    StepReorderRequest,
    TaskChainCreate,
    TaskChainDetailResponse,
    TaskChainListResponse,
    TaskChainResponse,
    TaskChainUpdate,
)

router = APIRouter(prefix="/workspaces/{workspace_id}/chains", tags=["Task Chains"])


def calculate_next_run(schedule: str, timezone: str) -> datetime:
    """Calculate next run time based on cron schedule and timezone."""
    tz = pytz.timezone(timezone)
    now = datetime.now(tz)
    cron = croniter(schedule, now)
    next_run = cron.get_next(datetime)
    return next_run.astimezone(pytz.UTC).replace(tzinfo=None)


def calculate_min_interval_minutes(schedule: str, timezone: str) -> int:
    """Calculate minimum interval between cron runs in minutes."""
    tz = pytz.timezone(timezone)
    now = datetime.now(tz)
    cron = croniter(schedule, now)
    run_times = [cron.get_next(datetime) for _ in range(10)]
    min_interval = float("inf")
    for i in range(1, len(run_times)):
        interval = (run_times[i] - run_times[i - 1]).total_seconds() / 60
        min_interval = min(min_interval, interval)
    return int(min_interval)


# ============================================================================
# Chain CRUD Endpoints
# ============================================================================


@router.get("", response_model=TaskChainListResponse)
async def list_task_chains(
    workspace: CurrentWorkspace,
    db: DB,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    is_active: bool | None = Query(None),
):
    """List all task chains for a workspace."""
    chain_repo = TaskChainRepository(db)
    skip = (page - 1) * limit

    chains = await chain_repo.get_by_workspace(
        workspace_id=workspace.id,
        skip=skip,
        limit=limit,
        is_active=is_active,
    )
    total = await chain_repo.count_by_workspace(
        workspace_id=workspace.id,
        is_active=is_active,
    )

    return TaskChainListResponse(
        chains=[TaskChainResponse.model_validate(chain) for chain in chains],
        pagination=PaginationMeta(
            page=page,
            limit=limit,
            total=total,
            total_pages=(total + limit - 1) // limit if total > 0 else 1,
        ),
    )


@router.post("", response_model=TaskChainDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_task_chain(
    data: TaskChainCreate,
    workspace: ActiveSubscriptionWorkspace,
    user_plan: UserPlan,
    db: DB,
):
    """Create a new task chain with optional steps."""
    chain_repo = TaskChainRepository(db)
    step_repo = ChainStepRepository(db)
    workspace_repo = WorkspaceRepository(db)

    # Check plan limits for chains
    if user_plan.max_task_chains == 0:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Task Chains are not available on your plan. Please upgrade.",
        )

    current_count = await chain_repo.count_by_workspace(workspace.id)
    if current_count >= user_plan.max_task_chains:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Task chain limit reached. Your plan allows {user_plan.max_task_chains} chain(s)",
        )

    # Check step count limit
    if len(data.steps) > user_plan.max_chain_steps:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Too many steps. Your plan allows {user_plan.max_chain_steps} step(s) per chain",
        )

    # Validate cron schedule if trigger type is cron
    next_run_at = None
    if data.trigger_type == TriggerType.CRON:
        if not data.schedule:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Schedule is required for cron trigger type",
            )
        interval_minutes = calculate_min_interval_minutes(data.schedule, data.timezone)
        if interval_minutes < user_plan.min_chain_interval_minutes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Chain interval too frequent. Your plan requires minimum {user_plan.min_chain_interval_minutes} minute(s) between runs",
            )
        next_run_at = calculate_next_run(data.schedule, data.timezone)

    # Validate delayed trigger
    if data.trigger_type == TriggerType.DELAYED:
        if not data.execute_at:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="execute_at is required for delayed trigger type",
            )
        from datetime import timezone as dt_tz
        now = datetime.now(dt_tz.utc)
        execute_at = data.execute_at if data.execute_at.tzinfo else data.execute_at.replace(tzinfo=dt_tz.utc)
        if execute_at <= now:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="execute_at must be in the future",
            )
        next_run_at = data.execute_at

    # Create chain
    chain = await chain_repo.create(
        workspace_id=workspace.id,
        worker_id=data.worker_id,
        name=data.name,
        description=data.description,
        tags=data.tags,
        trigger_type=data.trigger_type,
        schedule=data.schedule,
        timezone=data.timezone,
        execute_at=data.execute_at,
        stop_on_failure=data.stop_on_failure,
        timeout_seconds=data.timeout_seconds,
        notify_on_failure=data.notify_on_failure,
        notify_on_success=data.notify_on_success,
        notify_on_partial=data.notify_on_partial,
        is_active=True,
        is_paused=False,
        next_run_at=next_run_at,
    )

    # Create steps if provided
    created_steps = []
    for i, step_data in enumerate(data.steps):
        step = await step_repo.create(
            chain_id=chain.id,
            step_order=i,
            name=step_data.name,
            url=str(step_data.url),
            method=step_data.method,
            headers=step_data.headers,
            body=step_data.body,
            timeout_seconds=step_data.timeout_seconds,
            retry_count=step_data.retry_count,
            retry_delay_seconds=step_data.retry_delay_seconds,
            condition=step_data.condition.model_dump() if step_data.condition else None,
            extract_variables=step_data.extract_variables,
            continue_on_failure=step_data.continue_on_failure,
        )
        created_steps.append(step)

    # Update workspace counter
    await workspace_repo.update_task_chains_count(workspace, 1)
    await db.commit()

    # Refresh chain to get relationships
    chain = await chain_repo.get_with_steps(chain.id)

    return TaskChainDetailResponse(
        **TaskChainResponse.model_validate(chain).model_dump(),
        steps=[ChainStepResponse.model_validate(s) for s in chain.steps],
    )


@router.get("/{chain_id}", response_model=TaskChainDetailResponse)
async def get_task_chain(
    chain_id: UUID,
    workspace: CurrentWorkspace,
    db: DB,
):
    """Get a task chain with its steps."""
    chain_repo = TaskChainRepository(db)
    chain = await chain_repo.get_with_steps(chain_id)

    if chain is None or chain.workspace_id != workspace.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task chain not found",
        )

    return TaskChainDetailResponse(
        **TaskChainResponse.model_validate(chain).model_dump(),
        steps=[ChainStepResponse.model_validate(s) for s in chain.steps],
    )


@router.patch("/{chain_id}", response_model=TaskChainResponse)
async def update_task_chain(
    chain_id: UUID,
    data: TaskChainUpdate,
    workspace: ActiveSubscriptionWorkspace,
    user_plan: UserPlan,
    db: DB,
):
    """Update a task chain."""
    chain_repo = TaskChainRepository(db)
    chain = await chain_repo.get_by_id(chain_id)

    if chain is None or chain.workspace_id != workspace.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task chain not found",
        )

    update_data = data.model_dump(exclude_unset=True)

    # Handle trigger type changes
    trigger_type = update_data.get("trigger_type", chain.trigger_type)
    schedule = update_data.get("schedule", chain.schedule)
    timezone = update_data.get("timezone", chain.timezone)
    execute_at = update_data.get("execute_at", chain.execute_at)

    if trigger_type == TriggerType.CRON:
        if schedule:
            interval_minutes = calculate_min_interval_minutes(schedule, timezone)
            if interval_minutes < user_plan.min_chain_interval_minutes:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Chain interval too frequent. Your plan requires minimum {user_plan.min_chain_interval_minutes} minute(s) between runs",
                )
            update_data["next_run_at"] = calculate_next_run(schedule, timezone)
    elif trigger_type == TriggerType.DELAYED:
        if execute_at:
            from datetime import timezone as dt_tz
            now = datetime.now(dt_tz.utc)
            exec_at_aware = execute_at if execute_at.tzinfo else execute_at.replace(tzinfo=dt_tz.utc)
            if exec_at_aware <= now:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="execute_at must be in the future",
                )
            update_data["next_run_at"] = execute_at

    if update_data:
        chain = await chain_repo.update(chain, **update_data)
        await db.commit()

    return TaskChainResponse.model_validate(chain)


@router.delete("/{chain_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task_chain(
    chain_id: UUID,
    workspace: CurrentWorkspace,
    db: DB,
):
    """Delete a task chain and all its steps."""
    chain_repo = TaskChainRepository(db)
    workspace_repo = WorkspaceRepository(db)
    chain = await chain_repo.get_by_id(chain_id)

    if chain is None or chain.workspace_id != workspace.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task chain not found",
        )

    await chain_repo.delete(chain)
    await workspace_repo.update_task_chains_count(workspace, -1)
    await db.commit()


@router.post("/{chain_id}/run", status_code=status.HTTP_202_ACCEPTED)
async def run_task_chain(
    chain_id: UUID,
    workspace: ActiveSubscriptionWorkspace,
    user_plan: UserPlan,
    db: DB,
    data: ChainRunRequest | None = None,
):
    """Manually trigger a task chain execution."""
    chain_repo = TaskChainRepository(db)
    chain = await chain_repo.get_with_steps(chain_id)

    if chain is None or chain.workspace_id != workspace.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task chain not found",
        )

    if not chain.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot run inactive chain",
        )

    if not chain.steps:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot run chain with no steps",
        )

    # Check rate limit based on plan
    from datetime import timedelta, timezone as dt_tz
    if chain.last_run_at:
        min_interval = timedelta(minutes=user_plan.min_chain_interval_minutes)
        now = datetime.now(dt_tz.utc)
        last_run = chain.last_run_at if chain.last_run_at.tzinfo else chain.last_run_at.replace(tzinfo=dt_tz.utc)
        time_since_last_run = now - last_run
        if time_since_last_run < min_interval:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Chain interval too frequent. Your plan requires minimum {user_plan.min_chain_interval_minutes} minute(s) between runs",
            )

    # Update last_run_at to prevent rapid re-runs (update before enqueue to prevent race)
    await chain_repo.update(chain, last_run_at=datetime.utcnow())
    await db.commit()

    # Enqueue chain for immediate execution
    try:
        from arq import create_pool

        from app.workers.settings import get_redis_settings

        redis = await create_pool(get_redis_settings())
        await redis.enqueue_job(
            "execute_chain",
            chain_id=str(chain_id),
            initial_variables=data.initial_variables if data else {},
        )
        await redis.close()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to enqueue chain: {str(e)}",
        )

    return {"message": "Chain queued for execution", "chain_id": str(chain_id)}


@router.post("/{chain_id}/pause", response_model=TaskChainResponse)
async def pause_task_chain(
    chain_id: UUID,
    workspace: CurrentWorkspace,
    db: DB,
):
    """Pause a task chain."""
    chain_repo = TaskChainRepository(db)
    chain = await chain_repo.get_by_id(chain_id)

    if chain is None or chain.workspace_id != workspace.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task chain not found",
        )

    if chain.is_paused:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Chain is already paused",
        )

    chain = await chain_repo.pause(chain)
    await db.commit()

    return TaskChainResponse.model_validate(chain)


@router.post("/{chain_id}/resume", response_model=TaskChainResponse)
async def resume_task_chain(
    chain_id: UUID,
    workspace: ActiveSubscriptionWorkspace,
    db: DB,
):
    """Resume a paused task chain."""
    chain_repo = TaskChainRepository(db)
    chain = await chain_repo.get_by_id(chain_id)

    if chain is None or chain.workspace_id != workspace.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task chain not found",
        )

    if not chain.is_paused:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Chain is not paused",
        )

    next_run_at = None
    if chain.trigger_type == TriggerType.CRON and chain.schedule:
        next_run_at = calculate_next_run(chain.schedule, chain.timezone)
    elif chain.trigger_type == TriggerType.DELAYED and chain.execute_at:
        next_run_at = chain.execute_at

    chain = await chain_repo.resume(chain, next_run_at)
    await db.commit()

    return TaskChainResponse.model_validate(chain)


@router.post("/{chain_id}/copy", response_model=TaskChainDetailResponse, status_code=status.HTTP_201_CREATED)
async def copy_task_chain(
    chain_id: UUID,
    workspace: ActiveSubscriptionWorkspace,
    user_plan: UserPlan,
    db: DB,
):
    """Create a copy of an existing task chain with all its steps."""
    chain_repo = TaskChainRepository(db)
    workspace_repo = WorkspaceRepository(db)

    chain = await chain_repo.get_with_steps(chain_id)
    if chain is None or chain.workspace_id != workspace.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task chain not found",
        )

    # Check plan limits
    current_count = await chain_repo.count_by_workspace(workspace.id)
    if current_count >= user_plan.max_task_chains:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Task chain limit reached. Your plan allows {user_plan.max_task_chains} chain(s)",
        )

    # Create copy
    new_name = f"{chain.name} (copy)"
    new_chain = await chain_repo.copy(chain, new_name)

    # Update workspace counter
    await workspace_repo.update_task_chains_count(workspace, 1)
    await db.commit()

    # Refresh to get steps
    new_chain = await chain_repo.get_with_steps(new_chain.id)

    return TaskChainDetailResponse(
        **TaskChainResponse.model_validate(new_chain).model_dump(),
        steps=[ChainStepResponse.model_validate(s) for s in new_chain.steps],
    )


# ============================================================================
# Chain Step Endpoints
# ============================================================================


@router.get("/{chain_id}/steps", response_model=list[ChainStepResponse])
async def list_chain_steps(
    chain_id: UUID,
    workspace: CurrentWorkspace,
    db: DB,
):
    """List all steps for a task chain."""
    chain_repo = TaskChainRepository(db)
    step_repo = ChainStepRepository(db)

    chain = await chain_repo.get_by_id(chain_id)
    if chain is None or chain.workspace_id != workspace.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task chain not found",
        )

    steps = await step_repo.get_by_chain(chain_id)
    return [ChainStepResponse.model_validate(s) for s in steps]


@router.post("/{chain_id}/steps", response_model=ChainStepResponse, status_code=status.HTTP_201_CREATED)
async def create_chain_step(
    chain_id: UUID,
    data: ChainStepCreate,
    workspace: ActiveSubscriptionWorkspace,
    user_plan: UserPlan,
    db: DB,
):
    """Add a step to a task chain."""
    chain_repo = TaskChainRepository(db)
    step_repo = ChainStepRepository(db)

    chain = await chain_repo.get_by_id(chain_id)
    if chain is None or chain.workspace_id != workspace.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task chain not found",
        )

    # Check step limit
    current_count = await step_repo.count_by_chain(chain_id)
    if current_count >= user_plan.max_chain_steps:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Step limit reached. Your plan allows {user_plan.max_chain_steps} step(s) per chain",
        )

    # Get max step order and append at end if step_order not specified correctly
    max_order = await step_repo.get_max_step_order(chain_id)
    step_order = data.step_order if data.step_order <= max_order + 1 else max_order + 1

    step = await step_repo.create(
        chain_id=chain_id,
        step_order=step_order,
        name=data.name,
        url=str(data.url),
        method=data.method,
        headers=data.headers,
        body=data.body,
        timeout_seconds=data.timeout_seconds,
        retry_count=data.retry_count,
        retry_delay_seconds=data.retry_delay_seconds,
        condition=data.condition.model_dump() if data.condition else None,
        extract_variables=data.extract_variables,
        continue_on_failure=data.continue_on_failure,
    )
    await db.commit()

    return ChainStepResponse.model_validate(step)


@router.put("/{chain_id}/steps/reorder", response_model=list[ChainStepResponse])
async def reorder_chain_steps(
    chain_id: UUID,
    data: StepReorderRequest,
    workspace: ActiveSubscriptionWorkspace,
    db: DB,
):
    """Reorder steps in a task chain."""
    chain_repo = TaskChainRepository(db)
    step_repo = ChainStepRepository(db)

    chain = await chain_repo.get_by_id(chain_id)
    if chain is None or chain.workspace_id != workspace.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task chain not found",
        )

    # Validate all step IDs belong to this chain
    existing_steps = await step_repo.get_by_chain(chain_id)
    existing_ids = {str(s.id) for s in existing_steps}

    step_orders = []
    for item in data.step_orders:
        for step_id, order in item.items():
            if step_id not in existing_ids:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Step {step_id} does not belong to this chain",
                )
            step_orders.append({"step_id": UUID(step_id), "step_order": order})

    await step_repo.reorder_steps(chain_id, step_orders)
    await db.commit()

    steps = await step_repo.get_by_chain(chain_id)
    return [ChainStepResponse.model_validate(s) for s in steps]


@router.patch("/{chain_id}/steps/{step_id}", response_model=ChainStepResponse)
async def update_chain_step(
    chain_id: UUID,
    step_id: UUID,
    data: ChainStepUpdate,
    workspace: ActiveSubscriptionWorkspace,
    db: DB,
):
    """Update a chain step."""
    chain_repo = TaskChainRepository(db)
    step_repo = ChainStepRepository(db)

    chain = await chain_repo.get_by_id(chain_id)
    if chain is None or chain.workspace_id != workspace.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task chain not found",
        )

    step = await step_repo.get_by_id(step_id)
    if step is None or step.chain_id != chain_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Step not found",
        )

    update_data = data.model_dump(exclude_unset=True)

    # Convert HttpUrl to string if present
    if "url" in update_data and update_data["url"] is not None:
        update_data["url"] = str(update_data["url"])

    # Note: condition and extract_variables are already dicts after model_dump()

    if update_data:
        step = await step_repo.update(step, **update_data)
        await db.commit()

    return ChainStepResponse.model_validate(step)


@router.delete("/{chain_id}/steps/{step_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chain_step(
    chain_id: UUID,
    step_id: UUID,
    workspace: CurrentWorkspace,
    db: DB,
):
    """Delete a chain step."""
    chain_repo = TaskChainRepository(db)
    step_repo = ChainStepRepository(db)

    chain = await chain_repo.get_by_id(chain_id)
    if chain is None or chain.workspace_id != workspace.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task chain not found",
        )

    step = await step_repo.get_by_id(step_id)
    if step is None or step.chain_id != chain_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Step not found",
        )

    await step_repo.delete(step)
    await db.commit()


# ============================================================================
# Chain Execution Endpoints
# ============================================================================


@router.get("/{chain_id}/executions", response_model=ChainExecutionListResponse)
async def list_chain_executions(
    chain_id: UUID,
    workspace: CurrentWorkspace,
    db: DB,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    """List executions for a task chain."""
    chain_repo = TaskChainRepository(db)
    exec_repo = ChainExecutionRepository(db)

    chain = await chain_repo.get_by_id(chain_id)
    if chain is None or chain.workspace_id != workspace.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task chain not found",
        )

    skip = (page - 1) * limit
    executions = await exec_repo.get_by_chain(chain_id, skip=skip, limit=limit)
    total = await exec_repo.count_by_chain(chain_id)

    return ChainExecutionListResponse(
        executions=[ChainExecutionResponse.model_validate(e) for e in executions],
        pagination=PaginationMeta(
            page=page,
            limit=limit,
            total=total,
            total_pages=(total + limit - 1) // limit if total > 0 else 1,
        ),
    )


@router.get("/{chain_id}/executions/{execution_id}", response_model=ChainExecutionDetailResponse)
async def get_chain_execution(
    chain_id: UUID,
    execution_id: UUID,
    workspace: CurrentWorkspace,
    db: DB,
):
    """Get detailed chain execution with step results."""
    chain_repo = TaskChainRepository(db)
    exec_repo = ChainExecutionRepository(db)

    chain = await chain_repo.get_by_id(chain_id)
    if chain is None or chain.workspace_id != workspace.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task chain not found",
        )

    execution = await exec_repo.get_with_step_executions(execution_id)
    if execution is None or execution.chain_id != chain_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Execution not found",
        )

    from app.schemas.task_chain import StepExecutionResponse

    return ChainExecutionDetailResponse(
        **ChainExecutionResponse.model_validate(execution).model_dump(),
        step_executions=[
            StepExecutionResponse.model_validate(se) for se in execution.step_executions
        ],
    )
