"""Resource profile schemas for roadmap wave planning and skill mapping"""
from typing import Dict, List, Optional, Literal
from pydantic import BaseModel, Field, validator
from datetime import datetime, date
from enum import Enum


class SkillLevel(str, Enum):
    """Skill proficiency levels"""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


class RoleType(str, Enum):
    """Resource role types for cybersecurity initiatives"""
    SECURITY_ARCHITECT = "security_architect"
    SECURITY_ENGINEER = "security_engineer"
    COMPLIANCE_ANALYST = "compliance_analyst"
    PROJECT_MANAGER = "project_manager"
    SOLUTION_ARCHITECT = "solution_architect"
    CYBER_ANALYST = "cyber_analyst"
    PENETRATION_TESTER = "penetration_tester"
    INCIDENT_RESPONDER = "incident_responder"
    GOVERNANCE_SPECIALIST = "governance_specialist"
    RISK_ANALYST = "risk_analyst"


class WavePhase(str, Enum):
    """Roadmap wave phases"""
    WAVE_1 = "wave_1"
    WAVE_2 = "wave_2" 
    WAVE_3 = "wave_3"
    WAVE_4 = "wave_4"
    WAVE_5 = "wave_5"


class SkillRequirement(BaseModel):
    """Skill requirement definition"""
    skill_name: str = Field(description="Name of the required skill")
    skill_category: str = Field(description="Category (technical, compliance, management, etc.)")
    required_level: SkillLevel = Field(description="Minimum required proficiency level")
    critical: bool = Field(default=False, description="Whether this skill is critical for success")
    description: Optional[str] = Field(description="Detailed skill description")


class RoleProfile(BaseModel):
    """Role profile with skill requirements and capacity"""
    role_type: RoleType = Field(description="Type of role")
    role_title: str = Field(description="Specific role title")
    fte_required: float = Field(ge=0, le=2.0, description="Full-time equivalent required (0-2.0)")
    duration_weeks: int = Field(ge=1, description="Duration in weeks")
    skill_requirements: List[SkillRequirement] = Field(description="Required skills for this role")
    seniority_level: str = Field(description="Seniority level (junior/mid/senior/principal)")
    hourly_rate_range: Optional[Dict[str, float]] = Field(description="Hourly rate range by region")
    remote_eligible: bool = Field(default=True, description="Whether role can be performed remotely")


class WaveResourceAllocation(BaseModel):
    """Resource allocation for a specific wave"""
    wave: WavePhase = Field(description="Wave identifier")
    wave_name: str = Field(description="Descriptive wave name")
    start_date: date = Field(description="Wave start date")
    end_date: date = Field(description="Wave end date")
    role_allocations: List[RoleProfile] = Field(description="Role allocations for this wave")
    total_fte: Optional[float] = Field(description="Total FTE for wave (calculated)")
    estimated_cost: Optional[float] = Field(description="Estimated cost for wave (calculated)")
    critical_path: bool = Field(default=False, description="Whether this wave is on critical path")

    @validator('end_date')
    def end_after_start(cls, v, values):
        if 'start_date' in values and v <= values['start_date']:
            raise ValueError('end_date must be after start_date')
        return v


class InitiativeResourceProfile(BaseModel):
    """Complete resource profile for an initiative"""
    initiative_id: str = Field(description="Initiative identifier")
    initiative_name: str = Field(description="Initiative name")
    total_duration_weeks: int = Field(ge=1, description="Total initiative duration")
    wave_allocations: List[WaveResourceAllocation] = Field(description="Resource allocations by wave")
    skill_summary: Dict[str, int] = Field(description="Summary of skill requirements by category")
    total_fte_demand: float = Field(description="Total FTE demand across all waves")
    total_estimated_cost: float = Field(description="Total estimated cost")
    resource_constraints: List[str] = Field(default_factory=list, description="Identified resource constraints")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ResourcePlanningRequest(BaseModel):
    """Request to generate resource planning for initiatives"""
    initiatives: List[Dict] = Field(description="Initiative details for resource planning")
    planning_horizon_weeks: int = Field(ge=4, le=156, description="Planning horizon in weeks (1-3 years)")
    target_start_date: date = Field(description="Target start date for planning")
    wave_duration_weeks: int = Field(default=12, ge=4, le=26, description="Standard wave duration")
    skill_constraints: Optional[Dict[str, int]] = Field(description="Available skill capacity constraints")


class ResourcePlanningResponse(BaseModel):
    """Response with resource planning details"""
    initiative_profiles: List[InitiativeResourceProfile] = Field(description="Resource profiles by initiative")
    planning_summary: Dict = Field(description="Overall planning summary and statistics")
    skill_demand_forecast: Dict[str, List[Dict]] = Field(description="Skill demand by time period")
    wave_overlay: List[Dict] = Field(description="Wave overlay for Gantt chart visualization")
    resource_conflicts: List[Dict] = Field(description="Identified resource conflicts and recommendations")
    calculation_timestamp: datetime = Field(default_factory=datetime.utcnow)


