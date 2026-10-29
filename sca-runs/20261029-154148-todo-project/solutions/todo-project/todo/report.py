def summary(store: TodoStore) -> str:
    """Returns a summary of the to-do list."""
    num_tasks = len(store.items())
    done_count = sum(1 for item in store.items() if item.done)
    pending_count = len(store.pending())

    if num_tasks == 0:
        return "0 tasks: 0 done, 0 pending. Nothing pending."
    elif num_tasks == 1:
        if pending_count == 0:
            return f"{num_tasks} task: {done_count} done, {pending_count} pending. Next: {store.pending()[0].title}"
        else:
            return f"{num_tasks} task: {done_count} done, {pending_count} pending. Next: {store.pending()[0].title}"
    else:
        if pending_count == 0:
            return f"{num_tasks} tasks: {done_count} done, {pending_count} pending. Next: {store.pending()[0].title}"
        else:
            return f"{num_tasks} tasks: {done_count} done, {pending_count} pending. Next: {store.pending()[0].title}"