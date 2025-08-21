"""Roadmap cost calculation schemas with T-shirt sizing and regional rates"""
from typing import Dict, List, Optional, Literal
from pydantic import BaseModel, Field, validator
from datetime import datetime
from enum import Enum


class TShirtSize(str, Enum):
    """T-shirt sizes for effort estimation"""
    S = "S"
    M = "M"
    L = "L"
    XL = "XL"


class Scenario(str, Enum):
    """Cost calculation scenarios with different multipliers"""
    BASELINE = "baseline"
    CONSTRAINED = "constrained"
    ACCELERATED = "accelerated"


class Region(str, Enum):
    """Supported regions for cost calculation"""
    US_EAST = "us-east"
    US_WEST = "us-west"
    EU_WEST = "eu-west"
    ASIA_PACIFIC = "asia-pacific"
    INDIA = "india"


class RegionalRates(BaseModel):
    """Hourly rates by region and role level"""
    senior_consultant: float = Field(description="Senior consultant hourly rate")
    consultant: float = Field(description="Consultant hourly rate")  
    analyst: float = Field(description="Analyst hourly rate")
    project_manager: float = Field(description="Project manager hourly rate")
    architect: float = Field(description="Solution architect hourly rate")


class CostComponent(BaseModel):
    """Individual cost component breakdown"""
    category: str = Field(description="Cost category (labor/tooling/services)")
    description: str = Field(description="Component description")
    base_amount: float = Field(ge=0, description="Base cost amount")
    regional_multiplier: float = Field(default=1.0, description="Regional adjustment multiplier")
    scenario_multiplier: float = Field(default=1.0, description="Scenario adjustment multiplier") 
    total_amount: float = Field(description="Final calculated amount")


class LaborCosts(BaseModel):
    """Labor cost breakdown by role"""
    senior_consultant_hours: float = Field(default=0, ge=0, description="Senior consultant hours")
    consultant_hours: float = Field(default=0, ge=0, description="Consultant hours")
    analyst_hours: float = Field(default=0, ge=0, description="Analyst hours")
    project_manager_hours: float = Field(default=0, ge=0, description="Project manager hours")
    architect_hours: float = Field(default=0, ge=0, description="Architect hours")
    total_hours: Optional[float] = Field(description="Total labor hours (calculated)")
    total_cost: Optional[float] = Field(description="Total labor cost (calculated)")


class ToolingCosts(BaseModel):
    """Tooling and licensing cost breakdown"""
    security_tools: float = Field(default=0, ge=0, description="Security tooling costs")
    compliance_tools: float = Field(default=0, ge=0, description="Compliance tooling costs")
    monitoring_tools: float = Field(default=0, ge=0, description="Monitoring tooling costs")
    integration_tools: float = Field(default=0, ge=0, description="Integration tooling costs")
    training_materials: float = Field(default=0, ge=0, description="Training and materials costs")
    total_cost: Optional[float] = Field(description="Total tooling cost (calculated)")


class MicrosoftServicesCosts(BaseModel):
    """Microsoft services and licensing costs"""
    azure_security_services: float = Field(default=0, ge=0, description="Azure security services")
    microsoft_365_licenses: float = Field(default=0, ge=0, description="Microsoft 365 licensing")
    azure_infrastructure: float = Field(default=0, ge=0, description="Azure infrastructure costs")
    support_services: float = Field(default=0, ge=0, description="Microsoft support services")
    training_certification: float = Field(default=0, ge=0, description="Training and certification")
    total_cost: Optional[float] = Field(description="Total Microsoft services cost (calculated)")


class TSizeCostMapping(BaseModel):
    """T-shirt size to cost range mapping"""
    size: TShirtSize = Field(description="T-shirt size")
    min_cost: float = Field(ge=0, description="Minimum cost range")
    max_cost: float = Field(ge=0, description="Maximum cost range")
    typical_cost: float = Field(ge=0, description="Typical cost estimate")
    labor_weeks: float = Field(ge=0, description="Typical labor weeks")
    description: str = Field(description="Size description and typical scope")

    @validator('max_cost')
    def max_greater_than_min(cls, v, values):
        if 'min_cost' in values and v < values['min_cost']:
            raise ValueError('max_cost must be greater than or equal to min_cost')
        return v

    @validator('typical_cost')
    def typical_in_range(cls, v, values):
        if 'min_cost' in values and 'max_cost' in values:
            if v < values['min_cost'] or v > values['max_cost']:
                raise ValueError('typical_cost must be between min_cost and max_cost')
        return v


