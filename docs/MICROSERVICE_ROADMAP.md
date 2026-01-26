# Stage Buddy V2 - Microservice Architecture Roadmap

**Version:** 1.0
**Date:** January 2026
**Status:** Planning (Post-MVP)

---

## Executive Summary

This document outlines the migration path from Stage Buddy's current monolithic architecture to a microservice-based system. The goal is to enable independent scaling, deployment, and development of each analysis engine.

---

## Current Architecture (Monolith)

```
┌─────────────────────────────────────────────────────────────┐
│                    Stage Buddy V2                            │
│                   (Single Process)                           │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │   Spirit    │  │   Chest     │  │   Body      │  ...    │
│  │   Engine    │  │   Engine    │  │   Engine    │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
│                         │                                    │
│              ┌──────────┴──────────┐                        │
│              │  Shared Resources   │                        │
│              │  - Audio Pipeline   │                        │
│              │  - Transcription    │                        │
│              │  - Data Structures  │                        │
│              └─────────────────────┘                        │
└─────────────────────────────────────────────────────────────┘
```

**Pros:**
- Simple deployment
- Low latency (no network calls)
- Shared memory for large data

**Cons:**
- Single point of failure
- Cannot scale engines independently
- Deployment affects all components

---

## Target Architecture (Microservices)

```
┌─────────────────────────────────────────────────────────────────────┐
│                         API Gateway                                  │
│                    (Load Balancer + Auth)                           │
└───────────────────────────┬─────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│    Spirit     │   │    Chest      │   │    Body       │
│    Service    │   │    Service    │   │    Service    │
│   (Port 5001) │   │   (Port 5002) │   │   (Port 5003) │
└───────────────┘   └───────────────┘   └───────────────┘
        │                   │                   │
        └───────────────────┼───────────────────┘
                            │
                            ▼
                ┌───────────────────────┐
                │    Shared Services    │
                │  ┌─────────────────┐  │
                │  │  Audio Service  │  │
                │  │  (extraction,   │  │
                │  │   transcription)│  │
                │  └─────────────────┘  │
                │  ┌─────────────────┐  │
                │  │  Storage (S3)   │  │
                │  └─────────────────┘  │
                │  ┌─────────────────┐  │
                │  │  Message Queue  │  │
                │  │  (Redis/RabbitMQ)│ │
                │  └─────────────────┘  │
                └───────────────────────┘
```

---

## API Specifications

### Spirit Service API

```yaml
POST /api/v1/spirit/analyze
Content-Type: application/json

Request:
{
  "audio_url": "s3://bucket/performance.wav",
  "performance_id": "perf_abc123",
  "transcript": "Optional pre-computed transcript",
  "word_segments": [...],  # Optional
  "options": {
    "segment_duration": 3.0,
    "include_feedback": true
  }
}

Response:
{
  "performance_id": "perf_abc123",
  "spirit_score": 3.45,
  "sub_scores": {
    "emotion_alignment": 0.65,
    "transition_quality": 0.72,
    "emotional_range": 0.58,
    "settling": 0.81
  },
  "vocal_emotions": [...],
  "ideal_emotions": [...],
  "feedback": "Your spirit is waking up...",
  "processing_time_ms": 8234,
  "version": "spirit-engine-v1.2"
}
```

### Chest Service API

```yaml
POST /api/v1/chest/analyze
Content-Type: application/json

Request:
{
  "audio_url": "s3://bucket/performance.wav",
  "performance_id": "perf_abc123",
  "word_segments": [...],  # Optional, for pause alignment
  "options": {
    "include_energy_curve": false,
    "include_feedback": true
  }
}

Response:
{
  "performance_id": "perf_abc123",
  "chest_score": 4.12,
  "sub_scores": {
    "breath_control": 0.78,
    "projection": 0.82,
    "pause_technique": 0.71,
    "vocal_health": 0.85
  },
  "breath_events": [...],
  "pause_events": [...],
  "fatigue_detected": false,
  "feedback": "Your breath control is solid...",
  "processing_time_ms": 5123,
  "version": "chest-engine-v1.0"
}
```

### Orchestrator API

```yaml
POST /api/v1/performance/analyze
Content-Type: application/json

Request:
{
  "video_url": "s3://bucket/performance.mp4",
  "performance_id": "perf_abc123",
  "engines": ["spirit", "chest", "body", "audience"],
  "callback_url": "https://app.stagebuddy.ai/webhook/results"
}

Response:
{
  "job_id": "job_xyz789",
  "status": "processing",
  "estimated_time_seconds": 45
}

# Callback payload (async):
{
  "job_id": "job_xyz789",
  "performance_id": "perf_abc123",
  "status": "completed",
  "overall_score": 15.8,
  "results": {
    "spirit": { ... },
    "chest": { ... },
    "body": { ... },
    "audience": { ... }
  }
}
```

---

## Service Implementation Template

### FastAPI Service Skeleton

