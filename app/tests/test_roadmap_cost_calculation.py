"""Unit tests for roadmap cost calculation service"""
import pytest
from datetime import datetime
from app.api.schemas.roadmap_costs import (
    TShirtSize, Scenario, Region, RegionalRates, CostComponent,
    LaborCosts, ToolingCosts, MicrosoftServicesCosts, TSizeCostMapping,
    CostCalculationRequest, CostCalculationResponse, ScenarioMultipliers
)
from app.services.roadmap_cost_calculation import RoadmapCostCalculationService


class TestRegionalRates:
    """Test regional rates validation and configuration"""
    
    def test_valid_regional_rates(self):
        """Test creating valid regional rates"""
        rates = RegionalRates(
            senior_consultant=175.0,
            consultant=150.0,
            analyst=125.0,
            project_manager=160.0,
            architect=190.0
        )
        assert rates.senior_consultant == 175.0
        assert rates.architect == 190.0

    def test_rate_bounds(self):
        """Test that rates must be non-negative"""
        with pytest.raises(ValueError):
            RegionalRates(
                senior_consultant=-10.0,
                consultant=150.0,
                analyst=125.0,
                project_manager=160.0,
                architect=190.0
            )


class TestTSizeCostMapping:
    """Test T-shirt size cost mapping validation"""
    
    def test_valid_mapping(self):
        """Test creating valid T-shirt size mapping"""
        mapping = TSizeCostMapping(
            size=TShirtSize.M,
            min_cost=75000,
            max_cost=200000,
            typical_cost=125000,
            labor_weeks=12.0,
            description="Medium initiatives"
        )
        assert mapping.size == TShirtSize.M
        assert mapping.typical_cost == 125000
    
    def test_max_cost_validation(self):
        """Test that max_cost must be >= min_cost"""
        with pytest.raises(ValueError, match="max_cost must be greater than or equal to min_cost"):
            TSizeCostMapping(
                size=TShirtSize.M,
                min_cost=200000,
                max_cost=75000,  # Invalid: less than min_cost
                typical_cost=125000,
                labor_weeks=12.0,
                description="Invalid mapping"
            )
    
    def test_typical_cost_validation(self):
        """Test that typical_cost must be between min and max"""
        with pytest.raises(ValueError, match="typical_cost must be between min_cost and max_cost"):
            TSizeCostMapping(
                size=TShirtSize.M,
                min_cost=75000,
                max_cost=200000,
                typical_cost=250000,  # Invalid: greater than max_cost
                labor_weeks=12.0,
                description="Invalid mapping"
            )


class TestCostComponents:
    """Test cost component models"""
    
    def test_labor_costs(self):
        """Test labor costs model"""
        labor = LaborCosts(
            senior_consultant_hours=40,
            consultant_hours=80,
            analyst_hours=60,
            project_manager_hours=20,
            architect_hours=30
        )
        assert labor.senior_consultant_hours == 40
        assert labor.total_hours is None  # Calculated by service
    
    def test_tooling_costs(self):
        """Test tooling costs model"""
        tooling = ToolingCosts(
            security_tools=25000,
            compliance_tools=15000,
            monitoring_tools=10000,
            integration_tools=8000,
            training_materials=5000
        )
        assert tooling.security_tools == 25000
        assert tooling.total_cost is None  # Calculated by service
    
    def test_microsoft_services_costs(self):
        """Test Microsoft services costs model"""
        ms_costs = MicrosoftServicesCosts(
            azure_security_services=30000,
            microsoft_365_licenses=20000,
            azure_infrastructure=15000,
            support_services=10000,
            training_certification=5000
        )
        assert ms_costs.azure_security_services == 30000
        assert ms_costs.total_cost is None  # Calculated by service


