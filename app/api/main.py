# app/api/main.py
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, select
from pathlib import Path
import json
import os
import logging
from typing import List, Dict
from datetime import datetime, timezone
from api.assist import router as assist_router
from api.storage import router as storage_router
from api.db import create_db_and_tables, get_session
from api.models import Assessment, Answer
from api.schemas import AssessmentCreate, AssessmentResponse, AnswerUpsert, ScoreResponse, PillarScore
from api.scoring import compute_scores
from api.routes import assessments as assessments_router, orchestrations as orchestrations_router, engagements as engagements_router, documents, summary, presets as presets_router, version as version_router, admin_auth as admin_auth_router, gdpr as gdpr_router, admin_settings as admin_settings_router, evidence as evidence_router, csf as csf_router, workshops as workshops_router, minutes as minutes_router, roadmap_prioritization as roadmap_prioritization_router, chat as chat_router
# from services.mcp_gateway.main import router as mcp_gateway_router  # Broken imports
from domain.repository import InMemoryRepository
from domain.file_repo import FileRepository
from ai.llm import LLMClient
from ai.orchestrator import Orchestrator
from config import config

# Import middleware components
from .middleware.performance import PerformanceTrackingMiddleware, CorrelationIDMiddleware
from .middleware.security_headers import SecurityHeadersMiddleware
from .middleware.rate_limiting import RateLimitingMiddleware
from services.performance import start_performance_monitoring, stop_performance_monitoring
from services.cache import cache_manager

app = FastAPI(title="AI Maturity Tool API", version="0.1.0")

# --- Middleware stack (order matters - first added runs last) ---
# 1. Security headers middleware (runs last, adds headers to all responses)
app.add_middleware(SecurityHeadersMiddleware)

# 2. Rate limiting middleware (disabled by default, can be enabled via env var)
rate_limiting_enabled = os.getenv('RATE_LIMITING_ENABLED', '0') == '1'
if rate_limiting_enabled:
    requests_per_minute = int(os.getenv('RATE_LIMIT_PER_MINUTE', '60'))
    burst_per_second = int(os.getenv('RATE_LIMIT_BURST_PER_SECOND', '10'))
    app.add_middleware(RateLimitingMiddleware, 
                      default_requests_per_minute=requests_per_minute,
                      burst_requests_per_second=burst_per_second,
                      enabled=True)

# 3. Performance tracking middleware 
app.add_middleware(PerformanceTrackingMiddleware)

# 4. Correlation ID middleware (runs first to ensure correlation IDs are available)
app.add_middleware(CorrelationIDMiddleware)

# --- CORS configuration (env-driven) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],  # allow custom headers like X-User-Email, X-Engagement-ID, X-Correlation-ID
    expose_headers=["Content-Disposition", "X-Response-Time-MS", "X-Correlation-ID", "X-Cache-Hits", "X-Cache-Misses", "X-Cache-Hit-Rate"],
)