```python
# chest_service/app.py
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List
import logging

from chest_engine import ChestEngine, ChestAnalysisResult

app = FastAPI(
    title="Stage Buddy Chest Service",
    version="1.0.0"
)

# Initialize engine at startup
engine = None

@app.on_event("startup")
async def startup():
    global engine
    engine = ChestEngine()
    logging.info("Chest Engine initialized")

@app.get("/health")
async def health_check():
    return {"status": "healthy", "engine_loaded": engine is not None}

@app.get("/metrics")
async def metrics():
    return {
        "requests_total": app.state.request_count,
        "average_processing_ms": app.state.avg_processing_time
    }

class AnalyzeRequest(BaseModel):
    audio_url: str
    performance_id: str
    word_segments: Optional[List[dict]] = None
    options: Optional[dict] = None

class AnalyzeResponse(BaseModel):
    performance_id: str
    chest_score: float
    sub_scores: dict
    processing_time_ms: float
    version: str

@app.post("/api/v1/chest/analyze", response_model=AnalyzeResponse)
async def analyze(request: AnalyzeRequest):
    try:
        # Download audio from URL
        audio_path = download_audio(request.audio_url)

        # Run analysis
        result = engine.analyze(
            audio_path=audio_path,
            word_segments=request.word_segments
        )

        return AnalyzeResponse(
            performance_id=request.performance_id,
            chest_score=result.overall_score,
            sub_scores={
                "breath_control": result.breath_control_score,
                "projection": result.projection_score,
                "pause_technique": result.pause_technique_score,
                "vocal_health": result.vocal_health_score
            },
            processing_time_ms=result.processing_time_ms,
            version="chest-engine-v1.0"
        )

    except Exception as e:
        logging.error(f"Analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

### Dockerfile

```dockerfile
# chest_service/Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Environment variables
ENV MODEL_CACHE_DIR=/app/models
ENV LOG_LEVEL=INFO

# Health check
HEALTHCHECK --interval=30s --timeout=10s \
    CMD curl -f http://localhost:8000/health || exit 1

# Run service
EXPOSE 8000
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Docker Compose (Development)

```yaml
# docker-compose.yml
version: '3.8'

services:
  spirit-service:
    build: ./spirit_service
    ports:
      - "5001:8000"
    environment:
      - MODEL_CACHE_DIR=/models
    volumes:
      - model-cache:/models

  chest-service:
    build: ./chest_service
    ports:
      - "5002:8000"
    environment:
      - MODEL_CACHE_DIR=/models
    volumes:
      - model-cache:/models

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  orchestrator:
    build: ./orchestrator
    ports:
      - "5000:8000"
    depends_on:
      - spirit-service
      - chest-service
      - redis
    environment:
      - SPIRIT_SERVICE_URL=http://spirit-service:8000
      - CHEST_SERVICE_URL=http://chest-service:8000
      - REDIS_URL=redis://redis:6379

volumes:
  model-cache:
```

---

## Migration Strategy

### Phase 1: Prepare for Extraction (Current)

1. **Clean API boundaries** in monolith
   - Each engine has clear `analyze(audio_path) -> Result` interface
   - No tight coupling between engines
   - JSON-serializable data structures

2. **Add feature flags**
   ```python
   if settings.USE_MICROSERVICES:
       result = call_chest_service(audio_url)
   else:
       result = chest_engine.analyze(audio_path)
   ```

### Phase 2: Strangler Fig Pattern

1. Deploy microservice alongside monolith
2. Route percentage of traffic to microservice
3. Monitor performance and correctness
4. Gradually increase traffic to microservice
5. Decommission monolith endpoint

### Phase 3: Full Microservices

1. All engines run as independent services
2. Orchestrator coordinates analysis jobs
3. Message queue for async processing
4. Independent scaling per engine

---

## Infrastructure Requirements

### Kubernetes Deployment

```yaml
# chest-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: chest-service
spec:
  replicas: 3
  selector:
    matchLabels:
      app: chest-service
  template:
    spec:
      containers:
      - name: chest
        image: stagebuddy/chest-service:v1.0
        resources:
          requests:
            memory: "2Gi"
            cpu: "1"
          limits:
            memory: "4Gi"
            cpu: "2"
        ports:
        - containerPort: 8000
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
```

### Scaling Strategy

| Service | CPU-bound | Memory | Recommended Replicas |
|---------|-----------|--------|---------------------|
| Spirit | High (ML models) | 4GB | 2-5 |
| Chest | Medium | 2GB | 2-4 |
| Body | High (video) | 8GB | 2-5 |
| Audience | Low | 1GB | 1-2 |

---

## Timeline

| Phase | Duration | Milestone |
|-------|----------|-----------|
| MVP (Monolith) | Current | All engines working in single process |
| API Cleanup | 2 weeks | Clean interfaces, feature flags |
| First Service | 2 weeks | Chest as standalone service |
| Full Extraction | 4 weeks | All engines as services |
| Production | 2 weeks | Kubernetes deployment |

**Total: ~10 weeks post-MVP**

---

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Network latency | Slower analysis | Batch processing, caching |
| Service failures | Partial results | Circuit breakers, fallbacks |
| Data consistency | Wrong scores | Idempotent operations, versioning |
| Complexity | Dev velocity | Clear documentation, monitoring |

---

*This roadmap will be updated as the MVP matures and production requirements become clearer.*