class TestRoadmapCostCalculationService:
    """Test roadmap cost calculation service functionality"""
    
    def setup_method(self):
        """Set up test service instance"""
        self.service = RoadmapCostCalculationService()
    
    def test_initialization(self):
        """Test service initialization with default values"""
        assert len(self.service._regional_rates) == 5  # All regions
        assert Region.US_EAST in self.service._regional_rates
        assert len(self.service._t_shirt_mappings) == 4  # All T-shirt sizes
        assert self.service._scenario_multipliers.baseline == 1.0
    
    def test_calculate_labor_costs_basic(self):
        """Test basic labor cost calculation"""
        labor_costs = LaborCosts(
            senior_consultant_hours=40,
            consultant_hours=80,
            analyst_hours=60
        )
        
        regional_rates = self.service._regional_rates[Region.US_EAST]
        
        updated_labor, components = self.service.calculate_labor_costs(
            labor_costs, regional_rates
        )
        
        # Verify calculation
        expected_senior_cost = 40 * 175.0  # US_EAST senior consultant rate
        expected_consultant_cost = 80 * 150.0  # US_EAST consultant rate
        expected_analyst_cost = 60 * 125.0  # US_EAST analyst rate
        expected_total = expected_senior_cost + expected_consultant_cost + expected_analyst_cost
        
        assert updated_labor.total_cost == expected_total
        assert updated_labor.total_hours == 180  # 40 + 80 + 60
        assert len(components) == 3  # Only populated roles
    
    def test_calculate_labor_costs_with_scenario(self):
        """Test labor cost calculation with scenario multiplier"""
        labor_costs = LaborCosts(senior_consultant_hours=40)
        regional_rates = self.service._regional_rates[Region.US_EAST]
        scenario_multiplier = 1.3  # Accelerated scenario
        
        updated_labor, components = self.service.calculate_labor_costs(
            labor_costs, regional_rates, scenario_multiplier
        )
        
        expected_cost = 40 * 175.0 * 1.3
        assert updated_labor.total_cost == expected_cost
        assert components[0].scenario_multiplier == 1.3
        assert components[0].total_amount == expected_cost
    
    def test_calculate_tooling_costs(self):
        """Test tooling cost calculation"""
        tooling_costs = ToolingCosts(
            security_tools=25000,
            compliance_tools=15000,
            monitoring_tools=10000
        )
        
        updated_tooling, components = self.service.calculate_tooling_costs(tooling_costs)
        
        expected_total = 25000 + 15000 + 10000
        assert updated_tooling.total_cost == expected_total
        assert len(components) == 3  # Only populated tools
    
    def test_calculate_microsoft_costs(self):
        """Test Microsoft services cost calculation"""
        ms_costs = MicrosoftServicesCosts(
            azure_security_services=30000,
            microsoft_365_licenses=20000
        )
        
        updated_ms_costs, components = self.service.calculate_microsoft_costs(ms_costs)
        
        expected_total = 30000 + 20000
        assert updated_ms_costs.total_cost == expected_total
        assert len(components) == 2  # Only populated services
    
    def test_get_scenario_multiplier(self):
        """Test scenario multiplier retrieval"""
        assert self.service.get_scenario_multiplier(Scenario.BASELINE) == 1.0
        assert self.service.get_scenario_multiplier(Scenario.CONSTRAINED) == 0.8
        assert self.service.get_scenario_multiplier(Scenario.ACCELERATED) == 1.3
    
    def test_get_t_shirt_mapping(self):
        """Test T-shirt size mapping retrieval"""
        mapping = self.service.get_t_shirt_mapping(TShirtSize.M)
        assert mapping is not None
        assert mapping.size == TShirtSize.M
        assert mapping.min_cost == 75000
        assert mapping.max_cost == 200000
    
    def test_calculate_initiative_costs_basic(self):
        """Test basic initiative cost calculation"""
        initiative_data = {
            'initiative_id': 'test-001',
            'name': 'Test Initiative',
            't_shirt_size': 'M',
            'labor_costs': {
                'senior_consultant_hours': 40,
                'consultant_hours': 80
            },
            'tooling_costs': {
                'security_tools': 25000
            },
            'microsoft_services_costs': {
                'azure_security_services': 30000
            }
        }
        
        result = self.service.calculate_initiative_costs(
            initiative_data, Region.US_EAST, Scenario.BASELINE
        )
        
        # Verify basic properties
        assert result.initiative_id == 'test-001'
        assert result.t_shirt_size == TShirtSize.M
        assert result.region == Region.US_EAST
        assert result.scenario == Scenario.BASELINE
        
        # Verify cost components are populated
        assert result.total_labor_cost > 0
        assert result.total_tooling_cost == 25000
        assert result.total_microsoft_cost == 30000
        assert result.total_cost > 0
        
        # Verify cost confidence is calculated
        assert result.cost_confidence in ["High", "Medium", "Low", "Unknown"]
    
    def test_calculate_initiative_costs_with_scenario(self):
        """Test initiative cost calculation with different scenarios"""
        initiative_data = {
            'initiative_id': 'test-002',
            'name': 'Test Initiative',
            't_shirt_size': 'L',
            'labor_costs': {'senior_consultant_hours': 100},
            'tooling_costs': {'security_tools': 50000},
            'microsoft_services_costs': {'azure_security_services': 40000}
        }
        
        # Calculate for different scenarios
        baseline_result = self.service.calculate_initiative_costs(
            initiative_data, Region.US_EAST, Scenario.BASELINE
        )
        
        accelerated_result = self.service.calculate_initiative_costs(
            initiative_data, Region.US_EAST, Scenario.ACCELERATED
        )
        
        # Accelerated should cost more than baseline
        assert accelerated_result.total_cost > baseline_result.total_cost
        assert accelerated_result.total_labor_cost > baseline_result.total_labor_cost
    
    def test_calculate_portfolio_costs(self):
        """Test portfolio cost calculation"""
        initiatives = [
            {
                'initiative_id': 'init-001',
                'name': 'Initiative 1',
                't_shirt_size': 'S',
                'labor_costs': {'consultant_hours': 40},
                'tooling_costs': {'security_tools': 10000},
                'microsoft_services_costs': {'azure_security_services': 15000}
            },
            {
                'initiative_id': 'init-002',
                'name': 'Initiative 2',
                't_shirt_size': 'M',
                'labor_costs': {'senior_consultant_hours': 60},
                'tooling_costs': {'compliance_tools': 20000},
                'microsoft_services_costs': {'microsoft_365_licenses': 25000}
            }
        ]
        
        request = CostCalculationRequest(
            initiatives=initiatives,
            region=Region.US_EAST,
            scenario=Scenario.BASELINE
        )
        
        response = self.service.calculate_portfolio_costs(request)
        
        assert len(response.calculated_costs) == 2
        assert response.total_portfolio_cost > 0
        assert "total_initiatives" in response.calculation_summary
        assert response.calculation_summary["total_initiatives"] == 2
        
        # Verify summary includes cost breakdown
        assert "total_labor_cost" in response.calculation_summary
        assert "total_tooling_cost" in response.calculation_summary
        assert "total_microsoft_cost" in response.calculation_summary
        assert "cost_by_size" in response.calculation_summary
        assert "confidence_distribution" in response.calculation_summary
    
    def test_cost_confidence_calculation(self):
        """Test cost confidence level calculation"""
        # Small initiative with typical cost should have high confidence
        small_initiative = {
            'initiative_id': 'small-001',
            'name': 'Small Initiative',
            't_shirt_size': 'S',
            'labor_costs': {'consultant_hours': 40},  # ~$6,000
            'tooling_costs': {'security_tools': 20000},
            'microsoft_services_costs': {'azure_security_services': 20000}
        }
        
        result = self.service.calculate_initiative_costs(
            small_initiative, Region.US_EAST, Scenario.BASELINE
        )
        
        # Should be within S range (25k-75k) so medium/high confidence
        assert result.cost_confidence in ["High", "Medium"]
        assert result.total_cost >= 25000  # Above minimum for S
    
    def test_update_t_shirt_mappings(self):
        """Test updating T-shirt size mappings"""
        new_mappings = [
            TSizeCostMapping(
                size=TShirtSize.S,
                min_cost=30000,  # Updated minimum
                max_cost=80000,
                typical_cost=55000,
                labor_weeks=5.0,
                description="Updated small initiatives"
            )
        ]
        
        original_count = len(self.service._t_shirt_mappings)
        self.service.update_t_shirt_mappings(new_mappings, "test-user")
        
        # Verify update
        assert len(self.service._t_shirt_mappings) == 1
        assert self.service._t_shirt_mappings[0].min_cost == 30000
        assert self.service._updated_by == "test-user"
    
    def test_get_configuration_info(self):
        """Test retrieving configuration information"""
        config = self.service.get_configuration_info()
        
        assert len(config.regional_rates) == 5
        assert config.scenario_multipliers.baseline == 1.0
        assert len(config.default_t_shirt_mappings) == 4
        assert "cost =" in config.cost_formula_description
        assert config.schema_version == "v2.0"