@app.on_event("startup")
async def on_startup():
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, config.logging.level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)
    
    # Check and log CI/ML mode configuration
    ci_mode = os.getenv('CI_MODE', '0') == '1'
    ml_disabled = os.getenv('DISABLE_ML', '0') == '1'
    graceful_mode = os.getenv('GRACEFUL_STARTUP', '0') == '1'
    
    if ci_mode or ml_disabled or graceful_mode:
        logger.info(
            "Application starting in lightweight mode",
            extra={
                "ci_mode": ci_mode,
                "ml_disabled": ml_disabled,
                "graceful_mode": graceful_mode,
                "heavy_deps_skipped": True,
                "performance_mode": "optimized"
            }
        )
    
    # Initialize database with error handling
    try:
        create_db_and_tables()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        if not graceful_mode:
            raise
        logger.warning("Continuing in graceful mode without database")
    
    # Wire up domain dependencies with error handling
    try:
        app.state.repo = FileRepository()
        logger.info("File repository initialized")
    except Exception as e:
        logger.error(f"File repository initialization failed: {e}")
        if not graceful_mode:
            raise
        # Create a minimal mock repository
        from domain.repository import InMemoryRepository
        app.state.repo = InMemoryRepository()
        logger.warning("Using in-memory repository fallback")
    
    try:
        app.state.orchestrator = Orchestrator(LLMClient())
        logger.info("Orchestrator initialized")
    except Exception as e:
        logger.error(f"Orchestrator initialization failed: {e}")
        if not graceful_mode:
            raise
        # Create a minimal mock orchestrator
        app.state.orchestrator = None
        logger.warning("Orchestrator disabled due to initialization failure")
    
    # Initialize performance monitoring and caching with error handling
    if not graceful_mode:
        logger.info("Starting performance monitoring and cache services...")
        
        # Start cache cleanup tasks
        try:
            if config.cache.enabled:
                await cache_manager.start_all_cleanup()
                logger.info(
                    "Cache services started",
                    extra={
                        "cache_enabled": config.cache.enabled,
                        "presets_ttl": config.cache.presets_ttl_seconds,
                        "framework_ttl": config.cache.framework_ttl_seconds,
                        "user_roles_ttl": config.cache.user_roles_ttl_seconds
                    }
                )
            else:
                logger.info("Cache services disabled")
        except Exception as e:
            logger.error(f"Cache initialization failed: {e}")
            if not graceful_mode:
                raise
            logger.warning("Cache services disabled due to initialization failure")
        
        # Start performance monitoring
        try:
            if config.performance.enable_request_timing or config.performance.enable_query_timing:
                await start_performance_monitoring()
                logger.info(
                    "Performance monitoring started",
                    extra={
                        "request_timing": config.performance.enable_request_timing,
                        "query_timing": config.performance.enable_query_timing,
                        "slow_request_threshold_ms": config.performance.slow_request_threshold_ms,
                        "slow_query_threshold_ms": config.performance.slow_query_threshold_ms,
                        "alerts_enabled": config.performance.enable_performance_alerts
                    }
                )
            else:
                logger.info("Performance monitoring disabled")
        except Exception as e:
            logger.error(f"Performance monitoring initialization failed: {e}")
            if not graceful_mode:
                raise
            logger.warning("Performance monitoring disabled due to initialization failure")
    else:
        logger.info("Performance monitoring and cache services skipped in graceful mode")
    
    # Validate RAG configuration if enabled
    if config.rag.enabled:
        is_valid, errors = config.validate_azure_config()
        if not is_valid:
            logger.warning(
                "RAG is enabled but configuration is invalid",
                extra={
                    "errors": errors,
                    "rag_enabled": config.rag.enabled
                }
            )
        else:
            logger.info(
                "RAG services configured and enabled",
                extra={
                    "azure_openai_endpoint": config.azure_openai.endpoint,
                    "azure_search_endpoint": config.azure_search.endpoint,
                    "search_index": config.azure_search.index_name,
                    "embedding_model": config.azure_openai.embedding_model
                }
            )
    else:
        logger.info("RAG services disabled")
    
    # Validate AAD configuration if enabled
    if config.aad_groups.enabled:
        is_valid, errors = config.validate_aad_config()
        if not is_valid:
            logger.warning(
                "AAD groups is enabled but configuration is invalid",
                extra={
                    "errors": errors,
                    "aad_enabled": config.aad_groups.enabled
                }
            )
        else:
            logger.info(
                "AAD groups authentication configured and enabled",
                extra={
                    "tenant_id": config.aad_groups.tenant_id,
                    "client_configured": bool(config.aad_groups.client_id),
                    "cache_ttl_minutes": config.aad_groups.cache_ttl_minutes,
                    "require_tenant_isolation": config.aad_groups.require_tenant_isolation,
                    "allowed_tenants_count": len(config.aad_groups.allowed_tenant_ids)
                }
            )
    else:
        logger.info("AAD groups authentication disabled")
    
    # Initialize Service Bus
    if config.service_bus.is_configured():
        logger.info(
            "Service Bus configured - using Azure Service Bus",
            namespace=config.service_bus.namespace,
            max_retries=config.service_bus.max_retries
        )
        
        # Send test message to verify connectivity
        try:
            from services.service_bus import ServiceBusProducer
            producer = ServiceBusProducer()
            test_payload = {
                "test": True,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "service": "api_startup"
            }
            await producer.send_message(
                topic="health",
                message_type="startup_test",
                payload=test_payload,
                idempotency_key=f"startup-{datetime.now(timezone.utc).isoformat()}"
            )
            logger.info("Service Bus test message sent successfully")
        except Exception as e:
            logger.error(f"Failed to send Service Bus test message: {e}")
    else:
        logger.warning(
            "Service Bus configuration not found - using in-memory queue fallback",
            namespace_configured=bool(config.service_bus.namespace),
            connection_string_configured=bool(config.service_bus.connection_string)
        )
    
    # Initialize preset service
    from services import presets as preset_service
    preset_service.ensure_dirs()
    # register bundled presets if present
    try:
        # Use absolute paths that work both locally and in Docker
        base_path = Path("/app") if Path("/app").exists() else Path(".")
        bundled = {
            "cyber-for-ai": base_path / "config/presets/cyber-for-ai.json",
            "cscm-v3": base_path / "config/presets/preset_cscm_v3.json",
            # add others here if you have them
        }
        preset_service.BUNDLED.update({k: v for k, v in bundled.items() if v.exists()})
        logger.info(f"Loaded bundled presets: {list(preset_service.BUNDLED.keys())}")
    except Exception as e:
        logger.error(f"Failed to load bundled presets: {e}")
    
    # Initialize MCP Gateway configuration
    try:
        from services.mcp_gateway import init_mcp_config
        mcp_config = init_mcp_config()
        logger.info(
            "MCP Gateway initialized",
            extra={
                "base_data_path": str(mcp_config.base_data_path),
                "security_enabled": mcp_config.security.enable_path_jailing,
                "content_redaction": mcp_config.security.enable_content_redaction,
                "tools_enabled": {
                    "filesystem": mcp_config.filesystem.enabled,
                    "pdf_parser": mcp_config.pdf_parser.enabled,
                    "search": mcp_config.search.enabled
                }
            }
        )
    except Exception as e:
        logger.error(f"Failed to initialize MCP Gateway: {e}")
    
    # Log comprehensive route information for debugging
    try:
        routes = []
        route_methods = {}
        for route in app.routes:
            if hasattr(route, 'path'):
                routes.append(route.path)
                if hasattr(route, 'methods'):
                    route_methods[route.path] = list(route.methods)
        
        # Log route statistics
        total_routes = len(routes)
        api_routes = [r for r in routes if r.startswith('/api/')]
        business_routes = [r for r in api_routes if r not in ['/', '/health', '/version']]
        
        logger.info(
            "API Route Loading Summary",
            extra={
                "total_routes": total_routes,
                "api_routes_count": len(api_routes),
                "business_routes_count": len(business_routes),
                "basic_routes": ['/', '/health', '/version'],
                "critical_endpoints_loaded": bool([r for r in routes if any(x in r for x in ['/features', '/engagements', '/assessments'])]),
                "startup_status": "SUCCESS" if total_routes > 10 else "LIMITED_ROUTES"
            }
        )
        
        # Log failed routers if any
        if hasattr(app.state, 'failed_routers') or 'failed_routers' in locals():
            failed_count = len(failed_routers) if 'failed_routers' in locals() else 0
            if failed_count > 0:
                logger.warning(
                    f"Router Loading Issues: {failed_count} routers failed to load",
                    extra={
                        "failed_routers": failed_routers if 'failed_routers' in locals() else [],
                        "total_failed": failed_count
                    }
                )
        
        # Log sample of loaded routes for verification
        if total_routes > 0:
            logger.info(
                "Sample Loaded Routes",
                extra={
                    "first_10_routes": sorted(routes)[:10],
                    "business_sample": sorted(business_routes)[:5],
                    "diagnostic_available": "/api/diagnostic" in routes,
                    "router_status_available": "/api/router-status" in routes
                }
            )
        else:
            logger.error("CRITICAL: No routes loaded! This indicates a serious application issue.")
            
    except Exception as e:
        logger.error(f"Failed to log route information: {e}")
    
    logger.info("=== API STARTUP COMPLETE ===")


