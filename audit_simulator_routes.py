import importlib
import inspect

module = importlib.import_module(
    "backend.app.routers.simulator_isolation_test"
)

public_paths = {
    "/health",
    "/symbols",
    "/market/quote",
    "/market/candles",
}

print("\nSIMULATOR ROUTE AUTHENTICATION AUDIT")
print("-" * 75)

for route in module.router.routes:
    methods = sorted(route.methods or [])
    path = route.path
    endpoint = getattr(route, "endpoint", None)

    if endpoint is None:
        continue

    params = inspect.signature(endpoint).parameters
    has_user = "user" in params
    is_public = path in public_paths

    if is_public:
        status = "PUBLIC — expected"
    elif has_user:
        status = "USER PARAMETER — inspect dependency"
    else:
        status = "CHECK — no user parameter"

    print(f"{','.join(methods):12} {path:45} {status}")

print("\nNote: this is a static audit, not proof of authorization.")
