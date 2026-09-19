from app.services.adapters import ashby, greenhouse, lever

ADAPTERS = {
    "greenhouse": greenhouse.list_jobs,
    "lever": lever.list_jobs,
    "ashby": ashby.list_jobs,
}