@app.on_event("shutdown")
async def on_shutdown():
    """Clean shutdown of performance monitoring and cache services"""
    logger = logging.getLogger(__name__)
    logger.info("Shutting down performance monitoring and cache services...")
    
    # Stop performance monitoring
    try:
        await stop_performance_monitoring()
        logger.info("Performance monitoring stopped")
    except Exception as e:
        logger.error(f"Error stopping performance monitoring: {e}")
    
    # Stop cache cleanup tasks
    try:
        await cache_manager.stop_all_cleanup()
        logger.info("Cache cleanup tasks stopped")
    except Exception as e:
        logger.error(f"Error stopping cache services: {e}")
    
    logger.info("Application shutdown complete")


# Feature flags endpoint
@app.get("/api/features")
async def get_feature_flags():
    """Get current S4 feature flag status"""
    from config import feature_flags
    
    return {
        "s4_enabled": feature_flags.is_s4_enabled(),
        "features": {
            "csf": feature_flags.csf_enabled,
            "workshops": feature_flags.workshops_enabled,
            "minutes": feature_flags.minutes_enabled,
            "chat": feature_flags.chat_enabled,
            "service_bus": feature_flags.service_bus_orchestration_enabled
        },
        "enabled_list": feature_flags.get_enabled_features(),
        "environment": os.getenv("ENVIRONMENT", "development")
    }

