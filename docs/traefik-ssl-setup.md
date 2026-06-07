# ARIA — Traefik SSL / HTTPS Setup

> Traefik 3 + Let's Encrypt ile otomatik SSL. **nginx KULLANILMAZ.**

## Mimari

```
Internet (HTTPS :443)
  │
  ▼
Traefik 3
  ├── TLS termination (Let's Encrypt)
  ├── HTTP → HTTPS redirect (:80 → :443)
  ├── /api/*     → Gunicorn (4 Uvicorn) → FastAPI :8000
  ├── /          → Next.js :3000
  ├── /minio     → MinIO :9000
  └── /auth      → Keycloak :8080
```

## 1. Traefik Static Config (traefik.yml)

```yaml
# traefik.yml — static configuration
entryPoints:
  web:
    address: ":80"
    http:
      redirections:
        entryPoint:
          to: websecure
          scheme: https

  websecure:
    address: ":443"

certificatesResolvers:
  letsencrypt:
    acme:
      email: ops@b2metric.com
      storage: /letsencrypt/acme.json
      httpChallenge:
        entryPoint: web

providers:
  docker:
    endpoint: "unix:///var/run/docker.sock"
    exposedByDefault: false
    network: aria-net

api:
  dashboard: true
  insecure: false  # prod'da false, sadece localhost'tan erisim

log:
  level: INFO

accessLog: {}
```

## 2. Docker Compose — Traefik Service

```yaml
# docker-compose.prod.yml
services:
  traefik:
    image: traefik:v3.3
    container_name: aria-traefik
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./traefik/traefik.yml:/traefik.yml:ro
      - ./traefik/dynamic.yml:/dynamic.yml:ro
      - traefik_certs:/letsencrypt
      - /var/run/docker.sock:/var/run/docker.sock:ro
    networks:
      - aria-net
    command:
      - "--configFile=/traefik.yml"
    labels:
      - "traefik.enable=true"
      # Dashboard (sadece localhost)
      - "traefik.http.routers.dashboard.rule=Host(`traefik.aria.local`)"
      - "traefik.http.routers.dashboard.service=api@internal"
      - "traefik.http.routers.dashboard.entrypoints=websecure"
      - "traefik.http.routers.dashboard.tls.certresolver=letsencrypt"

volumes:
  traefik_certs:
```

## 3. Docker Compose — App Services (Labels)

```yaml
  backend:
    image: aria-backend:latest
    # ... other config ...
    networks:
      - aria-net
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.backend.rule=Host(`aria.b2metric.com`) && PathPrefix(`/api`)"
      - "traefik.http.routers.backend.entrypoints=websecure"
      - "traefik.http.routers.backend.tls.certresolver=letsencrypt"
      - "traefik.http.services.backend.loadbalancer.server.port=8000"

  frontend:
    image: aria-web:latest
    networks:
      - aria-net
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.frontend.rule=Host(`aria.b2metric.com`)"
      - "traefik.http.routers.frontend.entrypoints=websecure"
      - "traefik.http.routers.frontend.tls.certresolver=letsencrypt"

  minio:
    image: minio/minio
    networks:
      - aria-net
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.minio.rule=Host(`aria.b2metric.com`) && PathPrefix(`/artifacts`)"
      - "traefik.http.routers.minio.entrypoints=websecure"
      - "traefik.http.routers.minio.tls.certresolver=letsencrypt"
```

## 4. Traefik Dynamic Config — Middleware

```yaml
# dynamic.yml
http:
  middlewares:
    rate-limit:
      rateLimit:
        average: 100
        burst: 50
        period: 1s

    circuit-breaker:
      circuitBreaker:
        expression: "ResponseCodeRatio(500, 600, 0, 600) > 0.25"
        checkPeriod: "30s"
        fallbackDuration: "30s"

    security-headers:
      headers:
        frameDeny: true
        sslRedirect: true
        browserXssFilter: true
        contentTypeNosniff: true
        stsIncludeSubdomains: true
        stsPreload: true
        stsSeconds: 31536000
        customFrameOptionsValue: "DENY"

  routers:
    backend:
      middlewares:
        - rate-limit
        - circuit-breaker
        - security-headers
```

## 5. Let's Encrypt Staging (Test)

Production'a geçmeden önce staging ile test et:

```yaml
certificatesResolvers:
  letsencrypt-staging:
    acme:
      email: ops@b2metric.com
      storage: /letsencrypt/acme-staging.json
      caServer: "https://acme-staging-v02.api.letsencrypt.org/directory"
      httpChallenge:
        entryPoint: web
```

Staging sertifikaları **rate limit'e takılmaz**. Çalıştığını görünce production'a geç:

```yaml
      # caServer kaldır → production Let's Encrypt
```

## 6. Verify

```bash
# Sertifika kontrolü
curl -vI https://aria.b2metric.com/api/health

# Traefik dashboard
open https://traefik.aria.local

# Sertifika detayı
openssl s_client -connect aria.b2metric.com:443 -servername aria.b2metric.com </dev/null 2>/dev/null | openssl x509 -noout -dates -subject
```

## 7. Otomatik Yenileme

Traefik otomatik yapar — sertifika expire olmadan 30 gün önce yeniler. `acme.json` volume-mounted olduğu için restart'ta kaybolmaz.

## Önemli Notlar

- **Rate limit:** Let's Encrypt production'da haftada 50 sertifika. Test ederken staging kullan.
- **acme.json:** 600 permissions (sadece root okuyabilir). Container restart'ta kaybolmaması için volume.
- **DNS:** `aria.b2metric.com` A record'u Traefik sunucusuna yönlenmeli.
- **HTTP Challenge:** Port 80 açık olmalı (Let's Encrypt doğrulama için), sonra 443'e redirect.