class TestCostCalculationRequest:
    """Test cost calculation request validation"""
    
    def test_valid_request(self):
        """Test creating a valid cost calculation request"""
        initiatives = [
            {
                'initiative_id': 'test-001',
                'name': 'Test Initiative',
                't_shirt_size': 'M'
            }
        ]
        
        request = CostCalculationRequest(
            initiatives=initiatives,
            region=Region.US_EAST,
            scenario=Scenario.BASELINE
        )
        
        assert len(request.initiatives) == 1
        assert request.region == Region.US_EAST
        assert request.scenario == Scenario.BASELINE
    
    def test_custom_rates(self):
        """Test request with custom regional rates"""
        custom_rates = RegionalRates(
            senior_consultant=200.0,
            consultant=175.0,
            analyst=150.0,
            project_manager=180.0,
            architect=220.0
        )
        
        request = CostCalculationRequest(
            initiatives=[{}],
            region=Region.US_EAST,
            custom_rates=custom_rates
        )
        
        assert request.custom_rates.senior_consultant == 200.0


class TestIntegrationScenarios:
    """Test realistic integration scenarios"""
    
    def setup_method(self):
        """Set up test service instance"""
        self.service = RoadmapCostCalculationService()
    
    def test_cybersecurity_transformation_portfolio(self):
        """Test calculating costs for a cybersecurity transformation portfolio"""
        initiatives = [
            # Large infrastructure security upgrade
            {
                'initiative_id': 'sec-001',
                'name': 'Infrastructure Security Upgrade',
                't_shirt_size': 'L',
                'labor_costs': {
                    'senior_consultant_hours': 200,
                    'consultant_hours': 300,
                    'architect_hours': 100
                },
                'tooling_costs': {
                    'security_tools': 150000,
                    'monitoring_tools': 75000
                },
                'microsoft_services_costs': {
                    'azure_security_services': 100000,
                    'support_services': 50000
                }
            },
            # Medium compliance implementation
            {
                'initiative_id': 'comp-001',
                'name': 'SOC 2 Compliance Implementation',
                't_shirt_size': 'M',
                'labor_costs': {
                    'senior_consultant_hours': 80,
                    'consultant_hours': 120,
                    'project_manager_hours': 40
                },
                'tooling_costs': {
                    'compliance_tools': 50000,
                    'training_materials': 15000
                },
                'microsoft_services_costs': {
                    'microsoft_365_licenses': 30000,
                    'training_certification': 20000
                }
            },
            # Small security awareness training
            {
                'initiative_id': 'train-001',
                'name': 'Security Awareness Training',
                't_shirt_size': 'S',
                'labor_costs': {
                    'consultant_hours': 60,
                    'analyst_hours': 40
                },
                'tooling_costs': {
                    'training_materials': 25000
                },
                'microsoft_services_costs': {
                    'training_certification': 15000
                }
            }
        ]
        
        # Test different scenarios
        for scenario in [Scenario.BASELINE, Scenario.CONSTRAINED, Scenario.ACCELERATED]:
            request = CostCalculationRequest(
                initiatives=initiatives,
                region=Region.US_EAST,
                scenario=scenario
            )
            
            response = self.service.calculate_portfolio_costs(request)
            
            # Verify portfolio results
            assert len(response.calculated_costs) == 3
            assert response.total_portfolio_cost > 0
            
            # Verify cost distribution by size
            size_summary = response.calculation_summary["cost_by_size"]
            assert "S" in size_summary
            assert "M" in size_summary  
            assert "L" in size_summary
            
            # Large initiatives should cost more than small ones
            large_init = next(calc for calc in response.calculated_costs if calc.t_shirt_size == TShirtSize.L)
            small_init = next(calc for calc in response.calculated_costs if calc.t_shirt_size == TShirtSize.S)
            assert large_init.total_cost > small_init.total_cost
    
    def test_regional_cost_differences(self):
        """Test that different regions produce different costs"""
        initiative_data = {
            'initiative_id': 'region-test',
            'name': 'Regional Cost Test',
            't_shirt_size': 'M',
            'labor_costs': {
                'senior_consultant_hours': 100,
                'consultant_hours': 100
            }
        }
        
        # Calculate for different regions
        us_east_result = self.service.calculate_initiative_costs(
            initiative_data, Region.US_EAST, Scenario.BASELINE
        )
        
        india_result = self.service.calculate_initiative_costs(
            initiative_data, Region.INDIA, Scenario.BASELINE
        )
        
        # India should be less expensive than US East
        assert india_result.total_labor_cost < us_east_result.total_labor_cost
        assert india_result.total_cost < us_east_result.total_cost
        
        # But tooling costs should be the same (not region-dependent)
        initiative_with_tooling = {
            **initiative_data,
            'tooling_costs': {'security_tools': 50000}
        }
        
        us_with_tooling = self.service.calculate_initiative_costs(
            initiative_with_tooling, Region.US_EAST, Scenario.BASELINE
        )
        
        india_with_tooling = self.service.calculate_initiative_costs(
            initiative_with_tooling, Region.INDIA, Scenario.BASELINE
        )
        
        # Tooling costs should be identical
        assert us_with_tooling.total_tooling_cost == india_with_tooling.total_tooling_cost