# Performance monitoring endpoint
@app.get("/api/performance/metrics")
async def get_performance_metrics(time_window_minutes: int = 60):
    """Get performance metrics for monitoring and debugging"""
    from services.performance import get_performance_statistics, get_recent_alerts
    from services.cache import get_cache_metrics
    
    try:
        # Get performance statistics
        perf_stats = get_performance_statistics(time_window_minutes)
        
        # Get recent alerts
        recent_alerts = get_recent_alerts(limit=20)
        
        # Get cache metrics
        cache_metrics = get_cache_metrics()
        
        return {
            "time_window_minutes": time_window_minutes,
            "performance_statistics": {
                "total_requests": perf_stats.total_requests,
                "avg_response_time_ms": round(perf_stats.avg_response_time_ms, 2),
                "p95_response_time_ms": round(perf_stats.p95_response_time_ms, 2),
                "p99_response_time_ms": round(perf_stats.p99_response_time_ms, 2),
                "slow_requests_count": perf_stats.slow_requests_count,
                "total_db_queries": perf_stats.total_db_queries,
                "avg_query_time_ms": round(perf_stats.avg_query_time_ms, 2),
                "slow_queries_count": perf_stats.slow_queries_count,
                "cache_hit_rate": round(perf_stats.cache_hit_rate, 2),
                "memory_usage_mb": round(perf_stats.memory_usage_mb, 2),
                "cpu_usage_percent": round(perf_stats.cpu_usage_percent, 2)
            },
            "cache_metrics": cache_metrics,
            "recent_alerts": [
                {
                    "type": alert.alert_type,
                    "message": alert.message,
                    "severity": alert.severity,
                    "timestamp": alert.timestamp.isoformat(),
                    "correlation_id": alert.correlation_id
                }
                for alert in recent_alerts
            ],
            "configuration": {
                "cache_enabled": config.cache.enabled,
                "performance_monitoring_enabled": config.performance.enable_request_timing,
                "slow_request_threshold_ms": config.performance.slow_request_threshold_ms,
                "slow_query_threshold_ms": config.performance.slow_query_threshold_ms,
                "alerts_enabled": config.performance.enable_performance_alerts
            }
        }
    except Exception as e:
        logger.error(f"Error retrieving performance metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve performance metrics")



# Add diagnostic endpoint to verify API is working
@app.get("/api/diagnostic")
async def diagnostic_endpoint():
    """Diagnostic endpoint to verify API functionality"""
    import sys
    return {
        "status": "API is running",
        "python_version": sys.version,
        "fastapi_loaded": True,
        "diagnostic": "If you see this, FastAPI is working but routes may not be loading"
    }

# Include routers with error handling
import logging
logger = logging.getLogger(__name__)

failed_routers = []

try:
    app.include_router(assist_router)
except Exception as e:
    logger.error(f"Failed to include assist_router: {e}")
    failed_routers.append(("assist_router", str(e)))

try:
    app.include_router(storage_router)
except Exception as e:
    logger.error(f"Failed to include storage_router: {e}")
    failed_routers.append(("storage_router", str(e)))

try:
    app.include_router(assessments_router.router)
except Exception as e:
    logger.error(f"Failed to include assessments_router: {e}")
    failed_routers.append(("assessments_router", str(e)))

try:
    app.include_router(orchestrations_router.router)
except Exception as e:
    logger.error(f"Failed to include orchestrations_router: {e}")
    failed_routers.append(("orchestrations_router", str(e)))

try:
    app.include_router(engagements_router.router)
except Exception as e:
    logger.error(f"Failed to include engagements_router: {e}")
    failed_routers.append(("engagements_router", str(e)))