class CSVExportRequest(BaseModel):
    """Request to export resource planning to CSV"""
    initiative_ids: Optional[List[str]] = Field(description="Specific initiatives to export (optional)")
    include_skills: bool = Field(default=True, description="Include skill requirements in export")
    include_costs: bool = Field(default=True, description="Include cost estimates in export")
    export_format: Literal["summary", "detailed", "skills_matrix"] = Field(default="detailed", description="Export format type")


class CSVExportResponse(BaseModel):
    """Response with CSV export data"""
    csv_content: str = Field(description="CSV formatted content")
    filename: str = Field(description="Suggested filename")
    export_timestamp: datetime = Field(default_factory=datetime.utcnow)
    record_count: int = Field(description="Number of records exported")
    export_format: str = Field(description="Format used for export")


class GanttChartRequest(BaseModel):
    """Request for Gantt chart data"""
    initiative_ids: Optional[List[str]] = Field(description="Specific initiatives to include")
    include_resource_overlay: bool = Field(default=True, description="Include resource allocation overlay")
    include_skill_heatmap: bool = Field(default=False, description="Include skill demand heatmap")
    timeline_granularity: Literal["weekly", "monthly", "quarterly"] = Field(default="weekly", description="Timeline granularity")


class GanttTask(BaseModel):
    """Gantt chart task representation"""
    task_id: str = Field(description="Unique task identifier")
    task_name: str = Field(description="Task display name")
    start_date: date = Field(description="Task start date")
    end_date: date = Field(description="Task end date")
    duration_days: int = Field(description="Task duration in days")
    progress: float = Field(default=0.0, ge=0.0, le=1.0, description="Task completion progress (0-1)")
    parent_id: Optional[str] = Field(description="Parent task ID for hierarchy")
    initiative_id: str = Field(description="Associated initiative ID")
    wave: WavePhase = Field(description="Associated wave")
    resource_allocation: List[Dict] = Field(description="Resource allocation for this task")
    critical_path: bool = Field(default=False, description="Whether task is on critical path")


class GanttChartResponse(BaseModel):
    """Response with Gantt chart data"""
    tasks: List[GanttTask] = Field(description="Gantt chart tasks")
    timeline_start: date = Field(description="Overall timeline start date")
    timeline_end: date = Field(description="Overall timeline end date")
    resource_summary: Dict = Field(description="Resource utilization summary")
    skill_heatmap: Optional[Dict] = Field(description="Skill demand heatmap data")
    critical_path: List[str] = Field(description="Critical path task IDs")
    milestone_dates: List[Dict] = Field(description="Key milestone dates")


class WaveOverlayRequest(BaseModel):
    """Request for wave overlay visualization data"""
    planning_horizon_weeks: int = Field(ge=4, le=156, description="Planning horizon")
    include_resource_utilization: bool = Field(default=True, description="Include resource utilization data")
    aggregate_by: Literal["role", "skill", "cost"] = Field(default="role", description="Aggregation method")


class WaveOverlayResponse(BaseModel):
    """Response with wave overlay data"""
    wave_periods: List[Dict] = Field(description="Wave period definitions")
    resource_utilization: Dict = Field(description="Resource utilization by wave")
    skill_demand_trends: Dict = Field(description="Skill demand trends across waves")
    cost_distribution: Dict = Field(description="Cost distribution by wave")
    capacity_analysis: Dict = Field(description="Capacity vs demand analysis")
    recommendations: List[str] = Field(description="Resource planning recommendations")


class SkillMappingInfo(BaseModel):
    """Skill mapping configuration and metadata"""
    available_skills: List[Dict] = Field(description="Available skills catalog")
    skill_categories: List[str] = Field(description="Skill categories")
    role_skill_matrix: Dict[RoleType, List[str]] = Field(description="Default skills by role type")
    proficiency_definitions: Dict[SkillLevel, str] = Field(description="Skill level definitions")
    schema_version: str = Field(default="v1.0", description="Skill mapping schema version")


class ResourceConfigurationInfo(BaseModel):
    """Resource planning configuration information"""
    available_roles: List[Dict] = Field(description="Available role types and descriptions")
    skill_mapping: SkillMappingInfo = Field(description="Skill mapping configuration")
    default_wave_duration: int = Field(description="Default wave duration in weeks")
    max_planning_horizon: int = Field(description="Maximum planning horizon in weeks")
    supported_export_formats: List[str] = Field(description="Supported CSV export formats")
    gantt_granularities: List[str] = Field(description="Supported Gantt chart granularities")