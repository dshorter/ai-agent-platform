
graph TD

    subgraph Phone["iPhone (Couch Mission Control)"]
        T["Terminus\n(SSH + tunnels + shell)"]
        S["Safari\n(HTTP client)"]
        P["PG Orbit\n(DB client)"]
    end

    subgraph VPS["VPS / Hetzner"]
        subgraph Docker["Docker host"]
            N8N["n8n container\nlistens on localhost:5678"]
            PG["Postgres container\n(hvac-postgres)\nlistens on localhost:5432"]
        end
        VOL["Named volume:\n hvac-postgres-data\n(future: tiny backup container / cron pg_dump)"]
    end

    %% Client relationships on phone
    S -->|"http://localhost:5678\n(iPhone localhost)"| T
    P -->|"localhost:5432\n(iPhone localhost)"| T

    %% SSH + tunnels
    T -->|"SSH to VPS\n(key-based auth)"| VPS
    T -. "Local port forwards:\nL5678 → VPS:5678\nL5432 → VPS:5432" .- VPS

    %% On VPS side
    VPS -->|"port 5678"| N8N
    VPS -->|"port 5432"| PG
    PG --> VOL