try:
    app.include_router(documents.router)
except Exception as e:
    logger.error(f"Failed to include documents router: {e}")
    failed_routers.append(("documents", str(e)))

try:
    app.include_router(summary.router)
except Exception as e:
    logger.error(f"Failed to include summary router: {e}")
    failed_routers.append(("summary", str(e)))

try:
    app.include_router(presets_router.router)
except Exception as e:
    logger.error(f"Failed to include presets_router: {e}")
    failed_routers.append(("presets_router", str(e)))

try:
    app.include_router(version_router.router)
except Exception as e:
    logger.error(f"Failed to include version_router: {e}")
    failed_routers.append(("version_router", str(e)))

try:
    app.include_router(admin_auth_router.router)
except Exception as e:
    logger.error(f"Failed to include admin_auth_router: {e}")
    failed_routers.append(("admin_auth_router", str(e)))

try:
    app.include_router(gdpr_router.router)
except Exception as e:
    logger.error(f"Failed to include gdpr_router: {e}")
    failed_routers.append(("gdpr_router", str(e)))

try:
    app.include_router(admin_settings_router.router)
except Exception as e:
    logger.error(f"Failed to include admin_settings_router: {e}")
    failed_routers.append(("admin_settings_router", str(e)))

try:
    app.include_router(evidence_router.router)
except Exception as e:
    logger.error(f"Failed to include evidence_router: {e}")
    failed_routers.append(("evidence_router", str(e)))

try:
    app.include_router(roadmap_prioritization_router.router)
except Exception as e:
    logger.error(f"Failed to include roadmap_prioritization_router: {e}")
    failed_routers.append(("roadmap_prioritization_router", str(e)))

# MCP Gateway router
# MCP gateway router disabled - broken imports
# try:
#     app.include_router(mcp_gateway_router)
# except Exception as e:
#     logger.error(f"Failed to include mcp_gateway_router: {e}")
#     failed_routers.append(("mcp_gateway_router", str(e)))

# Add diagnostic info about failed routers
@app.get("/api/router-status")
async def router_status():
    """Check which routers failed to load"""
    return {
        "failed_routers": failed_routers,
        "failed_count": len(failed_routers)
    }

# S4 Feature routers - conditionally included based on feature flags
from config import feature_flags

if feature_flags.csf_enabled:
    app.include_router(csf_router.router)
    logger.info("CSF Grid feature enabled")

if feature_flags.workshops_enabled:
    app.include_router(workshops_router.router)
    logger.info("Workshops & Consent feature enabled")

if feature_flags.minutes_enabled:
    app.include_router(minutes_router.router)
    logger.info("Minutes Publishing feature enabled")

# Include chat router if enabled
if feature_flags.chat_enabled:
    app.include_router(chat_router.router)
    logger.info("Chat feature enabled")

def load_preset(preset_id: str) -> dict:
    # Use new preset service for consistency
    from services import presets as preset_service
    try:
        preset = preset_service.get_preset(preset_id)
        return preset.model_dump()
    except HTTPException as e:
        # Fallback to old bundled method for backwards compatibility
        preset_path = Path(__file__).resolve().parents[1] / "config" / "presets" / f"{preset_id}.json"
        if not preset_path.exists():
            raise FileNotFoundError(preset_path) from e
        return json.loads(preset_path.read_text(encoding="utf-8"))

# Health endpoint moved to version router

# Additional health endpoints for compatibility
@app.get("/health") 
async def health_redirect():
    """Health endpoint redirect for root path compatibility"""
    from .routes.version import health_check
    return await health_check()

@app.get("/api/health") 
async def api_health_redirect():
    """Health endpoint redirect for API prefix compatibility"""
    from .routes.version import health_check
    return await health_check()