class TestSnapshotScenarios:
    """Test snapshot scenarios for cost calculation consistency"""
    
    def setup_method(self):
        """Set up test service instance"""
        self.service = RoadmapCostCalculationService()
    
    def test_cost_calculation_snapshot(self):
        """Test that cost calculations remain consistent (snapshot test)"""
        # Define a standard test scenario
        initiative_data = {
            'initiative_id': 'snapshot-001',
            'name': 'Snapshot Test Initiative',
            't_shirt_size': 'M',
            'labor_costs': {
                'senior_consultant_hours': 80,
                'consultant_hours': 120,
                'analyst_hours': 60,
                'project_manager_hours': 40,
                'architect_hours': 20
            },
            'tooling_costs': {
                'security_tools': 50000,
                'compliance_tools': 30000,
                'monitoring_tools': 20000
            },
            'microsoft_services_costs': {
                'azure_security_services': 40000,
                'microsoft_365_licenses': 25000,
                'azure_infrastructure': 35000
            }
        }
        
        result = self.service.calculate_initiative_costs(
            initiative_data, Region.US_EAST, Scenario.BASELINE
        )
        
        # Expected values based on US_EAST rates and baseline scenario
        # Labor: 80*175 + 120*150 + 60*125 + 40*160 + 20*190 = 57,700
        # Tooling: 50,000 + 30,000 + 20,000 = 100,000
        # Microsoft: 40,000 + 25,000 + 35,000 = 100,000
        # Total: 257,700
        
        assert abs(result.total_labor_cost - 57700) < 1  # Allow for floating point precision
        assert result.total_tooling_cost == 100000
        assert result.total_microsoft_cost == 100000
        assert abs(result.total_cost - 257700) < 1
        
        # Verify T-shirt size confidence
        # Medium range is 75k-200k, so 257.7k should be "Low" confidence
        assert result.cost_confidence == "Low"
    
    def test_scenario_multiplier_snapshot(self):
        """Test that scenario multipliers work consistently"""
        initiative_data = {
            'initiative_id': 'scenario-test',
            'name': 'Scenario Test',
            't_shirt_size': 'S',
            'labor_costs': {'consultant_hours': 40},  # 40 * 150 = 6,000
            'tooling_costs': {'security_tools': 20000},
            'microsoft_services_costs': {'azure_security_services': 20000}
        }
        
        baseline = self.service.calculate_initiative_costs(
            initiative_data, Region.US_EAST, Scenario.BASELINE
        )
        
        constrained = self.service.calculate_initiative_costs(
            initiative_data, Region.US_EAST, Scenario.CONSTRAINED
        )
        
        accelerated = self.service.calculate_initiative_costs(
            initiative_data, Region.US_EAST, Scenario.ACCELERATED
        )
        
        # Expected values:
        # Baseline: 6,000 + 20,000 + 20,000 = 46,000
        # Constrained: (6,000 + 20,000 + 20,000) * 0.8 = 36,800
        # Accelerated: (6,000 + 20,000 + 20,000) * 1.3 = 59,800
        
        assert abs(baseline.total_cost - 46000) < 1
        assert abs(constrained.total_cost - 36800) < 1
        assert abs(accelerated.total_cost - 59800) < 1