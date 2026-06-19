from backend.app.main import app

routes = [(r.path, r.methods) for r in app.routes if hasattr(r, "methods")]
for path, methods in sorted(routes):
    print(f"{sorted(methods)} {path}")
