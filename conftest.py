def pytest_collection_modifyitems(config, items):
    # Deselect slow tests unless the user explicitly targets them via -m.
    if config.option.markexpr:
        return
    slow = [item for item in items if item.get_closest_marker("slow")]
    if slow:
        config.hook.pytest_deselected(items=slow)
        items[:] = [
            item for item in items if not item.get_closest_marker("slow")
        ]
