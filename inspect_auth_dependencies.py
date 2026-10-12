import importlib

module = importlib.import_module(
    "backend.app.routers.simulator_isolation_test"
)

print("\nPRIVATE ROUTE DEPENDENCY CHECK")
print("=" * 80)

public_paths = {
    "/health",
    "/symbols",
    "/market/quote",
    "/market/candles",
}

for route in module.router.routes:
    path = route.path
    if path.removeprefix("/api/simulator") in public_paths:
        continue

    print(f"\n{','.join(sorted(route.methods or [])):10} {path}")

    dependencies = getattr(route, "dependant", None)
    if dependencies is None:
        print("  Could not inspect dependencies")
        continue

    for dep in dependencies.dependencies:
        call = getattr(dep, "call", None)
        name = getattr(call, "__name__", repr(call))
        print(f"  Dependency: {name}")

        for nested in getattr(dep, "dependencies", []):
            nested_call = getattr(nested, "call", None)
            nested_name = getattr(nested_call, "__name__", repr(nested_call))
            print(f"    Nested dependency: {nested_name}")