class InitiativeCostCalculation(BaseModel):
    """Complete cost calculation for an initiative"""
    initiative_id: str = Field(description="Initiative identifier")
    name: str = Field(description="Initiative name")
    t_shirt_size: TShirtSize = Field(description="T-shirt size estimate")
    region: Region = Field(description="Primary region for cost calculation")
    scenario: Scenario = Field(description="Cost calculation scenario")
    
    # Cost breakdowns
    labor_costs: LaborCosts = Field(description="Labor cost breakdown")
    tooling_costs: ToolingCosts = Field(description="Tooling cost breakdown")
    microsoft_services_costs: MicrosoftServicesCosts = Field(description="Microsoft services breakdown")
    
    # Calculated totals
    total_labor_cost: float = Field(description="Total labor cost")
    total_tooling_cost: float = Field(description="Total tooling cost")
    total_microsoft_cost: float = Field(description="Total Microsoft services cost")
    total_cost: float = Field(description="Grand total cost")
    
    # Additional metadata
    cost_components: List[CostComponent] = Field(description="Detailed cost component breakdown")
    calculation_timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Confidence and sizing
    cost_confidence: str = Field(description="Cost estimate confidence level")
    size_justification: str = Field(description="Justification for T-shirt size selection")


class CostCalculationRequest(BaseModel):
    """Request to calculate costs for initiatives"""
    initiatives: List[Dict] = Field(description="Initiative details for cost calculation")
    region: Region = Field(description="Target region for cost calculation")
    scenario: Scenario = Field(default=Scenario.BASELINE, description="Cost calculation scenario")
    custom_rates: Optional[RegionalRates] = Field(description="Custom regional rates (optional)")


class CostCalculationResponse(BaseModel):
    """Response with calculated costs"""
    calculated_costs: List[InitiativeCostCalculation] = Field(description="Cost calculations")
    regional_rates_used: RegionalRates = Field(description="Regional rates used in calculation")
    scenario_multipliers: Dict[str, float] = Field(description="Scenario multipliers applied")
    total_portfolio_cost: float = Field(description="Sum of all initiative costs")
    calculation_summary: Dict = Field(description="Summary statistics")


class TSizeUpdateRequest(BaseModel):
    """Request to update T-shirt size mappings"""
    size_mappings: List[TSizeCostMapping] = Field(description="Updated size mappings")
    description: Optional[str] = Field(description="Update description")


class TSizeConfigResponse(BaseModel):
    """Response with T-shirt size configuration"""
    size_mappings: List[TSizeCostMapping] = Field(description="Current size mappings")
    last_updated: datetime = Field(description="Last update timestamp")
    updated_by: Optional[str] = Field(description="Last updated by user")


class ScenarioMultipliers(BaseModel):
    """Multipliers for different cost scenarios"""
    baseline: float = Field(default=1.0, description="Baseline scenario multiplier")
    constrained: float = Field(default=0.8, description="Constrained budget multiplier")
    accelerated: float = Field(default=1.3, description="Accelerated timeline multiplier")


class CostConfigurationInfo(BaseModel):
    """Cost calculation configuration and schema information"""
    regional_rates: Dict[Region, RegionalRates] = Field(description="Regional rates by region")
    scenario_multipliers: ScenarioMultipliers = Field(description="Scenario multiplier configuration")
    default_t_shirt_mappings: List[TSizeCostMapping] = Field(description="Default T-shirt size mappings")
    cost_formula_description: str = Field(
        default="cost = (labor + tooling + microsoft_services) * regional_multiplier * scenario_multiplier",
        description="Cost calculation formula"
    )
    schema_version: str = Field(default="v2.0", description="Cost schema version")