@app.get("/api/diagnostic")
async def diagnostic_endpoint():
    """Comprehensive diagnostic endpoint for production debugging"""
    import sys
    import os
    from datetime import datetime, timezone
    
    # Count loaded routes
    routes = []
    business_routes = []
    for route in app.routes:
        if hasattr(route, 'path'):
            routes.append(route.path)
            if '/api/' in route.path and route.path not in ['/', '/health', '/version']:
                business_routes.append(route.path)
    
    return {
        "status": "API diagnostic information",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "environment": {
            "python_version": sys.version,
            "working_directory": os.getcwd(),
            "pythonpath_set": os.environ.get('PYTHONPATH', 'NOT_SET'),
            "ci_mode": os.environ.get('CI_MODE', '0') == '1',
            "ml_disabled": os.environ.get('DISABLE_ML', '0') == '1'
        },
        "routes": {
            "total_routes": len(routes),
            "business_routes_count": len(business_routes),
            "sample_routes": routes[:10],
            "sample_business_routes": business_routes[:10]
        },
        "failed_routers": failed_routers if 'failed_routers' in globals() else [],
        "fastapi_loaded": True,
        "diagnosis": "If you see this, FastAPI basic functionality is working"
    }


@app.post("/assessments", response_model=AssessmentResponse)
def create_assessment(assessment: AssessmentCreate, session: Session = Depends(get_session)):
    """Create a new assessment"""
    # Verify preset exists
    try:
        load_preset(assessment.preset_id)
    except FileNotFoundError:
        raise HTTPException(status_code=400, detail="Invalid preset_id")
    
    db_assessment = Assessment(**assessment.dict())
    session.add(db_assessment)
    session.commit()
    session.refresh(db_assessment)
    
    return AssessmentResponse(
        id=db_assessment.id,
        name=db_assessment.name,
        preset_id=db_assessment.preset_id,
        created_at=db_assessment.created_at,
        answers=[]
    )


@app.get("/assessments/{assessment_id}", response_model=AssessmentResponse)
def get_assessment(assessment_id: str, session: Session = Depends(get_session)):
    """Get assessment with answers"""
    assessment = session.get(Assessment, assessment_id)
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")
    
    answers = [
        AnswerUpsert(
            pillar_id=ans.pillar_id,
            question_id=ans.question_id,
            level=ans.level,
            notes=ans.notes
        )
        for ans in assessment.answers
    ]
    
    return AssessmentResponse(
        id=assessment.id,
        name=assessment.name,
        preset_id=assessment.preset_id,
        created_at=assessment.created_at,
        answers=answers
    )


@app.post("/assessments/{assessment_id}/answers")
def upsert_answer(assessment_id: str, answer: AnswerUpsert, session: Session = Depends(get_session)):
    """Upsert an answer (insert or update by pillar_id and question_id)"""
    # Verify assessment exists
    assessment = session.get(Assessment, assessment_id)
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")
    
    # Find existing answer
    statement = select(Answer).where(
        Answer.assessment_id == assessment_id,
        Answer.pillar_id == answer.pillar_id,
        Answer.question_id == answer.question_id
    )
    existing = session.exec(statement).first()
    
    if existing:
        # Update existing
        existing.level = answer.level
        existing.notes = answer.notes
    else:
        # Create new
        db_answer = Answer(
            assessment_id=assessment_id,
            **answer.dict()
        )
        session.add(db_answer)
    
    session.commit()
    return {"status": "success"}


@app.get("/assessments/{assessment_id}/scores", response_model=ScoreResponse)
def get_scores(assessment_id: str, session: Session = Depends(get_session)):
    """Get scores for an assessment"""
    # Get assessment
    assessment = session.get(Assessment, assessment_id)
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")
    
    # Load preset
    try:
        preset = load_preset(assessment.preset_id)
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="Preset not found")
    
    # Group answers by pillar
    answers_by_pillar: Dict[str, List[Answer]] = {}
    for answer in assessment.answers:
        if answer.pillar_id not in answers_by_pillar:
            answers_by_pillar[answer.pillar_id] = []
        answers_by_pillar[answer.pillar_id].append(answer)
    
    # Compute scores
    pillar_scores_dict, overall_score, gates_applied = compute_scores(answers_by_pillar, preset)
    
    # Build response
    pillar_scores = []
    for pillar in preset["pillars"]:
        pillar_id = pillar["id"]
        total_questions = len(preset["questions"].get(pillar_id, []))
        questions_answered = len(answers_by_pillar.get(pillar_id, []))
        
        pillar_scores.append(PillarScore(
            pillar_id=pillar_id,
            score=pillar_scores_dict.get(pillar_id),
            weight=pillar["weight"],
            questions_answered=questions_answered,
            total_questions=total_questions
        ))
    
    return ScoreResponse(
        assessment_id=assessment_id,
        pillar_scores=pillar_scores,
        overall_score=overall_score,
        gates_applied=gates_applied
    )
