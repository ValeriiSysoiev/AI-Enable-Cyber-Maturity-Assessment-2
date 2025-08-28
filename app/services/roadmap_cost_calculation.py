"""Roadmap cost calculation service with regional rates and T-shirt sizing"""
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from api.schemas.roadmap_costs import (
    TShirtSize, Scenario, Region, RegionalRates, CostComponent,
    LaborCosts, ToolingCosts, MicrosoftServicesCosts, TSizeCostMapping,
    InitiativeCostCalculation, CostCalculationRequest, CostCalculationResponse,
    ScenarioMultipliers, CostConfigurationInfo
)

logger = logging.getLogger(__name__)


class RoadmapCostCalculationService:
    """Service for calculating roadmap initiative costs with regional rates and scenarios"""
    
    def __init__(self):
        self._regional_rates = self._initialize_regional_rates()
        self._scenario_multipliers = ScenarioMultipliers()
        self._t_shirt_mappings = self._initialize_t_shirt_mappings()
        self._last_updated = datetime.utcnow()
        self._updated_by = "system"
    
    def _initialize_regional_rates(self) -> Dict[Region, RegionalRates]:
        """Initialize default regional rates"""
        return {
            Region.US_EAST: RegionalRates(
                senior_consultant=175.0,
                consultant=150.0,
                analyst=125.0,
                project_manager=160.0,
                architect=190.0
            ),
            Region.US_WEST: RegionalRates(
                senior_consultant=185.0,
                consultant=160.0,
                analyst=135.0,
                project_manager=170.0,
                architect=200.0
            ),
            Region.EU_WEST: RegionalRates(
                senior_consultant=165.0,
                consultant=140.0,
                analyst=115.0,
                project_manager=150.0,
                architect=180.0
            ),
            Region.ASIA_PACIFIC: RegionalRates(
                senior_consultant=155.0,
                consultant=130.0,
                analyst=105.0,
                project_manager=140.0,
                architect=170.0
            ),
            Region.INDIA: RegionalRates(
                senior_consultant=95.0,
                consultant=75.0,
                analyst=55.0,
                project_manager=85.0,
                architect=110.0
            )
        }
    
    def _initialize_t_shirt_mappings(self) -> List[TSizeCostMapping]:
        """Initialize default T-shirt size to cost mappings"""
        return [
            TSizeCostMapping(
                size=TShirtSize.S,
                min_cost=25000,
                max_cost=75000,
                typical_cost=50000,
                labor_weeks=4.0,
                description="Small initiatives: minor configurations, single tool implementations, basic training"
            ),
            TSizeCostMapping(
                size=TShirtSize.M,
                min_cost=75000,
                max_cost=200000,
                typical_cost=125000,
                labor_weeks=12.0,
                description="Medium initiatives: multi-tool integrations, moderate process changes, departmental rollouts"
            ),
            TSizeCostMapping(
                size=TShirtSize.L,
                min_cost=200000,
                max_cost=500000,
                typical_cost=300000,
                labor_weeks=24.0,
                description="Large initiatives: enterprise-wide implementations, major process redesign, complex integrations"
            ),
            TSizeCostMapping(
                size=TShirtSize.XL,
                min_cost=500000,
                max_cost=1200000,
                typical_cost=750000,
                labor_weeks=48.0,
                description="Extra large initiatives: full digital transformation, multi-year programs, organization-wide change"
            )
        ]
    
    def calculate_labor_costs(
        self, 
        labor_costs: LaborCosts, 
        regional_rates: RegionalRates,
        scenario_multiplier: float = 1.0
    ) -> Tuple[LaborCosts, List[CostComponent]]:
        """Calculate labor costs with regional rates and scenario adjustments"""
        components = []
        
        # Calculate individual role costs
        senior_cost = labor_costs.senior_consultant_hours * regional_rates.senior_consultant
        consultant_cost = labor_costs.consultant_hours * regional_rates.consultant
        analyst_cost = labor_costs.analyst_hours * regional_rates.analyst
        pm_cost = labor_costs.project_manager_hours * regional_rates.project_manager
        architect_cost = labor_costs.architect_hours * regional_rates.architect
        
        # Apply scenario multiplier
        senior_cost *= scenario_multiplier
        consultant_cost *= scenario_multiplier
        analyst_cost *= scenario_multiplier
        pm_cost *= scenario_multiplier
        architect_cost *= scenario_multiplier
        
        # Create cost components
        if labor_costs.senior_consultant_hours > 0:
            components.append(CostComponent(
                category="labor",
                description="Senior Consultant",
                base_amount=labor_costs.senior_consultant_hours * regional_rates.senior_consultant,
                scenario_multiplier=scenario_multiplier,
                total_amount=senior_cost
            ))
        
        if labor_costs.consultant_hours > 0:
            components.append(CostComponent(
                category="labor", 
                description="Consultant",
                base_amount=labor_costs.consultant_hours * regional_rates.consultant,
                scenario_multiplier=scenario_multiplier,
                total_amount=consultant_cost
            ))
        
        if labor_costs.analyst_hours > 0:
            components.append(CostComponent(
                category="labor",
                description="Analyst",
                base_amount=labor_costs.analyst_hours * regional_rates.analyst,
                scenario_multiplier=scenario_multiplier,
                total_amount=analyst_cost
            ))
        
        if labor_costs.project_manager_hours > 0:
            components.append(CostComponent(
                category="labor",
                description="Project Manager", 
                base_amount=labor_costs.project_manager_hours * regional_rates.project_manager,
                scenario_multiplier=scenario_multiplier,
                total_amount=pm_cost
            ))
        
        if labor_costs.architect_hours > 0:
            components.append(CostComponent(
                category="labor",
                description="Solution Architect",
                base_amount=labor_costs.architect_hours * regional_rates.architect,
                scenario_multiplier=scenario_multiplier,
                total_amount=architect_cost
            ))
        
        # Calculate totals
        total_hours = (
            labor_costs.senior_consultant_hours + labor_costs.consultant_hours + 
            labor_costs.analyst_hours + labor_costs.project_manager_hours + 
            labor_costs.architect_hours
        )
        total_cost = senior_cost + consultant_cost + analyst_cost + pm_cost + architect_cost
        
        updated_labor = LaborCosts(
            senior_consultant_hours=labor_costs.senior_consultant_hours,
            consultant_hours=labor_costs.consultant_hours,
            analyst_hours=labor_costs.analyst_hours,
            project_manager_hours=labor_costs.project_manager_hours,
            architect_hours=labor_costs.architect_hours,
            total_hours=total_hours,
            total_cost=total_cost
        )
        
        return updated_labor, components
    
    def calculate_tooling_costs(
        self, 
        tooling_costs: ToolingCosts,
        scenario_multiplier: float = 1.0
    ) -> Tuple[ToolingCosts, List[CostComponent]]:
        """Calculate tooling costs with scenario adjustments"""
        components = []
        
        # Apply scenario multiplier to each component
        security_total = tooling_costs.security_tools * scenario_multiplier
        compliance_total = tooling_costs.compliance_tools * scenario_multiplier
        monitoring_total = tooling_costs.monitoring_tools * scenario_multiplier
        integration_total = tooling_costs.integration_tools * scenario_multiplier
        training_total = tooling_costs.training_materials * scenario_multiplier
        
        # Create cost components
        if tooling_costs.security_tools > 0:
            components.append(CostComponent(
                category="tooling",
                description="Security Tools",
                base_amount=tooling_costs.security_tools,
                scenario_multiplier=scenario_multiplier,
                total_amount=security_total
            ))
        
        if tooling_costs.compliance_tools > 0:
            components.append(CostComponent(
                category="tooling",
                description="Compliance Tools",
                base_amount=tooling_costs.compliance_tools,
                scenario_multiplier=scenario_multiplier,
                total_amount=compliance_total
            ))
        
        if tooling_costs.monitoring_tools > 0:
            components.append(CostComponent(
                category="tooling",
                description="Monitoring Tools",
                base_amount=tooling_costs.monitoring_tools,
                scenario_multiplier=scenario_multiplier,
                total_amount=monitoring_total
            ))
        
        if tooling_costs.integration_tools > 0:
            components.append(CostComponent(
                category="tooling",
                description="Integration Tools",
                base_amount=tooling_costs.integration_tools,
                scenario_multiplier=scenario_multiplier,
                total_amount=integration_total
            ))
        
        if tooling_costs.training_materials > 0:
            components.append(CostComponent(
                category="tooling",
                description="Training Materials",
                base_amount=tooling_costs.training_materials,
                scenario_multiplier=scenario_multiplier,
                total_amount=training_total
            ))
        
        total_cost = (
            security_total + compliance_total + monitoring_total + 
            integration_total + training_total
        )
        
        updated_tooling = ToolingCosts(
            security_tools=tooling_costs.security_tools,
            compliance_tools=tooling_costs.compliance_tools,
            monitoring_tools=tooling_costs.monitoring_tools,
            integration_tools=tooling_costs.integration_tools,
            training_materials=tooling_costs.training_materials,
            total_cost=total_cost
        )
        
        return updated_tooling, components
    
    def calculate_microsoft_costs(
        self,
        ms_costs: MicrosoftServicesCosts,
        scenario_multiplier: float = 1.0
    ) -> Tuple[MicrosoftServicesCosts, List[CostComponent]]:
        """Calculate Microsoft services costs with scenario adjustments"""
        components = []
        
        # Apply scenario multiplier
        azure_security_total = ms_costs.azure_security_services * scenario_multiplier
        m365_total = ms_costs.microsoft_365_licenses * scenario_multiplier
        azure_infra_total = ms_costs.azure_infrastructure * scenario_multiplier
        support_total = ms_costs.support_services * scenario_multiplier
        training_total = ms_costs.training_certification * scenario_multiplier
        
        # Create cost components
        if ms_costs.azure_security_services > 0:
            components.append(CostComponent(
                category="microsoft_services",
                description="Azure Security Services",
                base_amount=ms_costs.azure_security_services,
                scenario_multiplier=scenario_multiplier,
                total_amount=azure_security_total
            ))
        
        if ms_costs.microsoft_365_licenses > 0:
            components.append(CostComponent(
                category="microsoft_services",
                description="Microsoft 365 Licenses",
                base_amount=ms_costs.microsoft_365_licenses,
                scenario_multiplier=scenario_multiplier,
                total_amount=m365_total
            ))
        
        if ms_costs.azure_infrastructure > 0:
            components.append(CostComponent(
                category="microsoft_services",
                description="Azure Infrastructure",
                base_amount=ms_costs.azure_infrastructure,
                scenario_multiplier=scenario_multiplier,
                total_amount=azure_infra_total
            ))
        
        if ms_costs.support_services > 0:
            components.append(CostComponent(
                category="microsoft_services",
                description="Support Services",
                base_amount=ms_costs.support_services,
                scenario_multiplier=scenario_multiplier,
                total_amount=support_total
            ))
        
        if ms_costs.training_certification > 0:
            components.append(CostComponent(
                category="microsoft_services",
                description="Training & Certification",
                base_amount=ms_costs.training_certification,
                scenario_multiplier=scenario_multiplier,
                total_amount=training_total
            ))
        
        total_cost = (
            azure_security_total + m365_total + azure_infra_total + 
            support_total + training_total
        )
        
        updated_ms_costs = MicrosoftServicesCosts(
            azure_security_services=ms_costs.azure_security_services,
            microsoft_365_licenses=ms_costs.microsoft_365_licenses,
            azure_infrastructure=ms_costs.azure_infrastructure,
            support_services=ms_costs.support_services,
            training_certification=ms_costs.training_certification,
            total_cost=total_cost
        )
        
        return updated_ms_costs, components
    
    def get_scenario_multiplier(self, scenario: Scenario) -> float:
        """Get multiplier for cost scenario"""
        if scenario == Scenario.BASELINE:
            return self._scenario_multipliers.baseline
        elif scenario == Scenario.CONSTRAINED:
            return self._scenario_multipliers.constrained
        elif scenario == Scenario.ACCELERATED:
            return self._scenario_multipliers.accelerated
        else:
            return 1.0
    
    def get_t_shirt_mapping(self, size: TShirtSize) -> Optional[TSizeCostMapping]:
        """Get T-shirt size mapping"""
        for mapping in self._t_shirt_mappings:
            if mapping.size == size:
                return mapping
        return None
    
    def calculate_initiative_costs(
        self,
        initiative_data: Dict,
        region: Region,
        scenario: Scenario = Scenario.BASELINE,
        custom_rates: Optional[RegionalRates] = None
    ) -> InitiativeCostCalculation:
        """Calculate costs for a single initiative"""
        
        # Get rates and multipliers
        regional_rates = custom_rates if custom_rates else self._regional_rates[region]
        scenario_multiplier = self.get_scenario_multiplier(scenario)
        
        # Extract cost components from initiative data
        labor_costs = LaborCosts(**initiative_data.get('labor_costs', {}))
        tooling_costs = ToolingCosts(**initiative_data.get('tooling_costs', {}))
        ms_costs = MicrosoftServicesCosts(**initiative_data.get('microsoft_services_costs', {}))
        
        # Calculate costs for each category
        updated_labor, labor_components = self.calculate_labor_costs(
            labor_costs, regional_rates, scenario_multiplier
        )
        updated_tooling, tooling_components = self.calculate_tooling_costs(
            tooling_costs, scenario_multiplier
        )
        updated_ms_costs, ms_components = self.calculate_microsoft_costs(
            ms_costs, scenario_multiplier
        )
        
        # Calculate totals
        total_labor_cost = updated_labor.total_cost or 0
        total_tooling_cost = updated_tooling.total_cost or 0
        total_microsoft_cost = updated_ms_costs.total_cost or 0
        total_cost = total_labor_cost + total_tooling_cost + total_microsoft_cost
        
        # Combine all cost components
        all_components = labor_components + tooling_components + ms_components
        
        # Determine cost confidence based on T-shirt size
        t_shirt_size = TShirtSize(initiative_data.get('t_shirt_size', 'M'))
        size_mapping = self.get_t_shirt_mapping(t_shirt_size)
        
        if size_mapping:
            if size_mapping.min_cost <= total_cost <= size_mapping.max_cost:
                cost_confidence = "High"
            elif abs(total_cost - size_mapping.typical_cost) / size_mapping.typical_cost <= 0.3:
                cost_confidence = "Medium"
            else:
                cost_confidence = "Low"
        else:
            cost_confidence = "Unknown"
        
        logger.info(
            f"Calculated costs for initiative {initiative_data.get('initiative_id')}",
            extra={
                "total_cost": total_cost,
                "region": region.value,
                "scenario": scenario.value,
                "t_shirt_size": t_shirt_size.value,
                "cost_confidence": cost_confidence
            }
        )
        
        return InitiativeCostCalculation(
            initiative_id=initiative_data.get('initiative_id', ''),
            name=initiative_data.get('name', ''),
            t_shirt_size=t_shirt_size,
            region=region,
            scenario=scenario,
            labor_costs=updated_labor,
            tooling_costs=updated_tooling,
            microsoft_services_costs=updated_ms_costs,
            total_labor_cost=total_labor_cost,
            total_tooling_cost=total_tooling_cost,
            total_microsoft_cost=total_microsoft_cost,
            total_cost=total_cost,
            cost_components=all_components,
            cost_confidence=cost_confidence,
            size_justification=initiative_data.get('size_justification', f"{t_shirt_size.value} size initiative")
        )
    
    def calculate_portfolio_costs(self, request: CostCalculationRequest) -> CostCalculationResponse:
        """Calculate costs for multiple initiatives"""
        calculated_costs = []
        
        for initiative_data in request.initiatives:
            cost_calculation = self.calculate_initiative_costs(
                initiative_data,
                request.region,
                request.scenario,
                request.custom_rates
            )
            calculated_costs.append(cost_calculation)
        
        # Calculate portfolio totals
        total_portfolio_cost = sum(calc.total_cost for calc in calculated_costs)
        
        # Generate summary statistics
        calculation_summary = {
            "total_initiatives": len(calculated_costs),
            "total_labor_cost": sum(calc.total_labor_cost for calc in calculated_costs),
            "total_tooling_cost": sum(calc.total_tooling_cost for calc in calculated_costs),
            "total_microsoft_cost": sum(calc.total_microsoft_cost for calc in calculated_costs),
            "average_initiative_cost": total_portfolio_cost / len(calculated_costs) if calculated_costs else 0,
            "cost_by_size": self._summarize_costs_by_size(calculated_costs),
            "confidence_distribution": self._summarize_confidence_distribution(calculated_costs)
        }
        
        logger.info(
            f"Calculated portfolio costs for {len(calculated_costs)} initiatives",
            extra={
                "total_portfolio_cost": total_portfolio_cost,
                "region": request.region.value,
                "scenario": request.scenario.value
            }
        )
        
        return CostCalculationResponse(
            calculated_costs=calculated_costs,
            regional_rates_used=request.custom_rates or self._regional_rates[request.region],
            scenario_multipliers={
                "baseline": self._scenario_multipliers.baseline,
                "constrained": self._scenario_multipliers.constrained,
                "accelerated": self._scenario_multipliers.accelerated
            },
            total_portfolio_cost=total_portfolio_cost,
            calculation_summary=calculation_summary
        )
    
    def _summarize_costs_by_size(self, calculations: List[InitiativeCostCalculation]) -> Dict:
        """Summarize costs by T-shirt size"""
        summary = {}
        for calc in calculations:
            size = calc.t_shirt_size.value
            if size not in summary:
                summary[size] = {"count": 0, "total_cost": 0}
            summary[size]["count"] += 1
            summary[size]["total_cost"] += calc.total_cost
        return summary
    
    def _summarize_confidence_distribution(self, calculations: List[InitiativeCostCalculation]) -> Dict:
        """Summarize confidence level distribution"""
        summary = {}
        for calc in calculations:
            confidence = calc.cost_confidence
            summary[confidence] = summary.get(confidence, 0) + 1
        return summary
    
    def get_configuration_info(self) -> CostConfigurationInfo:
        """Get current cost calculation configuration"""
        return CostConfigurationInfo(
            regional_rates=self._regional_rates,
            scenario_multipliers=self._scenario_multipliers,
            default_t_shirt_mappings=self._t_shirt_mappings
        )
    
    def update_t_shirt_mappings(self, mappings: List[TSizeCostMapping], updated_by: str = "unknown") -> None:
        """Update T-shirt size mappings"""
        self._t_shirt_mappings = mappings
        self._last_updated = datetime.utcnow()
        self._updated_by = updated_by
        
        logger.info(
            "Updated T-shirt size mappings",
            extra={
                "mapping_count": len(mappings),
                "updated_by": updated_by
            }
        )


# Global service instance
roadmap_cost_service = RoadmapCostCalculationService()